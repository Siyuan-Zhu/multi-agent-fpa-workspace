# ADR-0003: Tiered Opex Compression Guardrails and Protected Expense Categories

- **Leading Word**: **Tiered-compression routing**
- **Enforcing Modules**: `src/cut_review_rules.py`, `src/verify_governance.py`
- **Owner Agent**: `agent.fpa.budget_architect`

## Rule Specification

Evaluate every `UNLOCKED` operating cost center (`Fund_Type == "OPERATING"`) in `src/cut_review_rules.py` using policy thresholds loaded from `config/workspace_governance.json`:

| Expense Category | Growth Branch (`YoY_Growth_Pct`) | `Recommended_Adjustment_Pct` | `Review_Disposition` |
| :--- | :--- | :---: | :--- |
| `Contractual Infrastructure` | Any | `0.00%` | `PROTECTED_NO_CUT` |
| `Regulatory Compliance` | Any | `0.00%` | `PROTECTED_NO_CUT` |
| `Personnel & Compensation` | Any | `0.00%` | `ROUTED_TO_HEADCOUNT_SCENARIO` |
| `Discretionary Opex` | `>= +8.00%` | `-12.00%` | `TIER_1_MAX_CAP_CUT` |
| `Discretionary Opex` | `+3.00%` to `< +8.00%` | `-6.50%` | `TIER_2_MODERATE_CUT` |
| `Discretionary Opex` | `< +3.00%` | `-3.00%` | `TIER_3_BASELINE_TRIM` |

Calculate the post-review line budget as `Final_Budget_NIU = round(Rough_Budget_NIU * (1.0 + Recommended_Adjustment_Pct / 100.0), 2)`.

## Verification Criterion (`src/verify_governance.py`)

- Every `UNLOCKED` row in `Contractual Infrastructure`, `Regulatory Compliance`, and `Personnel & Compensation` has `Recommended_Adjustment_Pct == 0.00%` and matches its mandated disposition.
- Every `UNLOCKED` row in `Discretionary Opex` satisfies `-12.00% <= Recommended_Adjustment_Pct <= -3.00%` according to its `YoY_Growth_Pct` tier.
