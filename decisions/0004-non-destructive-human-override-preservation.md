# ADR-0004: Non-Destructive Human Override Preservation Across Pipeline Re-Runs

- **Leading Word**: **Locked-cell primacy**
- **Enforcing Modules**: `src/cut_review_rules.py`, `src/verify_governance.py`
- **Owner Agents**: `agent.fpa.budget_architect` (execution), `agent.fpa.governance_auditor` (verification)

## Rule Specification

1. **Pass 1 Controller Lock Injection**:
   - Load signed human overrides from `data/raw/human_analyst_overrides.csv` (`7` cost centers: `CC-103`, `CC-107`, `CC-202`, `CC-208`, `CC-303`, `CC-309`, `CC-903`).
   - Set `Analyst_Override_Flag = "LOCKED"` and write the controller-approved `Recommended_Adjustment_Pct`, `Final_Budget_NIU`, `Review_Disposition`, and `Analyst_Commentary` in-place via `openpyxl.load_workbook()`.
   - Record a canonical SHA-256 fingerprint over `Cost_Center|Analyst_Override_Flag|Recommended_Adjustment_Pct|Final_Budget_NIU|Review_Disposition|Analyst_Commentary` for all `36` rows.
2. **Pass 2 Non-Destructive Macro Re-Run**:
   - Inspect `Analyst_Override_Flag` on each row before applying the `+1.50%` `Baseline_Growth_Driver_Pct` update:
     - When `Analyst_Override_Flag == "UNLOCKED"`: update `Baseline_Growth_Driver_Pct`, `Rough_Budget_NIU`, `Recommended_Adjustment_Pct`, `Final_Budget_NIU`, `Review_Disposition`, and `Analyst_Commentary`.
     - When `Analyst_Override_Flag == "LOCKED"`: leave the row untouched so all controller-approved fields and cell hashes remain identical to Pass 1.

## Verification Criterion (`src/verify_governance.py`)

- `7/7` `LOCKED` rows exhibit `0.00 NIU` delta and identical Pass 1 vs. Pass 2 SHA-256 fingerprints, independently recomputed from the saved workbook cells.
- `29/29` `UNLOCKED` rows exhibit positive `Final_Budget_NIU` recalculation deltas under the `+1.50%` macro driver update.
