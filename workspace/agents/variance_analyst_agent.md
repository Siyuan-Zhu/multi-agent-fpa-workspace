# Tier 3 Role Contract: Variance Analyst Agent (`variance_analyst_agent.md`)

- **Agent ID**: `agent.fpa.variance_analyst`
- **Inherits**: `workspace/GLOBAL_CONTEXT.md`, `workspace/WORKSPACE_CONTEXT.md`
- **Disclosed Reference**: Read `decisions/0001-ttm-seasonal-baseline-and-one-off-exclusion.md` before Step 1.

## Ordered Execution Steps

1. **Isolate recurring actuals from one-off spikes (Stage 1)**
   - **Action**: Execute `python3 src/prepare_data.py` to generate and validate `data/raw/historical_actuals_24m.csv` (`864` monthly rows across `36` cost centers) and `data/raw/human_analyst_overrides.csv` (`7` controller locks), separating every `Is_One_Off_Spike == 1` record into `data/processed/excluded_one_off_items.csv` and writing clean series to `data/processed/clean_recurring_actuals_24m.csv`.
   - **Completion Criterion**: Both processed CSVs exist on disk; `excluded_one_off_items.csv` contains all `4` one-off events totaling `410.00 NIU` (`95.00 NIU` in `P12M` and `315.00 NIU` in `TTM`); and `Gross_Actual_NIU - One_Off_NIU == Recurring_Actual_NIU` holds within `1e-6` across all `864` records.

2. **Compute full-cycle TTM velocity and seasonality metrics (Stage 2)**
   - **Action**: Execute `python3 src/build_trends.py` to aggregate `P12M` (`2024-10`..`2025-09`) and `TTM` (`2025-10`..`2026-09`) recurring actuals per cost center, calculating `YoY_Growth_Pct`, `YoY_Growth_Bps`, `Monthly_CV`, `Q4_Share_Pct`, and `Seasonality_Index` into `data/processed/ttm_trend_metrics.csv`.
   - **Completion Criterion**: `data/processed/ttm_trend_metrics.csv` contains all `36` cost-center rows with `P12M_Recurring_NIU` summing to `11,825.99 NIU`, `TTM_Gross_NIU` summing to `12,780.04 NIU`, `TTM_Excluded_One_Off_NIU` summing to `315.00 NIU`, and `TTM_Recurring_NIU` summing to `12,465.04 NIU`.

## Access Scope (`config/workspace_governance.json`)

| Scope | Allowed Paths | Target Behavior |
| :--- | :--- | :--- |
| **EXECUTE** | `src/prepare_data.py`, `src/build_trends.py` | Run deterministic Stage 1 and Stage 2 modules |
| **READ** | `data/raw/*`, `decisions/0001-*.md`, `config/workspace_governance.json` | Inspect raw ledger inputs and `ADR-0001` rules |
| **WRITE** | `data/processed/clean_recurring_actuals_24m.csv`, `data/processed/excluded_one_off_items.csv`, `data/processed/ttm_trend_metrics.csv` | Emit schema-validated recurring and trend tables |
