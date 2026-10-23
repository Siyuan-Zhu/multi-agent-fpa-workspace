# AGENTS.md

A budgeting pipeline on synthetic data, run by three Claude Agent SDK agents. `README.md` explains what it does. This file covers changing it safely.

## Before every commit, run the CI sequence

```bash
pip install -r requirements.txt pytest "ruff>=0.6,<1"
ruff check . && python src/run_all.py && pytest -q
```

The tests never call a model. Live agent runs also need `requirements-agents.txt` and a Claude Code login or `ANTHROPIC_API_KEY`.

## Rules

- Every figure comes from script output or a workbook formula. Docs quote it from a fresh `python src/run_all.py`.
- Data stays synthetic: invented cost centers, amounts in NIU.
- `data/` and `output/` are rebuilt on every run. To change them, change the script that writes them.
- `demo/` is a recording. When a script's output changes, the replay test goes red: ask before re-recording, because it calls the live model (`python src/run_agents.py --record demo/clean_run`, and `--tamper --record demo/rejected_run`).
- Ask before changing role scopes or ADR thresholds in `config/workspace_governance.json`. They set what each agent may run, read and write; `tests/test_agents.py` pins each role's tools.
- `workspace/GLOBAL_CONTEXT.md` and `WORKSPACE_CONTEXT.md` go into every agent's system prompt and stay under 40 lines (tested).
- `src/agents/sdk_runner.py` is the only module that imports `claude_agent_sdk`, which keeps CI free of the SDK.

## Gotchas

- `docs/rerun_preservation_proof.json` is a committed copy that no script writes. Refresh it from `data/processed/` when Stage 4 output changes.
- `tests/test_pipeline.py` fails if `assets/` or `src/generate_charts.py` exists.
- `run_pipeline` in `src/agents/coordinator.py` deletes `data/processed/` and `output/` before it starts.
