"""Stage 1: Deterministic synthetic actuals generation, schema validation, and ADR-0001 one-off separation.

Owner Agent: agent.fpa.variance_analyst
Governing Policy: ADR-0001 (TTM Seasonal Baseline and One-Off Restructuring Exclusion)
Reporting Unit: Normalized Index Units (NIU)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple
import pandas as pd

from src.domain import (
    CONFIG_PATH,
    PROCESSED_DIR,
    RAW_DIR,
    CostCenterBaseline,
    load_governance_policy,
)


MONTHS_P12M: Tuple[str, ...] = (
    "2024-10", "2024-11", "2024-12", "2025-01", "2025-02", "2025-03",
    "2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09",
)
MONTHS_TTM: Tuple[str, ...] = (
    "2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03",
    "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09",
)
ALL_MONTHS_24M: Tuple[str, ...] = MONTHS_P12M + MONTHS_TTM

LINE_ITEM_CATALOG: Tuple[CostCenterBaseline, ...] = (
    # Division A — Core Platform (10 lines: CC-101 .. CC-110)
    CostCenterBaseline("LI-01", "DIV-A", "Division A — Core Platform", "OPERATING", "CC-101", "Platform Core Compute Clusters", "Contractual Infrastructure", 42.0, 1.055, "FLAT"),
    CostCenterBaseline("LI-02", "DIV-A", "Division A — Core Platform", "OPERATING", "CC-102", "Observability & Telemetry SaaS", "Contractual Infrastructure", 18.5, 1.060, "FLAT"),
    CostCenterBaseline("LI-03", "DIV-A", "Division A — Core Platform", "OPERATING", "CC-103", "Product Engineering Compensation", "Personnel & Compensation", 95.0, 1.045, "FLAT"),
    CostCenterBaseline("LI-04", "DIV-A", "Division A — Core Platform", "OPERATING", "CC-104", "Developer Sandbox Cloud Burst", "Discretionary Opex", 16.0, 1.115, "Q4_HEAVY"),
    CostCenterBaseline("LI-05", "DIV-A", "Division A — Core Platform", "OPERATING", "CC-105", "SOC2 & ISO Security Audits", "Regulatory Compliance", 11.0, 1.035, "Q2_Q4"),
    CostCenterBaseline("LI-06", "DIV-A", "Division A — Core Platform", "OPERATING", "CC-106", "External UI/UX Prototyping Studio", "Discretionary Opex", 14.0, 1.095, "Q4_HEAVY"),
    CostCenterBaseline("LI-07", "DIV-A", "Division A — Core Platform", "OPERATING", "CC-107", "API Gateway Bandwidth Commit", "Contractual Infrastructure", 24.0, 1.050, "FLAT"),
    CostCenterBaseline("LI-08", "DIV-A", "Division A — Core Platform", "OPERATING", "CC-108", "Technical Documentation Contractors", "Discretionary Opex", 9.5, 1.045, "FLAT"),
    CostCenterBaseline("LI-09", "DIV-A", "Division A — Core Platform", "OPERATING", "CC-109", "Quality Assurance Automation Lab", "Discretionary Opex", 12.0, 1.020, "FLAT"),
    CostCenterBaseline("LI-10", "DIV-A", "Division A — Core Platform", "OPERATING", "CC-110", "Site Reliability Engineering Payroll", "Personnel & Compensation", 68.0, 1.040, "FLAT"),

    # Division B — Field Operations (10 lines: CC-201 .. CC-210)
    CostCenterBaseline("LI-11", "DIV-B", "Division B — Field Operations", "OPERATING", "CC-201", "Regional Commercial Account Payroll", "Personnel & Compensation", 88.0, 1.050, "FLAT"),
    CostCenterBaseline("LI-12", "DIV-B", "Division B — Field Operations", "OPERATING", "CC-202", "Trade Show Pavilions", "Discretionary Opex", 22.0, 1.125, "Q4_HEAVY"),
    CostCenterBaseline("LI-13", "DIV-B", "Division B — Field Operations", "OPERATING", "CC-203", "Field Fleet Telematics Leases", "Contractual Infrastructure", 19.0, 1.030, "FLAT"),
    CostCenterBaseline("LI-14", "DIV-B", "Division B — Field Operations", "OPERATING", "CC-204", "Regional Prospecting Roadshows", "Discretionary Opex", 15.5, 1.090, "Q4_HEAVY"),
    CostCenterBaseline("LI-15", "DIV-B", "Division B — Field Operations", "OPERATING", "CC-205", "Channel Partner Enablement Kits", "Discretionary Opex", 13.0, 1.055, "Q2_Q4"),
    CostCenterBaseline("LI-16", "DIV-B", "Division B — Field Operations", "OPERATING", "CC-206", "Export Licensing & Trade Compliance", "Regulatory Compliance", 8.5, 1.025, "FLAT"),
    CostCenterBaseline("LI-17", "DIV-B", "Division B — Field Operations", "OPERATING", "CC-207", "CRM Seat Subscription Tiers", "Contractual Infrastructure", 21.0, 1.045, "FLAT"),
    CostCenterBaseline("LI-18", "DIV-B", "Division B — Field Operations", "OPERATING", "CC-208", "Digital Demand Generation Campaigns", "Discretionary Opex", 27.5, 1.105, "Q4_HEAVY"),
    CostCenterBaseline("LI-19", "DIV-B", "Division B — Field Operations", "OPERATING", "CC-209", "Field Solutions Engineering Payroll", "Personnel & Compensation", 54.0, 1.042, "FLAT"),
    CostCenterBaseline("LI-20", "DIV-B", "Division B — Field Operations", "OPERATING", "CC-210", "Hospitality & Client Executive Briefings", "Discretionary Opex", 11.5, 1.018, "Q4_HEAVY"),

    # Division C — Shared Services (10 lines: CC-301 .. CC-310)
    CostCenterBaseline("LI-21", "DIV-C", "Division C — Shared Services", "OPERATING", "CC-301", "Corporate Finance & Legal Payroll", "Personnel & Compensation", 62.0, 1.038, "FLAT"),
    CostCenterBaseline("LI-22", "DIV-C", "Division C — Shared Services", "OPERATING", "CC-302", "ERP Core Licensing", "Contractual Infrastructure", 26.0, 1.040, "FLAT"),
    CostCenterBaseline("LI-23", "DIV-C", "Division C — Shared Services", "OPERATING", "CC-303", "Statutory Tax & External Audit Fees", "Regulatory Compliance", 14.5, 1.060, "Q2_Q4"),
    CostCenterBaseline("LI-24", "DIV-C", "Division C — Shared Services", "OPERATING", "CC-304", "Executive Leadership Offsites", "Discretionary Opex", 10.5, 1.098, "Q4_HEAVY"),
    CostCenterBaseline("LI-25", "DIV-C", "Division C — Shared Services", "OPERATING", "CC-305", "Global Data Privacy Counsel Retainer", "Regulatory Compliance", 9.0, 1.030, "FLAT"),
    CostCenterBaseline("LI-26", "DIV-C", "Division C — Shared Services", "OPERATING", "CC-306", "Management Consulting Benchmarks", "Discretionary Opex", 17.0, 1.062, "Q2_Q4"),
    CostCenterBaseline("LI-27", "DIV-C", "Division C — Shared Services", "OPERATING", "CC-307", "Workplace Facilities & Security Systems", "Contractual Infrastructure", 23.0, 1.028, "FLAT"),
    CostCenterBaseline("LI-28", "DIV-C", "Division C — Shared Services", "OPERATING", "CC-308", "Internal Learning & Stipend Programs", "Discretionary Opex", 8.0, 1.015, "FLAT"),
    CostCenterBaseline("LI-29", "DIV-C", "Division C — Shared Services", "OPERATING", "CC-309", "Recruiting Agency Placement Retainers", "Discretionary Opex", 15.0, 1.088, "Q2_Q4"),
    CostCenterBaseline("LI-30", "DIV-C", "Division C — Shared Services", "OPERATING", "CC-310", "Environmental & Safety Filings", "Regulatory Compliance", 7.5, 1.022, "FLAT"),

    # Designated R&D Reserve (6 lines: CC-901 .. CC-906, ring-fenced per ADR-0002)
    CostCenterBaseline("LI-31", "DIV-R", "Designated R&D Reserve", "DESIGNATED_RESERVE", "CC-901", "Next-Gen Autonomous Agent Testbed", "Designated R&D Reserve", 34.0, 1.070, "FLAT"),
    CostCenterBaseline("LI-32", "DIV-R", "Designated R&D Reserve", "DESIGNATED_RESERVE", "CC-902", "Proprietary Training Compute Reserve", "Designated R&D Reserve", 46.0, 1.080, "Q4_HEAVY"),
    CostCenterBaseline("LI-33", "DIV-R", "Designated R&D Reserve", "DESIGNATED_RESERVE", "CC-903", "Applied AI Research Fellows Payroll", "Personnel & Compensation", 58.0, 1.050, "FLAT"),
    CostCenterBaseline("LI-34", "DIV-R", "Designated R&D Reserve", "DESIGNATED_RESERVE", "CC-904", "Synthetic Benchmark Dataset Licensing", "Designated R&D Reserve", 19.5, 1.065, "Q2_Q4"),
    CostCenterBaseline("LI-35", "DIV-R", "Designated R&D Reserve", "DESIGNATED_RESERVE", "CC-905", "Experimental Silicon Accelerator Lease", "Contractual Infrastructure", 29.0, 1.045, "FLAT"),
    CostCenterBaseline("LI-36", "DIV-R", "Designated R&D Reserve", "DESIGNATED_RESERVE", "CC-906", "University Research Grant Consortium", "Designated R&D Reserve", 16.5, 1.040, "FLAT"),
)

ONE_OFF_SPIKES: Dict[Tuple[str, str], Tuple[float, str]] = {
    ("CC-104", "2025-03"): (95.00, "Legacy cluster retirement charge (ADR-0001 exclusion)"),
    ("CC-108", "2026-01"): (120.00, "Data center rack consolidation fee (ADR-0001 exclusion)"),
    ("CC-205", "2026-04"): (110.00, "Regional depot lease exit settlement (ADR-0001 exclusion)"),
    ("CC-306", "2026-07"): (85.00, "ERP chart-of-accounts migration spike (ADR-0001 exclusion)"),
}

HUMAN_ANALYST_OVERRIDES: List[Dict[str, Any]] = [
    {
        "Line_ID": "LI-03",
        "Cost_Center": "CC-103",
        "Analyst_Override_Flag": "LOCKED",
        "Override_Adjustment_Pct": 2.50,
        "Override_Final_Budget_NIU": 1246.80,
        "Review_Disposition": "HUMAN_LOCKED_APPROVED",
        "Analyst_ID": "FP&A-CTRL-01",
        "Analyst_Commentary": "Locked per VP Engineering sign-off: retains 2 principal systems architects for Q2 platform migration.",
    },
    {
        "Line_ID": "LI-07",
        "Cost_Center": "CC-107",
        "Analyst_Override_Flag": "LOCKED",
        "Override_Adjustment_Pct": -4.00,
        "Override_Final_Budget_NIU": 298.50,
        "Review_Disposition": "HUMAN_LOCKED_APPROVED",
        "Analyst_ID": "FP&A-CTRL-01",
        "Analyst_Commentary": "Locked per negotiated multi-year bandwidth addendum signed 2026-09-14.",
    },
    {
        "Line_ID": "LI-12",
        "Cost_Center": "CC-202",
        "Analyst_Override_Flag": "LOCKED",
        "Override_Adjustment_Pct": -8.50,
        "Override_Final_Budget_NIU": 286.40,
        "Review_Disposition": "HUMAN_LOCKED_APPROVED",
        "Analyst_ID": "FP&A-CTRL-02",
        "Analyst_Commentary": "Locked by Field Ops Controller: flagship Q3 commercial summit booth deposit already contracted.",
    },
    {
        "Line_ID": "LI-18",
        "Cost_Center": "CC-208",
        "Analyst_Override_Flag": "LOCKED",
        "Override_Adjustment_Pct": -5.00,
        "Override_Final_Budget_NIU": 362.10,
        "Review_Disposition": "HUMAN_LOCKED_APPROVED",
        "Analyst_ID": "FP&A-CTRL-02",
        "Analyst_Commentary": "Locked per CMO pipeline target: preserves high-intent search campaigns in H1.",
    },
    {
        "Line_ID": "LI-23",
        "Cost_Center": "CC-303",
        "Analyst_Override_Flag": "LOCKED",
        "Override_Adjustment_Pct": 3.00,
        "Override_Final_Budget_NIU": 195.20,
        "Review_Disposition": "HUMAN_LOCKED_APPROVED",
        "Analyst_ID": "FP&A-CTRL-03",
        "Analyst_Commentary": "Locked per Audit Committee engagement letter covering multi-jurisdiction statutory filings.",
    },
    {
        "Line_ID": "LI-29",
        "Cost_Center": "CC-309",
        "Analyst_Override_Flag": "LOCKED",
        "Override_Adjustment_Pct": -10.00,
        "Override_Final_Budget_NIU": 182.70,
        "Review_Disposition": "HUMAN_LOCKED_APPROVED",
        "Analyst_ID": "FP&A-CTRL-03",
        "Analyst_Commentary": "Locked per CHRO review: retains specialized executive search retainer while insourcing tier-2 roles.",
    },
    {
        "Line_ID": "LI-33",
        "Cost_Center": "CC-903",
        "Analyst_Override_Flag": "LOCKED",
        "Override_Adjustment_Pct": 0.00,
        "Override_Final_Budget_NIU": 756.00,
        "Review_Disposition": "HUMAN_LOCKED_RING_FENCED",
        "Analyst_ID": "FP&A-CTRL-RD",
        "Analyst_Commentary": "Locked per R&D Board Charter: ring-fenced cohort of 6 Applied AI Research Fellows (ADR-0002/0004).",
    },
]

_SEASONAL_WEIGHTS: Dict[str, Tuple[float, ...]] = {
    "Q4_HEAVY": (0.92, 0.94, 0.96, 0.90, 0.92, 0.95, 0.96, 0.98, 1.01, 1.14, 1.16, 1.16),
    "Q2_Q4": (0.90, 0.90, 0.95, 1.10, 1.12, 1.08, 0.88, 0.90, 0.92, 1.08, 1.09, 1.08),
    "FLAT": (0.98, 0.99, 1.00, 0.99, 1.00, 1.01, 1.00, 1.01, 1.00, 1.01, 1.00, 1.01),
}


def _seasonal_multiplier(profile: str, month_index_in_year: int) -> float:
    """Return deterministic monthly seasonal weight whose 12-month average equals 1.00."""
    weights = _SEASONAL_WEIGHTS.get(profile, _SEASONAL_WEIGHTS["FLAT"])
    return weights[month_index_in_year]


def generate_raw_datasets(
    raw_dir: Path = RAW_DIR,
    catalog: Tuple[CostCenterBaseline, ...] = LINE_ITEM_CATALOG,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate deterministic 24-month raw actuals and human analyst override tables."""
    raw_dir.mkdir(parents=True, exist_ok=True)

    records: List[Dict[str, Any]] = []
    for item in catalog:
        for m_idx, month_str in enumerate(ALL_MONTHS_24M):
            window_label = "P12M" if m_idx < 12 else "TTM"
            month_in_year = m_idx % 12
            year_multiplier = 1.0 if m_idx < 12 else item.annual_trend_factor
            seasonal_mult = _seasonal_multiplier(item.seasonality_profile, month_in_year)

            recurring_niu = round(item.base_monthly_niu * year_multiplier * seasonal_mult, 2)
            spike_info = ONE_OFF_SPIKES.get((item.cost_center, month_str))
            if spike_info is not None:
                one_off_niu = round(spike_info[0], 2)
                one_off_reason = spike_info[1]
                is_one_off = 1
            else:
                one_off_niu = 0.00
                one_off_reason = "NONE"
                is_one_off = 0

            gross_niu = round(recurring_niu + one_off_niu, 2)
            records.append(
                {
                    "Line_ID": item.line_id,
                    "Division_ID": item.division_id,
                    "Division_Name": item.division_name,
                    "Fund_Type": item.fund_type,
                    "Cost_Center": item.cost_center,
                    "Line_Item_Name": item.line_item_name,
                    "Expense_Category": item.expense_category,
                    "Seasonality_Profile": item.seasonality_profile,
                    "Month": month_str,
                    "Window": window_label,
                    "Gross_Actual_NIU": gross_niu,
                    "One_Off_NIU": one_off_niu,
                    "Recurring_Actual_NIU": recurring_niu,
                    "Is_One_Off_Spike": is_one_off,
                    "One_Off_Reason": one_off_reason,
                }
            )

    raw_df = pd.DataFrame(records)
    overrides_df = pd.DataFrame(HUMAN_ANALYST_OVERRIDES)

    raw_df.to_csv(raw_dir / "historical_actuals_24m.csv", index=False)
    overrides_df.to_csv(raw_dir / "human_analyst_overrides.csv", index=False)
    return raw_df, overrides_df


def validate_and_separate_actuals(
    raw_df: pd.DataFrame,
    overrides_df: pd.DataFrame,
    processed_dir: Path = PROCESSED_DIR,
    config_path: Path = CONFIG_PATH,
) -> Dict[str, Any]:
    """Validate schema invariants and enforce ADR-0001 one-off restructuring exclusion."""
    policy = load_governance_policy(config_path)
    processed_dir.mkdir(parents=True, exist_ok=True)

    required_cols = {
        "Line_ID",
        "Division_ID",
        "Division_Name",
        "Fund_Type",
        "Cost_Center",
        "Line_Item_Name",
        "Expense_Category",
        "Month",
        "Window",
        "Gross_Actual_NIU",
        "One_Off_NIU",
        "Recurring_Actual_NIU",
        "Is_One_Off_Spike",
        "One_Off_Reason",
    }
    missing = required_cols - set(raw_df.columns)
    if missing:
        raise ValueError(f"Missing required columns in raw actuals: {sorted(missing)}")

    expected_records = len(LINE_ITEM_CATALOG) * policy.total_months
    if len(raw_df) != expected_records:
        raise ValueError(f"Expected {expected_records} monthly records, got {len(raw_df)}")

    if raw_df["Cost_Center"].nunique() != len(LINE_ITEM_CATALOG):
        raise ValueError(f"Expected {len(LINE_ITEM_CATALOG)} distinct cost centers, got {raw_df['Cost_Center'].nunique()}")

    if len(overrides_df) != len(HUMAN_ANALYST_OVERRIDES):
        raise ValueError(f"Expected {len(HUMAN_ANALYST_OVERRIDES)} human analyst overrides, got {len(overrides_df)}")

    residual = (raw_df["Gross_Actual_NIU"] - raw_df["One_Off_NIU"] - raw_df["Recurring_Actual_NIU"]).abs().max()
    if residual > 1e-6:
        raise ValueError(f"ADR-0001 reconciliation error: max residual {residual}")

    excluded_df = raw_df[raw_df["Is_One_Off_Spike"] == 1].copy()
    if len(excluded_df) != policy.expected_one_off_event_count:
        raise ValueError(
            f"ADR-0001 expected {policy.expected_one_off_event_count} one-off events, found {len(excluded_df)}"
        )

    clean_df = raw_df.drop(columns=["Gross_Actual_NIU", "One_Off_NIU", "Is_One_Off_Spike", "One_Off_Reason"]).copy()

    excluded_df.to_csv(processed_dir / "excluded_one_off_items.csv", index=False)
    clean_df.to_csv(processed_dir / "clean_recurring_actuals_24m.csv", index=False)

    ttm_excluded_niu = round(float(excluded_df[excluded_df["Window"] == "TTM"]["One_Off_NIU"].sum()), 2)
    p12m_excluded_niu = round(float(excluded_df[excluded_df["Window"] == "P12M"]["One_Off_NIU"].sum()), 2)
    total_excluded_niu = round(float(excluded_df["One_Off_NIU"].sum()), 2)

    return {
        "total_monthly_records": int(len(raw_df)),
        "max_reconciliation_residual_niu": round(float(residual), 6),
        "distinct_line_items": int(raw_df["Cost_Center"].nunique()),
        "divisions_count": int(raw_df["Division_ID"].nunique()),
        "excluded_one_off_events": int(len(excluded_df)),
        "p12m_excluded_one_off_niu": p12m_excluded_niu,
        "ttm_excluded_one_off_niu": ttm_excluded_niu,
        "total_excluded_one_off_niu": total_excluded_niu,
        "human_overrides_count": int(len(overrides_df)),
    }


def run_stage_1(
    raw_dir: Path = RAW_DIR,
    processed_dir: Path = PROCESSED_DIR,
    config_path: Path = CONFIG_PATH,
) -> Dict[str, Any]:
    """Execute Stage 1 end-to-end and return summary telemetry."""
    raw_df, overrides_df = generate_raw_datasets(raw_dir=raw_dir)
    return validate_and_separate_actuals(
        raw_df=raw_df,
        overrides_df=overrides_df,
        processed_dir=processed_dir,
        config_path=config_path,
    )


def run_stage_1_on_existing_raw(
    raw_dir: Path = RAW_DIR,
    processed_dir: Path = PROCESSED_DIR,
    config_path: Path = CONFIG_PATH,
) -> Dict[str, Any]:
    """Run the Stage 1 checks on raw files already on disk, without regenerating them.

    The agent runtime uses this entry point: the coordinator writes the ledger extract once,
    and the variance analyst only reads `data/raw/`.
    """
    raw_df = pd.read_csv(raw_dir / "historical_actuals_24m.csv")
    overrides_df = pd.read_csv(raw_dir / "human_analyst_overrides.csv")
    return validate_and_separate_actuals(
        raw_df=raw_df,
        overrides_df=overrides_df,
        processed_dir=processed_dir,
        config_path=config_path,
    )


if __name__ == "__main__":
    stats = run_stage_1()
    print(f"[Stage 1] Completed prepare_data.py: {stats}")
