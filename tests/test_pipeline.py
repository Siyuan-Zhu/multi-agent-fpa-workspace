"""Unit test suite for Flagship 4: Governed Multi-Agent FP&A Workspace (Option 4B).

Run via:
    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import unittest
import openpyxl
import pandas as pd

from src.build_rough_budget import build_rough_budget_workbook
from src.build_trends import compute_trend_metrics
from src.cut_review_rules import (
    apply_pass_1_rules_and_human_locks,
    evaluate_adr_0003_rule,
    execute_pass_2_non_destructive_rerun,
)
from src.domain import (
    BudgetLineItem,
    CostCenterBaseline,
    GovernanceAuditReport,
    RerunPreservationProof,
    TrendMetrics,
    load_governance_policy,
)
from src.prepare_data import LINE_ITEM_CATALOG, run_stage_1
from src.run_all import run_all
from src.verify_governance import run_governance_audit


ROOT_DIR = Path(__file__).resolve().parents[1]


class TestMultiAgentFPAWorkspace(unittest.TestCase):
    """End-to-end verification of the deepened FP&A modules, ADR-0001..0004, and confidentiality rules."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = load_governance_policy()
        cls.stage_1_summary = run_stage_1()
        cls.trend_metrics = compute_trend_metrics()
        cls.initial_budget_items = build_rough_budget_workbook()
        cls.pass_1_items = apply_pass_1_rules_and_human_locks()
        cls.rerun_proof = execute_pass_2_non_destructive_rerun(cls.pass_1_items, macro_driver_delta_pct=1.50)
        cls.audit_report = run_governance_audit()
        cls.pipeline_summary = run_all()

    def test_01_context_hierarchy_and_adr_files_exist(self) -> None:
        """Verify 3-Tier Context Hierarchy and 4 ADR markdown files exist and are non-empty."""
        expected_paths = [
            ROOT_DIR / "config" / "workspace_governance.json",
            ROOT_DIR / "workspace" / "GLOBAL_CONTEXT.md",
            ROOT_DIR / "workspace" / "WORKSPACE_CONTEXT.md",
            ROOT_DIR / "workspace" / "agents" / "variance_analyst_agent.md",
            ROOT_DIR / "workspace" / "agents" / "budget_architect_agent.md",
            ROOT_DIR / "workspace" / "agents" / "governance_auditor_agent.md",
            ROOT_DIR / "decisions" / "0001-ttm-seasonal-baseline-and-one-off-exclusion.md",
            ROOT_DIR / "decisions" / "0002-ring-fenced-designated-reserve-transfers.md",
            ROOT_DIR / "decisions" / "0003-tiered-opex-compression-and-protected-lines.md",
            ROOT_DIR / "decisions" / "0004-non-destructive-human-override-preservation.md",
        ]
        for path in expected_paths:
            self.assertTrue(path.exists(), f"Missing expected file: {path}")
            self.assertGreater(path.stat().st_size, 100, f"File unexpectedly small: {path}")

        # Verify top-level context files remain tight (< 40 lines each) per /writing-for-agents
        for top_ctx in (
            ROOT_DIR / "workspace" / "GLOBAL_CONTEXT.md",
            ROOT_DIR / "workspace" / "WORKSPACE_CONTEXT.md",
        ):
            line_count = len(top_ctx.read_text(encoding="utf-8").splitlines())
            self.assertLess(line_count, 40, f"{top_ctx.name} exceeds 40 lines ({line_count})")

        # Confirm dashboard SVG and assets directory are absent
        self.assertFalse((ROOT_DIR / "assets").exists())
        self.assertFalse((ROOT_DIR / "src" / "generate_charts.py").exists())

    def test_02_immutable_domain_types_and_seams(self) -> None:
        """Verify CostCenterBaseline, TrendMetrics, BudgetLineItem, RerunPreservationProof, and GovernanceAuditReport are frozen."""
        self.assertIsInstance(LINE_ITEM_CATALOG[0], CostCenterBaseline)
        self.assertIsInstance(self.trend_metrics[0], TrendMetrics)
        self.assertIsInstance(self.initial_budget_items[0], BudgetLineItem)
        self.assertIsInstance(self.rerun_proof, RerunPreservationProof)
        self.assertIsInstance(self.audit_report, GovernanceAuditReport)

        with self.assertRaises(FrozenInstanceError):
            LINE_ITEM_CATALOG[0].base_monthly_niu = 999.0  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            self.trend_metrics[0].ttm_recurring_niu = 0.0  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            self.pass_1_items[0].final_budget_niu = 0.0  # type: ignore[misc]

    def test_03_adr_0001_ttm_one_off_exclusion(self) -> None:
        """Verify ADR-0001 strips all 4 non-recurring spikes from TTM recurring actuals."""
        excluded_df = pd.DataFrame(pd.read_csv(ROOT_DIR / "data" / "processed" / "excluded_one_off_items.csv"))
        self.assertEqual(len(excluded_df), self.policy.expected_one_off_event_count)
        self.assertEqual(len(self.trend_metrics), 36)
        self.assertAlmostEqual(float(excluded_df["One_Off_NIU"].sum()), 410.00, places=2)
        self.assertAlmostEqual(sum(m.ttm_excluded_one_off_niu for m in self.trend_metrics), 315.00, places=2)

        for metric in self.trend_metrics:
            self.assertAlmostEqual(
                metric.ttm_gross_niu - metric.ttm_excluded_one_off_niu,
                metric.ttm_recurring_niu,
                places=5,
            )
        self.assertTrue(self.audit_report.adr_audits["ADR-0001"]["passed"])

    def test_04_adr_0002_ring_fenced_reserve_separation(self) -> None:
        """Verify ADR-0002 keeps Designated R&D Reserve (DIV-R) ring-fenced with zero operating sweeps."""
        self.assertTrue(self.audit_report.adr_audits["ADR-0002"]["passed"])
        self.assertEqual(self.audit_report.adr_audits["ADR-0002"]["ring_fenced_lines_count"], 6)
        self.assertEqual(self.audit_report.adr_audits["ADR-0002"]["cross_fund_transfer_niu"], 0.0)
        self.assertEqual(len(self.audit_report.adr_audits["ADR-0002"]["violations"]), 0)

        reserve_items = [item for item in self.initial_budget_items if item.division_id == self.policy.ring_fenced_division_id]
        self.assertEqual(len(reserve_items), 6)
        self.assertTrue(all(item.is_ring_fenced for item in reserve_items))

    def test_05_adr_0003_tiered_opex_compression_and_protected_lines(self) -> None:
        """Verify ADR-0003 caps Discretionary Opex cuts at -12.00% and protects Infrastructure/Compliance."""
        self.assertTrue(self.audit_report.adr_audits["ADR-0003"]["passed"])
        self.assertEqual(len(self.audit_report.adr_audits["ADR-0003"]["violations"]), 0)

        self.assertEqual(
            evaluate_adr_0003_rule("OPERATING", "Discretionary Opex", 9.5, policy=self.policy)[0],
            -12.00,
        )
        self.assertEqual(
            evaluate_adr_0003_rule("OPERATING", "Discretionary Opex", 5.0, policy=self.policy)[0],
            -6.50,
        )
        self.assertEqual(
            evaluate_adr_0003_rule("OPERATING", "Discretionary Opex", 1.5, policy=self.policy)[0],
            -3.00,
        )
        self.assertEqual(
            evaluate_adr_0003_rule("OPERATING", "Contractual Infrastructure", 9.0, policy=self.policy)[0],
            0.00,
        )

    def test_06_adr_0004_non_destructive_human_override_preservation(self) -> None:
        """Verify ADR-0004 preserves 7/7 LOCKED rows verbatim across Pass 2 re-run while updating 29/29 UNLOCKED rows."""
        self.assertTrue(self.audit_report.adr_audits["ADR-0004"]["passed"])
        self.assertEqual(self.rerun_proof.locked_rows_count, 7)
        self.assertEqual(self.rerun_proof.unlocked_rows_count, 29)
        self.assertTrue(self.rerun_proof.all_locked_rows_preserved_verbatim)
        self.assertTrue(self.rerun_proof.all_unlocked_rows_recalculated)

        for locked_item in self.rerun_proof.locked_row_proofs:
            self.assertTrue(locked_item["cryptographic_match"])
            self.assertEqual(locked_item["niu_delta"], 0.0)
            self.assertEqual(locked_item["pass_1_sha256"], locked_item["pass_2_sha256"])

        for unlocked_item in self.rerun_proof.unlocked_row_proofs:
            self.assertTrue(unlocked_item["dynamically_recalculated"])
            self.assertGreater(unlocked_item["niu_delta"], 0.0)

    def test_07_live_excel_formulas_intact(self) -> None:
        """Verify output/FY2027_Rolling_Budget_Model.xlsx contains live =SUM and =SUMIF Excel formulas."""
        wb = openpyxl.load_workbook(ROOT_DIR / "output" / "FY2027_Rolling_Budget_Model.xlsx", data_only=False)
        ws_model = wb["FY2027_Budget_Model"]
        ws_exec = wb["Executive_Summary"]

        self.assertEqual(ws_model["H38"].value, "=SUM(H2:H37)")
        self.assertEqual(ws_model["J38"].value, "=SUM(J2:J37)")
        self.assertEqual(ws_model["M38"].value, "=SUM(M2:M37)")
        self.assertEqual(ws_model["O38"].value, "=SUM(O2:O37)")
        self.assertEqual(ws_exec["H5"].value, "=SUM(H2:H4)")
        self.assertEqual(ws_exec["H7"].value, "=H5+H6")


if __name__ == "__main__":
    unittest.main()
