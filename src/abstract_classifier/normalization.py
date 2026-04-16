from __future__ import annotations

import re
import unicodedata
from typing import Any

DOI_PREFIX_RE = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE)
NON_ALNUM_RE = re.compile(r"[^0-9a-z]+")
WHITESPACE_RE = re.compile(r"\s+")


def normalize_doi(value: Any) -> str:
    text = _coerce_text(value).lower()
    if not text:
        return ""
    text = DOI_PREFIX_RE.sub("", text)
    return text.strip().rstrip(".;,)")


def normalize_title(value: Any) -> str:
    text = _coerce_text(value)
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.lower()
    text = NON_ALNUM_RE.sub(" ", text)
    return WHITESPACE_RE.sub(" ", text).strip()


def normalize_year(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None

    text = _coerce_text(value)
    if not text:
        return None

    try:
        number = float(text)
    except ValueError:
        return None

    if not number.is_integer():
        return None
    return int(number)


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text
