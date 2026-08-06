# Classification/semantic_matcher.py
"""
MiniLM-based hierarchical semantic matcher with document chunking.

Match Excerpts come from the FCP hierarchy descriptions (fcp_CSV-UTF.csv),
not from the document. For each matched row we rank the description
sentences by similarity to the document and keep the top ~500 characters.

Six excerpt columns are always produced (EN + FR):
  Function_Match_Excerpt_EN / _FR
  Sub_Function_Match_Excerpt_EN / _FR
  Records_Match_Excerpt_EN / _FR   (sourced from Business_Process_EN / _FR)
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Chunking (document side – used only for classification scoring)
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    max_chars: int = 450,      # ~90–110 tokens for MiniLM
    overlap_chars: int = 100,  # ~20–25 tokens
) -> list[dict]:
    """
    Split text into overlapping character windows.
    Returns list of {"text": str, "start": int, "end": int}.
    """
    text = text.strip()
    if not text:
        return []

    if len(text) <= max_chars:
        return [{"text": text, "start": 0, "end": len(text)}]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))

        if end < len(text):
            window = text[start:end]
            for sep in [". ", "? ", "! ", "\n\n", "\n"]:
                pos = window.rfind(sep)
                if pos > max_chars * 0.4:
                    end = start + pos + len(sep)
                    break

        chunk_text_ = text[start:end].strip()
        if chunk_text_:
            chunks.append({"text": chunk_text_, "start": start, "end": end})

        if end >= len(text):
            break
        start = max(start + 1, end - overlap_chars)

    return chunks


# ---------------------------------------------------------------------------
# Hierarchy-description excerpt helpers
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    """Split a hierarchy description into short sentences / clauses."""
    if not text or not str(text).strip():
        return []
    text = str(text).strip()
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) > 15]


def _top_matching_excerpt(
    description: str,
    doc_embedding,
    embedder,
    max_chars: int = 500,
) -> str:
    """
    From a hierarchy description, keep the sentences most similar
    to the document embedding, up to max_chars.
    """
    sentences = _split_sentences(description)
    if not sentences:
        raw = (description or "").strip()
        return raw[:max_chars]

    sent_embs = embedder.encode(
        sentences,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    doc_vec = np.asarray(doc_embedding, dtype=np.float32).reshape(1, -1)
    scores = cosine_similarity(doc_vec, sent_embs)[0]

    ranked = sorted(
        zip(scores, sentences),
        key=lambda x: float(x[0]),
        reverse=True,
    )

    chosen: list[str] = []
    length = 0
    for _score, sent in ranked:
        if length + len(sent) + 1 > max_chars and chosen:
            break
        chosen.append(sent)
        length += len(sent) + 1

    return " ".join(chosen).strip()[:max_chars]


# ---------------------------------------------------------------------------
# Main matcher
# ---------------------------------------------------------------------------

def semantic_match(
    text: str,
    hierarchy_df: pd.DataFrame,
    indexes: dict[str, np.ndarray],
    embedder,
    min_confidence: float = 0.22,
    high_threshold: float = 0.55,
    medium_threshold: float = 0.35,
    excerpt_length: int = 500,
) -> dict:
    """
    Hierarchical semantic classification of one document.

    Returns hierarchy fields + six Match Excerpt columns (EN/FR)
    + confidence scores.
    """
    text = (text or "").strip()
    if len(text) < 40 or hierarchy_df.empty or embedder is None:
        return _fallback_unknown()

    # ---- Chunk + embed document ----
    chunks = chunk_text(text)
    if not chunks:
        return _fallback_unknown()

    chunk_texts = [c["text"] for c in chunks]
    chunk_embs = embedder.encode(
        chunk_texts,
        normalize_embeddings=True,
        batch_size=32,
        show_progress_bar=False,
    )
    chunk_embs = np.asarray(chunk_embs, dtype=np.float32)

    # Document vector used later to rank hierarchy sentences
    doc_vec = chunk_embs.mean(axis=0)

    # ---- Stage 1: Function ----
    func_index = indexes.get("function")
    if func_index is None or len(func_index) == 0:
        return _fallback_unknown()

    sims = cosine_similarity(chunk_embs, func_index)  # (n_chunks, n_rows)
    flat_idx = int(np.argmax(sims))
    best_chunk_idx, best_row_idx = np.unravel_index(flat_idx, sims.shape)
    conf = float(sims[best_chunk_idx, best_row_idx])

    if conf < min_confidence:
        logger.info(f"Function confidence too low ({conf:.3f}) → Unknown")
        return _fallback_unknown()

    best_row = hierarchy_df.iloc[int(best_row_idx)]

    # ---- Stage 2: Sub-Function (restricted to same Function_EN) ----
    sub_conf = 0.0
    function_name = best_row.get("Function_EN", "")

    sub_mask = hierarchy_df["Function_EN"] == function_name
    sub_candidates = hierarchy_df[sub_mask]

    if not sub_candidates.empty and "sub_function" in indexes:
        sub_indices = np.where(sub_mask.values)[0]
        sub_embs = indexes["sub_function"][sub_indices]

        sub_sims = cosine_similarity(chunk_embs, sub_embs)
        sub_flat = int(np.argmax(sub_sims))
        sub_chunk_i, sub_local_i = np.unravel_index(sub_flat, sub_sims.shape)
        sub_conf = float(sub_sims[sub_chunk_i, sub_local_i])

        if sub_conf >= min_confidence:
            sub_row_idx = int(sub_indices[sub_local_i])
            best_row = hierarchy_df.iloc[sub_row_idx]  # refine to best sub-row

    # ---- Six Match Excerpts from hierarchy descriptions ----
    func_excerpt_en = _top_matching_excerpt(
        best_row.get("Function_Desc_EN", ""), doc_vec, embedder, excerpt_length
    )
    func_excerpt_fr = _top_matching_excerpt(
        best_row.get("Function_Desc_FR", ""), doc_vec, embedder, excerpt_length
    )
    sub_excerpt_en = _top_matching_excerpt(
        best_row.get("Sub-Function_Desc_EN", ""), doc_vec, embedder, excerpt_length
    )
    sub_excerpt_fr = _top_matching_excerpt(
        best_row.get("Sub-Function_Desc_FR", ""), doc_vec, embedder, excerpt_length
    )
    # Records excerpts intentionally use Business_Process_* columns
    records_excerpt_en = _top_matching_excerpt(
        best_row.get("Business_Process_EN", ""), doc_vec, embedder, excerpt_length
    )
    records_excerpt_fr = _top_matching_excerpt(
        best_row.get("Business_Process_FR", ""), doc_vec, embedder, excerpt_length
    )

    # ---- Assemble result ----
    result = {
        "Function_EN": best_row.get("Function_EN", ""),
        "Function_FR": best_row.get("Function_FR", ""),
        "Function_Desc_Sum_EN": best_row.get("Function_Desc_Sum_EN", ""),
        "Function_Desc_Sum_FR": best_row.get("Function_Desc_Sum_FR", ""),
        "Sub-Function_EN": best_row.get("Sub-Function_EN", ""),
        "Sub-Function_FR": best_row.get("Sub-Function_FR", ""),
        "Sub-Function_Desc_Summ_EN": best_row.get("Sub-Function_Desc_Summ_EN", ""),
        "Sub-Function_Desc_Summ_FR": best_row.get("Sub-Function_Desc_Summ_FR", ""),
        "Business_Process_EN": best_row.get("Business_Process_EN", ""),
        "Business_Process_FR": best_row.get("Business_Process_FR", ""),
        "Full_File_Class_No": best_row.get("Full_File_Class_No", ""),
        "Records": best_row.get("Records", ""),
        "Retention Period": best_row.get("Retention Period", ""),
        "Retention Trigger": best_row.get("Retention Trigger", ""),
        # optional level numbers if you add columns later
        "File Class No - Level1": best_row.get("File Class No - Level1", ""),
        "File Class No - Level2": best_row.get("File Class No - Level2", ""),
        "File Class No - Level3": best_row.get("File Class No - Level3", ""),
        # excerpts (already computed above)
        "Function_Match_Excerpt_EN": func_excerpt_en,
        "Function_Match_Excerpt_FR": func_excerpt_fr,
        "Sub_Function_Match_Excerpt_EN": sub_excerpt_en,
        "Sub_Function_Match_Excerpt_FR": sub_excerpt_fr,
        "Records_Match_Excerpt_EN": records_excerpt_en,
        "Records_Match_Excerpt_FR": records_excerpt_fr,
        "overall_confidence": round(conf, 3),
        "sub_function_confidence": round(sub_conf, 3),
        "confidence_category": (
            "High" if conf >= high_threshold
            else "Medium" if conf >= medium_threshold
            else "Low"
        ),
        "needs_review": "No" if conf >= medium_threshold else "Yes",
    }

    logger.info(
        f"Match | conf={conf:.3f} | {result['Function_EN']} → "
        f"{result['Sub-Function_EN']} | review={result['needs_review']}"
    )
    return result


def _fallback_unknown() -> dict:
    return {
        "Function_EN": "Unknown",
        "Function_FR": "Inconnu",
        "Function_Desc_Sum_EN": "",
        "Function_Desc_Sum_FR": "",
        "Sub-Function_EN": "Unknown",
        "Sub-Function_FR": "Inconnu",
        "Sub-Function_Desc_Summ_EN": "",
        "Sub-Function_Desc_Summ_FR": "",
        "Business_Process_EN": "Unknown",
        "Business_Process_FR": "Inconnu",
        "Full_File_Class_No": "",
        "Records": "",
        "Retention Period": "",
        "Retention Trigger": "",
        "Function_Match_Excerpt_EN": "",
        "Function_Match_Excerpt_FR": "",
        "Sub_Function_Match_Excerpt_EN": "",
        "Sub_Function_Match_Excerpt_FR": "",
        "Records_Match_Excerpt_EN": "",
        "Records_Match_Excerpt_FR": "",
        "overall_confidence": 0.0,
        "sub_function_confidence": 0.0,
        "confidence_category": "Low",
        "needs_review": "Yes",
    }