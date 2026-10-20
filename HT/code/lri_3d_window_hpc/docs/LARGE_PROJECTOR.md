# Large-cutoff angular projectors: algebra, memory, and failure policy

## Why the kernel dimension is known before any SVD

For a fixed collection of bosonic species (n,l), with occupancy q_(n,l), the
magnetic-space character is

    chi(z) = product_(n,l) [t^q_(n,l)] product_(m=-l)^l (1-t z^m)^(-1).

Let c_M be its coefficient at magnetic quantum number M. Each integral spin-j
representation contributes one vector to each M=-j,...,j. Therefore at J>=0,

    multiplicity(spin J) = c_J - c_(J+1),
    rank(Jplus : M=J -> M=J+1) = c_(J+1).

The whole species block is present in the total-level regulator: rotations change
m but preserve n,l, occupancies, N and spatial inversion. Thus the SVD block must
have full row rank and exactly `sources-targets` null vectors. An empty return
value is NOT a safe response to a numerical exception.

On a spin-j component, the nonzero eigenvalue of Jminus Jplus at M=J is

    j(j+1)-J(J+1),  j >= J+1.

Its smallest possible positive value is 2(J+1). Since j <= N <= L, the condition
number of the nonzero singular spectrum is at most

    sqrt((L(L+1)-J(J+1))/(2(J+1))).

This is a statement about the exact complete representation, not a diagnosis of
any malformed numerical input. It motivates checking dimension, finiteness,
nullity, residual and orthogonality independently. It does not justify weakening
`rcond` or filtering tiny physical coefficients.

The source call `null_space(...,rcond=5e-13)` remains first. The retry uses
`scipy.linalg.svd(...,full_matrices=True,lapack_driver='gesvd')`, counts singular
values above the SAME threshold, and takes the remaining right singular vectors.
SciPy documents `gesdd` and `gesvd` as alternative SVD drivers. Using `svd` directly
also works on older SciPy versions whose `null_space` did not expose that keyword.
The tested runtime is recorded in the result files; no SciPy downgrade is required.

## Exact graph accounting

With g_k=(k+1)(k+2)/2 oscillators at positive level k,

    D(L) = sum_(r=0)^L [t^r] product_(k>=1) (1-t^k)^(-g_k).

The number of stored unique-mode annihilation edges is exactly

    E(L) = sum_(k=1)^L g_k D(L-k).

For a particular mode of level k, removing one particle bijects states containing
that mode with all states up to level L-k. This counts edges, not particle number:
one state with occupancy q>0 in that mode contributes ONE edge with sqrt(q).

The preflight's byte count sums the dtypes and lengths of N,P,M,tree,last,ptr,
parents,modes,sqocc,counts and mode_levels. It is checked against actual arrays
at small cutoffs. It does not include auxiliary Python dictionaries, angular
projectors, vertices, SVD workspaces, or eigensolver vectors.

Counts and rank tables use integer arithmetic. Graph row indices use int32 only
when the row dimension fits it; edge pointers are int64. The SciPy/Numba tests
exercise int64 CSR pointers/indices and a sparse shape above 2^31 without creating
a huge dense vector. This is a dtype-path test, not a billions-of-nnz allocation.
The on-node probe records actual projector/vertex index widths and nnz.

## Removing avoidable large-cutoff memory peaks

The former projector builder appended one NumPy/Python scalar object at a time
into three Python lists (row,column,value). The repaired builder retains numeric
COO chunks and concatenates them in exactly the same order. It changes neither
null vectors nor the projected matrix. A dense-per-block upper count is

    sum_blocks c_J (c_J-c_(J+1)).

The preflight reports 24 times this count as a bound on *one* int64/int64/float64
COO payload, not as total memory. Concatenation, CSR conversion, the full graph,
and SVD buffers coexist. Sparse zeros are handled exactly as before; no threshold
pruning is introduced.

Projector hashing also streams contiguous array buffers in 4-MiB pieces. The
previous `.tobytes()` created a second full copy. A strided array is copied only
one bounded chunk at a time, preserving the original C-order digest.

## What the census does not solve

The maximum L20 scalar block is 10809 by 10967. This is now an exact count, not a
full tested dense SVD. Dense SVD remains cubic in block width and quadratic in
storage. The fix does not introduce a sparse nullspace algorithm or recoupled
basis. If L20 setup remains too expensive, the block-size and per-block timing
records now supply the evidence needed to choose that separate algorithmic change.
The complete scalar Hamiltonian still has all of its original physical cutoff
and matching uncertainties. This patch concerns numerical construction only.
