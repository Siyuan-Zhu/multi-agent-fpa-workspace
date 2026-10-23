# Tier 2: FY2027 Rolling Budget Workspace Context (`WORKSPACE_CONTEXT.md`)

Inherits `workspace/GLOBAL_CONTEXT.md`. Governs the `36` cost-center line items across `4` divisions for the `FY2027` cycle (`2026-10`..`2027-09`), benchmarked against `P12M` (`2024-10`..`2025-09`) and `TTM` (`2025-10`..`2026-09`).

## Division & Fund Topology

| Division ID | Division Name | Fund Type | Cost Centers | Lines | Pool Routing |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `DIV-A` | `Division A — Core Platform` | `OPERATING` | `CC-101`..`CC-110` | `10` | Operating Pool (`SUBTOTAL-OP`) |
| `DIV-B` | `Division B — Field Operations` | `OPERATING` | `CC-201`..`CC-210` | `10` | Operating Pool (`SUBTOTAL-OP`) |
| `DIV-C` | `Division C — Shared Services` | `OPERATING` | `CC-301`..`CC-310` | `10` | Operating Pool (`SUBTOTAL-OP`) |
| `DIV-R` | `Designated R&D Reserve` | `DESIGNATED_RESERVE` | `CC-901`..`CC-906` | `6` | **Ring-fenced** (`ADR-0002`) |

## Disclosed ADR & Role-Contract Pointers

- **Script-backed baseline hygiene** (`decisions/0001-ttm-seasonal-baseline-and-one-off-exclusion.md`): Read when ingesting `data/raw/historical_actuals_24m.csv`, encountering `Is_One_Off_Spike == 1`, or computing `P12M` vs. `TTM` recurring velocity in `src/prepare_data.py` and `src/build_trends.py`.
- **Ring-fenced reserve isolation** (`decisions/0002-ring-fenced-designated-reserve-transfers.md`): Read when aggregating `DIV-R` (`Fund_Type == "DESIGNATED_RESERVE"`) or constructing `Executive_Summary` subtotals in `src/build_rough_budget.py` and `src/cut_review_rules.py`.
- **Tiered-compression routing** (`decisions/0003-tiered-opex-compression-and-protected-lines.md`): Read when evaluating `Expense_Category` dispositions (`Discretionary Opex`, `Contractual Infrastructure`, `Regulatory Compliance`, `Personnel & Compensation`) on `UNLOCKED` rows in `src/cut_review_rules.py`.
- **Locked-cell primacy on re-run** (`decisions/0004-non-destructive-human-override-preservation.md`): Read when applying `data/raw/human_analyst_overrides.csv` or executing an in-place macro driver re-run on `output/FY2027_Rolling_Budget_Model.xlsx` in `src/cut_review_rules.py`.
- **Role-scoped execution contracts**:
  - **Stage 1 & Stage 2 (`Variance Analyst`)**: Read `workspace/agents/variance_analyst_agent.md` before running `src/prepare_data.py` or `src/build_trends.py`.
  - **Stage 3 & Stage 4 (`Budget Architect`)**: Read `workspace/agents/budget_architect_agent.md` before running `src/build_rough_budget.py` or `src/cut_review_rules.py`.
  - **Stage 5 (`Governance Auditor`)**: Read `workspace/agents/governance_auditor_agent.md` before running `src/verify_governance.py`.
