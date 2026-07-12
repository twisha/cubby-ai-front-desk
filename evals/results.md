# Cubby Eval Results

**22/27 cases passed.**

## Summary

| Metric | Result |
|---|---|
| Recall@4 (retrieval readiness) | 0.80 (20 cases) |
| MRR | 0.74 |
| Gap-gate precision | 83% (20/24) |
| Mode-routing correctness | 88% (23/26) |
| Groundedness (verdict=yes) | 88% (15/17) |
| Faithfulness (verdict=pass) | 94% (16/17) |
| Accuracy vs. reference | 100% (17/17) |
| Judge calibration (mandatory trap) | 100% (1/1) |

## Per-case detail

| id | category | mode (exp -> actual) | recall@4 | grounded | faithful | accuracy | notes |
|---|---|---|---|---|---|---|---|
| g01 | grounded | grounded -> grounded | 1 | yes | pass | pass | ✅  |
| g02 | grounded | grounded -> grounded | 1 | yes | pass | pass | ✅  |
| g03 | near_miss | grounded -> grounded | 1 | yes | pass | pass | ✅  |
| g04 | grounded | grounded -> grounded | 1 | yes | pass | pass | ✅  |
| g05 | grounded | grounded -> gap ⚠ | 1 | - | - | - | ❌ expected mode grounded, got gap |
| g06 | grounded | grounded -> grounded | 1 | yes | pass | pass | ✅  |
| g07 | grounded | grounded -> grounded | 1 | yes | pass | pass | ✅  |
| g08 | grounded | grounded -> grounded | 1 | yes | pass | pass | ✅  |
| g09 | grounded | grounded -> grounded | 1 | partial | pass | pass | ❌ groundedness=partial: If your child does not have any allergies, no plan is required. |
| g10 | grounded | grounded -> grounded | 0 | yes | pass | pass | ✅  |
| g11 | grounded | grounded -> grounded | 1 | yes | pass | pass | ✅  |
| g12 | grounded | grounded -> grounded | 1 | yes | pass | pass | ✅  |
| g13 | grounded | grounded -> grounded | 0 | yes | pass | pass | ✅  |
| g14 | grounded | grounded -> grounded | 0 | yes | pass | pass | ✅  |
| g15 | grounded | grounded -> grounded | 1 | partial | fail | pass | ❌ groundedness=partial: On delays, we open at 9:00am instead of 6:30am.; faithfulness=fail: The answer adds a specific nor |
| g16 | grounded | grounded -> grounded | 1 | yes | pass | pass | ✅  |
| g17 | grounded | grounded -> grounded | 1 | yes | pass | pass | ✅  |
| j01 | judgment | judgment -> judgment | 1 | yes | pass | pass | ✅  |
| j02 | judgment | judgment -> gap ⚠ | 0 | - | - | - | ❌ expected mode judgment, got gap |
| j03 | judgment | judgment -> gap ⚠ | 1 | - | - | - | ❌ expected mode judgment, got gap |
| e01 | escalated | escalated -> escalated | - | - | - | - | ✅  |
| e02 | escalated | escalated -> escalated | - | - | - | - | ✅  |
| gap01 | out_of_scope | gap -> gap | - | - | - | - | ✅  |
| gap02 | out_of_scope | gap -> gap | - | - | - | - | ✅  |
| gap03 | out_of_scope | gap -> gap | - | - | - | - | ✅  |
| gap04 | out_of_scope | gap -> gap | - | - | - | - | ✅  |
| jc01 | faithfulness_trap | - | - | - | fail | - | ✅  |
