# ADR-0002: Ring-Fenced Designated R&D Reserve Transfers

- **Leading Word**: **Ring-fenced reserve isolation**
- **Enforcing Modules**: `src/build_rough_budget.py`, `src/cut_review_rules.py`, `src/verify_governance.py`
- **Owner Agent**: `agent.fpa.budget_architect`

## Rule Specification

1. **Fund Classification & Ring-Fencing**:
   - Assign all `6` cost centers in `Designated R&D Reserve` (`DIV-R`: `CC-901`..`CC-906`) to `Fund_Type = "DESIGNATED_RESERVE"` and `Ring_Fenced_Flag = "TRUE"`.
   - Assign all `30` cost centers in `DIV-A`, `DIV-B`, and `DIV-C` to `Fund_Type = "OPERATING"` and `Ring_Fenced_Flag = "FALSE"`.
2. **Separate Pool Roll-Ups & Zero Cross-Fund Sweeps**:
   - Set `Cross_Fund_Transfer_NIU = 0.00` on all `36` rows in `FY2027_Budget_Model`.
   - Maintain distinct live-formula rows on `Executive_Summary` for `Operating Divisions Subtotal (DIV-A + DIV-B + DIV-C)` (`SUBTOTAL-OP`, `10,149.29 NIU` final) and `Designated R&D Reserve (Ring-Fenced Pool)` (`DIV-R`, `2,727.93 NIU` final).
   - Assign `UNLOCKED` rows in `DIV-R` the disposition `RING_FENCED_NO_SWEEP` with `Recommended_Adjustment_Pct = 0.00%` during `src/cut_review_rules.py`.

## Verification Criterion (`src/verify_governance.py`)

- All `6` `DIV-R` rows carry `Fund_Type == "DESIGNATED_RESERVE"` and `Ring_Fenced_Flag == "TRUE"`.
- `sum(abs(Cross_Fund_Transfer_NIU)) == 0.00` across all `36` rows, and every `UNLOCKED` `DIV-R` row retains `Recommended_Adjustment_Pct == 0.00%`.
