# Local validation of optimized-basis integration 1.1.0rc1

## What was validated

This is an integration candidate based on the supplied production code at
`e2ca07c`. It keeps the consistent full-vacuum-window model and introduces only
an opt-in numerical local subspace. It has **not been submitted to symmetry**,
benchmarked on the compute nodes, or independently reviewed as a production
release. Local numerical validation and on-cluster lease/filesystem validation
are distinct requirements.

The new scalar-window path is not a fifth-order epsilon polynomial. The existing
finite-coupling fixed-point equations, their absolute acceptance ceiling, and the
two primary-gap conditions are unchanged. No additional physical counterterm,
energy rescaling, individual-mode UV regulator, or descendant calibration is
included.

## Six-stage local receipt

`validation/basis_integration/local_staged_receipt.json` records all six passing
stages, with subprocess outputs, source/release fingerprints and actual runtime:

1. **104 pytest cases**: 70 original cases and 34 added basis/integration cases.
2. Seven saved-seed regressions, maximum low-gap discrepancy approximately
   **2.92e-13**.
3. Seven independent raw-baseline comparisons against the pinned `e637dfd`
   numerical source: all checked numerical arrays agree **exactly** in this
   runtime.
4. Raw and consistent-window calibration smoke calculations through the real CLI.
5. Six independent comparisons against the pinned `e2ca07c` source, spanning
   raw, consistent and literal prescriptions: exact agreement of the selected
   coupling, spectrum, vacuum-energy and window arrays.
6. Real basis training, immutable reuse, two held-out-cutoff point solves at two
   retained sizes, point restart/reuse, and independent larger original-local
   references at weak and strong coupling.

The same 104 pytest cases were rerun successfully from a clean distribution copy.
The old lease-race tests emit six Python 3.13 `fork`-from-multithreaded-process
warnings in this runtime. They passed; the warning should not be suppressed or
misrepresented as proof of target-cluster process/filesystem behavior.

Nine underlying files are byte-identical to the uploaded production revision:
`solver.py`, `local.py`, `window.py`, `basis.py`, `operators.py`, `kernels.py`,
`lease.py`, `scripts/pack_node.py`, and `scripts/run_lane.py`. Their hashes are in
`validation/basis_integration/protected_files.json`. Conditional dispatch,
configuration binding, manifests, and diagnostics were changed separately.

## Fresh optimized-basis comparisons

All displayed local counts are **per parity**. Training uses the vacuum, spin,
shadow and lower-cutoff vacua. The thermal state is not a density target or an
outer-convergence target. After a basis is frozen, every changed-coupling vacuum
window is recalculated and both primary gaps are retuned.

The complete fresh comparison table is
`validation/basis_integration/numerical_comparisons.csv`; the underlying command
log and raw envelopes are supplied alongside it. Values measure agreement with a
specified larger finite reference, not the physical continuum.

| Delta_sigma | Training L -> test L | Original reference states/parity | Optimized states/parity | Absolute thermal-gap difference | Largest five-level difference |
|---:|:---:|---:|---:|---:|---:|
| 0.24 | 4 -> 6 | 16 | 10 | 6.395e-14 | 2.009e-10 |
| 0.24 | 4 -> 6 | 16 | 12 | 6.273e-14 | 4.796e-13 |
| 0.025 | 8 -> 10 | 32 | 16 | 3.280e-12 | 3.230e-09 |
| 0.025 | 8 -> 10 | 32 | 24 | 3.663e-11 | 3.142e-09 |
| 0.01 | 12 -> 12 | 48 | 16 | 1.076e-12 | 1.526e-11 |
| 0.01 | 12 -> 12 | 48 | 24 | 1.966e-12 | 7.368e-12 |
| 0.025 | 16 -> 20 | 48 | 16 | 4.282e-10 | 1.347e-07 |
| 0.025 | 16 -> 20 | 48 | 24 | 5.646e-10 | 2.133e-07 |

The larger L=20 reference is solved independently in the original moving-energy
basis. The L=16 training basis never sees an L=20 state. Local-basis agreement
must be distinguished from uncertainty in the 48-state reference itself and from
bath/UV matching errors. The tested same-regulator local convergence audit uses
explicit 1e-6 thermal and 1e-5 common-low-gap budgets; the numerical solver gates
are not relaxed to these looser post-processing comparison budgets.

Sixteen retained functions are **not** declared sufficient at every delta or
production cutoff. Train a larger artifact when needed, and compare nested
retained sizes and independently increased teacher/auxiliary resolutions.

## Workflow and safety checks

The added tests exercise invalid/corrupt artifacts, incorrect parity/isometry,
wrong delta/auxiliary size, stale source/runtime, an altered expected checksum,
unbound result payloads, publication/reuse, recovery at selection and Newton
boundaries, complete-checkpoint finalization without repeating eigensolves,
solver-owned claim exclusion, embedded-basis descendant reconstruction after the
external basis is removed, and pack item/result/completion binding. A legacy
lane request carrying a new basis option is rejected rather than silently
ignoring it.

A separate real local workflow used the successful receipt to run:

```
frozen training request -> training CLI -> immutable basis reuse -> basis index
-> pack manifest -> original pack launcher -> validated result -> second launcher
```

One target item was launched exactly once; the second launcher verified and
reused its completion. The launcher may still execute its original warmup. These
are actual local processes with the original ownership code, not Slurm or
cross-node tests. Frozen requests retain historical absolute paths in the audit
records; regenerate them for the target installation instead of executing those
saved paths.

All six eligible `.sh`/`.sbatch` files in the symmetry layer, including the new
training template, were syntax checked. This is not evidence of successful scheduler submission.

## Numerical details

The implementation keeps float64, original Gaussian normal ordering, the
inherited eigensolver residual gates, and the absolute 1e-11 window fixed-point
acceptance ceiling. No fastmath, mixed precision, amplitude pruning, stale-window
approximation or automatic reduction of caps/tolerances is used.

Each power of the primitive local coordinate is projected independently. The
fixed-span Jacobian contracts the full local density matrix and differentiates
the self-consistent window. Descendant diagnostics use the directly projected
primitive annihilator; the local-energy-commutator shortcut is invalid in a
non-invariant compressed span. Both properties have independent matrix and
finite-difference tests.

Timing entries document executions and are **not a repeated performance
benchmark**. No end-to-end speedup or memory-reduction factor is claimed from
these integration runs. Training has a separate cost and temporarily uses the
larger teacher representation.

## Development failures retained in the record

During development, deliberately small weak/strong local spaces failed the
independent low-spectrum gates. A weak four-state test and a strong twelve-state
test were not promoted to accepted operating points. The gate was not relaxed;
validation uses larger retained spaces. Failed reports are included under
`validation/basis_integration/development/`.

An initial matrix test used an absolute tolerance smaller than one float64 ULP
for a large entry; its assertion was made scale-aware. A shortcut-negative-test
fixture originally used an invariant eigenspace, where the shortcut is valid;
it was replaced by a genuinely non-invariant parity span. These changes affect
test fixtures/assertions, not numerical physics or solver acceptance.

Two early test invocations were invalid: one lacked the explicit source import
path in subprocesses, and a tool time limit sent a stop signal during a pytest
session. Clean, uninterrupted runs with the correct import path passed. No
interrupted run is counted as a passing receipt.

## Deployment boundary

Use a new reviewed commit/immutable installation. Old receipts are stale because
the source and release fingerprints have changed. Regenerate bases on the
validated target runtime; copied evidence artifacts are not a generic production
basis library. Begin with the overlap/convergence pilot in `INTEGRATION.md`,
calibrate complete point solves and training costs separately, then extend only
where the independent local and bath checks pass. Existing experimental physical
corrections remain outside this package.
