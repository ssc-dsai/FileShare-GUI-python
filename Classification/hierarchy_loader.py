# Classification/hierarchy_loader.py
"""
Load and prepare the FCP hierarchy (fcp_CSV-UTF.csv) for semantic matching.

- Reads the official hierarchy CSV
- Builds clean searchable text per row (prefers summary, falls back to full description)
- Optionally caches hierarchy embeddings to disk for faster restarts
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# Columns we care about for matching and output
REQUIRED_COLS = [
    "Function_EN",
    "Function_FR",
    "Function_Desc_EN",
    "Function_Desc_FR",
    "Function_Desc_Sum_EN",
    "Function_Desc_Sum_FR",
    "Sub-Function_EN",
    "Sub-Function_FR",
    "Sub-Function_Desc_EN",
    "Sub-Function_Desc_FR",
    "Sub-Function_Desc_Summ_EN",
    "Sub-Function_Desc_Summ_FR",
    "Business_Process_EN",
    "Business_Process_FR",
    "Records",
    "Full_File_Class_No",
    "Retention Period",
    "Retention Trigger",
]


def load_hierarchy(csv_path: Path) -> pd.DataFrame:
    """
    Load the FCP hierarchy CSV and normalise column names / missing values.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Hierarchy CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    logger.info(f"Loaded hierarchy: {len(df)} rows from {csv_path.name}")

    # Ensure expected columns exist
    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = ""

    # Strip whitespace
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].fillna("").astype(str).str.strip()

    # Drop completely empty function rows
    df = df[df["Function_EN"].str.len() > 0].reset_index(drop=True)
    logger.info(f"Hierarchy rows after cleanup: {len(df)}")
    return df


def build_search_text(row: pd.Series, level: str = "function") -> str:
    """
    Build the text that will be embedded for a hierarchy row.

    Preference order:
      1. Short summary (if present)
      2. Full description
      3. Name only
    """
    if level == "function":
        summary = row.get("Function_Desc_Sum_EN", "") or ""
        full = row.get("Function_Desc_EN", "") or ""
        name = row.get("Function_EN", "") or ""
    elif level == "sub_function":
        summary = row.get("Sub-Function_Desc_Summ_EN", "") or ""
        full = row.get("Sub-Function_Desc_EN", "") or ""
        name = row.get("Sub-Function_EN", "") or ""
    else:  # business process / records
        summary = ""
        full = row.get("Records", "") or ""
        name = row.get("Business_Process_EN", "") or ""

    # Prefer concise summary when available; otherwise use full description
    text = summary.strip() if len(summary.strip()) > 40 else full.strip()
    if not text:
        text = name.strip()
    return text


def prepare_hierarchy_for_matching(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add helper columns used by the semantic matcher.
    """
    out = df.copy()
    out["_search_function"] = out.apply(lambda r: build_search_text(r, "function"), axis=1)
    out["_search_sub_function"] = out.apply(lambda r: build_search_text(r, "sub_function"), axis=1)
    out["_search_records"] = out.apply(lambda r: build_search_text(r, "records"), axis=1)
    return out


def embed_hierarchy_texts(
    texts: list[str],
    embedder,
    batch_size: int = 32,
) -> np.ndarray:
    """
    Embed a list of hierarchy description strings.
    Returns L2-normalised vectors.
    """
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)  # MiniLM-L12 dimension

    embeddings = embedder.encode(
        texts,
        normalize_embeddings=True,
        batch_size=batch_size,
        show_progress_bar=len(texts) > 50,
    )
    return np.asarray(embeddings, dtype=np.float32)


def load_or_build_hierarchy_index(
    csv_path: Path,
    embedder,
    cache_dir: Optional[Path] = None,
) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    """
    Load hierarchy + build (or load cached) embedding indexes.

    Returns
    -------
    hierarchy_df : prepared DataFrame
    indexes : {
        "function": np.ndarray,
        "sub_function": np.ndarray,
        "records": np.ndarray,
    }
    """
    df = load_hierarchy(csv_path)
    df = prepare_hierarchy_for_matching(df)

    cache_dir = Path(cache_dir) if cache_dir else None
    indexes: dict[str, np.ndarray] = {}

    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        readme_path = cache_dir / "README.txt"
        if not readme_path.exists():
            readme_path.write_text(
                "The three NumPy binary files are binary format for arrays "
                "(the embedding vectors). It is not executable machine code — "
                "it is just numeric data. It is safe to delete at any time but "
                "it helps speed up the classification. However we should\n\n"
                "* Keep it for normal use\n\n"
                "- Delete it only when the FCP hierarchy changes or the embedding model changes\n\n"
                "- It is local, offline, and not sent anywhere\n",
                encoding="utf-8",
            )

    for level, col in [
        ("function", "_search_function"),
        ("sub_function", "_search_sub_function"),
        ("records", "_search_records"),
    ]:
        cache_file = None
        if cache_dir is not None:
            cache_file = cache_dir / f"hierarchy_{level}_embeddings.npy"

        if cache_file is not None and cache_file.exists():
            logger.info(f"Loading cached {level} embeddings from {cache_file}")
            indexes[level] = np.load(cache_file)
        else:
            logger.info(f"Embedding hierarchy level: {level} ({len(df)} rows)...")
            texts = df[col].tolist()
            indexes[level] = embed_hierarchy_texts(texts, embedder)
            if cache_file is not None:
                np.save(cache_file, indexes[level])
                logger.info(f"Cached {level} embeddings → {cache_file}")

    return df, indexes