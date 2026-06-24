# CSP smoke checklist

Run these probes inside the slot worktree before a full CSP candidate run.
Prefix Python calls with `CUDA_VISIBLE_DEVICES=$GPU`, run from `$WT`, and tee
diagnostics to `$WT/runs/staging-smoke/smoke.log`.

## Stages

1. Import candidate module within 1 second:
   ```
   CUDA_VISIBLE_DEVICES=$GPU $PY -c "import sys; sys.path.insert(0, '$WT'); import candidate"
   ```
2. Initialize the candidate's model with a tiny batch of 8-16 train records on
   CUDA. Run one forward, backward, and optimizer step. Assert finite loss,
   gradient norm below `1e4`, and peak VRAM safely below `vram_total_mb`.
3. Sample 16 validation compositions using only `atomic_numbers` from
   `data/csp/mp20_ps_val.pt`. Assert finite wrapped fractional coordinates,
   `|det(lattice)| > 0.1`, and minimum interatomic distance above 0.5 Angstrom.
4. Write one CIF through the candidate's normal artifact path and re-parse it
   with `pymatgen.io.cif.CifParser`.

If the candidate API is too tangled to probe, fail with:

```
verdict: fail
summary: candidate API not factored for probing
```
