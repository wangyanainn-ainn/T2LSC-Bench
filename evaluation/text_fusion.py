from __future__ import annotations

from typing import Any, Dict


def _ocr_correct(stage1: Dict[str, Any]) -> bool:
    return bool(stage1.get("ocr_success") or stage1.get("ocr_exact_match") or stage1.get("ocr_normalized_match"))


def _vlm_correct(vlm: Dict[str, Any]) -> bool:
    return bool(vlm.get("vlm_exact_match") or vlm.get("vlm_normalized_match"))


def fuse_text_rendering(
    stage1: Dict[str, Any],
    vlm: Dict[str, Any],
    *,
    override_confidence: float = 0.7,
) -> Dict[str, Any]:
    ocr_ok = _ocr_correct(stage1)
    vlm_ok = _vlm_correct(vlm)
    vlm_conf = float(vlm.get("vlm_confidence") or 0.0)
    vlm_minor = bool(vlm.get("vlm_minor_character_error"))
    vlm_bad = bool(vlm.get("vlm_unreadable_or_ambiguous")) or not bool(vlm.get("vlm_text_readable"))
    vlm_error = bool(vlm.get("vlm_judge_error"))
    agreement = ocr_ok == vlm_ok

    if vlm_error:
        if ocr_ok:
            return {
                "ocr_vlm_agreement": False,
                "text_quality": "exact",
                "final_text_success": True,
                "decision_source": "ocr_only",
                "needs_review": False,
                "taa": 1,
                "taa_reason": "ocr_success_text_judge_unavailable",
            }
        return {
            "ocr_vlm_agreement": False,
            "text_quality": "ambiguous",
            "final_text_success": False,
            "decision_source": "manual_review",
            "needs_review": True,
            "taa": "uncertain",
            "taa_reason": "ocr_failed_text_judge_unavailable",
        }

    if ocr_ok and vlm_ok:
        return {
            "ocr_vlm_agreement": True,
            "text_quality": "exact",
            "final_text_success": True,
            "decision_source": "ocr_and_vlm",
            "needs_review": False,
            "taa": 1,
            "taa_reason": "ocr_and_vlm_text_match",
        }

    if not ocr_ok and vlm_ok and vlm_conf >= override_confidence:
        return {
            "ocr_vlm_agreement": False,
            "text_quality": "exact",
            "final_text_success": True,
            "decision_source": "vlm_override_ocr",
            "needs_review": False,
            "taa": 1,
            "taa_reason": "vlm_override_ocr_text_match",
        }

    if ocr_ok and (not vlm_ok or vlm_bad):
        return {
            "ocr_vlm_agreement": False,
            "text_quality": "ambiguous",
            "final_text_success": False,
            "decision_source": "manual_review",
            "needs_review": True,
            "taa": "uncertain",
            "taa_reason": "ocr_success_but_vlm_failed_or_unreadable",
        }

    if vlm_minor:
        return {
            "ocr_vlm_agreement": agreement,
            "text_quality": "minor_error",
            "final_text_success": False,
            "decision_source": "manual_review" if not agreement else "ocr_and_vlm",
            "needs_review": not agreement or vlm_conf < override_confidence,
            "taa": 0,
            "taa_reason": "vlm_minor_character_error",
        }

    if not ocr_ok and vlm_ok and vlm_conf < override_confidence:
        return {
            "ocr_vlm_agreement": False,
            "text_quality": "ambiguous",
            "final_text_success": False,
            "decision_source": "manual_review",
            "needs_review": True,
            "taa": "uncertain",
            "taa_reason": "ocr_failed_vlm_match_low_confidence",
        }

    return {
        "ocr_vlm_agreement": True,
        "text_quality": "failure",
        "final_text_success": False,
        "decision_source": "ocr_and_vlm",
        "needs_review": False,
        "taa": 0,
        "taa_reason": "ocr_and_vlm_text_failed",
    }
