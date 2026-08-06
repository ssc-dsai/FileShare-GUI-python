# Litigation/8_litigation_search.py
# Package → MiniLM vector search + BM25 on tombstone facts → Excel report
# Report includes Created By / Last Modified By from original files when available.

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from project_config import (
    EMBEDDING_MODEL_PATH,
    LITIGATION_INDEX_DIR,
    LITIGATION_REPORTS_DIR,
)
from Classification.semantic_matcher import chunk_text
from Litigation.utils.file_origin_meta import origin_metadata
from Litigation.utils.search_index import load_bm25_corpus, load_index
from Litigation.utils.tombstone_parse import (
    parse_tombstone_from_package,
    tokenize,
    tombstone_query_text,
)

LOG_DIR = LITIGATION_REPORTS_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"search_{datetime.now().strftime('%Y%m%d_%H%M')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("litigation_search")


def _normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return {k: 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def search_with_package(
    package_path: Path,
    top_k: int = 50,
    min_score: float = 0.22,
    hybrid_vector_weight: float = 0.6,
) -> Path | None:
    package_path = Path(package_path)
    if not package_path.is_file():
        logger.error(f"Package not found: {package_path}")
        print(f"ERROR: Package not found: {package_path}")
        return None

    logger.info("=" * 70)
    logger.info("LITIGATION SEARCH (MiniLM + BM25 tombstone)")
    logger.info(f"Package : {package_path}")
    logger.info(f"Index   : {LITIGATION_INDEX_DIR}")
    logger.info("=" * 70)

    package_text = package_path.read_text(encoding="utf-8", errors="replace")
    tomb = parse_tombstone_from_package(package_text)
    bm25_q = tombstone_query_text(tomb)
    logger.info(f"Tombstone fields used for BM25: {[k for k, v in tomb.items() if v]}")
    logger.info(f"BM25 query text: {bm25_q!r}")

    # ---------- Vector search (MiniLM) ----------
    embeddings, meta_rows, info = load_index(LITIGATION_INDEX_DIR)
    logger.info(f"Index info: {info}")

    if not EMBEDDING_MODEL_PATH.exists():
        raise FileNotFoundError(f"Embedding model not found: {EMBEDDING_MODEL_PATH}")

    embedder = SentenceTransformer(str(EMBEDDING_MODEL_PATH))
    query_chunks = chunk_text(package_text)
    if not query_chunks:
        logger.error("Package produced no query chunks.")
        return None

    q_texts = [c["text"] for c in query_chunks]
    q_embs = embedder.encode(
        q_texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False
    )
    q_embs = np.asarray(q_embs, dtype=np.float32)
    sims = cosine_similarity(q_embs, embeddings)
    best_per_index = sims.max(axis=0)

    vector_by_file: dict[str, dict] = {}
    for idx, score in enumerate(best_per_index):
        score = float(score)
        row = meta_rows[idx]
        fpath = row["file_path"]
        prev = vector_by_file.get(fpath)
        if prev is None or score > prev["vector_score"]:
            vector_by_file[fpath] = {
                "vector_score": score,
                "file_path": fpath,
                "file_name": row["file_name"],
                "snippet": row["text"][:500],
            }

    # ---------- BM25 on tombstone ----------
    bm25_by_file: dict[str, float] = {}
    matched_terms_by_file: dict[str, str] = {}

    if bm25_q.strip():
        try:
            tokenized_docs, doc_paths = load_bm25_corpus(LITIGATION_INDEX_DIR)
            bm25 = BM25Okapi(tokenized_docs)
            q_tokens = tokenize(bm25_q)
            raw_scores = bm25.get_scores(q_tokens)
            path_to_tokens = dict(zip(doc_paths, tokenized_docs))
            for path, sc in zip(doc_paths, raw_scores):
                sc = float(sc)
                if sc > 0:
                    bm25_by_file[path] = sc
                    doc_tok_set = set(path_to_tokens.get(path, []))
                    hit_terms = [t for t in q_tokens if t in doc_tok_set]
                    matched_terms_by_file[path] = ", ".join(sorted(set(hit_terms)))
            logger.info(f"BM25 positive hits: {len(bm25_by_file)}")
        except FileNotFoundError as e:
            logger.warning(str(e))
            logger.warning("Continuing with vector scores only. Rebuild index to enable BM25.")
    else:
        logger.info("No usable tombstone values (all Not Found / empty) — BM25 skipped.")

    # ---------- Merge + hybrid ----------
    all_paths = set(vector_by_file.keys()) | set(bm25_by_file.keys())
    norm_bm25 = _normalize_scores(bm25_by_file)
    vec_only = {p: vector_by_file[p]["vector_score"] for p in vector_by_file}
    norm_vec = _normalize_scores(vec_only)

    w_v = float(hybrid_vector_weight)
    w_b = 1.0 - w_v

    merged_rows = []
    for path in all_paths:
        v = vector_by_file.get(path, {})
        vector_score = float(v.get("vector_score", 0.0))
        bm25_score = float(bm25_by_file.get(path, 0.0))
        hybrid = w_v * norm_vec.get(path, 0.0) + w_b * norm_bm25.get(path, 0.0)

        if vector_score < min_score and bm25_score <= 0:
            continue

        origin = origin_metadata(Path(path))

        merged_rows.append({
            "vector_score": round(vector_score, 4),
            "bm25_score": round(bm25_score, 4),
            "hybrid_score": round(hybrid, 4),
            "matched_tombstone_terms": matched_terms_by_file.get(path, ""),
            "file_name": v.get("file_name") or Path(path).name,
            "file_path": path,
            "created_by": origin.get("created_by", ""),
            "last_modified_by": origin.get("last_modified_by", ""),
            "file_created": origin.get("file_created", ""),
            "file_modified": origin.get("file_modified", ""),
            "snippet": v.get("snippet", ""),
            "package": str(package_path),
            "package_name": package_path.stem,
            "searched_at": datetime.now().isoformat(timespec="seconds"),
            "tombstone_query": bm25_q,
        })

    ranked = sorted(
        merged_rows,
        key=lambda r: (r["hybrid_score"], r["vector_score"], r["bm25_score"]),
        reverse=True,
    )[:top_k]

    for i, r in enumerate(ranked, 1):
        r["rank"] = i

    logger.info(f"Report rows: {len(ranked)}")

    LITIGATION_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    report_path = LITIGATION_REPORTS_DIR / f"search_report_{package_path.stem}_{stamp}.xlsx"

    columns = [
        "rank",
        "hybrid_score",
        "vector_score",
        "bm25_score",
        "matched_tombstone_terms",
        "file_name",
        "file_path",
        "created_by",
        "last_modified_by",
        "file_created",
        "file_modified",
        "snippet",
        "tombstone_query",
        "package",
        "package_name",
        "searched_at",
    ]
    df = pd.DataFrame(ranked, columns=columns)
    df.to_excel(report_path, index=False, engine="openpyxl")
    csv_path = report_path.with_suffix(".csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    logger.info(f"Report: {report_path}")
    print("\n" + "=" * 70)
    print(f"Search complete | {len(ranked)} hits")
    print(f"Excel: {report_path}")
    print(f"CSV  : {csv_path}")
    print(f"Log  : {LOG_FILE}")
    if not bm25_q.strip():
        print("Note: BM25 skipped (no tombstone facts). Vector scores only.")
    print("=" * 70)
    return report_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    parser.add_argument("--top_k", type=int, default=50)
    parser.add_argument("--min_score", type=float, default=0.22)
    parser.add_argument(
        "--vector_weight",
        type=float,
        default=0.6,
        help="Hybrid weight for vector vs BM25 (0-1). Default 0.6 vector / 0.4 BM25",
    )
    args = parser.parse_args()
    search_with_package(
        Path(args.package),
        top_k=args.top_k,
        min_score=args.min_score,
        hybrid_vector_weight=args.vector_weight,
    )


if __name__ == "__main__":
    main()