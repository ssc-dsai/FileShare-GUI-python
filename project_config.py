# project_config.py
"""
CENTRALIZED PROJECT CONFIGURATION - SINGLE SOURCE OF TRUTH
All scripts import paths and settings from here.

DESIGN
------
Every major working directory is an INDEPENDENT absolute path.
This supports real Microsoft DFS / network-share environments where:
  - Source documents live on one share
  - Extracted texts, classification results, placeholders, clones, and
    litigation packages live on completely different volumes or shares.

Priority for each path:
  1. Environment variable (if set)
  2. Default value written in this file
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

# Creates a Summarized Package from the Court Case Files
LITIGATION_PACKAGES_DIR = Path(os.getenv(
    "LITIGATION_PACKAGES",
    r"C:\JAY_DOCS\Litigation_Packages"
)).resolve()

# Folder of court-case documents used to BUILD a litigation package
LITIGATION_CASE_SOURCE_DIR = Path(os.getenv(
    "LITIGATION_CASE_SOURCE_DIR",
    r"C:\JAY_DOCS\Litigation_Cases"   # put court-case files here
)).resolve()

LITIGATION_REPORTS_DIR = Path(os.getenv(
    "LITIGATION_REPORTS",
    r"C:\JAY_DOCS\Litigation_Reports"
)).resolve()

# Folder the end-user searches / packages from (matter share, review set, etc.)
LITIGATION_SEARCH_DIR = Path(os.getenv(
    "TARGET_LITIGATION_SEARCH_DIR",
    r"C:\JAY_DOCS\Synthetic_Docs"
)).resolve()

LITIGATION_INDEX_DIR = Path(os.getenv(
    "LITIGATION_INDEX_DIR",
    r"C:\JAY_DOCS\Litigation_Index"
)).resolve()



LITIGATION_SEARCH_ROOT = SOURCE_DOCS_DIR
LITIGATION_CONFIDENCE_THRESHOLD = 0.65

# ──────────────────────────────────────────────────────────────────
# LOCAL MODELS (fully offline)
# ──────────────────────────────────────────────────────────────────
MODELS_DIR = Path(os.getenv(
    "MODELS_DIR",
    r"C:\JAY_DOCS\models"
)).resolve()

# Embedding model – used for FCP hierarchy matching + Match Excerpts
EMBEDDING_MODEL_PATH = Path(os.getenv(
    "EMBEDDING_MODEL",
    str(MODELS_DIR / "paraphrase-multilingual-MiniLM-L12-v2")
)).resolve()

# Vision-Language model – used only for vision-flagged files + short rationales
VISION_MODEL_PATH = Path(os.getenv(
    "VISION_MODEL",
    str(MODELS_DIR / "Qwen2-VL-2B-Instruct")
)).resolve()

# Kept for backward compatibility / future text-only generative use
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
        LITIGATION_PACKAGES_DIR,
        LITIGATION_REPORTS_DIR,
        LITIGATION_SEARCH_DIR,
        LITIGATION_CASE_SOURCE_DIR,
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
    print(f"   • Litigation Packages    : {LITIGATION_PACKAGES_DIR}")
    print(f"   • Litigation Reports     : {LITIGATION_REPORTS_DIR}")
    print(f"   • Litigation search source : {LITIGATION_SEARCH_DIR}")
    print(f"   • Local models           : {MODELS_DIR}")


# Auto-run when imported
ensure_directories()

print("🚀 Central config loaded (independent absolute paths)")
print(f"   SOURCE_DOCS_DIR       = {SOURCE_DOCS_DIR}")
print(f"   EMBEDDING_MODEL_PATH  = {EMBEDDING_MODEL_PATH}")
print(f"   VISION_MODEL_PATH     = {VISION_MODEL_PATH}")