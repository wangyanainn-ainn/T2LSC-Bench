# Generation Prompt Templates

The released `benchmark/cases.jsonl` contains every fully instantiated English and Chinese prompt. The templates below summarize the exact construction.

## Natural Prompt

```text
Please generate a realistic image.

Scene:
{subject_description}

Scene openness requirements:
- Number of surrounding objects: {num_objects}
- Background density: {background_density}
- Camera distance: {camera_distance}

Text requirement:
The {text_role} {text_anchor} must read exactly: "{target_text}".
The text should be clearly readable, appear as one of the most prominent identifiers of the subject, and look like an original part of the subject design rather than an extra label, sticker, banner, lightbox, hanging tag, or separate sign.
```

## Anti-Leakage Prompt

The anti-leakage condition appends the following constraints to the complete natural prompt:

```text
Constraints:
1. Do not generate any other text, letters, numbers, or symbols besides the specified target text.
2. Do not add extra elements that would change the original semantic interpretation of the scene.
3. Do not propagate the meaning, attributes, or category implied by the target text into the subject or the background.
4. Do not make the target text appear more reasonable by adding supporting scene content, changing the subject appearance, or reconstructing the scene semantics.
5. Even if the target text conflicts with the scene semantics, the subject and scene content must remain unchanged, and the target text should be rendered directly and accurately.
```

Closed scenes use `1-3`, `low`, and `mid-shot`. Open scenes use `4-6`, `medium`, and `mid-to-far shot`. Chinese cases use the corresponding fixed Chinese instructions included in `cases.jsonl`.
