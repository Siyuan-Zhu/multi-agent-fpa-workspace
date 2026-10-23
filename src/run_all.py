"""Master Orchestrator: Execute all 4 deterministic FP&A pipeline stages and independent governance audit."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.build_rough_budget import run_stage_3
from src.build_trends import run_stage_2
from src.cut_review_rules import run_stage_4
from src.prepare_data import run_stage_1
from src.verify_governance import run_governance_audit


def run_all() -> Dict[str, Any]:
    """Execute the full Multi-Agent FP&A Workspace pipeline and return consolidated telemetry."""
    s1 = run_stage_1()
    s2 = run_stage_2()
    s3 = run_stage_3()
    s4 = run_stage_4()
    audit = run_governance_audit()

    return {
        "stage_1_prepare_data": s1,
        "stage_2_build_trends": s2,
        "stage_3_build_rough_budget": s3,
        "stage_4_cut_review_rules": s4,
        "governance_audit_compliant": audit.overall_governance_compliant,
        "adr_compliance_rate_pct": audit.adr_compliance_rate_pct,
        "portfolio_metrics_niu": audit.portfolio_metrics_niu,
        "disposition_breakdown": audit.disposition_breakdown,
    }


if __name__ == "__main__":
    results = run_all()
    print(json.dumps(results, indent=2))
