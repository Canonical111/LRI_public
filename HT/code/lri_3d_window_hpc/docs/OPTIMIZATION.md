# Exact optimizations of the three-dimensional dressed-window solver

## Scope and reference

The reference is the supplied `lri_3d_dressed_window_hpc.zip`; its latest numerical
code is preserved in `reference/baseline/code/`. This is not a comparison with an
older raw Hamiltonian. The optimization retains the spherical modes, total
positive-mode bath cutoff, Gaussian normal ordering, true SO(3) sectors, local
representation, scalar vacuum-window fixed point, primary tuning, and ordinary
dense/ARPACK solvers. No extra physical counterterm, tail fit, selected-tail
solver, mixed precision, fast-math or physical-amplitude cutoff is introduced.

## 1. Replace polar quadrature by the exact rotational trace

Let S_(J,M) embed a definite spin-J magnetic component with its multiplicity
columns in a common gauge, and let O_k(n)=:phi_b(n)^k:. The angular average is a
rotation scalar. Taking its trace over the magnetic indices gives, for any two
multiplicity labels alpha,beta,

    (W_k^J)_(alpha,beta)
       = 1/(2J+1) sum_(M=-J)^J
           <alpha,J,M|O_k(north)|beta,J,M>.

This follows by conjugating the insertion under rotations, tracing in the
spin-J representation, and using invariance of the trace. The bath cutoff
commutes with rotations, so the identity holds in the finite retained space.
For J=0 the integral is exactly one north-pole matrix element. For fixed J the
number of evaluations is 2J+1, independent of the bath cutoff, rather than the
paired L+1 Gauss-Legendre rule used by the reference.

At the north pole sqrt(4 pi)Y_lm=delta_(m,0)sqrt(2l+1), and hence

    B_north = sum_(n,l) u_(n,l) sqrt(2l+1) a_(n,l,0).

Only the field insertion contains m=0 oscillators. The external angular states
still include ALL magnetic occupation configurations; no nonzero-m spectator or
intermediate total-angular-momentum state is discarded. In particular, this is
not the invalid shortcut of projecting every ladder operation to total J=0.

The same normal-ordered particle-block products

    W_k = sum_j binom(k,j) (B^j S)^T (B^(k-j) S)

are evaluated for each required magnetic component. The implementation lowers
the original highest-weight columns consistently. The old polar construction
remains available by explicitly passing `nodes=L+1` to ProductOperator, and the
Gram backend remains an independent alternative. These provide independent
quadrature and magnetic-representation tests.

For low spin this removes both many quadrature evaluations and transitions
created by the nonzero spherical harmonics away from the pole. It is NOT a claim
that the trace is faster for arbitrarily large J. No quadrature approximation or
new integration tolerance is introduced.

## 2. Ranked species grouping for the SO(3) projector

The input already contained a ranked full Fock graph. The new improvement is in
the subsequent angular reduction: integer combinatorial species signatures and
J_+ destinations are formed in compiled loops, replacing per-state Python
Counters, list edits and rank calls. One Counter per species block is retained
solely to reproduce the original column sort order exactly.

The same species occupations are grouped, the same J_+ block matrices are used,
and the same nullspace tolerance (rcond=5e-13), sign gauge, orthogonality and
J_+ residual checks are retained. No near-zero physical matrix element is newly
pruned. The previous grouping implementation remains as highest_weight_legacy
for debugging, while tests use an independently preserved original module.

Hilbert-space growth is unchanged. This reduces overhead; it does not turn the
many-body problem into a polynomial-sized space.

## 3. Construct all lower-cutoff vacuum operators from the top bare vertices

A complete normal-ordered monomial annihilates before creating. Its intermediate
bath level never exceeds both endpoint levels. Therefore

    Pi_ell W_j^(L) Pi_ell = W_j^(ell),  ell <= L,

in the same homogeneous angular basis. Species block order and gauge do not
depend on higher bath shells. Lower-cutoff states are a contiguous column prefix
in the reference ordering; the code asserts that fact before slicing.

The top four bare matrices are constructed once. Every smaller vacuum problem
gets exact principal submatrices, independent mutable bath shifts, its own warm
vectors, and small level/parity metadata. It no longer builds another full Fock
graph, angular projector and polar quadrature. Sparse lower matrices are copied
rather than permitting in-place changes to alias the parent.

Only BARE vertices are reused. The lower vacuum energies at changed couplings
are still solved to the original self-consistent tolerances. This is not a
frozen-window or independent-subcutoff-tuning approximation. Tests compare
against individually rebuilt subcutoff operators and fixed-point tables.

## 4. Compute only required Newton roots; retain complete final validation

The two primary calibration equations use one even vacuum energy and the two
lowest odd scalar energies. The reference requested three roots in both sectors
at every trial. The optimized Newton loop requests (1 even,2 odd); its Jacobian
uses exactly those states and the same full local/window derivatives.

The accepted point STILL requests five roots per field parity and checks the
original tuning, eigenvector, orthogonality and vacuum fixed-point gates. Angular
diagnostics still request six roots. No final output or state-identification
check is removed. A smaller Ritz calculation can change roundoff, warm starts,
and the nonlinear iteration path, so comparisons use numerical tolerance and
retain branch/continuation caveats rather than promising universal bit equality.

The public `spectrum(theta,k=integer)` operation retains its symmetric root-count
meaning. A pair can be supplied to request unequal counts explicitly.

## 5. Local contraction and arithmetic

The tensor backend continues to store four sparse BxB bath vertices, not a full
(B*nz)^2 Hamiltonian. Work is O(nz sum_j nnz(W_j) + B*nz^2). For sufficiently large
threaded operations the local multiplier is repacked so that the inner output
index is contiguous. Separate partial sums preserve each channel's accumulation
order; row-owned parallelism has no shared floating-point reduction.

The tested one-thread path retains the reference serial local contraction, which
was faster than the proposed contiguous alternative. The old shared-ladder Gram
path is not made the default in 3D. Explicitly tested alternatives that were slower
are recorded in DEVELOPMENT.md rather than used to inflate the speedup.

ARPACK orthogonalization, matrix-vector bandwidth, sparse W4 fill, and the local
teacher can still dominate at larger sizes. The Krylov vectors still require
O(B*nz*ncv) memory on one node. There is no distributed-memory eigensolver.

## 6. Immutable optional disk cache

`--cache-dir` caches numerical Fock graphs, angular projectors and canonical bare
vertices. Graph/projector keys are independent of x; vertex keys include the exact
float hexadecimal x, cutoff, spin, construction rule and actual projector hash.
Local size and window prescription do not change bare bath vertices.

Keys also bind all construction-module contents and relevant runtime versions.
Arrays use `.npy`, are loaded read-only (optionally memory-mapped), and are verified
against content hashes, shapes and dtypes. Pickle/object arrays are forbidden.
A manifest is published by atomically renaming a complete private staging directory
on the same filesystem. Corrupt entries fail closed; they are not silently reused.
A competing projector writer reloads the published winner before constructing its
vertices, so different nullspace gauges cannot be paired with the wrong cache.

This is a performance cache, NOT a source of coupled-state approximations.
It never caches changed-coupling vacuum energies, eigenvectors or fitted couplings.
First creation costs time and disk space; cache-read hashing costs time too.
The memory/time effect depends on the filesystem. Local atomic publication tests
are not a guarantee for a particular shared parallel filesystem. Build caches once
per validated installation when possible, then permit concurrent read-only jobs.

## 7. Scope of validation

See PERFORMANCE.md for actual measured values. Independent tests cover polar vs
trace vertices, magnetic sectors, exact subcutoff restrictions, parity, window
responses, root counts, cache races/corruption, and direct full spectra. Correctness
is agreement for the declared finite numerical problems; it is not a proof of
continuum conformal symmetry or branch uniqueness. All cutoff/precision and physical
interpretation caveats of `reference/baseline/docs/METHOD.md` remain in force.
