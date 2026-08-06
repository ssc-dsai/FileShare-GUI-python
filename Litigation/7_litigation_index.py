# Litigation/7_litigation_index.py
# Index LITIGATION_SEARCH_DIR for semantic (MiniLM) + BM25 search.
# Originals are never modified.
#
#   python Litigation/7_litigation_index.py
#   python Litigation/7_litigation_index.py --rebuild

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from project_config import (
    EMBEDDING_MODEL_PATH,
    LITIGATION_INDEX_DIR,
    LITIGATION_SEARCH_DIR,
)

from Ingestion.extractors import extract_text_from_file
from Classification.semantic_matcher import chunk_text
from Litigation.utils.package_io import list_supported_files
from Litigation.utils.search_index import save_bm25_corpus, save_index
from Litigation.utils.tombstone_parse import tokenize

LOG_DIR = LITIGATION_INDEX_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"index_builder_{datetime.now().strftime('%Y%m%d_%H%M')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("litigation_index")


def build_index(rebuild: bool = False) -> None:
    logger.info("=" * 70)
    logger.info("LITIGATION INDEX BUILDER (MiniLM + BM25)")
    logger.info(f"Search dir : {LITIGATION_SEARCH_DIR}")
    logger.info(f"Index dir  : {LITIGATION_INDEX_DIR}")
    logger.info(f"Model      : {EMBEDDING_MODEL_PATH}")
    logger.info("=" * 70)

    if not LITIGATION_SEARCH_DIR.is_dir():
        logger.error(f"LITIGATION_SEARCH_DIR not found: {LITIGATION_SEARCH_DIR}")
        print(f"ERROR: Search folder not found: {LITIGATION_SEARCH_DIR}")
        return

    if not EMBEDDING_MODEL_PATH.exists():
        raise FileNotFoundError(f"Embedding model not found: {EMBEDDING_MODEL_PATH}")

    emb_path = LITIGATION_INDEX_DIR / "chunks_embeddings.npy"
    bm25_path = LITIGATION_INDEX_DIR / "bm25_corpus.pkl"
    if emb_path.exists() and bm25_path.exists() and not rebuild:
        logger.info("Index already exists. Use --rebuild to recreate.")
        print(f"Index already exists at {LITIGATION_INDEX_DIR}")
        print("Pass --rebuild to rebuild from scratch.")
        return

    logger.info("Loading MiniLM...")
    embedder = SentenceTransformer(str(EMBEDDING_MODEL_PATH))
    logger.info("Embedder ready")

    files = list_supported_files(LITIGATION_SEARCH_DIR)
    logger.info(f"Files to index: {len(files)}")
    if not files:
        print("No supported files found to index.")
        return

    meta_rows: list[dict] = []
    all_chunk_texts: list[str] = []
    bm25_tokenized: list[list[str]] = []
    bm25_paths: list[str] = []

    for i, path in enumerate(files, 1):
        logger.info(f"[{i}/{len(files)}] {path.name}")
        try:
            text = extract_text_from_file(path) or ""
            body = text.strip()

            # ---- MiniLM chunks ----
            chunks = chunk_text(body)
            if not chunks:
                chunks = [{
                    "text": body[:450] or path.name,
                    "start": 0,
                    "end": min(450, len(body)),
                }]

            for ci, ch in enumerate(chunks):
                meta_rows.append({
                    "file_path": str(path.resolve()),
                    "file_name": path.name,
                    "chunk_id": ci,
                    "start": ch["start"],
                    "end": ch["end"],
                    "text": ch["text"][:2000],
                })
                all_chunk_texts.append(ch["text"])

            # ---- BM25: one entry per file (full text tokens) ----
            bm25_tokenized.append(tokenize(body))
            bm25_paths.append(str(path.resolve()))

        except Exception as e:
            logger.error(f"Skip {path.name}: {type(e).__name__}: {e}")

    if not all_chunk_texts:
        logger.error("No text chunks produced.")
        return

    logger.info(f"Embedding {len(all_chunk_texts)} chunks...")
    embeddings = embedder.encode(
        all_chunk_texts,
        normalize_embeddings=True,
        batch_size=64,
        show_progress_bar=True,
    )
    embeddings = np.asarray(embeddings, dtype=np.float32)

    info = {
        "created": datetime.now().isoformat(),
        "search_dir": str(LITIGATION_SEARCH_DIR),
        "model": str(EMBEDDING_MODEL_PATH),
        "file_count": len(bm25_paths),
        "chunk_count": len(meta_rows),
        "bm25_docs": len(bm25_paths),
    }
    save_index(LITIGATION_INDEX_DIR, embeddings, meta_rows, info)
    save_bm25_corpus(LITIGATION_INDEX_DIR, bm25_tokenized, bm25_paths)
    logger.info(f"BM25 corpus saved ({len(bm25_paths)} documents)")

    print("\n" + "=" * 70)
    print(f"Index complete | {len(bm25_paths)} files | {len(meta_rows)} chunks")
    print(f"Index dir: {LITIGATION_INDEX_DIR}")
    print(f"  - chunks_embeddings.npy")
    print(f"  - chunks_meta.jsonl")
    print(f"  - bm25_corpus.pkl")
    print(f"  - index_info.json")
    print(f"Log      : {LOG_FILE}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Build litigation search index (MiniLM + BM25)")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild index even if one already exists",
    )
    args = parser.parse_args()
    build_index(rebuild=args.rebuild)


if __name__ == "__main__":
    main()