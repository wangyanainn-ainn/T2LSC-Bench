# Benchmark Schema

## `seeds.jsonl`

Each line defines one stable physical subject and its native text anchor. English and Chinese descriptions, anchors, and the aligned and two stress-test target strings are included.

## `cases.jsonl`

Each line contains:

- `case_id`: unique case identifier;
- `seed_id`: parent seed identifier;
- `language`: `en` or `zh`;
- `relation`: `aligned`, `conflict_1`, or `conflict_2`;
- `scene_openness`: `closed` or `open`;
- `prompt_mode`: `natural` or `anti_leakage`;
- `subject_description`: predefined subject identity and default structure;
- `text_anchor`: designated native text-bearing region;
- `target_text`: string to render at the anchor;
- `prompt`: complete generation prompt used for the case.

There are 50 seeds and 24 cases per seed, yielding 1,200 cases.
