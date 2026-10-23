"""Run the three FP&A agents on the Claude Agent SDK, or replay a recorded run without a model.

    python src/run_agents.py --record demo/clean_run             # live run; needs Claude Code auth or ANTHROPIC_API_KEY
    python src/run_agents.py --tamper --record demo/rejected_run # live run with one locked row edited before the audit
    python src/run_agents.py --replay demo/rejected_run          # no model, no key: re-issue the recorded tool calls
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.agents.coordinator import Recorder, ReplayRunner, load_recording, run_pipeline, save_recording


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--record", type=Path, help="directory to save the transcript and outputs in")
    parser.add_argument("--replay", type=Path, help="recorded run to replay against the real tools")
    parser.add_argument("--tamper", action="store_true", help="edit a locked row after the budget architect hands off")
    parser.add_argument("--model", default="sonnet")
    args = parser.parse_args()

    recorder = Recorder()
    if args.replay:
        recorded = json.loads((args.replay / "summary.json").read_text(encoding="utf-8"))
        replay = ReplayRunner(load_recording(args.replay))
        summary = run_pipeline(replay, recorder, tamper=recorded["tamper"])
        print(f"Recorded outcome: {recorded['outcome']}. Replayed outcome: {summary['outcome']}.")
        for mismatch in replay.mismatches:
            print(f"MISMATCH {mismatch}")
        return 0 if summary["outcome"] == recorded["outcome"] and not replay.mismatches else 1

    from src.agents.sdk_runner import make_sdk_runner

    summary = run_pipeline(make_sdk_runner(model=args.model), recorder, tamper=args.tamper)
    models = sorted({run["model"] for run in summary["runs"] if run.get("model")})
    summary["model"] = ", ".join(models)
    summary["total_cost_usd"] = round(sum(run.get("cost_usd") or 0.0 for run in summary["runs"]), 4)
    if args.record:
        save_recording(args.record, recorder, summary)
    print(json.dumps({k: summary[k] for k in ("outcome", "rejections", "model", "total_cost_usd")}, indent=2))
    return 0 if summary["outcome"] == "approved" else 1


if __name__ == "__main__":
    sys.exit(main())
