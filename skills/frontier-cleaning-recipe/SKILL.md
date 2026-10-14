---
name: frontier-cleaning-recipe
description: Propose a data-cleaning recipe for a Frontier dataset op by op (plan, preview, approval, run, diff) with the `frontier` context server. Use when asked to fix, normalise, clean, dedupe, re-split or otherwise change a dataset. Writes need an approval the server only grants through the Frontier ACP agent or a site policy.
---

# Cleaning recipe: agent proposes, code executes

For every op in the recipe, in this order and never skipping a step:

1. `<op>.plan` with explicit params. Read `warnings`; a missing field or parameter means you
   adjust the params, not that you proceed.
2. `<op>.preview` on a few samples. Note the statistics it returns.
3. `prep.request_approval` with the `plan_id` and a summary that cites the plan and preview
   numbers (what changes, how many samples/fields, ranges, why). A person decides. In Zed's
   agent panel the `frontier` context server runs with `--approver none`: the request is
   refused unless the site policy (`policy.ai.autonomous_op_classes`) covers the op. When it
   is refused, stop, report the plan and preview numbers, and tell the person to run the
   recipe through the Frontier ACP agent (`python -m frontier_agent acp`) or
   `frontier prep recipe run`, where approvals are a dialog.
4. `<op>.run` with `plan_id` and the `approval_token`. Only then.
5. `version.diff` to confirm the change.

Finish with the provenance summary: dataset and head version before and after, each op with
params and output version, approvals, judgments relied on, what was left undone and why.
Offer to save the steps as a `*.recipe.json` (snippet `frontier-recipe`) so the recipe is
replayable.
