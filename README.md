# multi-agent-fpa-workspace

A Python pipeline that builds a next-year operating budget in Excel from 24 months of cost-center actuals, enforces four budget rules in code, and proves that a re-run does not overwrite an analyst's manual adjustments.

The data is synthetic. `src/prepare_data.py` generates it: 36 invented cost centers, 24 months, 4 planted one-off spikes. No real ledger figures appear anywhere. Amounts are in NIU (index units, so no real currency shows up).

## The problem

You are building the FY2027 budget from 24 months of actuals. Four things go wrong if you work in a spreadsheet by hand:

1. One-off spikes distort the trend. A facility exit fee in one month makes a line look like it grew 110%. If you cut by growth rate, you cut the wrong lines.
2. Reserve money gets swept. A designated R&D reserve sits next to the operating lines. A blanket cut across all lines takes money the reserve was set aside for.
3. Some lines cannot be cut. Contracts and compliance costs are fixed. Payroll goes through a headcount discussion, not a percentage cut.
4. Re-running overwrites human work. The controller adjusts seven lines by hand. Then a driver changes and you recalculate. The manual adjustments are gone, and nobody can show they are intact.

## The solution

Five scripts run in order. `src/run_all.py` runs all of them.

| Stage | Script | What it does |
| :--- | :--- | :--- |
| 1 | `src/prepare_data.py` | Generates the actuals. Splits each month into recurring and one-off amounts and writes the spikes to `excluded_one_off_items.csv`. |
| 2 | `src/build_trends.py` | Compares the last 12 months (TTM) with the 12 before (P12M) on recurring amounts only. Gives each line a year-over-year growth rate. |
| 3 | `src/build_rough_budget.py` | Builds `output/FY2027_Rolling_Budget_Model.xlsx`: TTM recurring spend times a growth driver per expense category. Roll-ups are live Excel formulas (`SUM`, `SUMIF`). |
| 4 | `src/cut_review_rules.py` | Applies the cut rules, writes in the controller's seven manual locks, then re-runs the model with a +1.50 point change to the growth driver and records the proof. |
| 5 | `src/verify_governance.py` | Reads the workbook back and checks every rule. Writes `governance_audit_report.json`. |

### The four business rules

Each rule is a short decision record (ADR) in `decisions/`.

| ADR | Rule |
| :--- | :--- |
| [0001](decisions/0001-ttm-seasonal-baseline-and-one-off-exclusion.md) | Remove one-off items before measuring growth, and compare full 12-month windows so seasonality is in both periods. |
| [0002](decisions/0002-ring-fenced-designated-reserve-transfers.md) | The R&D reserve is its own pool. No automated cut touches it and no money moves between the reserve and operating lines. |
| [0003](decisions/0003-tiered-opex-compression-and-protected-lines.md) | Contract and compliance lines are never cut. Personnel goes to a headcount scenario. Discretionary lines are cut by growth: 12% if growth is 8% or more, 6.5% from 3% to 8%, 3% below that. |
| [0004](decisions/0004-non-destructive-human-override-preservation.md) | A row the controller locked is never rewritten. A re-run changes only unlocked rows. |

## What "multi-agent" means here

The `workspace/agents/*.md` files are role contracts for AI coding assistants such as Claude Code working in this repo. There are three roles: variance analyst (stages 1 and 2), budget architect (stages 3 and 4) and governance auditor (stage 5). Each file says which script that role runs, what it may read, and what it may write. The permissions are also in `config/workspace_governance.json`.

The assistant loads context in layers: `workspace/GLOBAL_CONTEXT.md` (rules that always apply), then `workspace/WORKSPACE_CONTEXT.md` (this budget cycle, the divisions, which ADR applies where), then the role file. An assistant asked to run stage 4 cannot touch the raw actuals or the audit report, and it is told to cite script output instead of doing arithmetic itself.

This is a governance pattern for AI-assisted FP&A. It limits what an assistant can change, and every number traces to a script or a cell formula.

## Method

- Recurring baseline. Growth is measured on recurring amounts only, because a spike in one window makes a normal line look like an outlier.
- Trailing 12 months against the prior 12. Two full years put each seasonal pattern (flat, Q2/Q4, Q4-heavy) in both windows, so growth is not a seasonal artefact.
- Growth driver by category. The rough budget grows each line by a rate tied to its own growth, clipped to a range per category. Payroll gets a flat rate.
- Live formulas. Totals in the workbook are Excel formulas, so a reviewer can click a cell and see the arithmetic.
- Hashes for the lock proof. For every row, stage 4 computes a SHA-256 hash over the fields a human controls: cost center, flag, adjustment %, final budget, disposition and commentary. It hashes all 36 rows after the locks go in, re-runs the model, and hashes again. A locked row passes only if the two hashes are identical.

## Findings

From a fresh run of `python src/run_all.py`:

| Result | Value |
| :--- | ---: |
| TTM gross spend | 12,780.04 NIU |
| One-off spikes removed (4 events, trailing 12 months) | 315.00 NIU |
| TTM recurring baseline | 12,465.04 NIU |
| Portfolio growth, gross vs recurring | 7.21% vs 5.40% |
| Discretionary lines that would land in the wrong cut tier without ADR-0001 | 4 of 13 |
| FY2027 rough budget after the re-run | 13,099.26 NIU |
| FY2027 final budget | 12,877.22 NIU (-222.04 NIU) |
| Operating pool, final | 10,149.29 NIU |
| Reserve pool, final | 2,727.93 NIU |
| Cross-fund transfers | 0.00 NIU |
| Dispositions across 36 lines | 10 protected, 4 to headcount, 10 discretionary cuts, 6 reserve (5 ring-fenced, 1 locked), 6 locked operating |
| Locked rows unchanged after the re-run | 7 of 7 (identical hashes, 0.00 NIU change) |
| Unlocked rows recalculated | 29 of 29 |

Left in, the spikes push three lines into the 12% cut tier when their recurring growth is under 8%, and one line, whose spike fell in the prior year, shows a 25% decline when its recurring growth is 11.5%. Removing them corrects four of the 13 discretionary lines.

Of the 222.04 NIU reduction, 141.40 NIU comes from the 10 discretionary cuts (4 at 12%, 3 at 6.5%, 3 at 3%) and 80.64 NIU from the controller's seven locked adjustments. The automated rules left the other 19 unlocked lines unchanged. The reserve ends 0.38 NIU below its rough figure, and all of that is the controller's own lock on CC-903. The per-row hash proof is in [`docs/rerun_preservation_proof.json`](docs/rerun_preservation_proof.json); each locked row lists its before and after hash, and they match.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
python src/run_all.py   # rebuilds data/ and output/ from scratch
pytest -q               # 7 tests
```

`data/` and `output/` are rebuilt on every run and are gitignored. CI runs ruff, the pipeline and pytest on Python 3.11 to 3.13.

## Scope and limits

- The data is synthetic. The findings show the rules working on a planted test case, and say nothing about any real company's budget.
- No model is called by the pipeline. The "agents" are instructions for AI coding assistants, and the pipeline is ordinary Python and Excel formulas.
- `src/verify_governance.py` uses the same domain module and policy file as the build stages. It is a regression check on the rules, not an independent audit.
- The re-run tests one scenario, a +1.50 point change to the growth driver. The thresholds and cut percentages are policy settings in `config/workspace_governance.json`.
- The output is an Excel workbook and JSON files. There is no interface.

MIT licensed.
