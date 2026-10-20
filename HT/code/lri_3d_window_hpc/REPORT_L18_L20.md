# L18/L20 numerical repair: measured evidence and deployment boundary

## Result

The specific SVD failure path in the supplied Expanse status report is repaired:
keep the inherited `null_space(...,rcond=5e-13)` call, retry only its `LinAlgError`
with LAPACK `gesvd`, and verify the complete kernel before accepting it. Both
ranked and legacy builders use the fix, including diagnostic spins 1 and 2.
The Hamiltonian, Gaussian normal ordering, total bath cutoff, self-consistent
window, local basis, float64 precision, ARPACK, and numerical gates are unchanged.

The repair passed a naturally failing full L16 projector locally and deliberately
forced fallback tests on the actual largest L18 spin-0, spin-1, and spin-2 species
blocks. The initial SVD failure in the latter tests is INJECTED; the matrices and
fallback calculations are real. The Expanse L18 failing block is not known because
the old probe did not record it. This release records that information next time.

This is NOT a claim that a complete L18/L20 Hamiltonian, eigensolve, or Expanse
receipt has passed. Full L18/L20 graphs exceed the safe scope of the local 4-GiB
memory allocation. L20 was checked by exact character counting and isolated
sparse-block construction, not a dense nullspace or full setup run.

## 1. Why this is the minimal fix, not an arbitrary basis change

A species block contains the complete tensor product of symmetric powers of
SU(2) irreducible representations. At M=J>=0, its raising map to M=J+1 has full row
rank. Hence its exact kernel dimension is sources minus targets. Its nonzero
singular values are square roots of j(j+1)-J(J+1), j>=J+1, and have an exact gap.

The largest scalar L18 block has singular values between sqrt(2) and sqrt(342),
not a large range suggesting physical rank ambiguity. The fixed-point conformal
spectrum plays no role in this algebraic identity. A LAPACK convergence failure
must not be treated as permission to omit angular states or loosen rcond.

The fallback computes a FULL right singular-vector matrix. It uses the same
relative rank rule, then checks dimension, finiteness, maximum absolute Jplus*Q,
and Q.T*Q-I against the inherited 1e-10 gates. Column ordering/sign conventions
are unchanged. Default-success blocks retain the original SVD exactly; retry
blocks can have another orthonormal gauge for the same null space.

If both drivers fail, an error contains cutoff, spin, inversion, species rank,
level, particle count, shape, and driver exceptions. Optional exact-matrix dumps
allow reproduction. No bad kernel is silently accepted. Rank/residual failures
also remain explicit errors, not triggers for an automatically weaker criterion.

## 2. Real failure reproduced, and the largest L18 blocks tested

### Complete L16 scalar projector

In this runtime, the unmodified source itself raises `SVD did not converge` at
L16, in a 1825-by-1864 block. The repaired full projector completes, with:

* full bath states: 8,778,392;
* scalar highest weights: 15,815;
* projector stored nonzeros: 4,291,885;
* two naturally required gesvd retries (1825-by-1864 and 303-by-307);
* maximum Jplus residual: 4.663e-15;
* maximum orthogonality defect: 1.777e-15.

The original and repaired graph hashes are equal. No bitwise equality of their
full L16 projectors can be claimed locally, because the original never returns
one. This does not contradict the report's successful Expanse L16 run: LAPACK
failures can depend on library/build/runtime and input history. The underlying
cause of the particular Expanse L18 failure is not diagnosed from this alone.

### Isolated largest L18 physical species blocks

Each first-driver failure below was deliberately injected. The retry is actual
float64 gesvd followed by independent sparse residual checks.

| Spin | Jplus shape (targets x sources) | Expected/returned nullity | max(abs(Jplus Q)) | max(abs(Q.T Q-I)) |
|---:|---|---:|---:|---:|
| 0 | 4524 x 4596 | 72 / 72 | 1.846e-15 | 8.882e-16 |
| 1 | 2802 x 2968 | 166 / 166 | 1.721e-15 | 1.777e-15 |
| 2 | 3987 x 4316 | 329 / 329 | 1.874e-15 | 2.221e-15 |

The scalar retry used about 132 seconds and 808 MiB peak process RSS locally.
These are isolated-block observations, not a full-projector or HPC timing model.
Final-source records have names `L18_*_final_retry.json`.

### L20: what was actually checked

The largest scalar species block is 10809 x 10967, with exact nullity 158.
Its sparse raising map has 59,507 nonzeros. Independent assembly gives the exact
character-predicted spectral moments:

    trace(Jplus Jplus.T) = 687410
    trace((Jplus Jplus.T)^2) = 79077604.

No L20 dense SVD, complete projector, vertices, or spectrum was run here. The dense
Jplus input alone would occupy 948,338,424 bytes; full singular-vector matrices,
input copies, LAPACK workspace and the Fock graph are additional. A sparse
construction/moment check does not establish the feasibility of that full stage.

## 3. Exact large-cutoff sizing replaces the report's estimated dimensions

The Fock generating product and independent symmetric-power character census agree.
The following counts are exact for the unchanged natural-inversion sectors.
Combined scalar dimension means BOTH field parities with 16 local states per parity.

| L | Full bath states | Annihilation edges | Scalar bath states | Combined scalar matrix dim | Resident graph arrays, GiB |
|---:|---:|---:|---:|---:|---:|
| 16 | 8,778,392 | 42,095,538 | 15,815 | 506,080 | 0.7452 |
| 18 | 40,968,710 | 213,091,592 | 55,859 | 1,787,488 | 3.6943 |
| 20 | 182,727,113 | 1,022,077,961 | 196,585 | 6,290,720 | 17.4109 |

**These are NOT peak RSS estimates.** Projectors, vertices, sparse products,
LAPACK workspace, Krylov vectors, temporary copies, and interpreter/library
storage are additional. The status report's L18/L20 full-memory and time budgets
remain unvalidated estimates, not measurements supplied by this patch.

Diagnostics are particularly important for memory planning. At L20, the spin-2
bath has 819,606 highest weights, giving 13,113,696 states PER field parity for
nz=16 (versus 3,145,360 for each scalar parity). A scalar job's memory budget is
not automatically adequate for `--diagnostics all`.

The census provides all spin block histograms and largest-block signatures, without
allocating the full graph. The setup probe additionally records actual sparse
nonzero counts and index widths when those stages are executed. The supplied
L20 vertex-nnz estimates remain estimates; they are not inferred from graph edges.

## 4. Memory changes with unchanged numerical content

* COO assembly now accumulates numerical row/column/value chunks, not millions of
  Python scalar objects. Concatenation preserves their exact order and values.
  Chunks and final CSR storage still coexist transiently; this is not zero-copy.
* Exact full graph-array cost is checked before allocating graph work arrays.
  A budget rejection no longer waits until after the initial large arrays exist.
* Projector-cache hashing streams 4-MiB chunks instead of first making a bytes
  copy of the whole sparse object. The digest is identical to the old digest,
  including noncontiguous one-dimensional arrays.
* Tests exercise int64 sparse pointers in the compiled serial/parallel contraction
  kernels, and sparse indices beyond 2^31. They do not allocate a billion-entry
  Hamiltonian. Runtime setup records dtype/nnz so the real Expanse probe can check
  its actual SciPy/Numba sparse objects.

These changes do not make the dense per-block SVD asymptotically subcubic or the
many-body growth polynomial. L20 can still be expensive. A separate angular
coupling/sparse-nullspace redesign would require new validation if probes show
that the retained dense algorithm is impractical.

## 5. Numerical validation and identity

The local quick suite has 96 passing tests: 62 inherited and 34 new tests,
including manifest integrity. New numerical tests force the fallback; compare
projector subspaces and rotated vertex matrices; reject missing kernels, bad
residuals, nonfinite inputs and both-driver failures; and verify character counts,
array guards, sparse int64 support and streamed hashes.

A complete original-versus-patched L14 graph/projector comparison gives identical
hashes for every graph array and projector CSR array. The original-success call
is not globally replaced by gesvd. Fresh raw AND window L8 solves at both x=.6
and x=.5182 give bit-identical five-level gap arrays against the immediate
pre-fix source on this runtime.

Inherited validators also pass:

* `validate_physics.py`: independent covariance, SU(2), normal-ordering and C2;
* `validate_numerics.py`: larger backend/weak-limit controls;
* `validate_large.py`: ten action comparisons through L14 (max abs1.763e-12,
  relative1.914e-15), and retuned six-root angular checks at L8;
* `validate_benchmarks.py`: all83 historical records verified against preserved
  pre-fix source bytes, followed by mandatory fresh current-source regressions.

The historical timing measurements are NOT relabelled as current performance
measurements. The pinned reference has its own manifest digest, and new-source
checks must pass before the audit can pass. There is no stale-hash whitelist,
expected-failure receipt, skipped-test option, or replacement of physical tests
by a promise of agreement.

The numerical source identity changes. Old static caches, checkpoints, and
completed campaigns are not renamed as new-source artifacts. Existing scientific
outputs remain valid records of their old prescription; new campaigns need a
new reviewed release and Expanse receipt. This local suite is not that receipt.

## 6. Available source versus the site's release

The status report says the final site release e895443 changed only new Expanse
files, and the original 615-file baseline manifest still passed. That baseline
ZIP is available here. The later site source, receipts, full L8-L16 envelopes,
and precise Expanse failing matrix were not attached. The surgical patch leaves
`cluster/expanse/`, `EXPANSE.md` and site tests untouched.

Use the patch on a fresh site branch. It supplies a strict manifest rebuild
script for the intentionally changed source and verified additions. Rebuild the
site's separate release checksums and new receipt with its existing reviewed
tools. The full ZIP is a standalone reference/test distribution, not a combined
site release. A later upload of e895443 is needed to audit its combined contract.

## 7. Reproduction and next evidence needed

`FIX_L18_L20.md` gives commands for counting-only and actually allocated probes.
Run the new site validation and L8-L16 regression before L18 calibration. Then
probe the L18 scalar and diagnostic sectors separately, capturing each stage's
memory and retry/block metadata. Test static-cache publication on Lustre before
sharing it across lanes. Only afterward probe L20 and run one continued x=.6 point.

All local large-block tests were on a four-CPU-quota Linux runtime with a 4-GiB
memory limit; no scheduler or Lustre tests were performed. No full L18/L20
performance, SU budget, finite-x curve value, or continuum accuracy is claimed.
