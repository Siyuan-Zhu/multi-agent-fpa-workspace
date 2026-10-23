# ADR-0001: TTM Seasonal Baseline and One-Off Restructuring Exclusion

- **Leading Word**: **Script-backed baseline hygiene**
- **Enforcing Modules**: `src/prepare_data.py`, `src/build_trends.py`, `src/verify_governance.py`
- **Owner Agent**: `agent.fpa.variance_analyst`

## Rule Specification

1. **Full-Cycle 12-Month Comparison Windows**:
   - Benchmark the 12-month Trailing Twelve Month window (`TTM`: `2025-10`..`2026-09`) against the prior 12-month window (`P12M`: `2024-10`..`2025-09`) across all `36` cost centers (`864` monthly records) so full annual seasonality (`FLAT`, `Q2_Q4`, `Q4_HEAVY`) is represented in both periods.
2. **One-Off Spike Separation (`Is_One_Off_Spike == 1`)**:
   - Strip flagged capital restructuring and facility exit spikes from gross actuals in Stage 1 (`src/prepare_data.py`):
     `Recurring_Actual_NIU = round(Gross_Actual_NIU - One_Off_NIU, 2)`
   - Archive all `4` flagged events (`410.00 NIU` across 24M: `95.00 NIU` in `P12M` at `CC-104`, and `315.00 NIU` in `TTM` across `CC-108`, `CC-205`, `CC-306`) to `data/processed/excluded_one_off_items.csv`.
   - Pass only `Recurring_Actual_NIU` (`data/processed/clean_recurring_actuals_24m.csv`) into Stage 2 (`src/build_trends.py`) to compute `YoY_Growth_Pct = round(((TTM_Recurring_NIU - P12M_Recurring_NIU) / P12M_Recurring_NIU) * 100.0, 2)`.

## Verification Criterion (`src/verify_governance.py`)

- `len(excluded_one_off_items.csv) == 4` with `One_Off_NIU` summing to `410.00 NIU` (`24M`) and `315.00 NIU` (`TTM`).
- `TTM_Gross_NIU (12,780.04 NIU) - TTM_Excluded_One_Off_NIU (315.00 NIU) == TTM_Recurring_NIU (12,465.04 NIU)` holds within `1e-6` across every cost center.
