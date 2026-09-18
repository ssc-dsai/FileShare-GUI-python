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

def metadata_dirs_for(embedder_key: str) -> dict:
    """Separate placeholder + clone folders per embedding model."""
    key = (embedder_key or "minilm").strip().lower()
    if key not in ("minilm", "qwen3"):
        key = "minilm"
    root = INJECTED_METADATA_DIR / key
    return {
        "key": key,
        "root": root,
        "placeholders": root / "placeholders",
    }

# ──────────────────────────────────────────────────────────────────
# LOCAL MODELS (fully offline) — load ONLY the selected embedder
# ──────────────────────────────────────────────────────────────────
MODELS_DIR = Path(os.getenv(
    "MODELS_DIR",
    r"C:\JAY_DOCS\models"
)).resolve()

EMBEDDING_MODEL_MINILM_PATH = Path(os.getenv(
    "EMBEDDING_MODEL",
    str(MODELS_DIR / "paraphrase-multilingual-MiniLM-L12-v2")
)).resolve()

EMBEDDING_MODEL_QWEN_PATH = Path(os.getenv(
    "EMBEDDING_MODEL_QWEN",
    str(MODELS_DIR / "Qwen3-Embedding-0.6B")
)).resolve()

# Alias used by older scripts (MiniLM)
EMBEDDING_MODEL_PATH = EMBEDDING_MODEL_MINILM_PATH

VISION_MODEL_PATH = Path(os.getenv(
    "VISION_MODEL",
    str(MODELS_DIR / "Qwen2-VL-2B-Instruct")
)).resolve()

CLASSIFICATION_MODEL_PATH = VISION_MODEL_PATH

EMBEDDER_CHOICES = {
    "minilm": {
        "label": "MiniLM (fast baseline)",
        "path": EMBEDDING_MODEL_MINILM_PATH,
        "cache_subdir": "minilm",
        "use_instruction": False,
        "chunk_chars": 450,
        "results_stem": "classification_results_minilm",
    },
    "qwen3": {
        "label": "Qwen3-Embedding-0.6B (stronger, GPU)",
        "path": EMBEDDING_MODEL_QWEN_PATH,
        "cache_subdir": "qwen3_0.6b",
        "use_instruction": True,
        "chunk_chars": 1800,
        "results_stem": "classification_results_qwen3",
    },
}

QWEN_DOC_INSTRUCTION = (
    "Identify which records function, sub-function, or business process "
    "this text belongs to. Focus on operational purpose and subject matter, "
    "not tone, formatting, or document length."
)


def resolve_embedder(key: str) -> dict:
    key = (key or "minilm").strip().lower()
    if key not in EMBEDDER_CHOICES:
        key = "minilm"
    cfg = dict(EMBEDDER_CHOICES[key])
    cfg["key"] = key
    cfg["cache_dir"] = CLASSIFICATION_RESULTS_DIR / "embedding_cache" / cfg["cache_subdir"]
    return cfg

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
    """Create working folders automatically (except SOURCE_DOCS_DIR)."""
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
    print(f"   • MiniLM embedder        : {EMBEDDING_MODEL_MINILM_PATH}")
    print(f"   • Qwen3 embedder         : {EMBEDDING_MODEL_QWEN_PATH}")
    print(f"   • Vision model           : {VISION_MODEL_PATH}")


ensure_directories()

print("🚀 Central config loaded (independent absolute paths)")
print(f"   SOURCE_DOCS_DIR              = {SOURCE_DOCS_DIR}")
print(f"   EMBEDDING_MODEL_MINILM_PATH  = {EMBEDDING_MODEL_MINILM_PATH}")
print(f"   EMBEDDING_MODEL_QWEN_PATH    = {EMBEDDING_MODEL_QWEN_PATH}")
print(f"   VISION_MODEL_PATH            = {VISION_MODEL_PATH}")