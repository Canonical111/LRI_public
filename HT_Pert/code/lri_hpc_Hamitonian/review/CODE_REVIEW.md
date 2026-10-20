# Code review of the lri_hpc_Hamitonian package (PLAN G1)

Scope:
- `lri_hpc/` (the solver), `reference/` (the original scripts), `analysis_original/*.py` (the fits from
  `lri_phi6_joint_C7_results.zip`), `slurm/` and `export_results.py`;
- the Expanse layer added here: `cluster/expanse/`.

Baseline: commit 67b009f, as received. The Hamiltonian, tuning conditions, particle caps, float64 arithmetic and
fit ansatz were **not** changed. Only acceptance gates, tests, deployment and audit code were added.

Findings are ranked by effect on finite-cutoff numbers or fits. "Fixed" means changed in this repository, with a
test. Review IDs (LRI-0xx) refer to the Codex plan-review log in `../lri_hpc_Hamitonian_loop/PLAN-REVIEW-LOG.md`.

## What was checked and found correct

- **Basis (`basis.py`).**
  - The suffix-count tables (G, Z) are counted with checked int64 overflow.
  - rank/unrank follows the depth-first nondecreasing-mode order of `reference/check_lri_hamiltonian.py`.
  - Zero-mode states |p⟩ have rank p, which `Space.sample` relies on.
  - `tests/test_ranking.py` compares dimension, P, N and both edge orientations exactly with the reference
    enumeration (`reference/compute_phi6.GapSpace`) at Λ = 2…24 and at Λ = 300 with P ≤ 6.
  - The round trips are exercised above 2^31 by `tests/test_int64.py`.
- **Edges.**
  - Creation and annihilation edges are built per row with occupation weights √occ and the square-root jets
    u_n(ε) of ((1−ε)/2)_n/n!. The same float64 recurrence is used as in the reference.
  - Indices are int32 up to 2^31 − 1 states and int64 above (`make_edges`).
  - `tests/test_operators.py` checks the ladder jets, both vertices and the quotient components against the
    reference to 2e-13…2e-10, at Λ = 4, 8, 12 and 24.
- **Vertices.** The Horner forms are M = C(C+2B)+B² and V = (C⁴+4C³B+6C²B²+4CB³+B⁴)/12.
  - Operators are never commuted.
  - The sphere-parity projection is applied only after each complete vertex, as in the reference.
  - Particle-parity pruning removes only rows that are identically zero.
- **Tuning and the quotient recursion.** These match the reference structure: E1−E0=(1−ε)/4, E3−E0=(3+ε)/4, and
  wavefunctions through ε³ give quotients through ε⁶ or ε⁷.
  - The built-in second-order shell check is an independent recomputation, and fails the job above 1e-10.
- **φ6 prescriptions.** The raw and vacuum-subtracted gaps are computed from the same wavefunctions as in
  `reference/compute_phi6.py`.
- **Regression against the saved tables** (Expanse, jobs 54519867, 54520113 and 54520360):
  - thermal d7 at Λ=40 and 50: at most 1.5e-9;
  - φ6 d5 at Λ=50: at most 2.0e-10 in D6;
  - φ6 d3 at Λ=128: at most 5.5e-12;
  - package tolerance: 1e-7 + 2e-11·|x|.
- **Fits (`analysis_original/`).**
  - The saved analysis is reproduced by rerunning `reproduce_saved_analysis.py`, to at most 6e-7 in C7.
  - An independent reimplementation from the REPORT equations (`analysis/audit_fits.py`) reproduces the A/B/C
    intercepts C4–C7 to 2e-11 relative, ω3 to 1e-9, ω4 and ω5 to 1e-8, and the held-out errors.
  - All 28 least-squares solves agree between float64 QR and 50-digit mpmath QR to 3.3e-7 relative. See
    `analysis/audit_fits.json`.

## Findings

### F1 (high; fixed): no acceptance gate on published or reused results
**Problem.** `solver.compute` published a result, and the CLI reused a completed output with `--resume`, without
checking:
- that the coefficients were finite and of the right length;
- that the tuning residual was small;
- that the shell residual was small.
The exporter accepted anything. A NaN or a mistuned run could therefore enter the fits silently.

**Fix.** `lri_hpc/validate.py::check_result` requires:
- finite coefficients of length degree+1;
- shell residual ≤ 1e-10;
- tuning residuals ≤ 1e-6 (thermal, or both φ6 prescriptions).
It is applied:
- before publishing and before checkpoint-result reuse (`solver.py`);
- before completed-output reuse (`__main__.py`);
- in `export_results.py`;
- in `cluster/expanse/run_lane.py` and `status.py`.
Test: `tests/test_validate.py`. Review ID LRI-001.

### F2 (medium; fixed): the full-recursion test computed residuals but did not assert them
**Problem.** `tests/test_full_recursion.py` compared the capped solver with an uncapped sixth-order recursion,
but a failure would still have exited 0.

**Fix.** It now asserts residuals ≤ 1e-8 for thermal and for both φ6 prescriptions. Review ID LRI-002.

### F3 (medium; partly fixed): the int64 index path was never exercised
**Problem.** Thermal Λ ≥ 112 (2,192,747,656 states and more) uses int64 edge indices, but no test reached that
path.

**Fix.** `tests/test_int64.py` builds a 110k-row shard of the Λ=112 basis through the row-range interface. It
checks:
- the int64 dtypes;
- rank/unrank round trips;
- the targets of the sampled rows' edges;
- that the ladder kernel is bitwise identical with int64 and int32 indices.

**Remaining.** A full-scale int64 run happens only in production (thermal 112–118, φ6 d5 148–160, d3 672–832),
where every output passes the F1 gates. Review ID LRI-005.

### F4 (medium; fixed for Expanse): the Slurm templates are not deployable as shipped
`slurm/array.slurm` and `slurm/distributed.slurm` have these problems:
- they set no account, modules or environment;
- they run `set -euo pipefail` before any environment activation (the Expanse site bashrc is not nounset-safe);
- they use a fixed `--memory-limit-gib 48`;
- they write results relative to the submission directory.
The MPI template is labelled experimental, and `tests/mpi_smoke.py` has never been run on a real MPI.

**Fix.** `cluster/expanse/` replaces them for Expanse:
- `env.sh` sets up modules, the venv and a node-local Numba cache;
- `validate.slurm` and `submit_validate.sh` run validation V with a gated summary;
- `campaign.py`, `submit_cutoffs.py`, `lane.slurm`, `run_lane.py` and `status.py` run production from a calibrated
  memory model, with lanes, locks, claims, accounting-backed status and bounded retries.
The MPI path is not used (single-node campaign, by user decision).

### F5 (medium; documented, not changed): the `--memory-limit-gib` screen is about twice the real footprint
The screen (`basis.py`) assumes 800 B/state plus 32 B/edge. The measured RSS on Expanse is:
- thermal d7: 398 B/state at Λ=70;
- φ6 d5: 327 B/state at Λ=70;
- φ6 d3: 230 B/state at Λ=200.
The screen would refuse thermal Λ ≥ 116 on a 2 TB node, although those runs fit. Production therefore omits the
flag; the Slurm memory cgroup is the hard limit. The screen is left as is because it is conservative by design.

### F6 (low; fixed): the thread count was not recorded
Results did not record the Numba thread count, so timings could not be attributed. `solver.py` now stores
`threads`.

Measured on an AMD EPYC 7742 node, thermal Λ=60: 16.3 s at 16 threads, 13.9 s at 32 and 19.2 s at 64 (V
54519867). A rerun gave 18.3, 18.8 and 16.5 s. Beyond about 16 threads the run is bandwidth-bound; production uses
at most 64 threads and claims no 128-thread scaling. Review ID LRI-010.

### F7 (low; not changed): tests write into the source tree
`tests/test_solver.py` writes `benchmarks/regression.json` inside the checkout, and running `tests/run_all.py` also
rewrites `benchmarks/full_recursion_validation.json` and `benchmarks/simulated_mpi_validation.json`. In a frozen Expanse checkout this
modifies the tree that the revision stamp describes. It is harmless for results, because the source fingerprint
covers only `lri_hpc/*.py`, but a test should write to a temporary directory.

### F8 (low; documented): the REPORT text differs from the code in places
The discrepancies between the REPORT text and the code or data are recorded in
`analysis/audit_fits.json:discrepancy_inventory`:
- REPORT §2 counts 26 fifth-order cutoffs "4..50, 54, 58"; the data have no 52 or 56.
- REPORT §6 does not state the reference thermal window; the code uses 16 ≤ Λ ≤ 50 with shift 0.
- The ω4 and ω5 fit uses basis A with Λ ≥ 16 on all fifth-order rows 4…58, with ω3 fixed.
None of these changes any quoted number.

## Reference scripts (`reference/`)
These are the original single-process scripts. They are correct at their intended sizes, and they are the
ground truth for the tests and regressions. Two limits:
- `check_lri_hamiltonian.py` stores ladder parents as int32 and builds a Python dict of states, so it cannot reach
  the production sizes. This is not a defect for its purpose.
- Its `--validate` full recursion is restricted to Λ ≤ 8, as documented.

## Not reviewed or out of scope
- Real-MPI behaviour (unused).
- The extrapolation's physics assumptions: those belong to the diagnosis (G3, `analysis/DIAGNOSIS.md`).
- `EFFECTIVE_HAMILTONIAN_PROPOSAL.md`: a proposal document, with no code.
