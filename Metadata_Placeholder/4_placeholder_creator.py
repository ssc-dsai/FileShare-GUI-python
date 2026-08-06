# Metadata_Placeholder/4_placeholder_creator.py
# Launched from Gradio via backend.runners.run_placeholders()
# Or manually:
#   python Metadata_Placeholder/4_placeholder_creator.py
#   python Metadata_Placeholder/4_placeholder_creator.py --excel classification_results.xlsx

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
    PLACEHOLDERS_DIR,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
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


# Columns we copy from classification_results into each JSON side-car
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
]


def _safe_value(value):
    """Convert pandas / numpy values to plain JSON-serialisable types."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        # keep numbers as numbers when sensible
        if isinstance(value, float) and value == int(value):
            return int(value)
        return value
    return str(value).strip()


def row_to_metadata(row: pd.Series) -> dict:
    meta = {}
    for field in METADATA_FIELDS:
        meta[field] = _safe_value(row.get(field, ""))

    original_path = str(row.get("original_path", "") or "")
    meta["original_filename"] = Path(original_path).name if original_path else meta.get("filename", "")
    meta["original_path"] = original_path
    meta["timestamp_created"] = datetime.now().isoformat()
    return meta


USER_EDITABLE_FLAGS = (
    "Litigation_hold",
    "Archival_value",
    "critical_business_content",
)


def _normalize_yes_no(value) -> str:
    s = str(value or "").strip().lower()
    if s in {"yes", "y", "true", "1"}:
        return "Yes"
    if s in {"no", "n", "false", "0", ""}:
        return "No"
    # keep unexpected text (e.g. "Partial") as-is but title-case lightly
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


def create_placeholders(excel_name: str = "classification_results.xlsx") -> int:
    PLACEHOLDERS_DIR.mkdir(parents=True, exist_ok=True)

    excel_path = CLASSIFICATION_RESULTS_DIR / excel_name
    if not excel_path.exists():
        # fallback to CSV
        csv_path = CLASSIFICATION_RESULTS_DIR / "classification_results.csv"
        if csv_path.exists():
            logger.info(f"Excel not found, using CSV: {csv_path}")
            df = pd.read_csv(csv_path, encoding="utf-8-sig")
        else:
            logger.error(f"Classification results not found: {excel_path}")
            print(f"ERROR: File not found: {excel_path}")
            return 0
    else:
        logger.info(f"Reading classification results: {excel_path}")
        df = pd.read_excel(excel_path)

    logger.info(f"Found {len(df)} rows")

    created = 0
    skipped = 0

    for _, row in df.iterrows():
        original_path_str = str(row.get("original_path", "") or "").strip()
        original_path = Path(original_path_str) if original_path_str else None

        # Prefer original filename for side-car name; fall back to classification filename
        if original_path and original_path.name:
            base_name = original_path.name
        else:
            base_name = str(row.get("filename", "unknown")).replace(".txt", "")
            if not base_name:
                base_name = f"row_{created + skipped + 1}"

        sidecar_name = f"{base_name}.metadata.json"
        sidecar_path = PLACEHOLDERS_DIR / sidecar_name

        metadata = row_to_metadata(row)

        logger.info(
            f"{sidecar_name} | Litigation_hold={metadata.get('Litigation_hold')} | "
            f"Archival_value={metadata.get('Archival_value')} | "
            f"critical_business_content={metadata.get('critical_business_content')}"
        )


        try:
            with open(sidecar_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            logger.info(f"Created: {sidecar_name}")
            created += 1
        except Exception as e:
            logger.error(f"Failed {sidecar_name}: {e}")
            skipped += 1

    logger.info(
        f"Placeholder creation finished | created={created} | skipped={skipped}"
    )
    logger.info(f"Output folder: {PLACEHOLDERS_DIR}")
    print("\n" + "=" * 70)
    print(f"Placeholders complete | {created} JSON files")
    print(f"Folder: {PLACEHOLDERS_DIR}")
    print(f"Log   : {LOG_FILE}")
    print("=" * 70)
    return created


def main():
    parser = argparse.ArgumentParser(description="Create metadata JSON side-cars from classification results")
    parser.add_argument(
        "--excel",
        default="classification_results.xlsx",
        help="Classification Excel filename inside CLASSIFICATION_RESULTS_DIR",
    )
    args = parser.parse_args()

    logger.info("=== Metadata Placeholder Creator Started ===")
    create_placeholders(args.excel)


if __name__ == "__main__":
    main()