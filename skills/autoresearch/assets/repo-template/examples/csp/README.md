# CSP example task pack

This directory preserves the original HACO crystal structure prediction setup
as a runnable example task pack for the generic autoresearch toolkit.

It defines:

- MP-20 polymorph data preparation in `prepare.py`
- fixed METRe validation scoring in `evaluate.py`
- task rules in `contract.md`
- CSP prior-method boundaries in `methods.md`
- smoke-test expectations in `smoke.md`

## Objective

Given a composition, generate a crystal structure: lattice plus fractional
coordinates. The primary metric is validation METRe match rate, where higher is
better.

## Bootstrap this example

From the repository root on a clean `agent/root` branch:

```
scripts/bootstrap.sh task=csp task_path=examples/csp run_tag=<run_tag>
```

Then launch the orchestrator:

```
You are the orchestrator of the autoresearch campaign task=csp run_tag=<run_tag>.
Read program.md and runs/csp/<run_tag>/campaign.json, then run the loop.
```

## Attribution

Portions of `evaluate.py` and `prepare.py` are derived from the OMatG project
(MIT). See comments in those files for details.
