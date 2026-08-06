# Classification/config_classification.py
"""
Classification phase settings: hierarchy path, thresholds, Excel column order.
"""

from __future__ import annotations

from pathlib import Path

# Project root = parent of Classification/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Hierarchy (FCP)
# ---------------------------------------------------------------------------
HIERARCHY_CSV = PROJECT_ROOT / "Resources-Sources" / "fcp_CSV-UTF.csv"

# ---------------------------------------------------------------------------
# Matching thresholds (MiniLM cosine)
# ---------------------------------------------------------------------------
FUNCTION_MIN_SCORE = 0.28
SUBFUNCTION_MIN_SCORE = 0.28
RECORDS_MIN_SCORE = 0.25
REVIEW_BELOW = 0.40          # overall_confidence below this → needs_review = Yes

# Chunking for long documents
CHUNK_SIZE_TOKENS = 100
CHUNK_OVERLAP_TOKENS = 20
MATCH_EXCERPT_CHARS = 500

# ---------------------------------------------------------------------------
# Excel / CSV column order
# ---------------------------------------------------------------------------
COLUMNS_ORDER = [
    # Identity
    "filename",
    "original_path",
    "text_length",
    "language_detected",
    "Title | Titre",
    "Document Type / Type de document",
    # Sensitivity / flags
    "Sensitivity",
    "Sensibilité",
    "personal_information",
    "vision_flagged",
    "Vision_Description",
    "needs_review",
    "overall_confidence",
    # Function
    "Function_EN",
    "Function_FR",
    "Function_Desc_Sum_EN",
    "Function_Desc_Sum_FR",
    "Function_Match_Excerpt_EN",
    "Function_Match_Excerpt_FR",
    # Sub-function
    "Sub-Function_EN",
    "Sub-Function_FR",
    "Sub-Function_Desc_Summ_EN",
    "Sub-Function_Desc_Summ_FR",
    "Sub_Function_Match_Excerpt_EN",
    "Sub_Function_Match_Excerpt_FR",
    # Records / business process
    "Full_File_Class_No",
    "Business_Process_EN",
    "Business_Process_FR",
    "Records_Match_Excerpt_EN",
    "Records_Match_Excerpt_FR",
    # Retention / disposition (from hierarchy when available)
    "Retention Period",
    "Retention Trigger",
    "Disposition Authorization / Autorisation de disposition",
    "Technical Environment | Environnement technique",
    "Litigation_hold",
    "Archival_value",
    "critical_business_content",
]

# Aliases some older code may still set (mapped in core if needed)
COLUMN_ALIASES = {
    "Vision_Description": "Vision_Description",
    "vision_Description": "Vision_Description",
}