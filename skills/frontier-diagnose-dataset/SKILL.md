---
name: frontier-diagnose-dataset
description: Diagnose a Frontier physics dataset (fields, units, layout, NaN/outliers, splits, leakage, versions) with the tools of the `frontier` context server, without changing it. Use when asked what is wrong with a dataset, to review a dataset card, or before proposing a cleaning recipe.
---

# Diagnose a Frontier dataset

Tools (from the `frontier` MCP server): `dataset.describe`, `dataset.sample_stats` (use
`lod: 2` on large surfaces, at most 3 samples), `quality.report`, `quality.check_leakage`,
`version.log`, `judge.choice` (families `field_class`, `units`, `layout`). Resources:
`frontier://datasets`, `frontier://dataset/{name}/card`, `frontier://dataset/{name}/provenance`.

1. Describe the dataset; note sample kind, count, time axis, fields with declared units,
   parameters with ranges, splits and strategy, head version.
2. Sample statistics on two or three samples: array shapes and `length` vs `n_points` /
   `n_faces`, NaN/inf counts, min/max/percentiles, `robust_z_max`.
3. For each field ask the judge which canonical quantity it holds and whether the declared
   unit is plausible for the value range and the conditions. Pass derived state only.
4. Quality report and leakage check.
5. Report the problems in order of severity, each with the op that fixes it
   (`prep.fields.rename`, `prep.fields.set_units`, `prep.frames.dedupe`,
   `prep.split.parameter_holdout`, `prep.geometry.near_duplicates`, `prep.samples.drop`).

Never run an op in a diagnosis. Never invent a number: every figure in the report comes
from a tool result.
