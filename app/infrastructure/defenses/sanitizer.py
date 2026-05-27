"""Input sanitization — Unicode NFKC normalization + control-character stripping.

NFKC collapses compatibility characters (e.g. fullwidth/zero-width variants used to
smuggle instructions past naive filters) into their canonical form. Control characters
(Unicode category C*) are removed except newline and tab, which are legitimate in
user text. This runs before any input classification so detectors see normalized text.
"""

import unicodedata

_CONTROL_WHITELIST = frozenset({"\n", "\t"})


def sanitize_input(text: str) -> str:
    """Normalize to NFKC and drop control/format characters (keeping \\n and \\t)."""
    normalized = unicodedata.normalize("NFKC", text)
    return "".join(
        ch for ch in normalized if ch in _CONTROL_WHITELIST or unicodedata.category(ch)[0] != "C"
    )
