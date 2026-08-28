# Labeling Guide

This guide summarizes the final decision boundaries used by the released evaluator and by manual review.

## TAA

- `1`: the complete target string is readable at the designated anchor and contains no visible character error.
- `0`: the anchor text has missing, substituted, malformed, or additional characters, or is rendered at the wrong location.
- `uncertain`: the available visual evidence remains insufficient after inspection.

Exact and normalized matches are accepted by the automated fusion rule. Normalization removes whitespace and applies case folding to Latin text; it does not correct character substitutions, insertions, or deletions.

## SSP

- `1`: the predefined subject remains visually identifiable and preserves its core category or function.
- `0`: visible evidence shows that the subject has been replaced or reinterpreted as a different category or function.
- `uncertain`: the subject cannot be reliably located or matched.

SSP failure does not by itself imply semantic leakage.

## SLR

- `1`: at least one clearly visible, non-textual cue outside the anchor supports the target-text semantics beyond the default subject context.
- `0`: no cue satisfies all leakage criteria, or candidate cues are naturally explained by the default subject context.
- `uncertain`: critical evidence is ambiguous or its location relative to the anchor cannot be determined.

Repeated target text, external readable text, ordinary contextual objects, generic blur, and unrelated structural degradation do not constitute SLR by themselves.

## Manual Review

Records with `needs_review=true` require inspection before final TAA aggregation. Reviewers should inspect the image without using generator identity or controlled-condition labels as evidence and replace the provisional TAA value with the final adjudicated label. Semantic `uncertain` labels remain excluded from their metric-specific denominators unless they are separately adjudicated.
