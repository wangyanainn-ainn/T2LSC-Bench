# T2LSC-Bench

**T2LSC-Bench** is a controlled diagnostic benchmark for localized semantic control in text-to-image generation. It evaluates whether a model can render target text at a designated native text anchor while preserving the predefined subject identity and preventing target-text-associated semantics from appearing in non-textual content outside that anchor.

Semantically matched targets provide a reference condition, while cross-domain targets act as diagnostic stress probes. A stress probe is not itself labeled as leakage: SLR is positive only when visible, target-text-associated, non-textual evidence appears outside the anchor beyond the default subject context.


## Repository Structure

```text
T2LSC-Bench/
|-- benchmark/
|   |-- seeds.jsonl              # 50 subject-anchor seeds
|   |-- cases.jsonl              # 1,200 bilingual prompt cases
|   `-- SCHEMA.md                # fields and controlled factors
|-- evaluation/
|   |-- main.py                  # end-to-end evaluation entry point
|   |-- ocr_eval.py              # PaddleOCR evidence extraction
|   |-- text_vlm_judge.py        # anchor-aware VLM text verifier
|   |-- text_fusion.py           # OCR-VLM fusion rules for TAA
|   |-- vlm_eval.py              # blinded SSP/SLR evaluation
|   |-- prompts.py               # fixed blinded semantic prompt
|   |-- text_metrics.py          # string-matching utilities
|   |-- utils.py                 # input/output and image utilities
|   `-- metrics.py               # TAA, SSP, SLR, and cSLR aggregation
|-- docs/
|   `-- LABELING_GUIDE.md        # decision boundaries and manual review
|-- prompts/
|   |-- generation_templates.md  # natural and anti-leakage templates
|   |-- taa_vlm_judge.txt        # text-verification prompt
|   `-- semantic_blind_judge.txt # blinded semantic prompt
|-- .env.example
|-- requirements.txt
`-- README.md
```

## Benchmark Composition

Each of the 50 seeds defines a concrete physical subject, its default identity or function, and a native text-bearing region. Every seed is expanded over four controlled factors:

| Factor | Conditions |
|---|---|
| Semantic relation | aligned, conflict 1, conflict 2 |
| Scene openness | closed, open |
| Prompt mode | natural, anti-leakage |
| Language | English, Chinese |

This yields `24` cases per seed and **1,200 prompt cases per evaluated generator**. 

## Evaluation Protocol

The implementation contains two independent branches:

1. **Text rendering:** PaddleOCR provides character-level evidence, and an anchor-aware VLM verifies content, readability, and placement. Fixed fusion rules produce the TAA label; unresolved cases are marked with `needs_review=true`.
2. **Semantic evaluation:** a blinded VLM judge receives only the image, subject description, text anchor, and target text. The semantic-relation label, prompt mode, full generation prompt, and generator identity are not passed to this judge.

The protocol reports:

- **TAA:** exact target-text rendering at the designated anchor;
- **SSP:** preservation of the predefined subject identity;
- **SLR:** target-text-associated non-textual evidence outside the anchor beyond the default subject context;
- **cSLR:** SLR among samples with exact anchor-text rendering.

Extra or repeated text outside the anchor is not SLR by itself. Generic subject degradation is also not SLR unless the visible change specifically supports the target-text semantics.

## Installation

Python 3.10 or later is recommended.

```bash
pip install -r requirements.txt
```

PaddleOCR additionally requires a PaddlePaddle build compatible with the local operating system and hardware. Install PaddlePaddle using its official platform-specific instructions before running the full pipeline.

## Input Format

The evaluator accepts JSON, JSONL, or CSV. Each sample requires an image path and the metadata used by the two judges:

```json
{
  "id": "sample-001",
  "image_path": "path/to/image.png",
  "subject_description": "a motor-oil jug with a front product label",
  "subject_name": "motor-oil jug",
  "text_anchor": "front label",
  "target_text": "APPLE JUICE"
}
```

Evaluation inputs are separate from `benchmark/cases.jsonl` because generated image paths depend on the generator and local storage layout.

## Run Evaluation

VLM calls use an OpenAI-compatible multimodal Chat Completions endpoint that accepts image data URLs.

```bash
export OPENAI_API_KEY="your-key"
export API_BASE_URL="https://your-endpoint/v1"
export AUDIT_MODEL="gemini-3.1-pro-preview"
export TEXT_JUDGE_MODEL="gemini-3.1-pro-preview"
export MM_EVAL_INPUT="inputs/samples.jsonl"
export MM_EVAL_OUTPUT="outputs/results.jsonl"
python -m evaluation.main
```

For PowerShell, set variables using `$env:NAME="value"`. Optional settings include:

```bash
export OCR_MIN_SCORE=0.5
export TEXT_JUDGE_OVERRIDE_CONFIDENCE=0.7
export MM_EVAL_IMAGE_MAX_SIDE=1600
export SKIP_EXISTING=1
```

The same variables are listed in [`.env.example`](.env.example).

Before reporting final TAA, manually resolve records with `needs_review=true`. The semantic branch may return `uncertain` when visible evidence is insufficient; such labels are excluded only from metrics that require the corresponding judgment.
The complete decision boundaries are summarized in [`docs/LABELING_GUIDE.md`](docs/LABELING_GUIDE.md).

## Compute Metrics

```bash
python evaluation/metrics.py outputs/results.jsonl
```

The script prints each metric together with its valid denominator. It performs no API calls and contains no paper results.

## Reproducibility Scope

This repository releases the benchmark definitions, complete generation prompts, fixed evaluation prompts, fusion logic, and metric implementation. It intentionally excludes generated images, model outputs, aggregate result tables, credentials, repair utilities, and provider-specific generation clients. Exact image-generation reproduction also depends on access to the evaluated proprietary model versions and their service-side behavior at the time of evaluation.

## License

A license is not included in this draft. Add the license approved by all authors before making the repository public; otherwise, third parties do not receive permission to reuse the released artifacts.

## Contact Information

Project Maintainer: Wang Yan

Author：Yan Wang, Xinyi Hou, Weiguo Lin, Junjun Si, and Siwei Ma

Project Link: [https://github.com/wangyanainn-ainn/T2LSC-Bench]

Note: This project is for academic research purposes only. Please comply with relevant laws and regulations and API usage terms.
