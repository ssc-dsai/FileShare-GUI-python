# Ingestion/1_Ingestion.py
# Launched from Gradio via backend.runners.run_ingestion()
# Or manually: python Ingestion/1_Ingestion.py

import gc
import os
import sys
from pathlib import Path
from project_config import EXTRACTED_TEXTS_DIR
# ── Add project root to Python path ─────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Import from central config (single source of truth) ─────────────────
from project_config import (
    SOURCE_DOCS_DIR as SOURCE_DIR,
    EXTRACTED_TEXTS_DIR as OUTPUT_PATH,
)

# ── Absolute package imports (works with runpy.run_path) ──
from Ingestion.logging_setup import setup_summary_logger
from Ingestion.utils_Ingestion import get_safe_txt_path, save_text_to_file, normalize_text
from Ingestion.extractors import extract_text_from_file

# ── Ingestion-specific settings ─────────────────
LOGS_PATH = OUTPUT_PATH / "logs"
SUPPORTED_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff",
    ".doc", ".docx", ".ppt", ".pptx", ".txt", ".rtf", ".odt",
}
EXCLUDED_EXTENSIONS = {".tmp", ".bak", ".log", ".DS_Store", ".thumbs.db"}
EXCLUDED_DIRS = {"logs", "extracted_texts", "classification_results", "__pycache__"}


def _title_from_filename(path: Path) -> str:
    """Build a clean Title-Case title from the file stem (pure-Python, no Ollama)."""
    stem = path.stem.replace("_", " ").replace("-", " ").strip()
    if len(stem) < 3:
        return "Untitled Document"
    return stem.title()[:120]


gc.collect()


def process_directory():
    if not SOURCE_DIR.is_dir():
        print(f"ERROR: SOURCE_DIR not found or inaccessible: {SOURCE_DIR}")
        return

    # Ensure output folders exist
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    LOGS_PATH.mkdir(parents=True, exist_ok=True)

    logger = setup_summary_logger(LOGS_PATH)
    logger.info(f"Ingestion started | SOURCE_DIR: {SOURCE_DIR.resolve()}")
    logger.info(f"Output folder   | {OUTPUT_PATH.resolve()}")

    processed = 0
    errors = 0
    vision_flagged = []

    for root, dirs, files in os.walk(SOURCE_DIR, topdown=True):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        current_root = Path(root)

        for file_name in files:
            full_path = current_root / file_name
            ext = full_path.suffix.lower()

            if ext in EXCLUDED_EXTENSIONS or ext not in SUPPORTED_EXTENSIONS:
                continue

            # Skip anything already inside the output tree
            if OUTPUT_PATH in full_path.parents or LOGS_PATH in full_path.parents:
                continue

            try:
                text = extract_text_from_file(full_path, extracted_texts_dir=EXTRACTED_TEXTS_DIR)

                vision_flag = "[VISION_FLAG: Yes]" in text

                # Pure-Python title (no Ollama)
                title = _title_from_filename(full_path)

                full_text = f"[Generated Title] {title}\n\n" + text
                full_text = normalize_text(full_text, preserve_paragraphs=True)

                txt_path = get_safe_txt_path(OUTPUT_PATH, full_path)
                save_text_to_file(full_text, txt_path)

                text_len = len(full_text)
                logger.info(
                    f"Success | {text_len:,} chars | {txt_path.name} | title={title[:60]}..."
                )

                if vision_flag:
                    logger.info(f"Vision flagged: {full_path.name}")
                    vision_flagged.append(full_path.name)

                processed += 1

            except Exception as e:
                logger.error(f"Error on {full_path.name}: {type(e).__name__} - {str(e)}")
                errors += 1

    logger.info(
        f"Ingestion complete | Processed: {processed} | Errors: {errors} | "
        f"Vision-flagged: {len(vision_flagged)}"
    )

    if vision_flagged:
        logger.info("VISION-FLAGGED FILES:")
        for f in vision_flagged:
            logger.info(f"- {f}")

    print("\n" + "=" * 70)
    print(f"Done | Processed: {processed} | Errors: {errors}")
    print(f"Summary log: {LOGS_PATH / 'zz_extraction_summary.log'}")
    print("=" * 70)


if __name__ == "__main__":
    process_directory()