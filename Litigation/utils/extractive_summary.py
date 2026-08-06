# Litigation/utils/extractive_summary.py
"""
Build a short extractive summary from document text (no generative LLM).
Keeps high-signal sentences for semantic search against large corpora.
"""

from __future__ import annotations

import re

# Words that often mark important litigation content
_SIGNAL = re.compile(
    r"(?i)\b("
    r"plaintiff|defendant|claimant|respondent|court|judge|order|motion|"
    r"affidavit|complaint|statement of claim|damages|settlement|contract|"
    r"breach|negligence|liability|indemnity|jurisdiction|evidence|"
    r"exhibit|hearing|trial|appeal|judgment|award|amount|\$|dated|between"
    r")\b"
)


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 40]


def extractive_summary(text: str, max_chars: int = 1200) -> str:
    """
    Prefer signal-rich sentences; fall back to head of document.
    Caps length so the package stays small enough to use as a query.
    """
    text = (text or "").strip()
    if not text:
        return ""

    # Drop vision/meta noise
    text = re.sub(r"\[VISION_FLAG:[^\]]*\]", " ", text)
    text = re.sub(r"Original Path\s*:.*", " ", text)

    sentences = _split_sentences(text)
    if not sentences:
        return text[:max_chars]

    scored = []
    for i, s in enumerate(sentences):
        score = len(_SIGNAL.findall(s)) * 3
        score += 2 if i < 3 else 0          # early sentences often matter
        score += 1 if any(ch.isdigit() for ch in s) else 0
        scored.append((score, i, s))

    scored.sort(key=lambda x: (-x[0], x[1]))

    chosen: list[str] = []
    length = 0
    for score, _i, s in scored:
        if score <= 0 and chosen:
            continue
        if length + len(s) + 1 > max_chars and chosen:
            break
        chosen.append(s)
        length += len(s) + 1

    if not chosen:
        return text[:max_chars]

    # Preserve roughly original order for readability
    ordered = sorted(chosen, key=lambda s: sentences.index(s) if s in sentences else 0)
    return " ".join(ordered)[:max_chars]