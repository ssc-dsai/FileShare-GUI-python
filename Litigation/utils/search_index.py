# Litigation/utils/search_index.py
"""On-disk index for litigation semantic search (local MiniLM)."""

from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

META_NAME = "chunks_meta.jsonl"
EMB_NAME = "chunks_embeddings.npy"
INFO_NAME = "index_info.json"
BM25_NAME = "bm25_corpus.pkl"


def index_paths(index_dir: Path) -> dict[str, Path]:
    index_dir = Path(index_dir)
    return {
        "dir": index_dir,
        "meta": index_dir / META_NAME,
        "emb": index_dir / EMB_NAME,
        "info": index_dir / INFO_NAME,
    }


def save_index(
    index_dir: Path,
    embeddings: np.ndarray,
    meta_rows: list[dict[str, Any]],
    info: dict[str, Any],
) -> None:
    paths = index_paths(index_dir)
    paths["dir"].mkdir(parents=True, exist_ok=True)

    np.save(paths["emb"], np.asarray(embeddings, dtype=np.float32))

    with open(paths["meta"], "w", encoding="utf-8") as f:
        for row in meta_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    paths["info"].write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Index saved → {paths['dir']} ({len(meta_rows)} chunks)")


def load_index(index_dir: Path) -> tuple[np.ndarray, list[dict], dict]:
    paths = index_paths(index_dir)
    if not paths["emb"].exists() or not paths["meta"].exists():
        raise FileNotFoundError(
            f"No search index found in {index_dir}. Run the indexer first."
        )

    embeddings = np.load(paths["emb"])
    meta_rows = []
    with open(paths["meta"], encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                meta_rows.append(json.loads(line))

    info = {}
    if paths["info"].exists():
        info = json.loads(paths["info"].read_text(encoding="utf-8"))

    logger.info(f"Loaded index: {len(meta_rows)} chunks from {index_dir}")
    return embeddings, meta_rows, info



def save_bm25_corpus(index_dir: Path, tokenized_docs: list[list[str]], doc_paths: list[str]) -> None:
    path = Path(index_dir) / BM25_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump({"tokenized_docs": tokenized_docs, "doc_paths": doc_paths}, f)


def load_bm25_corpus(index_dir: Path) -> tuple[list[list[str]], list[str]]:
    path = Path(index_dir) / BM25_NAME
    if not path.exists():
        raise FileNotFoundError(f"BM25 corpus not found: {path}. Rebuild the index.")
    with open(path, "rb") as f:
        data = pickle.load(f)
    return data["tokenized_docs"], data["doc_paths"]