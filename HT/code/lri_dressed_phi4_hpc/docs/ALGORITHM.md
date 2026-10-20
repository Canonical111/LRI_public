# Exact factorization of the supplied dressed-phi4 solver

## Scope

The input is `product_reference/dressed_zero.py` plus `fast_response.py` from
`lri_extended_comparison_study.zip`. This release optimizes that direct,
finite-Delta_sigma calculation. It does not optimize the spin-boson NRG solver,
calculate new perturbative coefficients, or supply missing high-state matching.

The numerical prescription is unchanged:

- All positive-mode partitions with N <= bath_cut, no particle cap.
- Fixed spatial reflection parity (even for primary tuning).
- `nz` interacting zero-mode eigenstates in EACH local parity.
- `osc` auxiliary oscillator functions, with quadrature powers formed before
  auxiliary projection, the same adaptive scale, and the same normal ordering.
- Two primary-gap tuning conditions, not a thermal target.

## Hamiltonian and packed layout

Put d = Delta_sigma. With q=a0+a0^dagger and p=(a0-a0^dagger)/i,

    H_z = d p^2/4 + A q^2 + g q^4/12,  A=d/4+r-g/2.

Let W_j be the normal-ordered, sphere-averaged bath vertex and L_j its local
multiplier:

    L1 = (2A-d/2) q + (g/3) q^3
    L2 = (A-d/4) I + (g/2) q^2
    L3 = (g/3) q
    L4 = (g/12) I.

After local projection, H = diag(w)+H_b+sum_j L_j tensor W_j, with all the source's
common scalar removals retained. Each bath state i has particle parity b_i. In a
fixed total field parity f, its allowed local parity is p_i=f XOR b_i. Store one
vector as X[i,a], a=0,...,nz-1. This includes exactly the original sector states,
only in a bath-major ordering. It does not discard a symmetry-allowed state.

## Backend 1: factorized bath vertices

Store W1,...,W4 only in bath space, never a full Kronecker matrix. For each bath
row i, form

    S_j[i,b] = sum_beta W_j[i,beta] X[beta,b].

The local parity of its input is p_i XOR (j mod 2), so

    (HX)[i,a] = (w[p_i,a]+H_b[i]) X[i,a]
             + sum_j,b L_j[p_i,a; p_i XOR j,b] S_j[i,b].

The quartic bath term has local identity multiplier and needs no dense local
mix. A compiled row-owned loop fuses sparse gathers and local contractions.
Different threads write different output bath rows, with no atomics or races.
Every row has a deterministic accumulation order. There is no fastmath.

For bath dimension B and local count z, work is approximately

    O(z sum_j nnz(W_j) + B z^2)

instead of multiplying a matrix with approximately O(z^2 nnz(W_j)) entries.
There is no nbody-dimension-squared allocation. Bath W_j can still become large;
that is the purpose of the second backend.

## Backend 2: shared normal-ordered ladder powers

Store only B=sum_{n>=1}u_n a_n and C=B^dagger on the FULL bath partition space,
including both reflection parities. Start with X embedded as zero outside the
requested reflection sector. Form B^a X for a=0,...,4 using four sweeps, then

    W_j X = B^j X + C(j B^(j-1)X + C(... + C X)).

The binomial coefficients are those of the normally ordered polynomial, not
commutator substitutions. The four W_j require ten creation sweeps in addition
to the shared four annihilation sweeps. Only THEN project reflection parity and
perform the three dense local contractions (L4 is a scalar identity).

An eight-sweep combined-Horner variant was also tested. It needs more repeated
local matrix multiplications across the full bath, and was slower in the measured
local dimensions. The released 14-sweep form targets measured runtime rather than
minimizing sweep count alone.

The same cutoff B,C operators are used as in the original normal-ordered
polynomials. No infinite-dimensional oscillator commutator is used to simplify
products across a finite-cutoff boundary. Reflection projection between ladders
would change the answer and is NOT done.

Storage is O(E+B z ncv+osc^2) up to fixed scratch factors, where E is the ladder
edge count. Work per action is O(E z+B z^2), with fixed factors for four powers.
The bath dimension B itself still grows with integer partitions; this release
does not eliminate Hilbert-space growth.

Small standalone sparse/local kernels use serial compiled loops below an
explicit two-million multiply-add work heuristic, avoiding repeated OpenMP team
launches. Large kernels parallelize disjoint rows. The tensor fused Hamiltonian
kernel remains parallel. This is an execution heuristic, not an amplitude cutoff
or a physical truncation. Re-measure the thread crossover on the target node.

## Exact rank construction

C(R,k) counts partitions of total weight <= R with every part >= k:

    C(R,k)=C(R,k+1)+C(R-k,k),  C(R,N+1)=1.

Counts are checked as Python integers before conversion to int64. An exact DFS
rank/unrank matches the source enumeration. Each creation row is constructed
independently; no Python dictionary of all partition tuples is necessary.

For prefix remainder R and next part n, the DFS rank increment is

    1+C(R,start)-C(R,n).

The all-state ladder edge count is exactly sum_{r=0}^{N-1} C(r,1): deleting one
copy of a specified occupied mode is a bijection. Stored mode metadata remain
immutable when weighted CSR matrices are sorted (covered by a regression test).

## Moving-subspace response without repeated large actions

The source finite-differences projected Hamiltonian expectations at theta +/- h,
including the parameter dependence of the local eigenvectors. We preserve that
response, including phase alignment and the adaptive auxiliary scale.

For each of the three reference eigenvectors, calculate once:

    rho_a = sum_i |psi[a,i]|^2
    K_j[a,c] = sum_i,beta psi[a,i] W_j[i,beta] psi[c,beta]
    E_bath = <psi|H_b|psi>.

At a nearby theta, after aligning local eigenvector phases to the reference,

    <H(theta)> = sum_a rho_a w_a(theta) + E_bath
              + sum_j,a,c K_j[a,c] L_j[a,c](theta).

Thus each finite-difference column requires only small local diagonalizations
and contractions, not another global Hamiltonian application for each perturbed
parameter. This is NOT fixed-basis Hellmann-Feynman: the local projected matrices
are recomputed at the perturbed couplings as in the original source.

## Eigensolver, roots, and numerical changes

The defaults preserve the reference:

- float64 throughout the physical computation;
- dense eigh for sector dimension <=650;
- otherwise symmetric eigsh, lowest algebraic eigenvalues, tol=3e-11;
- scalar shift 1.23456789 and ncv>=max(28,4*k+4);
- safeguarded Newton, two-column response differences of relative step 1e-5;
- recompute five low levels after tuning and test the primary identification;
- absolute eigenvector residual gate 2e-7 and original tuning acceptance.

The user may explicitly request tighter tolerances, larger ncv, or different
physical caps. These are recorded and change the result fingerprint. No tolerance
is silently relaxed after convergence failure. The seed thermal dimension is
never read or used as an objective; only its coupling coordinates initialize
Newton iteration.

Floating-point products are regrouped, and the vector ordering and deterministic
initial Lanczos vector change. Agreement is therefore tolerance-based, not a
claim of bitwise equality with SciPy's original sparse Kronecker action.

## Parallel scope

Within a point, Numba parallelizes disjoint bath rows. BLAS remains single-threaded
by default to avoid nested oversubscription. Independent x/cutoff/refinement lanes
parallelize across nodes using Slurm arrays. ARPACK orthogonalization and the root
logic are not distributed. Single-point MPI is explicitly rejected, not silently
implemented by replicated allocations. A future distributed eigensolver must
partition these row actions and their halos; no untested MPI backend is advertised
as working in this release.
