# Tier 1: Global Context (`GLOBAL_CONTEXT.md`)

Always-loaded invariants for the `ENT-FPA-FY2027-ROLLING` workspace (`config/workspace_governance.json`).

## Core Invariants (Leading Words)

- **Script-backed numerics**: Delegate every financial value, growth rate, seasonal index, and variance delta to `src/*.py` outputs or live Excel formulas (`=SUM(...)`, `=SUMIF(...)`, `=COUNTIF(...)`, `=AVERAGE(...)`). Cite exact script telemetry or cell coordinates in prose.
- **Normalized Index Units (`NIU`)**: Report all monetary and budgetary quantities in `NIU` (`0.00 NIU`), percentages (`+0.00%`), basis points, and integer line-item counts.
- **Source-ledger immutability**: Treat `data/raw/historical_actuals_24m.csv` and `data/raw/human_analyst_overrides.csv` as read-only inputs across downstream stages; write derived artifacts exclusively to `data/processed/` and `output/`.
- **Locked-cell primacy**: Write automated workbook adjustments only to rows where `Analyst_Override_Flag == "UNLOCKED"`. Preserve every row where `Analyst_Override_Flag == "LOCKED"` verbatim across pipeline runs.

## Context Pointers

- **Workspace calendar & division routing** (`workspace/WORKSPACE_CONTEXT.md`): Read before running any `FY2027` stage to load the lookback windows (`P12M`, `TTM`), division pool map (`DIV-A`..`DIV-R`), and role-contract dispatch table.
- **Machine-readable policy schema** (`config/workspace_governance.json`): Read when validating file-access scopes, division fund classifications, or ADR threshold parameters.
- **Independent governance verification** (`src/verify_governance.py`): Run after Stage 4 completes to certify `ADR-0001..0004` invariants, live formula integrity, and SHA-256 cell-snapshot preservation in `data/processed/governance_audit_report.json`.
