# Classification/enrichers.py
"""
Lightweight enrichers (no Ollama):
- language (EN / FR / Bil)
- personal_information (simple PRI / patterns)
- sensitivity (keyword heuristic)
- document type (from extension dictionary)
- regex overrides from RegEx-db.csv
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd
from langdetect import DetectorFactory, detect_langs
from langdetect.lang_detect_exception import LangDetectException
from project_config import DOC_TYPE_DICT, REGEX_DB_PATH

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Language
# ---------------------------------------------------------------------------

DetectorFactory.seed = 0  # stable results

_CHUNK = 500
_MIN_TEXT = 40
_BIL_SHARE = 0.25


def _chunks(text: str, size: int = _CHUNK) -> list[str]:
    text = " ".join((text or "").split())
    if not text:
        return []
    return [text[i : i + size] for i in range(0, len(text), size)]


def _chunk_label(chunk: str) -> str | None:
    try:
        langs = detect_langs(chunk)
    except LangDetectException:
        return None
    if not langs:
        return None
    top = langs[0]
    if top.prob < 0.55:
        return None
    if top.lang.startswith("en"):
        return "en"
    if top.lang.startswith("fr"):
        return "fr"
    return None


def enrich_language(text: str) -> dict:
    raw = (text or "").strip()
    if len(raw) < _MIN_TEXT:
        return {"language_detected": "und"}

    votes = {"en": 0, "fr": 0}
    scored = 0
    for ch in _chunks(raw):
        if len(ch) < 30:
            continue
        lab = _chunk_label(ch)
        if lab is None:
            continue
        votes[lab] += 1
        scored += 1

    if scored == 0:
        return {"language_detected": "und"}

    en_share = votes["en"] / scored
    fr_share = votes["fr"] / scored

    if en_share >= _BIL_SHARE and fr_share >= _BIL_SHARE:
        return {"language_detected": "Bil"}
    if fr_share > en_share:
        return {"language_detected": "French / Français"}
    if en_share > fr_share:
        return {"language_detected": "English / Anglais"}
    return {"language_detected": "Bil"}


# ---------------------------------------------------------------------------
# PII (lightweight)
# ---------------------------------------------------------------------------

_PRI_RE = re.compile(
    r"(?i)(Personal Record Identifier|PRI|CIDP|Code d'identification de dossier personnel)"
    r"[ :.]?\s*(\d{3}[- .]?\d{3}[- .]?\d{3})"
)
_SIN_RE = re.compile(r"\b\d{3}[ -]?\d{3}[ -]?\d{3}\b")


def enrich_pii(text: str) -> dict:
    if not text:
        return {"personal_information": "No"}
    if _PRI_RE.search(text) or _SIN_RE.search(text[:5000]):
        return {"personal_information": "Yes"}
    return {"personal_information": "No"}


# ---------------------------------------------------------------------------
# Sensitivity (keyword heuristic)
# ---------------------------------------------------------------------------

_SENSITIVE_KEYWORDS = [
    "protected a", "protected b", "protected c",
    "secret", "top secret", "confidentiel", "classifié",
    "personnel security", "security clearance",
]


def enrich_sensitivity(text: str) -> dict:
    sample = (text or "")[:4000].lower()
    for kw in _SENSITIVE_KEYWORDS:
        if kw in sample:
            return {"Sensitivity": "Protected", "Sensibilité": "Protégé"}
    return {"Sensitivity": "Unclassified", "Sensibilité": "Non classifié"}


# ---------------------------------------------------------------------------
# Document type from extension dictionary
# ---------------------------------------------------------------------------

_doc_type_cache: dict[str, str] | None = None


def _load_doc_type_map() -> dict[str, str]:
    global _doc_type_cache
    if _doc_type_cache is not None:
        return _doc_type_cache

    mapping: dict[str, str] = {}
    if DOC_TYPE_DICT.is_file():
        for line in DOC_TYPE_DICT.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            ext, label = line.split("=", 1)
            ext = ext.strip().lower()
            if ext.startswith("."):
                mapping[ext] = label.strip()
    _doc_type_cache = mapping
    logger.info(f"Loaded {len(mapping)} document-type mappings")
    return mapping


def enrich_document_type(original_path: str | Path | None) -> dict:
    if not original_path:
        return {"Document Type / Type de document": "Unknown"}
    ext = Path(original_path).suffix.lower()
    label = _load_doc_type_map().get(ext, "Unknown")
    return {"Document Type / Type de document": label}


# ---------------------------------------------------------------------------
# RegEx overrides
# ---------------------------------------------------------------------------

def load_regex_rules() -> list[dict]:
    if not REGEX_DB_PATH.exists() or REGEX_DB_PATH.stat().st_size == 0:
        return []
    try:
        df = pd.read_csv(REGEX_DB_PATH)
        if "status" in df.columns:
            df = df[df["status"].astype(str).str.lower() == "activate"]
        rules = []
        for _, row in df.iterrows():
            try:
                pattern = re.compile(str(row["pattern"]), re.IGNORECASE)
            except re.error as e:
                logger.warning(f"Invalid regex skipped: {row.get('rule_name')} – {e}")
                continue
            rules.append({
                "name": row.get("rule_name", "unnamed"),
                "pattern": pattern,
                "target_field": row.get("target_field", ""),
                "target_value": row.get("target_value", ""),
            })
        logger.info(f"Loaded {len(rules)} active RegEx rules")
        return rules
    except Exception as e:
        logger.warning(f"Could not load RegEx DB: {e}")
        return []


_regex_rules_cache: list[dict] | None = None


def apply_regex_overrides(text: str) -> dict[str, Any]:
    global _regex_rules_cache
    if _regex_rules_cache is None:
        _regex_rules_cache = load_regex_rules()

    overrides: dict[str, Any] = {}
    for rule in _regex_rules_cache:
        if rule["pattern"].search(text or ""):
            field = str(rule["target_field"]).strip()
            value = str(rule["target_value"]).strip()
            if field:
                overrides[field] = value
                logger.info(f"RegEx hit: {rule['name']} → {field}={value}")
    return overrides


# ---------------------------------------------------------------------------
# Vision flag helper
# ---------------------------------------------------------------------------

def is_vision_flagged(text: str) -> bool:
    return "[VISION_FLAG: Yes]" in (text or "")