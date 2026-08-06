# Classification/2_Classification.py
# Phase 2 – Classification (MiniLM hierarchy + multi-image vision)
#
#   python Classification/2_Classification.py

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from project_config import (
    CLASSIFICATION_RESULTS_DIR,
    EMBEDDING_MODEL_PATH,
    EXTRACTED_TEXTS_DIR,
    SOURCE_DOCS_DIR,
    VISION_MODEL_PATH,
)

from Classification.config_classification import COLUMNS_ORDER, HIERARCHY_CSV
from Classification.hierarchy_loader import load_or_build_hierarchy_index
from Classification.classification_core import classify_document
from Classification.vision_helper import build_vision_augmented_text

LOG_DIR = CLASSIFICATION_RESULTS_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "classification_summary.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("classification")

ORIGINAL_EXTS = [
    ".pdf", ".docx", ".doc", ".pptx", ".ppt",
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".gif", ".webp", ".bmp",
    ".xlsx", ".xls", ".txt",
]


def find_original_file(stem: str) -> Path | None:
    for ext in ORIGINAL_EXTS:
        cand = SOURCE_DOCS_DIR / f"{stem}{ext}"
        if cand.is_file():
            return cand
    if SOURCE_DOCS_DIR.is_dir():
        for h in SOURCE_DOCS_DIR.rglob(f"{stem}.*"):
            if h.is_file() and h.suffix.lower() in set(ORIGINAL_EXTS):
                return h
    return None


def run_classification() -> None:
    logger.info("=" * 70)
    logger.info("CLASSIFICATION STARTED")
    logger.info(f"Extracted texts : {EXTRACTED_TEXTS_DIR}")
    logger.info(f"Output          : {CLASSIFICATION_RESULTS_DIR}")
    logger.info(f"Embedding model : {EMBEDDING_MODEL_PATH}")
    logger.info(f"Vision model    : {VISION_MODEL_PATH}")
    logger.info("=" * 70)

    txt_files = sorted(
        p for p in EXTRACTED_TEXTS_DIR.glob("*.txt")
        if "_images" not in p.parts
    )
    if not txt_files:
        logger.warning("No .txt files found in EXTRACTED_TEXTS_DIR")
        print("No documents to classify.")
        return

    logger.info(f"Found {len(txt_files)} documents")

    if not EMBEDDING_MODEL_PATH.exists():
        raise FileNotFoundError(f"Embedding model not found: {EMBEDDING_MODEL_PATH}")

    logger.info("Loading local MiniLM embedder...")
    embedder = SentenceTransformer(str(EMBEDDING_MODEL_PATH))
    logger.info("Embedder ready")

    cache_dir = CLASSIFICATION_RESULTS_DIR / "embedding_cache"
    hierarchy_df, indexes = load_or_build_hierarchy_index(
        HIERARCHY_CSV, embedder, cache_dir=cache_dir
    )

    results: list[dict] = []

    for i, txt_path in enumerate(txt_files, 1):
        try:
            logger.info(f"[{i}/{len(txt_files)}] {txt_path.name}")
            raw_text = txt_path.read_text(encoding="utf-8", errors="replace")

            title = ""
            lines = raw_text.splitlines()
            if lines and lines[0].startswith("[Generated Title]"):
                title = lines[0].replace("[Generated Title]", "", 1).strip(" :")
                raw_text = "\n".join(lines[1:]).lstrip()

            original = find_original_file(txt_path.stem)

            body_for_match = raw_text
            vision_desc = "N/A"

            if "[VISION_FLAG: Yes]" in raw_text:
                body_for_match, vision_desc = build_vision_augmented_text(
                    raw_text,
                    model_path=VISION_MODEL_PATH,
                    original_path=original,
                    extracted_texts_dir=EXTRACTED_TEXTS_DIR,
                )

            row = classify_document(
                text=body_for_match,
                filename=txt_path.name,
                original_path=str(original) if original else "",
                embedder=embedder,
                hierarchy_df=hierarchy_df,
                indexes=indexes,
                vision_description=vision_desc,
            )

            if title:
                row["Title | Titre"] = title

            if "[VISION_FLAG: Yes]" in raw_text:
                row["vision_flagged"] = "Yes"
                row["Vision_Description"] = vision_desc if vision_desc else "N/A"
            else:
                row["vision_flagged"] = "No"
                row["Vision_Description"] = "N/A"

            for col in COLUMNS_ORDER:
                row.setdefault(col, "")

            results.append(row)
            logger.info(
                f"→ {row.get('Function_EN', 'Unknown')} | "
                f"conf={row.get('overall_confidence', '')} | "
                f"review={row.get('needs_review', '')}"
            )

        except Exception as e:
            logger.error(
                f"Failed {txt_path.name}: {type(e).__name__}: {e}",
                exc_info=True,
            )

    if not results:
        logger.warning("No successful classifications")
        print("No successful classifications.")
        return

    CLASSIFICATION_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(results)
    try:
        df = df.reindex(columns=COLUMNS_ORDER, fill_value="")
    except Exception:
        pass

    csv_path = CLASSIFICATION_RESULTS_DIR / "classification_results.csv"
    xlsx_path = CLASSIFICATION_RESULTS_DIR / "classification_results.xlsx"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_excel(xlsx_path, index=False, engine="openpyxl")

    logger.info(f"CSV saved: {csv_path}")
    logger.info(f"Excel saved: {xlsx_path}")

    print("\n" + "=" * 70)
    print(f"Classification complete | {len(results)} documents")
    print(f"CSV  : {csv_path}")
    print(f"Excel: {xlsx_path}")
    print(f"Log  : {LOG_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    run_classification()