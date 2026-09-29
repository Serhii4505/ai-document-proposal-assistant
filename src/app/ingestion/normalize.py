"""Text normalization that never executes or interprets source content."""

from __future__ import annotations

import re
import unicodedata


_HORIZONTAL_WHITESPACE = re.compile(r"[^\S\n]+")
_EXCESS_NEWLINES = re.compile(r"\n{3,}")


def normalize_text(value: str) -> str:
    """Normalize Unicode and whitespace while preserving paragraph boundaries."""

    normalized = unicodedata.normalize("NFKC", value.replace("\x00", ""))
    normalized = "".join(
        character
        for character in normalized
        if character in "\n\t" or unicodedata.category(character) != "Cc"
    )
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _HORIZONTAL_WHITESPACE.sub(" ", normalized)
    normalized = "\n".join(line.strip() for line in normalized.splitlines())
    return _EXCESS_NEWLINES.sub("\n\n", normalized).strip()

