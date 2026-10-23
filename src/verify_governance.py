"""Independent Governance Auditor: Verify ADR-0001..0004 compliance, live Excel formulas, and re-run lock integrity.

Owner Agent: agent.fpa.governance_auditor
Governing Policies: ADR-0001, ADR-0002, ADR-0003, ADR-0004
Reporting Unit: Normalized Index Units (NIU), Percentages (%), Basis Points (bps)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List
import openpyxl
import pandas as pd

from src.domain import (
    AUDIT_REPORT_PATH,
    CONFIG_PATH,
    PROCESSED_DIR,
    PROOF_PATH,
    RAW_DIR,
    ROOT_DIR,
    WORKBOOK_PATH,
    BudgetLineItem,
    GovernanceAuditReport,
    load_governance_policy,
)


def run_governance_audit(
    root_dir: Path = ROOT_DIR,
    config_path: Path = CONFIG_PATH,
    raw_dir: Path = RAW_DIR,
    processed_dir: Path = PROCESSED_DIR,
    workbook_path: Path = WORKBOOK_PATH,
    proof_path: Path = PROOF_PATH,
    audit_report_path: Path = AUDIT_REPORT_PATH,
) -> GovernanceAuditReport:
    """Audit all 4 ADRs, context hierarchy files, and Excel formula integrity."""
    policy = load_governance_policy(config_path)

    required_files = [config_path, workbook_path] + [
        root_dir / rel_path for rel_path in policy.required_relative_paths
    ]
    missing_files = [
        str(p.relative_to(root_dir)) if p.is_relative_to(root_dir) else str(p)
        for p in required_files
        if not p.exists()
    ]
    if missing_files:
        raise FileNotFoundError(f"Governance audit failed: missing required files {missing_files}")

    # 1. Audit ADR-0001: TTM Seasonal Baseline and One-Off Exclusion
    raw_df = pd.DataFrame(pd.read_csv(raw_dir / "historical_actuals_24m.csv"))
    excluded_df = pd.DataFrame(pd.read_csv(processed_dir / "excluded_one_off_items.csv"))
    trend_df = pd.DataFrame(pd.read_csv(processed_dir / "ttm_trend_metrics.csv"))

    ttm_raw_df = raw_df[raw_df["Window"] == "TTM"]
    ttm_gross_sum = round(float(ttm_raw_df["Gross_Actual_NIU"].sum()), 2)
    ttm_one_off_sum = round(float(ttm_raw_df["One_Off_NIU"].sum()), 2)
    ttm_rec_sum = round(float(ttm_raw_df["Recurring_Actual_NIU"].sum()), 2)
    trend_ttm_rec_sum = round(float(trend_df["TTM_Recurring_NIU"].sum()), 2)

    adr_0001_passed = (
        len(excluded_df) == policy.expected_one_off_event_count
        and abs((ttm_gross_sum - ttm_one_off_sum) - ttm_rec_sum) < 1e-6
        and abs(ttm_rec_sum - trend_ttm_rec_sum) < 1e-6
        and round(float(excluded_df["One_Off_NIU"].sum()), 2) == 410.00
        and ttm_one_off_sum == 315.00
    )

    # 2. Inspect Workbook in-place for ADR-0002, ADR-0003, ADR-0004, and Live Formulas
    wb = openpyxl.load_workbook(workbook_path, data_only=False)
    ws_model = wb["FY2027_Budget_Model"]
    ws_exec = wb["Executive_Summary"]

    model_formula_cells = {
        "H38": str(ws_model["H38"].value),
        "I38": str(ws_model["I38"].value),
        "J38": str(ws_model["J38"].value),
        "M38": str(ws_model["M38"].value),
        "O38": str(ws_model["O38"].value),
        "P38": str(ws_model["P38"].value),
    }
    exec_formula_cells = {
        "D5": str(ws_exec["D5"].value),
        "H5": str(ws_exec["H5"].value),
        "H6": str(ws_exec["H6"].value),
        "H7": str(ws_exec["H7"].value),
    }
    live_formulas_verified = all(v.startswith("=") for v in model_formula_cells.values()) and all(
        v.startswith("=") for v in exec_formula_cells.values()
    )

    workbook_items = [BudgetLineItem.from_worksheet_row(ws_model, row_idx) for row_idx in range(2, 38)]

    div_r_rows = 0
    cross_fund_transfers_niu = 0.0
    adr_0002_violations: List[str] = []
    adr_0003_violations: List[str] = []

    operating_final_niu = 0.0
    reserve_final_niu = 0.0
    operating_rough_niu = 0.0
    reserve_rough_niu = 0.0

    disposition_counts: Dict[str, int] = {}

    for item in workbook_items:
        disposition_counts[item.review_disposition] = disposition_counts.get(item.review_disposition, 0) + 1
        cross_fund_transfers_niu += abs(item.cross_fund_transfer_niu)

        if item.division_id == policy.ring_fenced_division_id:
            div_r_rows += 1
            reserve_rough_niu += item.rough_budget_niu
            reserve_final_niu += item.final_budget_niu
            if not item.is_ring_fenced:
                adr_0002_violations.append(f"{item.cost_center}: invalid ring-fence metadata")
            if item.analyst_override_flag == policy.unlocked_value and item.recommended_adjustment_pct != 0.0:
                adr_0002_violations.append(
                    f"{item.cost_center}: unlocked reserve line compressed by {item.recommended_adjustment_pct}%"
                )
        else:
            operating_rough_niu += item.rough_budget_niu
            operating_final_niu += item.final_budget_niu

        if item.analyst_override_flag == policy.unlocked_value and item.division_id != policy.ring_fenced_division_id:
            if item.expense_category in policy.protected_categories and item.recommended_adjustment_pct != 0.0:
                adr_0003_violations.append(
                    f"{item.cost_center}: protected category {item.expense_category} cut by {item.recommended_adjustment_pct}%"
                )
            elif item.expense_category in policy.headcount_review_categories and item.recommended_adjustment_pct != 0.0:
                adr_0003_violations.append(
                    f"{item.cost_center}: personnel line cut by {item.recommended_adjustment_pct}% without headcount scenario"
                )
            elif (
                item.expense_category == "Discretionary Opex"
                and item.recommended_adjustment_pct < policy.discretionary_max_cut_pct
            ):
                adr_0003_violations.append(
                    f"{item.cost_center}: discretionary cut {item.recommended_adjustment_pct}% exceeds {policy.discretionary_max_cut_pct}% cap"
                )

    adr_0002_passed = div_r_rows == 6 and cross_fund_transfers_niu == 0.0 and len(adr_0002_violations) == 0
    adr_0003_passed = len(adr_0003_violations) == 0

    # 3. Audit ADR-0004: Non-Destructive Human Override Preservation & Independent Worksheet Hash Check
    proof_data = json.loads(proof_path.read_text(encoding="utf-8"))
    workbook_hashes_by_cc = {item.cost_center: item.protected_fields_sha256 for item in workbook_items if item.is_locked}
    independent_hash_matches = all(
        workbook_hashes_by_cc.get(entry["cost_center"]) == entry["pass_1_sha256"]
        and entry["pass_1_sha256"] == entry["pass_2_sha256"]
        for entry in proof_data["locked_row_proofs"]
    )

    adr_0004_passed = (
        proof_data["locked_rows_count"] == 7
        and proof_data["unlocked_rows_count"] == 29
        and proof_data["all_locked_rows_preserved_verbatim"] is True
        and proof_data["all_unlocked_rows_recalculated"] is True
        and independent_hash_matches
    )

    overall_passed = (
        adr_0001_passed
        and adr_0002_passed
        and adr_0003_passed
        and adr_0004_passed
        and live_formulas_verified
    )

    report = GovernanceAuditReport(
        workspace_id=policy.workspace_id,
        reporting_unit=policy.reporting_unit,
        overall_governance_compliant=overall_passed,
        adr_compliance_rate_pct=100.0 if overall_passed else 0.0,
        live_excel_formulas_verified=live_formulas_verified,
        formula_samples={
            "FY2027_Budget_Model": model_formula_cells,
            "Executive_Summary": exec_formula_cells,
        },
        portfolio_metrics_niu={
            "p12m_recurring_total_niu": round(float(trend_df["P12M_Recurring_NIU"].sum()), 2),
            "ttm_gross_total_niu": ttm_gross_sum,
            "ttm_excluded_one_off_niu": ttm_one_off_sum,
            "ttm_recurring_total_niu": ttm_rec_sum,
            "fy2027_operating_rough_budget_niu": round(operating_rough_niu, 2),
            "fy2027_operating_final_budget_niu": round(operating_final_niu, 2),
            "fy2027_reserve_rough_budget_niu": round(reserve_rough_niu, 2),
            "fy2027_reserve_final_budget_niu": round(reserve_final_niu, 2),
            "fy2027_total_rough_budget_niu": round(operating_rough_niu + reserve_rough_niu, 2),
            "fy2027_total_final_budget_niu": round(operating_final_niu + reserve_final_niu, 2),
            "net_compression_reduction_niu": round(
                (operating_final_niu + reserve_final_niu) - (operating_rough_niu + reserve_rough_niu), 2
            ),
        },
        disposition_breakdown=disposition_counts,
        adr_audits={
            "ADR-0001": {
                "passed": adr_0001_passed,
                "excluded_events_count": int(len(excluded_df)),
                "total_24m_excluded_niu": round(float(excluded_df["One_Off_NIU"].sum()), 2),
                "ttm_excluded_niu": ttm_one_off_sum,
            },
            "ADR-0002": {
                "passed": adr_0002_passed,
                "ring_fenced_lines_count": div_r_rows,
                "cross_fund_transfer_niu": cross_fund_transfers_niu,
                "violations": adr_0002_violations,
            },
            "ADR-0003": {
                "passed": adr_0003_passed,
                "discretionary_cut_ceiling_pct": policy.discretionary_max_cut_pct,
                "violations": adr_0003_violations,
            },
            "ADR-0004": {
                "passed": adr_0004_passed,
                "locked_human_overrides_preserved": f"{proof_data['locked_rows_count']}/7",
                "unlocked_lines_recalculated": f"{proof_data['unlocked_rows_count']}/29",
                "cryptographic_sha256_verified": independent_hash_matches,
            },
        },
    )

    audit_report_path.parent.mkdir(parents=True, exist_ok=True)
    audit_report_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    if not overall_passed:
        raise RuntimeError(f"Governance verification failed: {json.dumps(report.to_dict(), indent=2)}")

    return report


if __name__ == "__main__":
    audit = run_governance_audit()
    print(
        f"[Governance Audit] Compliant={audit.overall_governance_compliant} | "
        f"ADR Compliance={audit.adr_compliance_rate_pct}% | "
        f"Final Budget={audit.portfolio_metrics_niu['fy2027_total_final_budget_niu']} NIU"
    )
