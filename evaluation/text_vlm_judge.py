from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Tuple

from .text_metrics import text_match_metrics
from .utils import b64_image, load_dotenv_if_present
from .vlm_eval import _is_retryable_error


TEXT_RENDERING_PROMPT = """You are a strict multimodal text rendering judge. Use only visible evidence from the image.
Your task is ONLY to decide whether the main target text at the specified text anchor is correctly rendered.
Do NOT evaluate semantic leakage, subject leakage, scene leakage, image aesthetics, or whether the requested text makes sense.
Ignore unrelated background text unless it is at the specified anchor and appears to be the main target text.

Inputs:
- expected target text: {expected_text}
- subject: {subject_name}
- text anchor: {text_anchor}

Return a SINGLE JSON object only (no markdown, no extra text). Schema:
{{
  "detected_text": "string",
  "text_visible": true | false,
  "text_readable": true | false,
  "exact_match": true | false,
  "normalized_match": true | false,
  "minor_character_error": true | false,
  "unreadable_or_ambiguous": true | false,
  "confidence": 0.0,
  "reason": "short evidence-based explanation"
}}

Judgment rules:
- exact_match is true only when the visible main target text exactly matches expected target text.
- normalized_match may ignore case, whitespace, and common punctuation.
- minor_character_error is true when the target text is mostly readable and clearly intended, but has a small character-level error.
- unreadable_or_ambiguous is true when you cannot reliably read the target text at the anchor.
- confidence must be a number from 0 to 1.
"""


def _openai_client():
    load_dotenv_if_present()
    from openai import OpenAI  # type: ignore
    import httpx  # type: ignore

    base_url = (os.getenv("API_BASE_URL") or "").strip() or None
    api_key = (
        (os.getenv("OPENAI_API_KEY") or "").strip()
        or (os.getenv("IMAGE_API_KEY") or "").strip()
        or (os.getenv("VLLM_API_KEY") or "").strip()
    )
    if not api_key:
        raise RuntimeError("Missing IMAGE_API_KEY / OPENAI_API_KEY / VLLM_API_KEY in env/.env")

    timeout_s = float(os.getenv("AUDIT_TIMEOUT_SECONDS", "180"))
    connect_s = float(os.getenv("AUDIT_CONNECT_TIMEOUT_SECONDS", "30"))
    http_client = httpx.Client(timeout=httpx.Timeout(timeout_s, connect=connect_s))
    return OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)


def _extract_json_object(text: str) -> Dict[str, Any]:
    text = text or ""
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        obj = json.loads(text[start : end + 1])
        if isinstance(obj, dict):
            return obj
    raise ValueError(f"Model did not return valid JSON. content_prefix={text[:200]!r}")


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _as_confidence(v: Any) -> float:
    try:
        value = float(v)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, value))


def call_text_rendering_judge(
    image_path: str,
    expected_text: str,
    text_anchor: str,
    subject_name: str,
) -> Tuple[Dict[str, Any], str]:
    model = (os.getenv("TEXT_JUDGE_MODEL") or os.getenv("AUDIT_MODEL") or os.getenv("MM_EVAL_MODEL") or "gpt-4o-mini").strip()
    client = _openai_client()
    max_retries = int((os.getenv("AUDIT_MAX_RETRIES") or "3").strip() or "3")
    retry_sleep_s = float((os.getenv("AUDIT_RETRY_SLEEP_SECONDS") or "2").strip() or "2")
    msg = TEXT_RENDERING_PROMPT.format(
        expected_text=expected_text,
        text_anchor=text_anchor,
        subject_name=subject_name,
    )
    image_b64 = b64_image(Path(image_path))

    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": msg},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                        ],
                    }
                ],
                temperature=0,
            )
            raw = resp.choices[0].message.content or ""
            return _extract_json_object(raw), raw
        except Exception as e:
            last_err = e
            if attempt >= max_retries or not _is_retryable_error(e):
                raise
            time.sleep(retry_sleep_s)
    raise RuntimeError(f"unreachable: exhausted retries but no result; last_err={last_err!r}")


def normalize_text_judge_result(parsed: Dict[str, Any], expected_text: str) -> Dict[str, Any]:
    detected = str(parsed.get("detected_text") or "")
    metrics = text_match_metrics(detected, expected_text)
    return {
        "vlm_detected_text": detected,
        "vlm_text_visible": _as_bool(parsed.get("text_visible")),
        "vlm_text_readable": _as_bool(parsed.get("text_readable")),
        "vlm_exact_match": _as_bool(parsed.get("exact_match")) or bool(metrics["exact_match"]),
        "vlm_normalized_match": _as_bool(parsed.get("normalized_match")) or bool(metrics["normalized_match"]),
        "vlm_minor_character_error": _as_bool(parsed.get("minor_character_error")),
        "vlm_unreadable_or_ambiguous": _as_bool(parsed.get("unreadable_or_ambiguous")),
        "vlm_confidence": _as_confidence(parsed.get("confidence")),
        "vlm_reason": str(parsed.get("reason") or ""),
        "vlm_judge_error": False,
    }


def failed_text_judge_result(reason: str) -> Dict[str, Any]:
    return {
        "vlm_detected_text": "",
        "vlm_text_visible": False,
        "vlm_text_readable": False,
        "vlm_exact_match": False,
        "vlm_normalized_match": False,
        "vlm_minor_character_error": False,
        "vlm_unreadable_or_ambiguous": True,
        "vlm_confidence": 0.0,
        "vlm_reason": reason,
        "vlm_judge_error": True,
    }
