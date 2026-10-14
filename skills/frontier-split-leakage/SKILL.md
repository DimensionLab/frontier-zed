---
name: frontier-split-leakage
description: Review train/val/test splits of a Frontier dataset for leakage (shared ids, parameter-range overlap, duplicate geometries across splits) with the `frontier` context server and propose a leakage-free parameter hold-out split. Use when asked about splits, generalisation tests, extrapolation or leakage.
---

# Review split leakage

1. `quality.check_leakage`: shared ids and whether the test range of each parameter sits
   inside the training range (`overlap: true` means interpolation only).
2. `dataset.describe`: parameters, split sizes, current strategy (`random` leaks by
   construction for a parametric family).
3. `prep.geometry.near_duplicates.plan` at 1% tolerance: duplicate groups straddling splits
   are leakage.
4. If a fix is warranted: `prep.split.parameter_holdout.plan` on the parameter the dataset
   card names (else the widest relative range), `side: top` for an extrapolation test,
   preview, then `prep.request_approval` citing sizes and ranges per split; run only with
   the token. If the approval is refused (the default in Zed's agent panel), hand the person
   the plan so they run it through the Frontier ACP agent or `frontier prep run`.
   Re-check with `quality.check_leakage` afterwards.

Report what you found with the numbers, and what changed (versions before and after).
