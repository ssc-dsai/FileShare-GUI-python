# Classification/hitl_review.py
"""Human-in-the-loop FCP override. Cascading Function → Sub-Function → Business Process."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from project_config import CLASSIFICATION_RESULTS_DIR, HIERARCHY_CSV

from Classification.archival_rules import archival_value_for

UNKNOWN = "Unknown"

FILL_COLS = [
    "Function_EN",
    "Function_FR",
    "Function_Desc_Sum_EN",
    "Function_Desc_Sum_FR",
    "Sub-Function_EN",
    "Sub-Function_FR",
    "Sub-Function_Desc_Summ_EN",
    "Sub-Function_Desc_Summ_FR",
    "Full_File_Class_No",
    "Business_Process_EN",
    "Business_Process_FR",
    "Retention Period",
    "Retention Trigger",
]

CLEAR_COLS = [
    "Function_Doc_Excerpt_EN",
    "Function_FCP_Excerpt_EN",
    "Function_Doc_Excerpt_FR",
    "Function_FCP_Excerpt_FR",
    "Sub_Function_Doc_Excerpt_EN",
    "Sub_Function_FCP_Excerpt_EN",
    "Sub_Function_Doc_Excerpt_FR",
    "Sub_Function_FCP_Excerpt_FR",
    "Records_Doc_Excerpt_EN",
    "Records_FCP_Excerpt_EN",
    "Records_Doc_Excerpt_FR",
    "Records_FCP_Excerpt_FR"
]

REPORTS = {
    "minilm": CLASSIFICATION_RESULTS_DIR / "classification_results_minilm.xlsx",
    "qwen3": CLASSIFICATION_RESULTS_DIR / "classification_results_qwen3.xlsx",
    "qwen3_4b": CLASSIFICATION_RESULTS_DIR / "classification_results_qwen3_4b.xlsx",
}

def report_path(embedder_key: str) -> Path:
    raw = (embedder_key or "").lower()
    if raw in REPORTS:
        return REPORTS[raw]
    if "4b" in raw:
        return REPORTS["qwen3_4b"]
    if "qwen" in raw:
        return REPORTS["qwen3"]
    return REPORTS["minilm"]

_ILLEGAL_XML = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def _sanitize_for_excel(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        out[col] = out[col].map(
            lambda v: _ILLEGAL_XML.sub("", v) if isinstance(v, str) else v
        )
    return out


def load_fcp() -> pd.DataFrame:
    if not HIERARCHY_CSV.exists():
        raise FileNotFoundError(f"FCP hierarchy not found: {HIERARCHY_CSV}")
    df = pd.read_csv(HIERARCHY_CSV, encoding="utf-8-sig", low_memory=False)
    for col in df.columns:
        if df[col].dtype == object or str(df[col].dtype) in {"string", "str"}:
            df[col] = df[col].fillna("").astype(str).str.strip()
    if "Function_EN" in df.columns:
        df = df[df["Function_EN"].astype(str).str.len() > 0].reset_index(drop=True)
    return df


def function_choices(fcp: pd.DataFrame) -> list[str]:
    vals = sorted({v for v in fcp["Function_EN"].tolist() if v})
    return [UNKNOWN] + vals


def subfunction_choices(fcp: pd.DataFrame, function_en: str) -> list[str]:
    if not function_en or function_en == UNKNOWN:
        return [UNKNOWN]
    mask = fcp["Function_EN"] == function_en
    vals = sorted({v for v in fcp.loc[mask, "Sub-Function_EN"].tolist() if v})
    return [UNKNOWN] + vals


def process_choices(fcp: pd.DataFrame, function_en: str, sub_en: str) -> list[str]:
    if not function_en or function_en == UNKNOWN or not sub_en or sub_en == UNKNOWN:
        return [UNKNOWN]
    mask = (fcp["Function_EN"] == function_en) & (fcp["Sub-Function_EN"] == sub_en)
    vals = sorted({v for v in fcp.loc[mask, "Business_Process_EN"].tolist() if v})
    return [UNKNOWN] + vals


def find_fcp_row(
    fcp: pd.DataFrame,
    function_en: str,
    sub_en: str,
    process_en: str,
) -> pd.Series | None:
    if function_en == UNKNOWN or not function_en:
        return None
    mask = fcp["Function_EN"] == function_en
    if sub_en and sub_en != UNKNOWN:
        mask = mask & (fcp["Sub-Function_EN"] == sub_en)
    if process_en and process_en != UNKNOWN:
        mask = mask & (fcp["Business_Process_EN"] == process_en)
    hits = fcp.loc[mask]
    if hits.empty:
        return None
    return hits.iloc[0]


def load_report(embedder_key: str) -> pd.DataFrame:
    path = report_path(embedder_key)
    if not path.is_file():
        raise FileNotFoundError(f"Classification report not found: {path}")
    return pd.read_excel(path, sheet_name=0)


def document_choices(df: pd.DataFrame) -> list[str]:
    if "filename" not in df.columns:
        return []
    return [str(v) for v in df["filename"].fillna("").tolist() if str(v).strip()]


def current_assignment(df: pd.DataFrame, filename: str) -> dict:
    rows = df[df["filename"].astype(str) == str(filename)]
    if rows.empty:
        return {
            "Function_EN": UNKNOWN,
            "Sub-Function_EN": UNKNOWN,
            "Business_Process_EN": UNKNOWN,
        }
    row = rows.iloc[0]
    return {
        "Function_EN": str(row.get("Function_EN", "") or UNKNOWN),
        "Sub-Function_EN": str(row.get("Sub-Function_EN", "") or UNKNOWN),
        "Business_Process_EN": str(row.get("Business_Process_EN", "") or UNKNOWN),
        "Full_File_Class_No": str(row.get("Full_File_Class_No", "") or ""),
    }


def _unknown_payload() -> dict:
    return {
        "Function_EN": "Unknown",
        "Function_FR": "Inconnu",
        "Function_Desc_Sum_EN": "",
        "Function_Desc_Sum_FR": "",
        "Sub-Function_EN": "Unknown",
        "Sub-Function_FR": "Inconnu",
        "Sub-Function_Desc_Summ_EN": "",
        "Sub-Function_Desc_Summ_FR": "",
        "Full_File_Class_No": "",
        "Business_Process_EN": "Unknown",
        "Business_Process_FR": "Inconnu",
        "Retention Period": "",
        "Retention Trigger": "",
    }


def apply_override(
    embedder_key: str,
    filename: str,
    function_en: str,
    sub_en: str,
    process_en: str,
) -> str:
    path = report_path(embedder_key)
    df = load_report(embedder_key)
    fcp = load_fcp()

    matches = df.index[df["filename"].astype(str) == str(filename)].tolist()
    if not matches:
        return f"❌ Filename not found in report: {filename}"

    if function_en == UNKNOWN or not function_en:
        payload = _unknown_payload()
    else:
        row = find_fcp_row(fcp, function_en, sub_en, process_en)
        if row is None:
            return (
                "❌ That combination is not a valid FCP row. "
                "Pick Function, then a Sub-Function listed for it, "
                "then a Business Process listed for that pair."
            )
        payload = {col: str(row.get(col, "") or "") for col in FILL_COLS}

    text_cols = list(FILL_COLS) + list(CLEAR_COLS) + [
        "needs_review",
        "confidence_category",
        "Archival_value",
    ]
    for col in text_cols:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype("string").fillna("")

    if "overall_confidence" in df.columns:
        df["overall_confidence"] = pd.to_numeric(df["overall_confidence"], errors="coerce")

    archival = archival_value_for(
        payload.get("Function_EN", ""),
        payload.get("Sub-Function_EN", ""),
        payload.get("Business_Process_EN", ""),
    )

    for idx in matches:
        for col in FILL_COLS:
            df.at[idx, col] = str(payload.get(col, "") or "")
        for col in CLEAR_COLS:
            df.at[idx, col] = ""
        if "needs_review" in df.columns:
            df.at[idx, "needs_review"] = "No"
        if "confidence_category" in df.columns:
            df.at[idx, "confidence_category"] = "Human"
        if "overall_confidence" in df.columns:
            df.at[idx, "overall_confidence"] = pd.NA
        df.at[idx, "Archival_value"] = archival

    extra = {}
    if path.exists():
        try:
            extra = pd.read_excel(path, sheet_name=None)
        except Exception:
            extra = {}

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        _sanitize_for_excel(df).to_excel(writer, sheet_name="classification", index=False)
        fcp_sheet = extra.get("FCP_Hierarchy", fcp)
        _sanitize_for_excel(fcp_sheet).to_excel(writer, sheet_name="FCP_Hierarchy", index=False)

    return (
        f"✅ Updated {filename} in {path.name}\n"
        f"Function: {payload.get('Function_EN')}\n"
        f"Sub-Function: {payload.get('Sub-Function_EN')}\n"
        f"Business Process: {payload.get('Business_Process_EN')}\n"
        f"Class No: {payload.get('Full_File_Class_No')}\n"
        f"Archival_value: {archival}\n"
        "Excerpt columns cleared."
    )