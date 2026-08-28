from __future__ import annotations

import unicodedata
from typing import Any, Dict


COMMON_PUNCT = {
    "-",
    "_",
    ".",
    ",",
    ":",
    ";",
    "'",
    '"',
    "`",
    "!",
    "?",
    "/",
    "\\",
    "|",
    "(",
    ")",
    "[",
    "]",
    "{",
    "}",
    "<",
    ">",
    "·",
    "•",
    "，",
    "。",
    "：",
    "；",
    "！",
    "？",
    "、",
    "（",
    "）",
    "【",
    "】",
    "《",
    "》",
    "“",
    "”",
    "‘",
    "’",
}


def normalize_for_text_match(text: Any) -> str:
    """Casefold and remove whitespace plus common punctuation for text rendering checks."""
    if text is None:
        return ""
    out = []
    for ch in unicodedata.normalize("NFKC", str(text)):
        if ch.isspace() or ch in COMMON_PUNCT:
            continue
        out.append(ch.casefold())
    return "".join(out)


def edit_distance(a: Any, b: Any) -> int:
    a = "" if a is None else str(a)
    b = "" if b is None else str(b)
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    if len(a) < len(b):
        short, long = a, b
    else:
        short, long = b, a
    prev = list(range(len(short) + 1))
    for i, c_long in enumerate(long, start=1):
        cur = [i]
        for j, c_short in enumerate(short, start=1):
            cur.append(
                min(
                    cur[j - 1] + 1,
                    prev[j] + 1,
                    prev[j - 1] + (0 if c_short == c_long else 1),
                )
            )
        prev = cur
    return prev[-1]


def char_error_rate(detected_text: Any, expected_text: Any) -> float:
    expected = "" if expected_text is None else str(expected_text)
    dist = edit_distance(detected_text, expected)
    return dist / max(1, len(expected))


def text_match_metrics(detected_text: Any, expected_text: Any) -> Dict[str, Any]:
    detected = "" if detected_text is None else str(detected_text)
    expected = "" if expected_text is None else str(expected_text)
    norm_detected = normalize_for_text_match(detected)
    norm_expected = normalize_for_text_match(expected)
    dist = edit_distance(detected, expected)
    return {
        "expected_text": expected,
        "detected_text": detected,
        "exact_match": detected == expected,
        "normalized_match": bool(norm_expected) and norm_detected == norm_expected,
        "edit_distance": dist,
        "cer": dist / max(1, len(expected)),
    }
