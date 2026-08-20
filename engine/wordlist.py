"""Small blacklist of words to avoid forming accidentally in the random fill
(plan §5.1 step 4 — "no accidental words" check).

Kept intentionally short and family-safe: enough to catch the obvious slurs and
crude words that would be unacceptable in a kids' activity book, without
shipping a large offensive corpus. Users can extend it via
``PuzzleConfig.extra_blacklist``.
"""
from __future__ import annotations

# Uppercase, length >= 3 (shorter tokens create too many false positives).
DEFAULT_BLACKLIST: frozenset[str] = frozenset(
    {
        "SHIT",
        "CRAP",
        "PISS",
        "FUCK",
        "COCK",
        "DICK",
        "TITS",
        "SLUT",
        "DAMN",
        "HELL",
        "ARSE",
        "TWAT",
        "WANK",
        "JERK",
        "BUTT",
    }
)


def build_blacklist(extra: list[str] | None = None) -> frozenset[str]:
    words = set(DEFAULT_BLACKLIST)
    for w in extra or []:
        w2 = (w or "").strip().upper()
        if len(w2) >= 3 and w2.isalpha():
            words.add(w2)
    return frozenset(words)
