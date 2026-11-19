# Metadata_Placeholder/4_placeholder_creator.py
#   python Metadata_Placeholder/4_placeholder_creator.py --excel classification_results_minilm.xlsx --embedder minilm
#   python Metadata_Placeholder/4_placeholder_creator.py --excel classification_results_qwen3.xlsx --embedder qwen3

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from project_config import (
    CLASSIFICATION_RESULTS_DIR,
    INJECTED_METADATA_DIR,
    metadata_dirs_for,
)

LOG_DIR = INJECTED_METADATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"placeholder_creator_{datetime.now().strftime('%Y%m%d_%H%M')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("placeholder")


METADATA_FIELDS = [
    "filename",
    "original_path",
    "text_length",
    "language_detected",
    "Title | Titre",
    "Document Type / Type de document",
    "Sensitivity",
    "Sensibilité",
    "personal_information",
    "Function_EN",
    "Function_FR",
    "Function_Desc_Sum_EN",
    "Function_Desc_Sum_FR",
    "Function_Match_Excerpt_EN",
    "Function_Match_Excerpt_FR",
    "Sub-Function_EN",
    "Sub-Function_FR",
    "Sub-Function_Desc_Summ_EN",
    "Sub-Function_Desc_Summ_FR",
    "Sub_Function_Match_Excerpt_EN",
    "Sub_Function_Match_Excerpt_FR",
    "Business_Process_EN",
    "Business_Process_FR",
    "Full_File_Class_No",
    "Records",
    "Records_Match_Excerpt_EN",
    "Records_Match_Excerpt_FR",
    "Retention Period",
    "Retention Trigger",
    "overall_confidence",
    "sub_function_confidence",
    "confidence_category",
    "needs_review",
    "Disposition Authorization / Autorisation de disposition",
    "Technical Environment | Environnement technique",
    "Litigation_hold",
    "Archival_value",
    "critical_business_content",
    "vision_flagged",
    "Vision_Description",
    "embedding_model",
]

USER_EDITABLE_FLAGS = (
    "Litigation_hold",
    "Archival_value",
    "critical_business_content",
)

KNOWN_WORKBOOKS = (
    "classification_results_qwen3_4b.xlsx",
    "classification_results_qwen3.xlsx",
    "classification_results_minilm.xlsx",
    "classification_results.xlsx",
)


def _safe_value(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and value == int(value):
            return int(value)
        return value
    return str(value).strip()


def _normalize_yes_no(value) -> str:
    s = str(value or "").strip().lower()
    if s in {"yes", "y", "true", "1"}:
        return "Yes"
    if s in {"no", "n", "false", "0", ""}:
        return "No"
    return str(value).strip() or "No"


def row_to_metadata(row: pd.Series) -> dict:
    meta = {}
    for field in METADATA_FIELDS:
        meta[field] = _safe_value(row.get(field, ""))

    for flag in USER_EDITABLE_FLAGS:
        meta[flag] = _normalize_yes_no(meta.get(flag, "No"))

    original_path = str(row.get("original_path", "") or "")
    meta["original_filename"] = Path(original_path).name if original_path else meta.get("filename", "")
    meta["original_path"] = original_path
    meta["timestamp_created"] = datetime.now().isoformat()
    return meta


def _resolve_excel(excel_name: str) -> Path | None:
    candidates: list[Path] = []
    name = (excel_name or "").strip()
    if name:
        p = Path(name)
        candidates.append(p if p.is_absolute() else CLASSIFICATION_RESULTS_DIR / p.name)

    for fallback in KNOWN_WORKBOOKS:
        fp = CLASSIFICATION_RESULTS_DIR / fallback
        if fp not in candidates:
            candidates.append(fp)

    for path in candidates:
        if path.is_file():
            return path
    return None


def _load_results(excel_path: Path) -> pd.DataFrame:
    logger.info(f"Reading classification results: {excel_path}")
    if excel_path.suffix.lower() == ".csv":
        return pd.read_csv(excel_path, encoding="utf-8-sig")
    return pd.read_excel(excel_path)


def create_placeholders(
    excel_name: str = "classification_results_minilm.xlsx",
    embedder_key: str = "minilm",
) -> int:
    dirs = metadata_dirs_for(embedder_key)
    out_dir = dirs["placeholders"]
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Embedder     : {dirs['key']}")
    logger.info(f"Placeholders : {out_dir}")

    excel_path = _resolve_excel(excel_name)
    if excel_path is None:
        for csv_name in (
            "classification_results_qwen3.csv",
            "classification_results_minilm.csv",
            "classification_results.csv",
        ):
            csv_path = CLASSIFICATION_RESULTS_DIR / csv_name
            if csv_path.is_file():
                excel_path = csv_path
                break

    if excel_path is None:
        logger.error(
            f"Classification results not found in {CLASSIFICATION_RESULTS_DIR}. "
            "Expected classification_results_minilm.xlsx or classification_results_qwen3.xlsx"
        )
        print(f"ERROR: No classification Excel found in {CLASSIFICATION_RESULTS_DIR}")
        return 0

    df = _load_results(excel_path)
    logger.info(f"Found {len(df)} rows")

    created = 0
    skipped = 0

    for _, row in df.iterrows():
        original_path_str = str(row.get("original_path", "") or "").strip()
        original_path = Path(original_path_str) if original_path_str else None

        if original_path and original_path.name:
            base_name = original_path.name
        else:
            base_name = str(row.get("filename", "unknown")).replace(".txt", "")
            if not base_name:
                base_name = f"row_{created + skipped + 1}"

        sidecar_name = f"{base_name}.metadata.json"
        sidecar_path = out_dir / sidecar_name
        metadata = row_to_metadata(row)
        if not metadata.get("embedding_model"):
            metadata["embedding_model"] = dirs["key"]

        logger.info(
            f"{sidecar_name} | embedder={metadata.get('embedding_model')} | "
            f"Litigation_hold={metadata.get('Litigation_hold')}"
        )

        try:
            with open(sidecar_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            logger.info(f"Created: {sidecar_path}")
            created += 1
        except Exception as e:
            logger.error(f"Failed {sidecar_name}: {e}")
            skipped += 1

    logger.info(f"Placeholder creation finished | created={created} | skipped={skipped}")
    logger.info(f"Source workbook: {excel_path}")
    print("\n" + "=" * 70)
    print(f"Placeholders complete | {created} JSON files | embedder={dirs['key']}")
    print(f"Source: {excel_path}")
    print(f"Folder: {out_dir}")
    print(f"Log   : {LOG_FILE}")
    print("=" * 70)
    return created


def main():
    parser = argparse.ArgumentParser(
        description="Create metadata JSON side-cars from classification results"
    )
    parser.add_argument(
        "--excel",
        default="classification_results_minilm.xlsx",
        help="Workbook in CLASSIFICATION_RESULTS_DIR",
    )
    parser.add_argument(
        "--embedder",
        default="minilm",
        choices=["minilm", "qwen3", "qwen3_4b"],
        help="Which model folder to write into",
    )
    args = parser.parse_args()

    key = args.embedder
    name = (args.excel or "").lower()
    if "4b" in name:
        key = "qwen3_4b"
    elif "qwen" in name:
        key = "qwen3"

    logger.info("=== Metadata Placeholder Creator Started ===")
    create_placeholders(args.excel, key)


if __name__ == "__main__":
    main()