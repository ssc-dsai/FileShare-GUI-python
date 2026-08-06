# Litigation/utils/tombstone_extractor.py
"""Extract key tombstone / structured data from litigation text (regex, no LLM)."""

from __future__ import annotations

import re
from pathlib import Path


def extract_tombstone_data(text: str, file_path: Path) -> dict:
    data = {
        "Source_File": file_path.name,
        "Plaintiff_Name": "Not Found",
        "Defendant_Name": "Not Found",
        "Case_Number": "Not Found",
        "Date_of_Incident": "Not Found",
        "Claim_Amount": "Not Found",
        "Key_File_Reference": "Not Found",
        "Document_Type": file_path.suffix.upper().replace(".", "") or "UNKNOWN",
    }
    if not text:
        return data

    m = re.search(r"(?i)(plaintiff|claimant|petitioner)\s*[:\-]\s*([^\n,;]+)", text)
    if m:
        data["Plaintiff_Name"] = m.group(2).strip()[:200]

    m = re.search(r"(?i)(defendant|respondent)\s*[:\-]\s*([^\n,;]+)", text)
    if m:
        data["Defendant_Name"] = m.group(2).strip()[:200]

    m = re.search(
        r"(?i)(case\s*no\.?|file\s*no\.?|court\s*file|docket(?:\s*no\.?)?)\s*[:\-#]?\s*([^\n]+)",
        text,
    )
    if m:
        data["Case_Number"] = m.group(2).strip()[:120]

    m = re.search(
        r"(?i)(date of incident|incident date|occurred on|date of loss)\s*[:\-]\s*([^\n]+)",
        text,
    )
    if m:
        data["Date_of_Incident"] = m.group(2).strip()[:80]

    m = re.search(
        r"(?i)(claim amount|damages|value of claim|settlement)\s*[:\-]?\s*\$?\s*([\d,]+(?:\.\d+)?)",
        text,
    )
    if m:
        data["Claim_Amount"] = f"${m.group(2).strip()}"

    m = re.search(r"(?i)(file class|imcc|full_file_class)\s*[:\-]?\s*([^\n]+)", text)
    if m:
        data["Key_File_Reference"] = m.group(2).strip()[:120]

    return data


def merge_tombstones(rows: list[dict]) -> dict:
    """Prefer first non-'Not Found' value for each key across documents."""
    keys = [
        "Plaintiff_Name",
        "Defendant_Name",
        "Case_Number",
        "Date_of_Incident",
        "Claim_Amount",
        "Key_File_Reference",
    ]
    merged = {k: "Not Found" for k in keys}
    sources = []
    for row in rows:
        sources.append(row.get("Source_File", ""))
        for k in keys:
            if merged[k] == "Not Found" and row.get(k) and row[k] != "Not Found":
                merged[k] = row[k]
    merged["Source_Files"] = "; ".join(s for s in sources if s)
    return merged