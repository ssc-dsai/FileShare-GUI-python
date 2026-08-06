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

from project_config import DOC_TYPE_DICT, REGEX_DB_PATH

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Language
# ---------------------------------------------------------------------------

def enrich_language(text: str) -> dict:
    if not text or len(text) < 50:
        return {"language_detected": "und"}

    sample = text[:3000].lower()
    fr = len(re.findall(
        r"\b(les?|la|le|des?|du|de|et|pour|dans|sur|avec|est|sont|que|qui|ce|cette|ces)\b",
        sample,
    )) + len(re.findall(r"[éèêëàâäôöûüç]", sample))
    en = len(re.findall(
        r"\b(the|and|or|to|of|in|for|on|with|is|are|this|that|these|those|be|have|do|will|can)\b",
        sample,
    ))

    if fr > 8 and en > 8:
        return {"language_detected": "Bil"}
    if fr > en * 1.8:
        return {"language_detected": "French / Français"}
    if en > fr * 1.8:
        return {"language_detected": "English / Anglais"}
    return {"language_detected": "Bil" if (fr + en) > 5 else "und"}


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