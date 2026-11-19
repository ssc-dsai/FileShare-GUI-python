# project_config.py
"""
CENTRALIZED PROJECT CONFIGURATION - SINGLE SOURCE OF TRUTH
Set variables in a local .env file (or OS environment). Save, then restart the app.
"""

from pathlib import Path
import os
from dotenv import load_dotenv


def _path_from_env(name: str, fallback: Path) -> Path:
    return Path(os.getenv(name, str(fallback))).resolve()


load_dotenv(dotenv_path=Path(__file__).parent.resolve() / ".env", override=False)
DOCS_ROOT = _path_from_env("DOCS_ROOT", Path(r"C:\Documents"))

# ──────────────────────────────────────────────────────────────────
# INDEPENDENT ABSOLUTE PATHS
# ──────────────────────────────────────────────────────────────────

SOURCE_DOCS_DIR = _path_from_env("SOURCE_DOCS", DOCS_ROOT / "Synthetic_Docs")

EXTRACTED_TEXTS_DIR = _path_from_env("EXTRACTED_TEXTS", DOCS_ROOT / "extracted_texts")

CLASSIFICATION_RESULTS_DIR = _path_from_env("CLASSIFICATION_RESULTS", DOCS_ROOT / "classification_results")

DEDUPS_DIR = _path_from_env("DEDUPS", DOCS_ROOT / "Dedups")

INJECTED_METADATA_DIR = _path_from_env("INJECTED_METADATA", DOCS_ROOT / "injected_metadata")

# Per-model output trees (placeholders + clones)
INJECTED_MINILM_DIR = INJECTED_METADATA_DIR / "minilm"
INJECTED_QWEN_DIR = INJECTED_METADATA_DIR / "qwen3"
INJECTED_QWEN3_4B_DIR = INJECTED_METADATA_DIR / "qwen3_4b"
PLACEHOLDERS_MINILM_DIR = INJECTED_MINILM_DIR / "placeholders"
PLACEHOLDERS_QWEN_DIR = INJECTED_QWEN_DIR / "placeholders"
PLACEHOLDERS_QWEN3_4B_DIR = INJECTED_QWEN3_4B_DIR / "placeholders"


def metadata_dirs_for(embedder_key: str) -> dict:
    """Separate placeholder + clone folders per embedding model."""
    key = (embedder_key or "minilm").strip().lower()
    if key not in ("minilm", "qwen3", "qwen3_4b"):
        key = "minilm"
    if key == "minilm":
        root = INJECTED_MINILM_DIR
    elif key == "qwen3_4b":
        root = INJECTED_QWEN3_4B_DIR
    else:
        root = INJECTED_QWEN_DIR
    return {
        "key": key,
        "root": root,
        "placeholders": root / "placeholders",
    }

# ──────────────────────────────────────────────────────────────────
# LOCAL MODELS (fully offline) — load ONLY the selected embedder
# ──────────────────────────────────────────────────────────────────
MODELS_DIR = _path_from_env("MODELS_DIR", DOCS_ROOT / "models")




EMBEDDING_MODEL_MINILM_PATH = _path_from_env(
    "EMBEDDING_MODEL",
    MODELS_DIR / "paraphrase-multilingual-MiniLM-L12-v2",
)

EMBEDDING_MODEL_PATH = EMBEDDING_MODEL_MINILM_PATH

EMBEDDING_MODEL_QWEN_PATH = _path_from_env(
    "EMBEDDING_MODEL_QWEN",
    MODELS_DIR / "Qwen3-Embedding-0.6B",
)

EMBEDDING_MODEL_QWEN3_4B_PATH = _path_from_env(
    "EMBEDDING_MODEL_QWEN3_4B",
    MODELS_DIR / "Qwen3-Embedding-4B",
)

INJECTED_QWEN3_4B_DIR = INJECTED_METADATA_DIR / "qwen3_4b"
PLACEHOLDERS_QWEN3_4B_DIR = INJECTED_QWEN3_4B_DIR / "placeholders"

VISION_MODEL_PATH = _path_from_env(
    "VISION_MODEL",
    MODELS_DIR / "Qwen2-VL-2B-Instruct",
)

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
        "label": "Qwen3-0.6B (stronger, GPU)",
        "path": EMBEDDING_MODEL_QWEN_PATH,
        "cache_subdir": "qwen3_0.6b",
        "use_instruction": True,
        "chunk_chars": 1800,
        "results_stem": "classification_results_qwen3",
    },
    "qwen3_4b": {
        "label": "Qwen3-4B (strongest, heavy and slower)",
        "path": EMBEDDING_MODEL_QWEN3_4B_PATH,
        "cache_subdir": "qwen3_4b",
        "use_instruction": True,
        "chunk_chars": 1800,
        "results_stem": "classification_results_qwen3_4b",
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
        INJECTED_MINILM_DIR,
        INJECTED_QWEN_DIR,
        PLACEHOLDERS_MINILM_DIR,
        PLACEHOLDERS_QWEN_DIR,
        MODELS_DIR,
        INJECTED_QWEN3_4B_DIR,
        PLACEHOLDERS_QWEN3_4B_DIR,
        EMBEDDING_MODEL_QWEN3_4B_PATH,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    print("✅ Project directories ready")
    print(f"   • Source documents       : {SOURCE_DOCS_DIR}")
    print(f"   • Extracted texts        : {EXTRACTED_TEXTS_DIR}")
    print(f"   • Classification results : {CLASSIFICATION_RESULTS_DIR}")
    print(f"   • Deduplication          : {DEDUPS_DIR}")
    print(f"   • Injected parent        : {INJECTED_METADATA_DIR}")
    print(f"   • Injected MiniLM        : {INJECTED_MINILM_DIR}")
    print(f"   • Placeholders MiniLM    : {PLACEHOLDERS_MINILM_DIR}")
    print(f"   • Injected Qwen3         : {INJECTED_QWEN_DIR}")
    print(f"   • Placeholders Qwen3     : {PLACEHOLDERS_QWEN_DIR}")
    print(f"   • Injected Qwen3-4B      : {INJECTED_QWEN3_4B_DIR}")
    print(f"   • Placeholders Qwen3-4B  : {PLACEHOLDERS_QWEN3_4B_DIR}")
    print(f"   • Qwen3-4B embedder      : {EMBEDDING_MODEL_QWEN3_4B_PATH}")
    print(f"   • Local models           : {MODELS_DIR}")
    print(f"   • MiniLM embedder        : {EMBEDDING_MODEL_MINILM_PATH}")
    print(f"   • Qwen3 embedder         : {EMBEDDING_MODEL_QWEN_PATH}")
    print(f"   • Vision model           : {VISION_MODEL_PATH}")


ensure_directories()

print("🚀 Central config loaded (independent absolute paths)")
print(f"   SOURCE_DOCS_DIR             = {SOURCE_DOCS_DIR}")
print(f"   EMBEDDING_MODEL_MINILM_PATH = {EMBEDDING_MODEL_MINILM_PATH}")
print(f"   EMBEDDING_MODEL_QWEN_PATH   = {EMBEDDING_MODEL_QWEN_PATH}")
print(f"   VISION_MODEL_PATH           = {VISION_MODEL_PATH}")
print(f"   EMBEDDING_MODEL_QWEN3_4B_PATH = {EMBEDDING_MODEL_QWEN3_4B_PATH}")
