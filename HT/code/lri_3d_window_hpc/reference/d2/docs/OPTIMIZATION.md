# Exact numerical changes and scaling

## Unchanged physical specification

At fixed x=Delta_sigma, modes have e_(a,b)=x+a+b, J=a-b and squared field weights
(x)_a (x)_b/(a! b!). All positive-mode occupations with N<=L are retained. The
scalar sector is J=0 with even spatial reflection. The zero mode is dressed and
optionally represented in the previously defined density-selected local span.
The Gaussian normal ordering, coupling normalization, vacuum even-floor rule,
two primary calibration conditions, and original dense/ARPACK eigensolvers
remain. No thermal/descendant data set a physical parameter.

No physical amplitudes are dropped. Sparse zeros removed by exact support or
symmetry are not amplitude pruning. Every Hamiltonian array remains float64;
integer ranking is exact within explicitly checked integer ranges. Floating-point
summation order changes, so validation is by tolerance, not universal bit equality.

## 1. Ranked bath representation

The old recursive DFS stored a Python tuple for each occupation state and a
large tuple-to-index dictionary. The new implementation preserves its DFS order
exactly but stores parent, last-mode and degree arrays. Tuples are reconstructed
only on demand by the compatibility `states` sequence.

Let c(k,l) count suffix multisets using modes >=k with total level <=l. Then

    c(k,l) = c(k+1,l) + [l>=level(k)] c(k,l-level(k)).

The empty suffix is included. For an ordered occupied-mode path, rank is computed
one label at a time by adding

    1 + c(start,left) - c(next_mode,left).

A compiled preorder walk stores N, particle number P, J and the unique occupied
labels' annihilation edges. Removing each label and applying the same rank rule
constructs the sparse annihilator without a dictionary. Reflection ranks are
computed once and reused by the scalar projector.

DP storage is O(number_of_modes * L), and the graph/tree storage is O(B + edges)
for B bath states. Edge construction has short occupation-path costs, bounded
by O(B L^2). The exponential/combinatorial growth of B is unchanged. The new
representation does not remove states or weaken the original regulator.

## 2. Exact sparse Gram factors

Let S embed the chosen fixed-J/reflection bath sector into the full bath, and B
be the full positive-mode annihilator. Put A_j=B^j S and E_j=S^T B^j S. Normal
ordering gives

    W_k = sum_(j=0)^k binom(k,j) A_j^T A_(k-j).

Since A_0=S, we store F_j=E_j+E_j^T, j=1,...,4, and A_1,A_2,A_3:

    W1 X = F1 X
    W2 X = F2 X + 2 A1^T (A1 X)
    W3 X = F3 X + 3 A1^T (A2 X) + 3 A2^T (A1 X)
    W4 X = F4 X + 4 A1^T (A3 X) + 6 A2^T (A2 X) + 4 A3^T (A1 X).

Only rows occurring in at least one image are kept in the shared image space.
This compression is exact. Full B/C matrices used during construction are freed
after the gram factors are formed. A4 is needed transiently to form E4, not stored
as a full auxiliary image. All angular sectors between annihilations survive.

Per matvec, the three forward image actions are shared. The quartic many-body
matrix and the projected W4 are never formed. Compared with the old ladder
backend, repeated sweeps through full-bath work arrays disappear. Unlike a
high-state tail model, these are identities within the same retained Hilbert space.

Operator storage is O(sum nnz(A_j) + sum nnz(F_j) + graph), including transposes.
Work is O(z * sparse_nonzeros + B_sector * z^2) up to fixed small factors. Block
residual calculations scale additionally with the requested block width. Temporary
storage includes three auxiliary-by-local arrays; it is not zero, nor is the
small projected matrix alone the total memory cost.

For smaller spaces, materialized projected W_j can be faster. The tensor backend
therefore remains, with sparse matrix/multiple-vector contractions and a compiled
local contraction. Auto chooses tensor through L=12 and gram above; calibrate this
policy on the target architecture rather than assuming a universal optimum.

## 3. Window iteration: less repeated work, same equation

The scalar fixed point remains lambda_min(Hraw+D(s))-s=0, with derivative -p0.
The absolute acceptance ceiling stays 1e-11 and the working tolerance stays 1e-12.
Only the ground eigenpair is requested during the top scalar fixed-point iteration.
The requested excited roots are solved once after convergence; their ground root
must independently pass the same fixed-point gate. The final five-level and
orthogonality/residual checks are not omitted.

A cached vacuum table is reused only when w and all local vertex matrices are
**exactly equal**, at unchanged basis/x/cutoff. It is useful for the final expanded
spectrum and diagnostic calls. A changed matrix invalidates the cache; no lagged
coupling table or extrapolated window is accepted. The dense small-block bare
Hamiltonian is likewise reused only at exactly equal local matrices, with the
current bath shift added to its diagonal at every call.

The level-to-window map is evaluated once on the O(L) unique levels and indexed
by the bath N array, replacing a Python loop over every bath state per iteration.
The kept bath diagonal is cached and updated when the shift changes, not gathered
anew on every matvec.

## 4. Symmetry diagnostics

The new cross-sector translation construction visits only input-sector states,
uses exact ranks for the resulting occupations, and applies both reflection
projectors. It avoids a full-angular Python state dictionary and full-space
translation matrices. Tests compare it with the original full projected operator.
The diagnostic is still free-generator ancestry, with the same ambiguity flags;
it is not a new interacting generator or an improved physical spectrum.

## 5. Parallelism and limits

Large sparse contractions use Numba row-owned CSR kernels; independent output
rows have no atomics or races. Rectangular output dimensions are explicit (the
Gram factors are not square). Small contractions use SciPy sparse multiplication.
Local BLAS is one-threaded in the HPC driver to avoid nested oversubscription.
One-, two-, and four-thread measurements are local evidence, not a many-node or
64-core scaling claim. ARPACK orthogonalization and sparse setup remain important
serial/memory-bandwidth limits.

Across nodes, use independent Slurm array items (x, cutoff, local-size or seed
checks). Each item is one process with its own result/claim/checkpoint. Sub-cutoff
vacua have a sequential dependence; they are not naively dispatched concurrently
inside one fixed-point evaluation. The release is NOT a distributed-memory
single-eigenproblem implementation and does not include MPI or GPU kernels.

## References for implementation semantics

- SciPy `eigsh`: https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Numba threading: https://numba.readthedocs.io/en/stable/user/threading-layer.html
- Numba parallel loops: https://numba.readthedocs.io/en/stable/user/parallel.html
- Slurm job arrays: https://slurm.schedmd.com/job_array.html

These document library/scheduler behavior, not the new performance measurements.
