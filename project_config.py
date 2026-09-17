# project_config.py
"""
CENTRALIZED PROJECT CONFIGURATION - SINGLE SOURCE OF TRUTH
Edit the absolute paths in this file for each machine. Save, then restart the app.

DESIGN
------
Every major working directory is an INDEPENDENT absolute path.
"""

from pathlib import Path
import os

# ──────────────────────────────────────────────────────────────────
# INDEPENDENT ABSOLUTE PATHS
# ──────────────────────────────────────────────────────────────────

SOURCE_DOCS_DIR = Path(os.getenv(
    "SOURCE_DOCS",
    r"C:\JAY_DOCS\Synthetic_Docs"
)).resolve()

EXTRACTED_TEXTS_DIR = Path(os.getenv(
    "EXTRACTED_TEXTS",
    r"C:\JAY_DOCS\extracted_texts"
)).resolve()

CLASSIFICATION_RESULTS_DIR = Path(os.getenv(
    "CLASSIFICATION_RESULTS",
    r"C:\JAY_DOCS\classification_results"
)).resolve()

DEDUPS_DIR = Path(os.getenv(
    "DEDUPS",
    r"C:\JAY_DOCS\Dedups"
)).resolve()

INJECTED_METADATA_DIR = Path(os.getenv(
    "INJECTED_METADATA",
    r"C:\JAY_DOCS\Injected_Metadata"
)).resolve()

PLACEHOLDERS_DIR = INJECTED_METADATA_DIR / "placeholders"

# ──────────────────────────────────────────────────────────────────
# LOCAL MODELS (fully offline)
# ──────────────────────────────────────────────────────────────────
MODELS_DIR = Path(os.getenv(
    "MODELS_DIR",
    r"C:\JAY_DOCS\models"
)).resolve()

EMBEDDING_MODEL_PATH = Path(os.getenv(
    "EMBEDDING_MODEL",
    str(MODELS_DIR / "paraphrase-multilingual-MiniLM-L12-v2")
)).resolve()

VISION_MODEL_PATH = Path(os.getenv(
    "VISION_MODEL",
    str(MODELS_DIR / "Qwen2-VL-2B-Instruct")
)).resolve()

CLASSIFICATION_MODEL_PATH = VISION_MODEL_PATH

# ──────────────────────────────────────────────────────────────────
# RESOURCE FILES (travel with the project)
# ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
RESOURCES_DIR = PROJECT_ROOT / "Resources-Sources"

HIERARCHY_CSV = RESOURCES_DIR / "fcp_CSV-UTF.csv"
DOC_TYPE_DICT = RESOURCES_DIR / "Doc_Type_Dictionary.txt"
REGEX_DB_PATH = RESOURCES_DIR / "RegEx-db.csv"
TRIVIAL_SUBJECTS = RESOURCES_DIR / "trivial_subjects.txt"


def ensure_directories():
    """Create all required folders automatically (except SOURCE_DOCS_DIR)."""
    dirs = [
        EXTRACTED_TEXTS_DIR,
        CLASSIFICATION_RESULTS_DIR,
        DEDUPS_DIR,
        INJECTED_METADATA_DIR,
        PLACEHOLDERS_DIR,
        MODELS_DIR,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    print("✅ Project directories ready")
    print(f"   • Source documents       : {SOURCE_DOCS_DIR}")
    print(f"   • Extracted texts        : {EXTRACTED_TEXTS_DIR}")
    print(f"   • Classification results : {CLASSIFICATION_RESULTS_DIR}")
    print(f"   • Deduplication          : {DEDUPS_DIR}")
    print(f"   • Injected metadata      : {INJECTED_METADATA_DIR}")
    print(f"   • Placeholders           : {PLACEHOLDERS_DIR}")
    print(f"   • Local models           : {MODELS_DIR}")


ensure_directories()

print("🚀 Central config loaded (independent absolute paths)")
print(f"   SOURCE_DOCS_DIR       = {SOURCE_DOCS_DIR}")
print(f"   EMBEDDING_MODEL_PATH  = {EMBEDDING_MODEL_PATH}")
print(f"   VISION_MODEL_PATH     = {VISION_MODEL_PATH}")