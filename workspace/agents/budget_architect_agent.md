# Tier 3 Role Contract: Budget Architect Agent (`budget_architect_agent.md`)

- **Agent ID**: `agent.fpa.budget_architect`
- **Inherits**: `workspace/GLOBAL_CONTEXT.md`, `workspace/WORKSPACE_CONTEXT.md`
- **Disclosed Reference**:
  - Read `decisions/0002-ring-fenced-designated-reserve-transfers.md` before Step 1 (`DIV-R` pool separation).
  - Read `decisions/0003-tiered-opex-compression-and-protected-lines.md` and `decisions/0004-non-destructive-human-override-preservation.md` before Step 2 (in-place compression and **locked-cell primacy**).

## Ordered Execution Steps

1. **Construct multi-tab baseline budget workbook (Stage 3)**
   - **Action**: Execute `python3 src/build_rough_budget.py` to build `output/FY2027_Rolling_Budget_Model.xlsx` from `data/processed/ttm_trend_metrics.csv` with three sheets (`FY2027_Budget_Model`, `Executive_Summary`, `ADR_Audit_Trail`) and live Excel formulas (`=SUM(...)`, `=SUMIF(...)`, `=COUNTIF(...)`, `=AVERAGE(...)`).
   - **Completion Criterion**: `output/FY2027_Rolling_Budget_Model.xlsx` exists with all `36` line items initialized to `Analyst_Override_Flag == "UNLOCKED"`, `Cross_Fund_Transfer_NIU == 0.00 NIU`, separate `SUBTOTAL-OP` (`10,260.74 NIU` rough) and `DIV-R` (`2,700.53 NIU` rough) pools on `Executive_Summary`, and intact `=SUM(...)` roll-up formulas on Row `38`.

2. **Apply tiered compression rules, controller locks, and Pass 2 macro re-run (Stage 4)**
   - **Action**: Execute `python3 src/cut_review_rules.py` to open `output/FY2027_Rolling_Budget_Model.xlsx` in-place via `openpyxl`, apply `ADR-0003` dispositions to `UNLOCKED` rows, inject the `7` controller locks from `data/raw/human_analyst_overrides.csv` (`Analyst_Override_Flag = "LOCKED"`), and run Pass 2 (`+1.50%` macro driver update) writing only to rows where `Analyst_Override_Flag == "UNLOCKED"`.
   - **Completion Criterion**: `data/processed/rerun_preservation_proof.json` is written with `all_locked_rows_preserved_verbatim == True` (`7/7` `LOCKED` rows matching Pass 1 SHA-256 cell hashes with `0.00 NIU` drift) and `all_unlocked_rows_recalculated == True` (`29/29` `UNLOCKED` rows updated to a Pass 2 final portfolio total of `12,877.22 NIU`).

## Access Scope (`config/workspace_governance.json`)

| Scope | Allowed Paths | Target Behavior |
| :--- | :--- | :--- |
| **EXECUTE** | `src/build_rough_budget.py`, `src/cut_review_rules.py` | Build and update the governed workbook in-place |
| **READ** | `data/processed/ttm_trend_metrics.csv`, `data/raw/human_analyst_overrides.csv`, `decisions/0002..0004`, `config/workspace_governance.json` | Load trend baselines, controller locks, and ADR thresholds |
| **WRITE** | `output/FY2027_Rolling_Budget_Model.xlsx`, `data/processed/rerun_preservation_proof.json` | Persist live-formula workbook and SHA-256 preservation proof |
