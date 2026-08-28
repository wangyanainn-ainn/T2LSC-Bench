from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .ocr_eval import evaluate_taa
from .text_fusion import fuse_text_rendering
from .text_vlm_judge import (
    call_text_rendering_judge,
    failed_text_judge_result,
    normalize_text_judge_result,
)
from .utils import load_done_ids, read_samples, write_replace_by_id
from .vlm_eval import call_ssp_slr


def compute_cslr(taa: Any, slr: Any) -> Optional[int]:
    if taa != 1:
        return None
    if slr == "uncertain" or slr is None:
        return None
    return 1 if slr == 1 else 0


def _as_tri(v: Any) -> Any:
    if v in (0, 1, "uncertain"):
        return v
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)) and v in (0, 1):
        return int(v)
    if isinstance(v, str):
        t = v.strip().lower()
        if t in {"0", "no", "false"}:
            return 0
        if t in {"1", "yes", "true"}:
            return 1
        if t in {"uncertain", "unknown", "maybe"}:
            return "uncertain"
    return "uncertain"


def main() -> None:
    input_path = Path(os.getenv("MM_EVAL_INPUT", "inputs/mm_eval_samples.json"))
    out_path = Path(os.getenv("MM_EVAL_OUTPUT", "outputs/results.jsonl"))
    out_path.parent.mkdir(parents=True, exist_ok=True)

    skip_done = (os.getenv("SKIP_EXISTING") or "1").strip().lower() in {"1", "true", "yes", "y"}
    min_ocr_score = float(os.getenv("OCR_MIN_SCORE", "0.5"))
    text_judge_enabled = (os.getenv("TEXT_JUDGE_ENABLED") or "1").strip().lower() in {"1", "true", "yes", "y"}
    text_override_confidence = float(os.getenv("TEXT_JUDGE_OVERRIDE_CONFIDENCE", "0.7"))
    sleep_s = float(os.getenv("MM_EVAL_SLEEP_SECONDS", "0") or "0")
    max_samples_raw = (os.getenv("MM_EVAL_MAX_SAMPLES") or "").strip()
    max_samples = int(max_samples_raw) if max_samples_raw else None

    samples = read_samples(input_path)
    done = load_done_ids(out_path) if skip_done else set()

    total = len(samples)
    processed = 0
    for i, s in enumerate(samples, start=1):
        if max_samples is not None and processed >= max_samples:
            break
        if skip_done and s.id in done:
            print(f"[{i}/{total}] skip {s.id}", flush=True)
            continue
        # If the image hasn't been generated yet, skip it for now (do NOT write an "uncertain" record),
        # so we can evaluate it later after generation completes.
        if not Path(s.image_path).exists():
            print(f"[{i}/{total}] skip_missing_image {s.id}", flush=True)
            continue

        stage1 = evaluate_taa(
            image_path=Path(s.image_path),
            target_text=s.target_text,
            text_anchor=s.text_anchor,
            min_score=min_ocr_score,
        )
        raw_text_judge: Any = ""
        if text_judge_enabled:
            try:
                text_judge_json, raw_text_judge = call_text_rendering_judge(
                    image_path=s.image_path,
                    expected_text=s.target_text,
                    text_anchor=s.text_anchor,
                    subject_name=s.subject_name or s.subject_description,
                )
                vlm_text = normalize_text_judge_result(text_judge_json, s.target_text)
            except Exception as e:
                vlm_text = failed_text_judge_result(f"text_judge_failed: {repr(e)}")
                raw_text_judge = ""
        else:
            vlm_text = failed_text_judge_result("text_judge_disabled")

        fused_text = fuse_text_rendering(
            stage1,
            vlm_text,
            override_confidence=text_override_confidence,
        )
        taa = fused_text.get("taa")

        # Stage 2 now runs for ALL samples (not gated by TAA)
        ssp: Any
        slr: Any
        ssp_reason: Any
        slr_reason: Any
        subject_identity: Any
        scene_cues: Any
        raw_stage2: Any
        try:
            stage2, raw = call_ssp_slr(
                image_path=s.image_path,
                subject_description=s.subject_description,
                text_anchor=s.text_anchor,
                target_text=s.target_text,
            )
            raw_stage2 = raw
            ssp = _as_tri(stage2.get("ssp"))
            slr = _as_tri(stage2.get("slr"))
            ssp_reason = stage2.get("ssp_reason") or ""
            slr_reason = stage2.get("slr_reason") or ""
            subject_identity = stage2.get("subject_identity") or ""
            scene_cues = stage2.get("scene_cues") or ""
        except Exception as e:
            ssp = "uncertain"
            slr = "uncertain"
            ssp_reason = f"stage2_failed: {repr(e)}"
            slr_reason = f"stage2_failed: {repr(e)}"
            subject_identity = ""
            scene_cues = ""
            raw_stage2 = ""

        cslr = compute_cslr(taa, slr)

        rec: Dict[str, Any] = {
            "id": s.id,
            "image_path": s.image_path,
            "subject_description": s.subject_description,
            "subject_name": s.subject_name,
            "text_anchor": s.text_anchor,
            "target_text": s.target_text,
            "relation": s.relation,
            "prompt": s.prompt,
            "taa": taa,
            "taa_reason": fused_text.get("taa_reason"),
            "ocr_taa": stage1.get("taa"),
            "ocr_taa_reason": stage1.get("taa_reason"),
            "visible_text": stage1.get("visible_text"),
            "text_location": stage1.get("text_location"),
            "ocr_raw": stage1.get("ocr_raw"),
            "case_id": s.id,
            "expected_text": stage1.get("expected_text"),
            "ocr_detected_text": stage1.get("ocr_detected_text"),
            "ocr_exact_match": stage1.get("ocr_exact_match"),
            "ocr_normalized_match": stage1.get("ocr_normalized_match"),
            "ocr_edit_distance": stage1.get("ocr_edit_distance"),
            "ocr_cer": stage1.get("ocr_cer"),
            "ocr_success": stage1.get("ocr_success"),
            **vlm_text,
            "ocr_vlm_agreement": fused_text.get("ocr_vlm_agreement"),
            "text_quality": fused_text.get("text_quality"),
            "final_text_success": fused_text.get("final_text_success"),
            "decision_source": fused_text.get("decision_source"),
            "needs_review": fused_text.get("needs_review"),
            "ssp": ssp,
            "ssp_reason": ssp_reason,
            "slr": slr,
            "slr_reason": slr_reason,
            "subject_identity": subject_identity,
            "scene_cues": scene_cues,
            "cslr": cslr,
            "raw_model_output_text_judge": raw_text_judge,
            "raw_model_output_stage2": raw_stage2,
        }

        write_replace_by_id(out_path, rec)
        print(f"[{i}/{total}] done {s.id} taa={rec['taa']} cslr={rec['cslr']}", flush=True)
        processed += 1
        if sleep_s > 0:
            time.sleep(sleep_s)

    print(f"[evaluation] wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
