# Numerical equivalence and precision

This document explains why the optimized solver computes the same finite
Hamiltonian-truncation coefficients as the supplied reference, and which
numerical properties were checked. The derivations concern the fixed bath
cutoff, local oscillator ceiling, symmetry sector, and scalar vacuum-window
prescription. They do not establish a continuum extrapolation or additional
connected effective-Hamiltonian matching.

The executable reference is [`reference/perturbative.py`](../reference/perturbative.py).
The optimized implementation is [`code/optimized_solver.py`](../code/optimized_solver.py),
with optional [`code/native_backend.py`](../code/native_backend.py) and
[`code/mpi_backend.py`](../code/mpi_backend.py).

## 1. The finite problem is unchanged

Write the Taylor Hamiltonian and one nondegenerate seed's eigenpair as

\[
H(\epsilon)=H_0+\sum_{n\geq1}H_n\epsilon^n,\qquad
E(\epsilon)=E_0+\sum_{n\geq1}E_n\epsilon^n,\qquad
|\psi(\epsilon)\rangle=\sum_{n\geq0}|\psi_n\rangle\epsilon^n.
\]

The intermediate normalization is
\(\langle\psi_0|\psi_n\rangle=\delta_{n0}\). The reference uses

\[
E_n=\sum_{k=1}^{n}\langle\psi_0|H_k|\psi_{n-k}\rangle,
\qquad
|\psi_n\rangle=
\frac{Q}{E_0-H_0}\sum_{k=1}^{n}(H_k-E_k)|\psi_{n-k}\rangle,
\]

where \(Q=1-|\psi_0\rangle\langle\psi_0|\). The implementation omits the
currently unknown mass and quartic couplings from the provisional energy,
then solves those two linear tuning equations exactly as in the reference.

The bath-level regulator remains \(N_b\leq L\), with the same scalar,
inversion-even basis and the same field-parity organization. The default local
occupation ceiling at requested order \(K\) is still required to cover
\(3+4\lfloor K/2\rfloor\). The optimization does not remove states, lower the
cutoff, change Gaussian normal ordering, replace the scalar window, or fit in
finite \(\epsilon\).

## 2. Seed rows and columns replace discarded vector work

The provisional energy requires one scalar matrix element, not the entire
vector \(H_k\psi_j\). The optimized `seed_row` method contracts the bath CSR
row belonging to the vacuum, with the same local oscillator block:

\[
\langle p|H_k|X\rangle
=\sum_{a,z}(H_k)_{p;(a,z)}X_{a,z}.
\]

This is an algebraic rearrangement of selecting the seed component after a
full Hamiltonian application. Sorted CSR indices allow a subcutoff to use the
initial segment of this row without constructing a new sparse matrix.

Likewise, `seed_column` obtains \(H_k|p\rangle\) from the Hermitian seed row.
The input bath vertices are real and explicitly symmetrized. Their
\((a,0)\) and \((0,a)\) elements agree, and the matching local oscillator
block is transposed in the corresponding way. Bath field parity fixes the
output local parity. Each combined CSR matrix is canonicalized so duplicate
entries are added before the indexed column construction.

These substitutions require the real Hermitian vertices produced by this
package. An arbitrary nonsymmetric sparse input is outside this solver's
contract. They can change floating-point summation order, so numerical
equivalence is assessed with scaled errors rather than assuming every
coefficient must have identical storage bytes.

## 3. Why half as many wavefunction orders suffice

The optional `stationary` strategy uses the stationary Rayleigh quotient.
For requested energy order \(K\), set

\[
m=\lfloor K/2\rfloor,\qquad
|\phi\rangle=\sum_{i=0}^{m}|\psi_i\rangle\epsilon^i.
\]

These wavefunction coefficients are computed by the same recurrence as above.
The difference from the exact formal eigenvector is
\(|\delta\rangle=|\psi\rangle-|\phi\rangle=O(\epsilon^{m+1})\).
Hermiticity and \((H-E)|\psi\rangle=0\) give

\[
\frac{\langle\phi|H|\phi\rangle}{\langle\phi|\phi\rangle}-E
=\frac{\langle\delta|(H-E)|\delta\rangle}
       {\langle\phi|\phi\rangle}
=O(\epsilon^{2m+2}).
\]

The denominator has constant coefficient one, so its formal inverse exists.
Consequently the Rayleigh quotient gives every energy coefficient through
order \(2m+1\), including the requested \(K\). This is an exact statement about
formal series of the finite Hermitian Hamiltonian, not a numerical
approximation that discards higher-order energy terms.

At \(K=8\), wavefunctions through \(m=4\) suffice; the energy error begins at
\(\epsilon^{10}\). The implementation nevertheless computes and reports only
the requested energy orders. At odd \(K\), the same rule gives energy
coefficients through \(K=2m+1\), with the first possible error at \(K+1\).

### Implemented coefficient formula

Define the truncated-wavefunction polynomials

\[
S(\epsilon)=\langle\phi|\phi\rangle,\qquad
Q(\epsilon)=\langle\phi|(H-E_0)|\phi\rangle.
\]

With \(S_0=1\), division of \(Q\) by \(S\) gives

\[
E_n=Q_n-\sum_{k=1}^{n-1}E_k S_{n-k}.
\]

The code accumulates each unordered pair of wavefunction orders once.
Diagonal pairs have factor one; off-diagonal pairs have factor two because
the Hamiltonian and vectors are real and Hermitian. Pairs involving
\(\psi_0\) use the seed-row contraction. Pairs with both orders positive use
a full sparse application followed by the necessary inner products.

When evaluating the provisional \(E_n\), the current local mass/quartic
diagonal is still handled by the unchanged tuning equations. The
Gaussian-normal-ordered bath vertices have zero vacuum diagonal. Thus no
uncomputed bath contribution to \(\langle\psi_0|H_n|\psi_0\rangle\) is lost.
Only seed rows of \(H_{K-1}\) can contribute at the final requested energy
order, so that last Hamiltonian need not be built as a full matrix.

Combined Hamiltonians are released after their final stationary contribution.
The original recurrence remains selectable for comparison. The recorded seed
recursion residual for a stationary run covers the wavefunction orders
actually constructed, namely through \(m\); it is not a claim to have
constructed or checked the omitted higher wavefunction coefficients.

## 4. The self-consistent window stays complete through the requested order

For the retained inversion-even bath levels, the specified window is

\[
D_\ell(N;\epsilon)
=E_{\mathrm{vac},\ell}(\epsilon)
 -E_{\mathrm{vac},\ell-N}(\epsilon),\qquad D_\ell(0;\epsilon)=0.
\]

Every lower vacuum uses the same mass and quartic coupling series as the top
cutoff. The lower vacua are not separately retuned. Their energies are those
of their own corrected Hamiltonians, making the window self-consistent.

For every Taylor coefficient \(D_{\ell,n}\),

\[
D_{\ell,n}|\psi_0\rangle=0,
\qquad
\langle\psi_0|D_{\ell,n}=0,
\]

because every primary seed has the bath vacuum. Therefore its first possible
energy contribution contains nonzero-order wavefunctions on both sides and
appears at order \(n+2\). In particular, computing \(E_n\) only requires
previously known window coefficients through \(D_{n-2}\).

This establishes the needed order-by-order dependency:

1. Determine all provisional root and subcutoff vacuum energies at order
   \(n\), using already known lower-order Hamiltonian/window coefficients.
2. Solve the common top-cutoff mass and quartic tuning equations at that order.
3. Set the corrected root and vacuum energies \(E_n\).
4. Construct every \(D_{\ell,n}\) from those vacuum energies.
5. Include that operator in every subsequent wavefunction or stationary
   numerator contribution that can affect a requested energy coefficient.

There is no additional same-order nonlinear eigenvalue problem hidden in
this procedure. The stationary identity is applied to the final formal
Hamiltonian series. Its proof does not require the coefficients of that
series to have been independent of the vacuum energies during their
construction.

Here the window begins at \(\epsilon^2\); its first primary-energy effects
are at \(\epsilon^4\). At \(K=8\), the code still constructs and retains
the scalar window coefficients through order eight and includes all their
contributions to the energies through order eight. The last window
coefficients first affect energies beyond order eight. A shorter
wavefunction series therefore does not remove the \(\epsilon^5\) window
correction or higher repeated-window contributions.

This statement concerns the supplied self-consistent scalar full-vacuum
window. It does not add connected, off-diagonal local, or energy-dependent
matching terms absent from that specified finite model.

## 5. Working precision and the native ABI

The default arithmetic remains `numpy.longdouble`. On the validation host it
has a 16-byte storage slot, a 64-bit binary significand, and maximum exponent
16384. NumPy prints this dtype as `float128` on that host, but it is the x87
extended format stored in 16 bytes, not IEEE binary128 with a 113-bit
significand. Increasing the cutoff and increasing arithmetic precision are
separate operations.

The native library checks its C++ `sizeof(long double)`, `LDBL_MANT_DIG`,
`LDBL_MAX_EXP`, byte order, and floating radix against NumPy before use. It
also checks the binary64 size and significand. An incompatible native ABI is
rejected. `auto` then falls back to the same-precision SciPy implementation;
an explicitly requested `native` backend fails with a clear diagnostic.

The compiler defaults include `-fno-fast-math` and `-ffp-contract=off`, and do
not request architecture-specific instruction selection. Source content,
compiler identity, flags, platform, and precision fingerprint identify the
local compilation cache. The library is published atomically after its ABI
has been checked. Build flags and ABI observations are saved in result
metadata.

Each OpenMP worker owns complete output rows. Within a row, nonzero entries
are accumulated in their CSR order for every dense right-hand side. Changing
the thread count does not change that summation order. A sorted row can stop
at the subcutoff column boundary; an unsorted row scans and skips excluded
columns. Neither operation changes the retained sum. No global process
thread count is changed by a sparse call.

For very small products, the backend can use one thread even when more were
requested. Its conservative work estimate is the number of stored nonzeros
in the requested row prefix, including columns beyond the subcutoff, times
the number of dense right-hand sides. The default threshold is 10,000 in
these work units. It can be configured with `serial_work_threshold` or
`HT3D_SERIAL_WORK_THRESHOLD`; zero disables the policy. Counting this upper
bound is constant-time and does not allocate a sparse slice. Requested and
effective thread-call histograms are recorded in result metadata. The policy
changes only row scheduling, never summation order, dtype, or retained entries.

The SO(3) projector construction retains the original floating-point
precision: the supplied projectors are generated in binary64 and then
promoted for the higher-precision vertex/coefficient operations. This
optimization does not turn those input projector entries into newly
computed extended-precision values. Their existing rounding error remains
part of the calculation.

Likewise, the explicitly selectable `float64` mode remains available for
diagnostics. It is not silently substituted for `longdouble` by the native
backend, the cache, or MPI.

### Local oscillator bands

The local normal-ordered powers through \({:}\phi^4{:}\), after the unchanged
parity organization, have at most five diagonals. The same bound holds for
the local mass/quartic combination at each Taylor order. The default
`local_mode='banded'` uses those exact diagonals through
`make_local_bands(block)` and
`apply_local_block(X, block, bands, mode='banded')` in
[`optimized_solver.py`](../code/optimized_solver.py). An entire diagonal is
omitted only when all its coefficients are exactly zero. No magnitude
threshold or modification of an oscillator matrix element is involved.

`LocalBands` caches the original-dtype weights and the required boundary
padding. A general application allocates a two-dimensional padded copy of
\(X\), takes a read-only sliding-window view, and contracts that view with
the weights using `einsum` with the working dtype and `casting='no'`.
The view does not materialize an \(n_b\times n_z\times b\) temporary.
With band width \(b\leq5\), arithmetic scales as \(O(n_b n_z b)\) instead
of \(O(n_b n_z^2)\) for a dense local product. The padded input and output
use \(O(n_b(n_z+b))\) storage, and cached weights use \(O(n_z b)\).
Band coordinates are ordered by increasing input column for every output
column. Numerical equivalence is checked at the retained dtype.

The general band contraction is used for long-double input batches with
at least 128 rows. This threshold applies to the actual local batch, which
can be smaller than the full bath after parity selection or MPI row
partitioning. Float64 and smaller batches use dense multiplication because
their measured setup and BLAS costs favor that path. In banded mode, exact
identity and diagonal blocks use direct identity/elementwise paths before
this dispatch decision. An identity application may return its input array
itself; callers must treat the result as read-only and avoid mutating that
alias. Inputs are never modified by these helpers.

Bath terms whose local power is \(q_0=I\) are added directly to the complete
Hamiltonian image, avoiding parity gathers and identity matrix products.
This exact identity addition is retained in both local modes. The option
`--local-mode dense`, or `local_mode='dense'`, forces the other local products
through the dense control path. The banded path does not change the sparse
bath matrices, coupling tuning, stationary-series order, or scalar window.

[`tests/check_local_bands.py`](../tests/check_local_bands.py) exercises 100
primitive cases: float64 and long double; both local parities; powers zero
through four; and 0, 8, 127, 128 and 2,243 input rows. Inputs are read-only,
and the cases cover the dispatch boundary and identity/zero-sized behavior.
With a verified physical `--store`, the script also compares all \(C,r,g\),
primary and subcutoff energies, retained wavefunctions, and window arrays
for raw and self-consistent prescriptions. The saved
[local-band validation](../results/local_bands_validation.json) records zero
differences in the primitive checks and in the recorded \(L=10\) coefficient,
energy and wavefunction comparisons. Whole-solver timing effects are reported
separately in the performance document; an identity-view microbenchmark is
not a whole-solver speedup.

## 6. MPI preserves rows and synchronizes the tuning series

The distributed backend owns disjoint contiguous sets of bath rows. Only
the owned sparse values are stored on each rank, with the seed row
replicated to support the exact seed-row and Hermitian seed-column
operations. The collective sparse product gathers only the owned rows;
the replicated seed row is never counted twice.

The fused Hamiltonian path evaluates the local oscillator contribution,
the first-order free term, and the sparse bath terms in the same order as
the serial Hamiltonian on each owned row. It gathers the completed
Hamiltonian image once, instead of gathering separately after every bath
term. The common `SeedSeries.apply` routine then adds the scalar window in
the same position as the serial path.

The collective is an `Allgatherv` of disjoint output segments, not a
floating-point sum. Working dtype is preserved. All ranks compare NumPy
precision fingerprints and MPI datatype size/extent before computing, and
the test suite sends values containing bits below binary64 epsilon through
the collective. Large gather operations are split into row chunks to keep
counts and displacements within the configured MPI integer limit.

After each perturbative order, rank zero broadcasts the current mass and
quartic coefficients and all root/subcutoff energies using their real
working dtype. The broadcast is not a reduction. It keeps the exact-zero
coupling decisions and the next vacuum-window construction identical on
all ranks, even if local scalar contraction roundoff differs. An equivalent
software environment and compatible floating-point ABI on all nodes remain
the supported deployment arrangement.

Wavefunction vectors and the small energy/window arrays are replicated.
This reduces sparse-matrix memory per rank but is not a fully distributed
vector eigensolver. Increasing rank count eventually makes replicated
vectors and communication important. Correct MPI execution is established
separately from any claim about performance on a multi-node cluster.

## 7. Validation and the meaning of agreement

The standalone tests and their saved reports separate different risks:

| Check | Purpose | Evidence |
|---|---|---|
| Native sparse fixtures | Precision retention, sorted and unsorted prefixes, duplicate entries, both index widths, read-only arrays, thread invariance, fallback | `tests/check_native_backend.py`; `results/native_backend_validation.json` |
| Physical finite-cutoff solver | Compare all energies, couplings, coefficients, and retained wavefunctions with the unchanged reference through order eight | `tests/check_optimized_solver.py`; physical validation reports |
| Independent stationary toy | Exercise even and odd orders and multiple nested windows with newly generated real Hermitian vertices, rather than reuse the physical data | `tests/check_stationary_independent.py`; `results/stationary_independent_validation.json` |
| Local oscillator bands | Preserve working precision and parity; cover read-only/empty batches, the dense/banded dispatch boundary, and physical dense-control comparisons | [`tests/check_local_bands.py`](../tests/check_local_bands.py); [`results/local_bands_validation.json`](../results/local_bands_validation.json) |
| Real MPI checks | Empty ranks, row prefixes, forced small collective limits, extended-precision transport, fused Hamiltonian application, synchronized coefficients | `tests/check_mpi_backend.py`; MPI validation reports |

The native suite contains 44 matrix fixtures and requires exact floating
value agreement with an ordered NumPy reference and across thread counts.
It does not compare unspecified padding bytes in long-double storage.

The independent toy campaign compares 20 cases at orders
\(2,3,4,5,6,7,8,9,10,12\), with raw and self-consistent windows at \(L=4\).
All coefficients, couplings, root energies, and three subcutoff vacuum
energies are compared with the unchanged recurrence. Its largest scaled
difference is approximately \(3.803\times10^{-17}\). This is a test of the
formal-series implementation through order twelve; it is not a calculation
of physical 3D coefficients through that order.

The initial physical \(L=0,2,4\) checks through order eight give a maximum
scaled difference of approximately \(2.78\times10^{-17}\) across the
stationary energy comparisons. The final frozen solver was also checked
against all 16 saved physical cases: every even cutoff from zero through
14, both raw and self-consistent prescriptions, and every requested series
through order eight. All passed, with a maximum scaled discrepancy of
\(6.592\times10^{-17}\). The complete results and source fingerprints are in
[`results/final_coefficient_validation.json`](../results/final_coefficient_validation.json);
[`tests/check_saved_coefficients.py`](../tests/check_saved_coefficients.py)
repeats that campaign. Timing runs are recorded separately in the
performance report. A typical scaled
comparison divides an absolute discrepancy by
\(\max(1,|\hbox{reference value}|)\), and absolute discrepancies are also
available where needed.

The rearranged sums, stationary inner products, sparse construction, and
machine-dependent long-double implementation can affect last bits. A
small roundoff discrepancy within the documented tolerance is expected;
it is distinct from changing the physical truncation, omitting window
terms, or reducing numerical precision.
