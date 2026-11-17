# Classification/archival_rules.py
from __future__ import annotations

from pathlib import Path

from project_config import PROJECT_ROOT

RULES_PATH = PROJECT_ROOT / "Resources-Sources" / "archival_rules.txt"


def load_archival_rules(path: Path | None = None) -> list[tuple[str, str, str]]:
    p = path or RULES_PATH
    if not p.is_file():
        return []
    rules = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [x.strip() for x in line.split("|")]
        while len(parts) < 3:
            parts.append("*")
        fn, sub, proc = parts[0], parts[1], parts[2]
        if fn:
            rules.append((fn, sub or "*", proc or "*"))
    return rules


def is_archival(
    function_en: str,
    sub_en: str,
    process_en: str,
    rules: list[tuple[str, str, str]] | None = None,
) -> bool:
    rules = rules if rules is not None else load_archival_rules()
    fn = (function_en or "").strip()
    sub = (sub_en or "").strip()
    proc = (process_en or "").strip()
    if not fn or fn.lower() == "unknown":
        return False
    for r_fn, r_sub, r_proc in rules:
        if r_fn != "*" and r_fn.casefold() != fn.casefold():
            continue
        if r_sub != "*" and r_sub.casefold() != sub.casefold():
            continue
        if r_proc != "*" and r_proc.casefold() != proc.casefold():
            continue
        return True
    return False


def archival_value_for(function_en: str, sub_en: str, process_en: str) -> str:
    return "Yes" if is_archival(function_en, sub_en, process_en) else "No"