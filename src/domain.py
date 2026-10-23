"""Domain types, policy loader, and worksheet row adapter for the Multi-Agent FP&A Workspace.

Provides immutable dataclasses (`frozen=True`) and single-source-of-truth policy evaluation
loaded from `config/workspace_governance.json`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config" / "workspace_governance.json"
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
OUTPUT_DIR = ROOT_DIR / "output"
WORKBOOK_PATH = OUTPUT_DIR / "FY2027_Rolling_Budget_Model.xlsx"
PROOF_PATH = PROCESSED_DIR / "rerun_preservation_proof.json"
AUDIT_REPORT_PATH = PROCESSED_DIR / "governance_audit_report.json"

BUDGET_MODEL_HEADERS: Tuple[str, ...] = (
    "Line_ID",
    "Division_ID",
    "Division_Name",
    "Fund_Type",
    "Cost_Center",
    "Line_Item_Name",
    "Expense_Category",
    "P12M_Recurring_NIU",
    "TTM_Excluded_One_Off_NIU",
    "TTM_Recurring_NIU",
    "YoY_Growth_Pct",
    "Baseline_Growth_Driver_Pct",
    "Rough_Budget_NIU",
    "Recommended_Adjustment_Pct",
    "Final_Budget_NIU",
    "Cross_Fund_Transfer_NIU",
    "Ring_Fenced_Flag",
    "Analyst_Override_Flag",
    "Review_Disposition",
    "Analyst_Commentary",
)


class _DictAccessibleDataclass:
    """Mixin enabling both attribute access and read-only mapping subscripting (`obj['key']`)."""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)  # type: ignore[arg-type]

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]


@dataclass(frozen=True)
class WorkspaceGovernancePolicy(_DictAccessibleDataclass):
    """Single-source-of-truth governance parameters parsed from `config/workspace_governance.json`."""

    workspace_id: str
    reporting_unit: str
    fiscal_year: str
    total_months: int
    expected_one_off_event_count: int
    ring_fenced_division_id: str
    discretionary_max_cut_pct: float
    discretionary_high_growth_trigger_pct: float
    discretionary_high_growth_cut_pct: float
    discretionary_moderate_growth_trigger_pct: float
    discretionary_moderate_growth_cut_pct: float
    discretionary_low_growth_cut_pct: float
    protected_categories: Tuple[str, ...]
    headcount_review_categories: Tuple[str, ...]
    lock_flag_column: str
    locked_value: str
    unlocked_value: str
    required_relative_paths: Tuple[str, ...]


def load_governance_policy(config_path: Path = CONFIG_PATH) -> WorkspaceGovernancePolicy:
    """Load and parse `config/workspace_governance.json` into an immutable policy object."""
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    hierarchy = raw["context_hierarchy"]
    agents = hierarchy["tier_3_agents"]
    adrs = raw["adr_policies"]
    adr1 = adrs["ADR-0001"]
    adr2 = adrs["ADR-0002"]
    adr3 = adrs["ADR-0003"]
    adr4 = adrs["ADR-0004"]

    required_paths = (
        hierarchy["tier_1_global"],
        hierarchy["tier_2_workspace"],
        agents["variance_analyst"]["contract_path"],
        agents["budget_architect"]["contract_path"],
        agents["governance_auditor"]["contract_path"],
        adr1["file"],
        adr2["file"],
        adr3["file"],
        adr4["file"],
    )

    return WorkspaceGovernancePolicy(
        workspace_id=str(raw["workspace_id"]),
        reporting_unit=str(raw["reporting_unit"]),
        fiscal_year=str(raw["fiscal_year"]),
        total_months=int(raw["historical_window"]["total_months"]),
        expected_one_off_event_count=int(adr1["expected_one_off_event_count"]),
        ring_fenced_division_id=str(adr2["ring_fenced_division_id"]),
        discretionary_max_cut_pct=float(adr3["discretionary_max_cut_pct"]),
        discretionary_high_growth_trigger_pct=float(adr3["discretionary_high_growth_trigger_pct"]),
        discretionary_high_growth_cut_pct=float(adr3["discretionary_high_growth_cut_pct"]),
        discretionary_moderate_growth_trigger_pct=float(adr3["discretionary_moderate_growth_trigger_pct"]),
        discretionary_moderate_growth_cut_pct=float(adr3["discretionary_moderate_growth_cut_pct"]),
        discretionary_low_growth_cut_pct=float(adr3["discretionary_low_growth_cut_pct"]),
        protected_categories=tuple(str(c) for c in adr3["protected_categories"]),
        headcount_review_categories=tuple(str(c) for c in adr3["headcount_review_categories"]),
        lock_flag_column=str(adr4["lock_flag_column"]),
        locked_value=str(adr4["locked_value"]),
        unlocked_value=str(adr4["unlocked_value"]),
        required_relative_paths=required_paths,
    )


@dataclass(frozen=True)
class CostCenterBaseline(_DictAccessibleDataclass):
    """Immutable catalog specification for a single cost-center line item in Stage 1."""

    line_id: str
    division_id: str
    division_name: str
    fund_type: str
    cost_center: str
    line_item_name: str
    expense_category: str
    base_monthly_niu: float
    annual_trend_factor: float
    seasonality_profile: str


@dataclass(frozen=True)
class TrendMetrics(_DictAccessibleDataclass):
    """Immutable Stage 2 P12M vs. TTM recurring velocity and seasonality metrics for a cost center."""

    line_id: str
    division_id: str
    division_name: str
    fund_type: str
    cost_center: str
    line_item_name: str
    expense_category: str
    seasonality_profile: str
    p12m_gross_niu: float
    p12m_one_off_niu: float
    p12m_recurring_niu: float
    ttm_gross_niu: float
    ttm_excluded_one_off_niu: float
    ttm_recurring_niu: float
    gross_yoy_growth_pct: float
    yoy_growth_pct: float
    yoy_growth_bps: int
    monthly_cv: float
    q4_share_pct: float
    seasonality_index: float

    def to_csv_row(self) -> Dict[str, Any]:
        """Serialize to the canonical column names used in `ttm_trend_metrics.csv`."""
        return {
            "Line_ID": self.line_id,
            "Division_ID": self.division_id,
            "Division_Name": self.division_name,
            "Fund_Type": self.fund_type,
            "Cost_Center": self.cost_center,
            "Line_Item_Name": self.line_item_name,
            "Expense_Category": self.expense_category,
            "Seasonality_Profile": self.seasonality_profile,
            "P12M_Gross_NIU": self.p12m_gross_niu,
            "P12M_One_Off_NIU": self.p12m_one_off_niu,
            "P12M_Recurring_NIU": self.p12m_recurring_niu,
            "TTM_Gross_NIU": self.ttm_gross_niu,
            "TTM_Excluded_One_Off_NIU": self.ttm_excluded_one_off_niu,
            "TTM_Recurring_NIU": self.ttm_recurring_niu,
            "Gross_YoY_Growth_Pct": self.gross_yoy_growth_pct,
            "YoY_Growth_Pct": self.yoy_growth_pct,
            "YoY_Growth_Bps": self.yoy_growth_bps,
            "Monthly_CV": self.monthly_cv,
            "Q4_Share_Pct": self.q4_share_pct,
            "Seasonality_Index": self.seasonality_index,
        }

    @classmethod
    def from_mapping(cls, row: Any) -> "TrendMetrics":
        """Construct a `TrendMetrics` instance from a pandas Series or dict row."""
        return cls(
            line_id=str(row["Line_ID"]),
            division_id=str(row["Division_ID"]),
            division_name=str(row["Division_Name"]),
            fund_type=str(row["Fund_Type"]),
            cost_center=str(row["Cost_Center"]),
            line_item_name=str(row["Line_Item_Name"]),
            expense_category=str(row["Expense_Category"]),
            seasonality_profile=str(row["Seasonality_Profile"]),
            p12m_gross_niu=round(float(row["P12M_Gross_NIU"]), 2),
            p12m_one_off_niu=round(float(row["P12M_One_Off_NIU"]), 2),
            p12m_recurring_niu=round(float(row["P12M_Recurring_NIU"]), 2),
            ttm_gross_niu=round(float(row["TTM_Gross_NIU"]), 2),
            ttm_excluded_one_off_niu=round(float(row["TTM_Excluded_One_Off_NIU"]), 2),
            ttm_recurring_niu=round(float(row["TTM_Recurring_NIU"]), 2),
            gross_yoy_growth_pct=round(float(row["Gross_YoY_Growth_Pct"]), 2),
            yoy_growth_pct=round(float(row["YoY_Growth_Pct"]), 2),
            yoy_growth_bps=int(row["YoY_Growth_Bps"]),
            monthly_cv=round(float(row["Monthly_CV"]), 4),
            q4_share_pct=round(float(row["Q4_Share_Pct"]), 2),
            seasonality_index=round(float(row["Seasonality_Index"]), 3),
        )


@dataclass(frozen=True)
class BudgetLineItem(_DictAccessibleDataclass):
    """Immutable representation of a row in `FY2027_Budget_Model` with canonical SHA-256 lock hashing."""

    line_id: str
    division_id: str
    division_name: str
    fund_type: str
    cost_center: str
    line_item_name: str
    expense_category: str
    p12m_recurring_niu: float
    ttm_excluded_one_off_niu: float
    ttm_recurring_niu: float
    yoy_growth_pct: float
    baseline_growth_driver_pct: float
    rough_budget_niu: float
    recommended_adjustment_pct: float
    final_budget_niu: float
    cross_fund_transfer_niu: float
    ring_fenced_flag: str
    analyst_override_flag: str
    review_disposition: str
    analyst_commentary: str

    @property
    def is_ring_fenced(self) -> bool:
        return self.fund_type == "DESIGNATED_RESERVE" and self.ring_fenced_flag == "TRUE"

    @property
    def is_locked(self) -> bool:
        return self.analyst_override_flag == "LOCKED"

    @property
    def protected_fields_sha256(self) -> str:
        """Compute canonical SHA-256 digest over ADR-0004 protected human-override fields."""
        payload = (
            f"{self.cost_center}|{self.analyst_override_flag}|"
            f"{self.recommended_adjustment_pct:.2f}|{self.final_budget_niu:.2f}|"
            f"{self.review_disposition}|{self.analyst_commentary}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_excel_row(self) -> List[Any]:
        """Return ordered cell values matching `BUDGET_MODEL_HEADERS` (Columns A..T)."""
        return [
            self.line_id,
            self.division_id,
            self.division_name,
            self.fund_type,
            self.cost_center,
            self.line_item_name,
            self.expense_category,
            round(self.p12m_recurring_niu, 2),
            round(self.ttm_excluded_one_off_niu, 2),
            round(self.ttm_recurring_niu, 2),
            round(self.yoy_growth_pct, 2),
            round(self.baseline_growth_driver_pct, 2),
            round(self.rough_budget_niu, 2),
            round(self.recommended_adjustment_pct, 2),
            round(self.final_budget_niu, 2),
            round(self.cross_fund_transfer_niu, 2),
            self.ring_fenced_flag,
            self.analyst_override_flag,
            self.review_disposition,
            self.analyst_commentary,
        ]

    def write_to_worksheet_row(self, ws: Any, row_idx: int) -> None:
        """Write all 20 fields of this `BudgetLineItem` to `row_idx` in `ws`."""
        for col_idx, val in enumerate(self.to_excel_row(), start=1):
            ws.cell(row=row_idx, column=col_idx, value=val)

    @classmethod
    def from_worksheet_row(cls, ws: Any, row_idx: int) -> "BudgetLineItem":
        """Read a `BudgetLineItem` from `row_idx` (Columns A..T) of an `openpyxl` worksheet."""
        return cls(
            line_id=str(ws.cell(row=row_idx, column=1).value),
            division_id=str(ws.cell(row=row_idx, column=2).value),
            division_name=str(ws.cell(row=row_idx, column=3).value),
            fund_type=str(ws.cell(row=row_idx, column=4).value),
            cost_center=str(ws.cell(row=row_idx, column=5).value),
            line_item_name=str(ws.cell(row=row_idx, column=6).value),
            expense_category=str(ws.cell(row=row_idx, column=7).value),
            p12m_recurring_niu=round(float(ws.cell(row=row_idx, column=8).value), 2),
            ttm_excluded_one_off_niu=round(float(ws.cell(row=row_idx, column=9).value), 2),
            ttm_recurring_niu=round(float(ws.cell(row=row_idx, column=10).value), 2),
            yoy_growth_pct=round(float(ws.cell(row=row_idx, column=11).value), 2),
            baseline_growth_driver_pct=round(float(ws.cell(row=row_idx, column=12).value), 2),
            rough_budget_niu=round(float(ws.cell(row=row_idx, column=13).value), 2),
            recommended_adjustment_pct=round(float(ws.cell(row=row_idx, column=14).value), 2),
            final_budget_niu=round(float(ws.cell(row=row_idx, column=15).value), 2),
            cross_fund_transfer_niu=round(float(ws.cell(row=row_idx, column=16).value), 2),
            ring_fenced_flag=str(ws.cell(row=row_idx, column=17).value),
            analyst_override_flag=str(ws.cell(row=row_idx, column=18).value),
            review_disposition=str(ws.cell(row=row_idx, column=19).value),
            analyst_commentary=str(ws.cell(row=row_idx, column=20).value),
        )

    def to_snapshot_dict(self, row_index: int) -> Dict[str, Any]:
        """Return canonical row snapshot dictionary including SHA-256 fingerprint."""
        return {
            "row_index": row_index,
            "line_id": self.line_id,
            "cost_center": self.cost_center,
            "override_flag": self.analyst_override_flag,
            "baseline_driver_pct": self.baseline_growth_driver_pct,
            "rough_budget_niu": self.rough_budget_niu,
            "recommended_adjustment_pct": self.recommended_adjustment_pct,
            "final_budget_niu": self.final_budget_niu,
            "review_disposition": self.review_disposition,
            "analyst_commentary": self.analyst_commentary,
            "protected_fields_sha256": self.protected_fields_sha256,
        }


@dataclass(frozen=True)
class RerunPreservationProof(_DictAccessibleDataclass):
    """Immutable Stage 4 cryptographic proof of ADR-0004 non-destructive human lock preservation."""

    adr_id: str
    macro_driver_rerun_shock_bps: int
    total_line_items: int
    locked_rows_count: int
    unlocked_rows_count: int
    all_locked_rows_preserved_verbatim: bool
    all_unlocked_rows_recalculated: bool
    pass_1_portfolio_final_budget_niu: float
    pass_2_portfolio_rough_budget_niu: float
    pass_2_portfolio_final_budget_niu: float
    net_compression_savings_vs_rough_niu: float
    locked_row_proofs: List[Dict[str, Any]]
    unlocked_row_proofs: List[Dict[str, Any]]


@dataclass(frozen=True)
class GovernanceAuditReport(_DictAccessibleDataclass):
    """Immutable Stage 5 independent governance audit report across ADR-0001..0004."""

    workspace_id: str
    reporting_unit: str
    overall_governance_compliant: bool
    adr_compliance_rate_pct: float
    live_excel_formulas_verified: bool
    formula_samples: Dict[str, Dict[str, str]]
    portfolio_metrics_niu: Dict[str, float]
    disposition_breakdown: Dict[str, int]
    adr_audits: Dict[str, Dict[str, Any]]
