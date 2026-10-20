# Extension to cutoffs beyond 44 on the symmetry cluster

This extends the supplied S10 package (`lri_1d_full_coefficient_cutoff_flow.zip`, baseline commit = the zip as
received) so the complete Dconn coefficients C0..C8 can be computed at even cutoffs L > 44 on symmetry `defq`.
**The numerics are unchanged:** the modified `code/ragged_quotient.py` gives bitwise identical C, r, g, energies and
vacuum-grid coefficients to the baseline (checked at L = 8, 16, 20) and reproduces the archived records to <= 1e-12.

## Changes
- `code/ragged_quotient.py`:
  - `--max-states` (default 2300000, the original guard). The guard is raised only explicitly, per planned run.
  - Each output `<scheme>_L<L>_d<deg>.json` is claimed with an O_EXCL lock file `<output>.lock` (works across nodes on
    BeeGFS, where flock is node-local). A held lock makes the run exit 73. The lock is removed on every exit the
    process survives; after a hard kill (OOM, time limit) check that no job is running before removing it by hand.
  - Unique temporary names `<output>.tmp.<host>.<pid>`, fsync, atomic rename.
  - A `provenance` block in each output: host, Slurm job/array ids, Python/NumPy/SciPy versions, platform, long-double
    mantissa bits, sha256 of the solver file, max_states.
- `code/compare_archive.py`: compares new records with the archived ones of the same name (C, r, g, energies,
  vacuum-grid coefficients within rtol 1e-10 relative to max(1,|old|); basis, edge and storage counts exactly).
- `slurm/`: `symmetry_env.sh` (anaconda3/2023.07-2, stack check, single-threaded BLAS), `validate.slurm`,
  `production.slurm` (one cutoff per array task, one process per exclusive defq node), `submit.sh`.

## Deployment: an immutable snapshot
Jobs must run the exact solver that was validated. Deploy each commit as a read-only, content-addressed snapshot and
submit from it; submit.sh refuses a writable tree, exports the solver sha256, and every job re-verifies it on the node.
```bash
C=$(git rev-parse --short=12 HEAD)
git archive --format=tar HEAD | ssh symmetry "mkdir -p ~/lri_s10/code/$C && tar -x -C ~/lri_s10/code/$C && chmod -R a-w ~/lri_s10/code/$C"
ssh symmetry "cd ~/lri_s10/code/$C && python3 tests/verify_manifest.py"
```

## Procedure (login node, from the snapshot)
```bash
slurm/submit.sh validate                          # Dconn L=40,42,44 and raw L=44 vs archive
# wait until it finishes and its log ends with PASS; production refuses otherwise: code/check_validation.py
# recomputes the four comparisons (rtol 1e-10, exact counts) against the archived records pinned by sha256, and
# requires this snapshot's solver sha256 and the same Python/NumPy/SciPy
slurm/submit.sh production 46,48,50,52,54,56,58,60 # stage A
# inspect maxrss/seconds of stage A, then (only if the projected peak RSS stays below ~160 GiB):
slurm/submit.sh production 62,64,66,68,70,72
```
Outputs: `<SCRATCH>/lri_s10/{validation/<job>,production}/`, logs in `<SCRATCH>/lri_s10/logs/`.

## Resource expectations (extrapolated from the archived L<=44 timings; to be measured in stage A)
L=44: 2.0 M states, 144 s, 2.4 GiB. Roughly x1.4 states, x1.6 time per +2 in L: L=60 ~23 M states, ~1 h, ~27 GiB;
L=72 ~109 M states, ~11 h, ~130 GiB. L >= 74 is not expected to fit a 180G defq node with this implementation.
