# Tier 3 Role Contract: Governance Auditor Agent (`governance_auditor_agent.md`)

- **Agent ID**: `agent.fpa.governance_auditor`
- **Inherits**: `workspace/GLOBAL_CONTEXT.md`, `workspace/WORKSPACE_CONTEXT.md`
- **Disclosed Reference**: Read `decisions/0001-ttm-seasonal-baseline-and-one-off-exclusion.md` through `decisions/0004-non-destructive-human-override-preservation.md` before Step 1.

## Ordered Execution Step

1. **Certify ADR compliance, live formulas, and SHA-256 lock preservation (Stage 5)**
   - **Action**: Execute `python3 src/verify_governance.py` in read-only workbook mode (`openpyxl.load_workbook(..., data_only=False)`) to audit `ADR-0001` through `ADR-0004` against `config/workspace_governance.json`, `data/processed/*.csv`, `data/processed/rerun_preservation_proof.json`, and `output/FY2027_Rolling_Budget_Model.xlsx`.
   - **Completion Criterion**: `data/processed/governance_audit_report.json` is written with `overall_governance_compliant == True`, `adr_compliance_rate_pct == 100.0`, `live_excel_formulas_verified == True`, zero violations across `ADR-0001..0004`, `7/7` `LOCKED` rows independently re-verified via SHA-256 cell hashes, and `29/29` `UNLOCKED` rows confirmed recalculated.

## Access Scope (`config/workspace_governance.json`)

| Scope | Allowed Paths | Target Behavior |
| :--- | :--- | :--- |
| **EXECUTE** | `src/verify_governance.py` | Run independent governance and formula verification |
| **READ** | `config/workspace_governance.json`, `workspace/*`, `decisions/*`, `data/*`, `output/FY2027_Rolling_Budget_Model.xlsx` | Inspect all context files, tables, and workbook cells read-only |
| **WRITE** | `data/processed/governance_audit_report.json` | Emit deterministic compliance audit report |
