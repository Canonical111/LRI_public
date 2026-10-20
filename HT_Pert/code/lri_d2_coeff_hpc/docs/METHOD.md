# Optimized 2D direct coefficient engine

## 1. Scope and unchanged physics

The source is `lri_2d_C8_perturbative_check.zip`, preserved byte-for-byte under
`reference/lri_d2_perturbative_C8/` (excluding only newly generated interpreter
caches from the distribution). This optimization is for its **coefficient engine**,
not a modification of the dressed nonperturbative solver or its old dispatcher.

We retain

\[
\epsilon=2s-2=2-4\Delta_\sigma,\qquad x=\frac12-\frac\epsilon4,
\]
\[
H=N+\frac P2-\frac\epsilon4P+r(\epsilon)M(\epsilon)
 +g(\epsilon)V(\epsilon)+D(\epsilon),
\quad M=\langle:\phi^2:\rangle_\theta,
\quad V=\langle:\phi^4:\rangle_\theta/12.
\]

Circle modes are labelled `(a,b)`, with energy `x+a+b`, angular momentum `a-b`,
and squared weight `(x)_a(x)_b/(a! b!)`. Physical endpoints obey `J=0`, spatial
reflection even, definite field parity, and the ORIGINAL total bath-level bound
`N <= L`. No individual-oscillator UV parent is substituted. No additional
counterterm, tail fit, reference thermal value, or decreased coefficient order
is introduced.

The primary gaps `E1-E0=x` and `E3-E0=2-x` alone fix the two couplings. The thermal
output is `E2-E0`. The three schemes remain distinct:

* `raw`: no diagonal window;
* `consistent`: `D^ell(N)=Ev(ell)-Ev(ell-N)`, with vacua calculated in their own
  corrected Hamiltonians;
* `literal`: raw sub-cutoff vacua supply the main window, retained as a control.

Every vacuum uses the SAME outer `r,g` Taylor series. The existing triangular
vacuum/tuning recursion and normalized stationary quotient are retained. In
particular the window is not frozen at order five. Raw/consistent differences
begin at fourth order; literal/consistent differences begin at sixth order for
this product regulator. These statements are checked, not fit conditions.

The optimized code supports coefficient degrees 2 through 8. Vectors, mode jets,
and graph amplitudes remain float64. Scalar polynomial contractions use extended
`numpy.longdouble` / C++ `long double`; platforms where these cannot supply at
least a 64-bit significand are rejected rather than silently downgraded. The
independent exact-Fraction oracle in the source is retained for small-cutoff tests.
This release does **not** introduce arbitrary-precision large-vector computation.

## 2. Profile before optimization

`results/reference_profile_L16.json` contains a fresh cProfile of the default
reference scalar-symmetry/envelope path, with compilation warmed separately.
The initial profile found 7,566 sparse matrix-vector calls. Complete Taylor
vertices dominated execution; construction of repeated CSR jets was the next
major cost. The largest phase was construction of mass/quartic energy moments.

Those observations motivated four changes: construct only the already-proven
auxiliary space, share graph topology among Taylor coefficients, fuse sparse
Taylor products, and avoid creation passes that are algebraically unnecessary
for energy moments. No optimization relies on a change in the physical answer.
Final unprofiled timings are separate from this instrumentation-heavy profile.

## 3. Generate the exact auxiliary envelope directly

The reference already proves `N+|J|<=L` for auxiliary ladder states reached in a
complete normal-ordered vertex between scalar endpoints. Set

\[
A=\sum a n_{ab},\qquad B=\sum b n_{ab},\qquad N=A+B,\quad J=A-B.
\]

Then

\[
N+|J|=2\max(A,B),\qquad A,B\leq L/2.
\]

We therefore enumerate this two-charge envelope directly rather than generating
the much larger unrestricted bath graph and discarding most states afterward.
This is the SAME existing envelope, not a new scalar cutoff.

A suffix count table obeys

\[
f(k,A,B,q)=f(k+1,A,B,q)
 +\mathbf1_{A\ge a_k,B\ge b_k,q>0}f(k,A-a_k,B-b_k,q-1).
\]

It counts multisets with at most `q` positive-mode particles. It supplies both an
exact dimension and exact rank lookup for reflected states and annihilation
children. No Python tuple dictionary of all occupations is stored.

Spatial-reflection orbits use the same `(state+mirror)/sqrt(2)` normalization as
the source. Two annihilations can reach the same child orbit. Their edges remain
separate and BOTH contribute; the physical coefficient equals the combined CSR
entry. Every orbit factor is retained. Reflection is checked to be an involution.

The zero mode is appended with the original exact perturbative bounds:

\[
P\leq3+4\lfloor d/2\rfloor,\qquad Q_{\rm positive}\leq4\lfloor d/2\rfloor.
\]

States are stably ordered by the envelope extent. Every smaller vacuum envelope
is an annihilation-closed prefix. Its scalar endpoints are exactly `N<=ell`.
Creation cannot leave that envelope and return during the creation portion of a
normal-ordered vertex. Nonzero auxiliary angular momenta are never projected away
between individual ladder factors.

`plan` independently counts reflection-fixed occupations using diagonal modes and
paired off-diagonal modes. Burnside averaging gives exact auxiliary dimensions.
A generating-function moment of the number of distinct occupied modes gives the
exact edge count. Both are tested against the actual graph. Rank-table, state,
edge and native integer limits are checked before allocation.

## 4. One graph and fused Taylor products

The reference stores one sparse matrix for every coefficient of the mode-weight
Taylor series, duplicating indices and row pointers. The new representation
stores creation adjacency once. Each edge has a child index, oscillator label,
and occupation/orbit amplitude. A separate transposed gather adjacency contains
parent indices and edge references, not duplicated amplitude or mode tables.
The tiny oscillator-jet table is shared.

For node-major Taylor vectors,

\[
y_{i,k}=\sum_{e:i\leftarrow j} A_e
          \sum_{r=0}^k u_{m_e,r}x_{j,k-r}.
\]

The native kernel specializes the short jet dimensions and fuses these sums into
one graph traversal. Horner additions and the final projection/division are fused
or parallelized as well. Creation and annihilation BOTH use row-owned gathers:
no two threads write the same output row, no atomics are needed, and no unsafe
parallel transpose scatter is used. Exact leading zeros in an input jet may be
skipped; no amplitude threshold or approximate sparsification is used.

Native compilation uses `-O3 -std=c++17 -fopenmp -fno-fast-math -ffp-contract=off`.
Neither fast-math nor FMA reassociation is requested. A native mode table is
shared for all edges. The compiler, flags, source hash and machine type identify
the compiled cache. An independent Numba backend implements the same mathematical
operation, also without fastmath. It is slower in the main benchmark, but avoids
the C++ compiler dependency and checks the native result.

For a fixed perturbative degree, work and persistent storage remain linear in
the graph and vector sizes. Fusing the jets changes memory traffic and allocation
cost, not the mathematical number of nonzero contractions. The exact Fock basis
still grows rapidly with the cutoff; no claim of polynomial-in-cutoff scalability
or removal of the fundamental Hilbert-space growth is made.

## 5. Annihilation-only energy moments

The scalar wavefunction has real Taylor coefficients. Writing the annihilation
sum as `B`, the normal-order identities give

\[
\begin{aligned}
\langle M\rangle
 &=2\langle\psi,B^2\psi\rangle+2\langle B\psi,B\psi\rangle,\\
\langle V\rangle
 &=\frac{2\langle\psi,B^4\psi\rangle
       +8\langle B\psi,B^3\psi\rangle
       +6\langle B^2\psi,B^2\psi\rangle}{12}.
\end{aligned}
\]

Every product here is a truncated polynomial convolution. These formulas remove
all creation passes from the moment stage and permit a streaming evaluation with
at most three large annihilation work arrays live. They are exact for the scalar
states, since the bra and ket already enforce angular projection. They are NOT
used to drop angular projections in a wavefunction update, where full vertices
are still required.

The current stationary quotient still uses wavefunctions through half order;
we do not claim that idea as a new optimization. The new code changes how its
moments are evaluated. A random-jet test compares these formulas with explicit
reference mass/quartic vertices; ordinary full-order recursion and exact rational
coefficients provide independent energy tests.

Complete degree-zero reference images are calculated once, not regenerated at
every Taylor order. For `raw` and `consistent`, the top-cutoff vacuum is exactly
the p=0 primary; its duplicate wavefunction/vertex/moment calculation is reused.
This identity is NOT applied in `literal` mode, whose two vacuum Hamiltonians
differ. No coupling-dependent vacuum is lagged or reused at changed couplings.

## 6. Precision and deterministic thread behavior

Sparse vectors remain float64. For polynomial dot products, each product is
formed in double precision as in the reference, then accumulated in long double.
The native reduction uses fixed blocks of 1,024 nodes, regardless of thread count.
Blocks are reduced in increasing order after the parallel loop. Changes in
thread scheduling therefore do not change that summation order. Native and Numba
thread-replay tests require bitwise equality within each backend on this platform.

Reference and optimized algorithms sum terms in different algebraic orders, so
cross-engine bitwise identity is NOT promised. Cross-engine checks compare `C`,
`r`, `g`, all four energies, and the ENTIRE sub-cutoff vacuum table. Scaled error
means `max(abs(new-old)/max(1,abs(old)))`. The production primary/finite gate is not
relaxed. Agreement tolerances are implementation tolerances, not physical errors.

## 7. HPC execution and honest scaling boundary

The supported multi-node path is a Slurm job array of independent
cutoff/scheme/order calculations. Each job uses a row-parallel shared-memory
solver. Cutoff jobs share no live floating-point state or mutable vacuum table.
A serial-node process may use a memory-mapped, read-only checked graph cache shared
with other jobs; node-local copies are preferable for large filesystems/campaigns.

**There is no distributed-memory single-cutoff matvec or MPI eigensolver in this
release.** A single cutoff's largest graph/workspace must fit on one node. The
local environment did not provide MPI and an optional installation attempt had no
network access; no MPI performance or validation is claimed. Likewise, local
multi-process array-task tests are not evidence of actual cross-node filesystem
or Slurm behavior. Those must be checked on the target cluster before a large run.

The new manifest schema is deliberately different from the old nonperturbative
campaign schema. The supplied original dispatcher, ownership leases and physics
solver are not modified or assigned a misleading existing validation receipt.

## 8. Persistence, interruptions and concurrency

The CLI source/runtime/model fingerprint includes the scheme, cutoff, degree,
particle-cap override, native/Numba backend and full/half-order method. Thread
count is execution metadata; a restart with a different thread count is allowed.
Source or dependency changes require a new identity. A verified completed output
is reused only with the same identity. Legacy plain JSON or corrupted envelopes
are rejected, not silently trusted or overwritten.

Output ownership is an atomic directory claim. An abandoned claim is never
recovered by guessing job liveness. A killed process can leave a claim requiring
manual removal AFTER its job is known to have stopped. This conservative policy
avoids unsafe cross-node lock stealing; it is not an automatic lease service.
Atomic-directory/rename semantics still require a filesystem smoke test.

Checkpoints are complete Taylor-boundary states, not partial matrix operations.
They include all primary/vacuum wavefunctions, couplings, energy coefficients,
completed moments and stage counters. Each generation is individually hashed and
published only after all arrays exist. An atomic pointer selects the latest
complete generation; one predecessor is retained. Corrupted arrays are rejected.
No pickle is used. SIGUSR1/SIGTERM/SIGINT request a checkpoint at the next safe
boundary, then exit 75. A hard kill cannot checkpoint the operation currently in
progress, but it leaves the previously published generation valid.

Checkpoint writes are rate-limited except when stopping. Include enough Slurm
warning time for the longest current contraction plus checkpoint I/O. A change in
rank partitioning is not relevant because the solver is shared-memory, not MPI.

## 9. Validation and profiling artifacts

`tests/test_numerics.py`: reference arrays, exact Fractions, all schemes, degree
coverage, full-order replay, enlarged support, exact graph and edge dimensions,
random-jet operators, annihilation moments, two backends, thread determinism,
analytic C2/vacuum/window identities, and memory/input rejection.

`tests/test_storage.py`: read-only cache reuse and corruption, restart at several
Taylor/moment boundaries, exclusive claims, CLI stop/resume, completed-result
reuse, and mismatched-scheme rejection. Additional campaign/signal checks are
recorded separately. The original file-level oracle remains available in the
preserved source archive.

Final benchmarks use separate sequential processes, three repetitions per
configuration, BLAS threads fixed to one, and separate warmup. They include
basis construction and the entire tuning/window coefficient solve but exclude
imports and one-time JIT/native compilation, whose warmup time is also recorded.
No old published timing is substituted for a fresh baseline. Timing ranges are
reported because a shared local host has measurement variability.

No full continuum coefficient, tail fit, or nonperturbative accuracy claim is
made by this optimization.

## Technical documentation consulted

* Numba, automatic parallelization and race-condition cautions:
  https://numba.readthedocs.io/en/stable/user/parallel.html
* Slurm job arrays: https://slurm.schedmd.com/job_array.html
* Slurm signal and resource flags: https://slurm.schedmd.com/sbatch.html

These documents justify API usage; they do not certify this cluster deployment.
The physical definitions and reference numerical outputs come exclusively from
the supplied 2D coefficient package.
