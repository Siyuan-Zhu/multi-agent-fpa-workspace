"""Stage 2: Compute Prior-12M vs. Trailing-12M (TTM) growth rates, volatility (CV), and seasonality indices.

Owner Agent: agent.fpa.variance_analyst
Governing Policy: ADR-0001 (Full-Cycle 12M Seasonal Baseline & One-Off Exclusion)
Reporting Unit: Normalized Index Units (NIU), Percentages (%), Basis Points (bps)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

from src.domain import PROCESSED_DIR, RAW_DIR, TrendMetrics


DEFAULT_RAW_ACTUALS_PATH = RAW_DIR / "historical_actuals_24m.csv"
DEFAULT_TREND_OUTPUT_PATH = PROCESSED_DIR / "ttm_trend_metrics.csv"

_LINE_METADATA_COLS: List[str] = [
    "Line_ID",
    "Division_ID",
    "Division_Name",
    "Fund_Type",
    "Cost_Center",
    "Line_Item_Name",
    "Expense_Category",
    "Seasonality_Profile",
]
_Q4_MONTHS = frozenset({"2026-07", "2026-08", "2026-09"})


def compute_trend_metrics(
    raw_path: Path = DEFAULT_RAW_ACTUALS_PATH,
    output_path: Path = DEFAULT_TREND_OUTPUT_PATH,
) -> List[TrendMetrics]:
    """Compute P12M vs. TTM recurring baseline metrics, volatility CV, and Q4 seasonality share."""
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing raw actuals at {raw_path}. Run src/prepare_data.py first.")

    raw_df = pd.DataFrame(pd.read_csv(raw_path))
    metrics_list: List[TrendMetrics] = []

    for keys, group in raw_df.groupby(_LINE_METADATA_COLS, sort=False):
        (
            line_id,
            div_id,
            div_name,
            fund_type,
            cost_center,
            line_name,
            category,
            seasonality_profile,
        ) = keys

        p12m_df = group[group["Window"] == "P12M"]
        ttm_df = group[group["Window"] == "TTM"]

        p12m_gross = round(float(p12m_df["Gross_Actual_NIU"].sum()), 2)
        p12m_one_off = round(float(p12m_df["One_Off_NIU"].sum()), 2)
        p12m_recurring = round(float(p12m_df["Recurring_Actual_NIU"].sum()), 2)

        ttm_gross = round(float(ttm_df["Gross_Actual_NIU"].sum()), 2)
        ttm_one_off = round(float(ttm_df["One_Off_NIU"].sum()), 2)
        ttm_recurring = round(float(ttm_df["Recurring_Actual_NIU"].sum()), 2)

        yoy_growth_pct = round(((ttm_recurring - p12m_recurring) / p12m_recurring) * 100.0, 2)
        yoy_growth_bps = int(round(yoy_growth_pct * 100))
        gross_yoy_growth_pct = round(((ttm_gross - p12m_gross) / p12m_gross) * 100.0, 2)

        ttm_mean = float(ttm_df["Recurring_Actual_NIU"].mean())
        ttm_std = float(ttm_df["Recurring_Actual_NIU"].std(ddof=0))
        monthly_cv = round(ttm_std / ttm_mean, 4) if ttm_mean > 0 else 0.0

        q4_recurring = float(ttm_df[ttm_df["Month"].isin(_Q4_MONTHS)]["Recurring_Actual_NIU"].sum())
        q4_share_pct = round((q4_recurring / ttm_recurring) * 100.0, 2)
        seasonality_index = round(q4_share_pct / 25.0, 3)

        metrics_list.append(
            TrendMetrics(
                line_id=str(line_id),
                division_id=str(div_id),
                division_name=str(div_name),
                fund_type=str(fund_type),
                cost_center=str(cost_center),
                line_item_name=str(line_name),
                expense_category=str(category),
                seasonality_profile=str(seasonality_profile),
                p12m_gross_niu=p12m_gross,
                p12m_one_off_niu=p12m_one_off,
                p12m_recurring_niu=p12m_recurring,
                ttm_gross_niu=ttm_gross,
                ttm_excluded_one_off_niu=ttm_one_off,
                ttm_recurring_niu=ttm_recurring,
                gross_yoy_growth_pct=gross_yoy_growth_pct,
                yoy_growth_pct=yoy_growth_pct,
                yoy_growth_bps=yoy_growth_bps,
                monthly_cv=monthly_cv,
                q4_share_pct=q4_share_pct,
                seasonality_index=seasonality_index,
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([m.to_csv_row() for m in metrics_list]).to_csv(output_path, index=False)
    return metrics_list


def run_stage_2(
    raw_path: Path = DEFAULT_RAW_ACTUALS_PATH,
    output_path: Path = DEFAULT_TREND_OUTPUT_PATH,
) -> Dict[str, Any]:
    """Execute Stage 2 and return summary telemetry."""
    metrics_list = compute_trend_metrics(raw_path=raw_path, output_path=output_path)
    return {
        "line_items_processed": len(metrics_list),
        "p12m_recurring_total_niu": round(sum(m.p12m_recurring_niu for m in metrics_list), 2),
        "ttm_gross_total_niu": round(sum(m.ttm_gross_niu for m in metrics_list), 2),
        "ttm_excluded_one_off_niu": round(sum(m.ttm_excluded_one_off_niu for m in metrics_list), 2),
        "ttm_recurring_total_niu": round(sum(m.ttm_recurring_niu for m in metrics_list), 2),
        "mean_yoy_growth_pct": round(sum(m.yoy_growth_pct for m in metrics_list) / len(metrics_list), 2),
    }


if __name__ == "__main__":
    stats = run_stage_2()
    print(f"[Stage 2] Completed build_trends.py: {stats}")
