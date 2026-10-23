"""Tests for the agent runtime: scopes, guards, the coordinator's send-back loop, and the recorded demo runs.

None of these call a model. The recorded runs in demo/ are replayed against the real tools.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List
import unittest

from src.agents.coordinator import Recorder, ReplayRunner, load_recording, run_pipeline
from src.agents.toolbox import SCRIPT_TOOLS, RoleToolbox, build_system_prompt
from src.domain import ROOT_DIR
from src.prepare_data import generate_raw_datasets


DEMO_DIR = ROOT_DIR / "demo"
RECORDED_RUNS = ("clean_run", "rejected_run")
EXPECTED_TOOLS = {
    "variance_analyst": {"run_prepare_data", "run_build_trends", "read_file", "submit_handoff"},
    "budget_architect": {"run_build_rough_budget", "run_cut_review_rules", "read_file", "read_workbook", "submit_handoff"},
    "governance_auditor": {"run_verify_governance", "read_file", "read_workbook", "submit_verdict"},
}


def _toolbox(role: str, task: str = "", **kwargs: Any) -> RoleToolbox:
    return RoleToolbox(role, task, lambda _event: None, **kwargs)


def scripted_runner(role: str, task: str, toolbox: RoleToolbox) -> Dict[str, Any]:
    """Stand-in for a model: runs the role's scripts in order, then hands off."""
    if role == "governance_auditor":
        output = json.loads(toolbox.call("run_verify_governance", {}))
        if output["output"]["status"] == "PASSED":
            toolbox.call("submit_verdict", {"verdict": "approve", "send_back_to": "none", "reasons": "Audit passed."})
        else:
            toolbox.call(
                "submit_verdict",
                {"verdict": "reject", "send_back_to": "budget_architect", "reasons": "ADR-0004 lock check failed."},
            )
    else:
        for script in toolbox.scope.allowed_scripts:
            toolbox.call(SCRIPT_TOOLS[script][0], {})
        toolbox.call("submit_handoff", {"status": "complete", "summary": "Stages ran."})
    return {}


class TestAgentRuntime(unittest.TestCase):
    """Guards that hold whatever the model does."""

    @classmethod
    def setUpClass(cls) -> None:
        generate_raw_datasets()

    def test_01_each_role_gets_only_its_own_tools(self) -> None:
        for role, expected in EXPECTED_TOOLS.items():
            self.assertEqual(set(_toolbox(role).specs), expected, role)

    def test_02_system_prompt_loads_the_three_tiers_in_order(self) -> None:
        prompt = build_system_prompt("budget_architect")
        positions = [
            prompt.index('path="workspace/GLOBAL_CONTEXT.md"'),
            prompt.index('path="workspace/WORKSPACE_CONTEXT.md"'),
            prompt.index('path="workspace/agents/budget_architect_agent.md"'),
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("variance_analyst_agent.md\"", prompt)

    def test_03_read_scope_is_enforced(self) -> None:
        analyst = _toolbox("variance_analyst")
        self.assertIn("ADR-0001", analyst.call("read_file", {"path": "decisions/0001-ttm-seasonal-baseline-and-one-off-exclusion.md"}))
        for path in (
            "workspace/agents/budget_architect_agent.md",
            "decisions/0003-tiered-opex-compression-and-protected-lines.md",
            "../README.md",
            "src/domain.py",
        ):
            self.assertTrue(analyst.call("read_file", {"path": path}).startswith("REFUSED"), path)
        auditor = _toolbox("governance_auditor")
        self.assertFalse(auditor.call("read_file", {"path": "workspace/agents/budget_architect_agent.md"}).startswith("REFUSED"))

    def test_04_write_outside_scope_is_flagged(self) -> None:
        stray = ROOT_DIR / "output" / "stray_note.txt"

        def writes_outside_scope() -> Dict[str, Any]:
            stray.parent.mkdir(parents=True, exist_ok=True)
            stray.write_text("not allowed", encoding="utf-8")
            return {}

        tools = dict(SCRIPT_TOOLS)
        tools["src/prepare_data.py"] = ("run_prepare_data", "test double", writes_outside_scope)
        analyst = _toolbox("variance_analyst", script_tools=tools)
        try:
            output = json.loads(analyst.call("run_prepare_data", {}))
        finally:
            stray.unlink(missing_ok=True)
        self.assertEqual(output["write_scope_violations"], ["output/stray_note.txt"])
        self.assertEqual(analyst.write_violations, ["output/stray_note.txt"])

    def test_05_real_scripts_write_only_inside_scope(self) -> None:
        analyst = _toolbox("variance_analyst")
        for tool in ("run_prepare_data", "run_build_trends"):
            output = json.loads(analyst.call(tool, {}))
            self.assertEqual(output["status"], "ok")
            self.assertEqual(output["write_scope_violations"], [])
        self.assertEqual(analyst.write_violations, [])

    def test_06_handoff_refuses_figures_not_in_tool_output(self) -> None:
        analyst = _toolbox("variance_analyst", task="Upstream figure: 1,234.56 NIU")
        refused = analyst.call("submit_handoff", {"status": "complete", "summary": "Recurring total 99,999.99 NIU."})
        self.assertTrue(refused.startswith("REFUSED"))
        self.assertIn("99999.99", refused)
        self.assertIsNone(analyst.result)
        accepted = analyst.call("submit_handoff", {"status": "complete", "summary": "Carried forward 1234.56 NIU."})
        self.assertTrue(accepted.startswith("Hand-off accepted"))

    def test_07_auditor_cannot_approve_without_a_passing_audit(self) -> None:
        auditor = _toolbox("governance_auditor")
        refused = auditor.call("submit_verdict", {"verdict": "approve", "send_back_to": "none", "reasons": "Looks fine."})
        self.assertTrue(refused.startswith("REFUSED"))
        self.assertIsNone(auditor.result)


class TestCoordinator(unittest.TestCase):
    """The hand-off order and the send-back loop, driven by a scripted runner."""

    def test_08_clean_run_is_approved_in_one_pass(self) -> None:
        summary = run_pipeline(scripted_runner, Recorder())
        self.assertEqual(summary["outcome"], "approved")
        self.assertEqual([run["role"] for run in summary["runs"]], ["variance_analyst", "budget_architect", "governance_auditor"])

    def test_09_tampered_run_is_sent_back_to_the_architect(self) -> None:
        summary = run_pipeline(scripted_runner, Recorder(), tamper=True)
        self.assertEqual(summary["outcome"], "approved")
        self.assertEqual(summary["rejections"], 1)
        self.assertEqual(
            [run["role"] for run in summary["runs"]],
            ["variance_analyst", "budget_architect", "governance_auditor", "budget_architect", "governance_auditor"],
        )
        self.assertEqual(summary["runs"][2]["result"]["verdict"], "reject")

    def test_10_rejections_are_capped(self) -> None:
        def always_reject(role: str, task: str, toolbox: RoleToolbox) -> Dict[str, Any]:
            if role != "governance_auditor":
                return scripted_runner(role, task, toolbox)
            toolbox.call("submit_verdict", {"verdict": "reject", "send_back_to": "budget_architect", "reasons": "No."})
            return {}

        summary = run_pipeline(always_reject, Recorder(), max_rejections=2)
        self.assertEqual(summary["outcome"], "halted: 3 rejections")


class TestRecordedRuns(unittest.TestCase):
    """The recorded demo runs replay against the current code with identical tool output."""

    def _replay(self, name: str) -> Dict[str, Any]:
        run_dir = DEMO_DIR / name
        events = load_recording(run_dir)
        recorded = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        replay = ReplayRunner(events)
        summary = run_pipeline(replay, Recorder(), tamper=recorded["tamper"])
        return {"events": events, "recorded": recorded, "replayed": summary, "mismatches": replay.mismatches}

    def test_11_recorded_runs_replay_identically(self) -> None:
        for name in RECORDED_RUNS:
            with self.subTest(run=name):
                result = self._replay(name)
                self.assertEqual(result["mismatches"], [])
                self.assertEqual(result["replayed"]["outcome"], result["recorded"]["outcome"])
                self.assertEqual(
                    [run["result"] for run in result["replayed"]["runs"]],
                    [run["result"] for run in result["recorded"]["runs"]],
                )

    def test_12_recorded_agents_used_only_their_own_tools(self) -> None:
        for name in RECORDED_RUNS:
            for event in load_recording(DEMO_DIR / name):
                if event["type"] == "tool_call":
                    self.assertIn(event["tool"], EXPECTED_TOOLS[event["role"]], f"{name} run {event['run']}")

    def test_13_recorded_runs_show_the_expected_paths(self) -> None:
        clean = json.loads((DEMO_DIR / "clean_run" / "summary.json").read_text(encoding="utf-8"))
        rejected = json.loads((DEMO_DIR / "rejected_run" / "summary.json").read_text(encoding="utf-8"))
        roles: List[str] = [run["role"] for run in rejected["runs"]]
        self.assertEqual(clean["outcome"], "approved")
        self.assertEqual(clean["rejections"], 0)
        self.assertEqual(rejected["outcome"], "approved")
        self.assertGreaterEqual(rejected["rejections"], 1)
        first_verdict = rejected["runs"][roles.index("governance_auditor")]["result"]
        self.assertEqual(first_verdict["verdict"], "reject")
        self.assertEqual(first_verdict["send_back_to"], "budget_architect")


if __name__ == "__main__":
    unittest.main()
