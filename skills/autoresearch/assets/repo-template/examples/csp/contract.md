# CSP task contract

This task pack is the original HACO crystal structure prediction problem,
adapted to the generic `candidate.py` / `primary_metric:` harness.

## Data

Three split files are written by `prepare.py` into `data/csp/`:

| file | use |
|---|---|
| `mp20_ps_train.pt` | gradient updates |
| `mp20_ps_val.pt` | sample conditioning on `atomic_numbers` only; score via `evaluate.py` |
| `mp20_ps_test.pt` | held out; never access during autoresearch |

Each file is a `torch.load`-able `list[dict]` with:

| key | dtype | shape | note |
|---|---|---|---|
| `lattice` | `float32` | `[3, 3]` | basis matrix in Angstrom, rows = a, b, c |
| `frac_coords` | `float32` | `[N, 3]` | fractional coordinates in `[0, 1)` |
| `atomic_numbers` | `int64` | `[N]` | atomic number Z |

`N` is variable per record, empirically in `[1, 20]`. Batching must handle
variable `N`.

The split is polymorph-aware: polymorphs of one composition stay on the same
side. Validation therefore tests a genuinely multimodal distribution
`p(structure | composition)`.

All lattices in the three splits are Niggli-reduced, with cell angles in
`[60, 120]` up to floating-point tolerance.

## Scoring

`evaluate.py` uses pymatgen
`StructureMatcher(ltol=0.3, stol=0.5, angle_tol=10.0)` and scores against the
full validation split. The primary metric is METRe match rate. Higher is better.

## Candidate output

Candidates write 9060 validation CIFs, indexed by validation-record order:

```
runs/<run_name>/val_samples/{idx:05d}.cif
```

Canonical generated structures contain lattice `[3, 3]` in Angstrom,
`frac_coords` in `[0, 1)`, and integer atomic numbers.

At the end of execution, the candidate must print:

```
primary_metric: <float>
```

For human continuity with the original CSP campaign, candidates may also print:

```
val_metre: <float>
```

The generic harness parses only `primary_metric:`.

## Hard constraints

- Editable implementation file: `candidate.py` only.
- Training data: only `data/csp/mp20_ps_train.pt`.
- Validation data: only `data/csp/mp20_ps_val.pt`, and only after training has
  finished. The sampler may use only per-record `atomic_numbers`.
- Test data: never accessed during search.
- Evaluation: always use this task pack's `evaluate.py` on the full validation
  split.
- Single GPU only. The slot sets `CUDA_VISIBLE_DEVICES`; candidate code should
  use `cuda`.
- No package installation at runtime.
- No writes outside `runs/<run_name>/`.
- If the evaluation subprocess times out or fails, print `primary_metric: nan`
  and exit cleanly when possible.
