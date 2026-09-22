# Classification/2_Classification.py
# Phase 2 – Classification
#
#   python Classification/2_Classification.py --embedder minilm
#   python Classification/2_Classification.py --embedder qwen3

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

import pandas as pd
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from project_config import (
    CLASSIFICATION_RESULTS_DIR,
    EXTRACTED_TEXTS_DIR,
    HIERARCHY_CSV,
    QWEN_DOC_INSTRUCTION,
    SOURCE_DOCS_DIR,
    VISION_MODEL_PATH,
    resolve_embedder,
)

from Classification.config_classification import COLUMNS_ORDER
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

_ILLEGAL_XML = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def _sanitize_for_excel(df: pd.DataFrame) -> pd.DataFrame:
    """Strip characters OpenPyXL rejects. Do not filter on dtype==object
    (pandas may use dtype 'str', which skipped the FCP descriptions)."""
    out = df.copy()
    for col in out.columns:
        out[col] = out[col].map(
            lambda v: _ILLEGAL_XML.sub("", v) if isinstance(v, str) else v
        )
    return out


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


def run_classification(embedder_key: str = "minilm") -> None:
    cfg = resolve_embedder(embedder_key)
    model_path = cfg["path"]
    cache_dir = cfg["cache_dir"]

    logger.info("=" * 70)
    logger.info("CLASSIFICATION STARTED")
    logger.info(f"Embedder key    : {cfg['key']} — {cfg['label']}")
    logger.info(f"Embedding model : {model_path}")
    logger.info(f"Cache dir       : {cache_dir}")
    logger.info(f"Instruction     : {cfg['use_instruction']}")
    logger.info(f"Extracted texts : {EXTRACTED_TEXTS_DIR}")
    logger.info(f"Output          : {CLASSIFICATION_RESULTS_DIR}")
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

    if not model_path.exists():
        raise FileNotFoundError(
            f"Embedding model not found: {model_path}\nDownload it first, then retry."
        )

    logger.info(f"Loading embedder from {model_path} (this model only)...")
    embedder = SentenceTransformer(str(model_path))
    logger.info("Embedder ready")

    cache_dir.mkdir(parents=True, exist_ok=True)
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
                use_instruction=cfg["use_instruction"],
                instruction=QWEN_DOC_INSTRUCTION if cfg["use_instruction"] else "",
                chunk_chars=cfg["chunk_chars"],
            )

            from Classification.archival_rules import archival_value_for
            row["Archival_value"] = archival_value_for(
                row.get("Function_EN", ""),
                row.get("Sub-Function_EN", ""),
                row.get("Business_Process_EN", ""),
            )

            if title:
                row["Title | Titre"] = title

            if "[VISION_FLAG: Yes]" in raw_text:
                row["vision_flagged"] = "Yes"
                row["Vision_Description"] = vision_desc if vision_desc else "N/A"
            else:
                row["vision_flagged"] = "No"
                row["Vision_Description"] = "N/A"

            row["embedding_model"] = cfg["key"]

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
        ordered = list(COLUMNS_ORDER)
        if "embedding_model" not in ordered:
            ordered = ordered + ["embedding_model"]
        df = df.reindex(columns=ordered, fill_value="")
    except Exception:
        pass

    stem = cfg.get("results_stem") or (
        "classification_results_qwen3" if cfg.get("key") == "qwen3"
        else "classification_results_minilm"
    )
    csv_path = CLASSIFICATION_RESULTS_DIR / f"{stem}.csv"
    xlsx_path = CLASSIFICATION_RESULTS_DIR / f"{stem}.xlsx"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    try:
        fcp_df = pd.read_csv(HIERARCHY_CSV, encoding="utf-8-sig", low_memory=False)
        fcp_df = _sanitize_for_excel(fcp_df)
    except Exception as e:
        logger.warning(f"Could not attach FCP sheet: {e}")
        fcp_df = None

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        _sanitize_for_excel(df).to_excel(writer, sheet_name="classification", index=False)
        if fcp_df is not None:
            fcp_df.to_excel(writer, sheet_name="FCP_Hierarchy", index=False)

    logger.info(f"CSV saved: {csv_path}")
    logger.info(f"Excel saved: {xlsx_path}")

    print("\n" + "=" * 70)
    print(f"Classification complete | {len(results)} documents | embedder={cfg.get('key')}")
    print(f"CSV  : {csv_path}")
    print(f"Excel: {xlsx_path}")
    print(f"Cache: {cfg.get('cache_dir')}")
    print(f"Log  : {LOG_FILE}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--embedder",
        default="minilm",
        choices=["minilm", "qwen3", "qwen3_4b"],
        help="Which local embedding model to load (only one is loaded).",
    )
    args = parser.parse_args()
    run_classification(args.embedder)


if __name__ == "__main__":
    main()