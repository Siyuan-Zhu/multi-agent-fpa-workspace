# multi-agent-fpa-workspace

A rolling-budget workflow built on **synthetic data**. Stage 1 (`src/prepare_data.py`) generates 24 months of actuals for 36 invented cost centers from fixed baselines, seasonal weights and 4 planted one-off spikes, so there are no real ledger figures anywhere in the repo. The three "agents" are markdown role contracts (`workspace/agents/*.md`) that say which script a role runs and what it may read or write. No model is called and nothing runs autonomously. All arithmetic is in Python or live Excel formulas, and the rules are written down as four short decision records in `decisions/`.

Amounts are index units (NIU).

## What it does

| Rule | What the code does | Result from the last run |
| :--- | :--- | :--- |
| ADR-0001 | Remove one-off spikes before trending | 4 spikes (315.00 NIU in the trailing 12 months) removed; recurring baseline 12,465.04 NIU against 12,780.04 gross |
| ADR-0002 | Keep the designated reserve separate from operating lines | 6 reserve lines (2,727.93 NIU final) and 30 operating lines (10,149.29 NIU final); no transfers between them |
| ADR-0003 | Tiered cuts on discretionary lines; no cuts on contractual, compliance or personnel lines | 10 discretionary lines cut; net change of -222.04 NIU against the rough budget |
| ADR-0004 | Controller-locked rows are never overwritten | 7 of 7 locked rows unchanged after a re-run with a +1.50% driver change; 29 of 29 unlocked rows recalculated |

The locked-row check compares SHA-256 hashes of each locked row before and after the second pass. The audit stage (`src/verify_governance.py`) re-reads the workbook and raw CSV and checks the ADR rules, but it uses the same domain module and policy file as the build stages, so it works as a regression check. The per-row proof is in [`docs/rerun_preservation_proof.json`](docs/rerun_preservation_proof.json).

## Layout

- `workspace/`: `GLOBAL_CONTEXT.md`, `WORKSPACE_CONTEXT.md` and the three role contracts (variance analyst, budget architect, governance auditor).
- `decisions/`: ADR-0001 to ADR-0004.
- `config/workspace_governance.json`: policy parameters and the read and write scopes for each role.
- `src/`: stages 1 to 5 plus `run_all.py`.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
python src/run_all.py   # regenerates data/ and output/ (gitignored)
pytest -q
```

`data/raw`, `data/processed` and `output/` are rebuilt on every run and are not committed. CI runs ruff, the pipeline and pytest on Python 3.11 to 3.13.

MIT licensed.
