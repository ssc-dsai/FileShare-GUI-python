# Litigation/utils/tombstone_parse.py
"""Parse aggregated tombstone block from a compact litigation package."""

from __future__ import annotations

import re

TOMBSTONE_KEYS = [
    "Plaintiff_Name",
    "Defendant_Name",
    "Case_Number",
    "Date_of_Incident",
    "Claim_Amount",
    "Key_File_Reference",
]


def parse_tombstone_from_package(text: str) -> dict[str, str]:
    """
    Extract key: value pairs from:
      === TOMBSTONE / KEY FACTS (AGGREGATED) ===
    """
    result = {k: "" for k in TOMBSTONE_KEYS}
    if not text:
        return result

    # Isolate tombstone section if present
    m = re.search(
        r"=== TOMBSTONE / KEY FACTS[^=]*===\s*(.*?)(?:===|\Z)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    block = m.group(1) if m else text

    for key in TOMBSTONE_KEYS:
        pat = rf"{re.escape(key)}\s*:\s*(.+)"
        km = re.search(pat, block, flags=re.IGNORECASE)
        if km:
            val = km.group(1).strip()
            if val and val.lower() not in {"not found", "n/a", "none", "-"}:
                result[key] = val
    return result




def tombstone_query_text(tomb: dict[str, str]) -> str:
    """Build BM25 query string from non-empty tombstone values only."""
    parts = []
    for key in TOMBSTONE_KEYS:
        val = (tomb.get(key) or "").strip()
        if val:
            parts.append(val)
    return " ".join(parts)


def tokenize(text: str) -> list[str]:
    text = (text or "").lower()
    return re.findall(r"[a-z0-9_$]+", text)