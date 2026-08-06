# Classification/classification_core.py
"""
Classify one document: enrichers + semantic_match.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

from Classification.config_classification import COLUMNS_ORDER, FUNCTION_MIN_SCORE, REVIEW_BELOW
from Classification.semantic_matcher import semantic_match
from Classification.enrichers import (
    apply_regex_overrides,
    enrich_document_type,
    enrich_language,
    enrich_pii,
    enrich_sensitivity,
)


def _safe(val: Any, default: str = "") -> str:
    if val is None:
        return default
    try:
        if isinstance(val, float) and np.isnan(val):
            return default
    except Exception:
        pass
    s = str(val).strip()
    return s if s and s.lower() != "nan" else default


def _finalize(row: dict) -> dict:
    for col in COLUMNS_ORDER:
        row.setdefault(col, "")
    return row


def classify_document(
    text: str,
    filename: str,
    original_path: str = "",
    embedder=None,
    hierarchy_df=None,
    indexes=None,
    vision_description: str = "N/A",
    **kwargs,
) -> dict:
    text = text or ""

    row: dict[str, Any] = {
        "filename": filename,
        "original_path": original_path or "",
        "text_length": len(text),
        "language_detected": "en",
        "Title | Titre": Path(filename).stem.replace("_", " ").title(),
        "Document Type / Type de document": "",
        "Sensitivity": "",
        "Sensibilité": "",
        "personal_information": "No",
        "vision_flagged": "No",
        "Vision_Description": "N/A",
        "needs_review": "Yes",
        "overall_confidence": 0.0,
        "Function_EN": "Unknown",
        "Function_FR": "",
        "Function_Desc_Sum_EN": "",
        "Function_Desc_Sum_FR": "",
        "Function_Match_Excerpt_EN": "",
        "Function_Match_Excerpt_FR": "",
        "Sub-Function_EN": "",
        "Sub-Function_FR": "",
        "Sub-Function_Desc_Summ_EN": "",
        "Sub-Function_Desc_Summ_FR": "",
        "Sub_Function_Match_Excerpt_EN": "",
        "Sub_Function_Match_Excerpt_FR": "",
        "Full_File_Class_No": "",
        "Business_Process_EN": "",
        "Business_Process_FR": "",
        "Records_Match_Excerpt_EN": "",
        "Records_Match_Excerpt_FR": "",
        "Retention Period": "",
        "Retention Trigger": "",
        # Not in FCP — defaults until a real source exists
        "Disposition Authorization / Autorisation de disposition": "2021/005",
        "Technical Environment | Environnement technique": "Microsoft's Distributed File System (DFS)",
        "Litigation_hold": "No",
        "Archival_value": "No",
        "critical_business_content": "No",
    }

    # ----- Enrichers (were missing from the pipeline) -----
    row.update(enrich_language(text))
    row.update(enrich_pii(text))
    row.update(enrich_sensitivity(text))
    row.update(enrich_document_type(original_path))
    row.update(apply_regex_overrides(text))  # may set personal_information, etc.

    if vision_description and str(vision_description).strip() not in ("", "N/A"):
        row["vision_flagged"] = "Yes"
        row["Vision_Description"] = str(vision_description).strip()
    else:
        row["vision_flagged"] = "No"
        row["Vision_Description"] = "N/A"

    if embedder is None or hierarchy_df is None or indexes is None:
        logger.warning(f"{filename}: embedder/hierarchy/indexes missing — Unknown")
        return _finalize(row)

    try:
        match = semantic_match(
            text=text,
            hierarchy_df=hierarchy_df,
            indexes=indexes,
            embedder=embedder,
            min_confidence=float(FUNCTION_MIN_SCORE),
        )
        if not isinstance(match, dict):
            match = {}
    except Exception as e:
        logger.error(f"{filename}: semantic_match failed: {e}", exc_info=True)
        return _finalize(row)

    for key in list(row.keys()):
        if key in match and match[key] not in (None, ""):
            row[key] = _safe(match[key], row.get(key, ""))

    conf = float(match.get("overall_confidence") or 0.0)
    row["overall_confidence"] = round(conf, 3)
    row["needs_review"] = _safe(match.get("needs_review"), "Yes")
    if conf < REVIEW_BELOW:
        row["needs_review"] = "Yes"
    if row.get("Function_EN", "Unknown") in ("", "Unknown"):
        row["needs_review"] = "Yes"

    return _finalize(row)