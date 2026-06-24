# Crystal Structure Prediction task pack

This is the original HACO task, preserved as a runnable example for the generic
autoresearch toolkit.

## Objective

Given a chemical composition, generate crystal structures with lattice vectors
and fractional atomic coordinates. The search optimizes validation METRe match
rate on the MP-20 polymorph split.

## Data

`prepare.py` downloads OMatG's pinned MP-20 polymorph split and writes:

- `data/csp/mp20_ps_train.pt`
- `data/csp/mp20_ps_val.pt`
- `data/csp/mp20_ps_test.pt`

The model may train only on the train split. During sampling, it may condition
on validation composition only through `atomic_numbers`.

## Metric

`evaluate.py` computes METRe match rate against the full validation split using
fixed pymatgen `StructureMatcher` tolerances. Higher is better.

## Candidate artifacts

Generated candidates write validation CIFs to:

```
runs/<run_name>/val_samples/{idx:05d}.cif
```

The candidate must print:

```
primary_metric: <float>
```

It may also print task-specific diagnostics such as `val_metre:` for backward
readability, but the generic harness parses only `primary_metric:`.
