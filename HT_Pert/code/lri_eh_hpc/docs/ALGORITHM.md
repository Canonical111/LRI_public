# The direct-response algorithm

## Scope and preserved prescription

This implements exactly the **isolated** `g(eps)^2 D(eps)` contribution from
`lri_effective_hamiltonian_campaign_update.zip`, with both primary gaps retuned.
It does not construct the rest of the physical effective Hamiltonian. In
particular the known `delta C4 = log(Lambda)/17496 + ...` is unchanged; the code
never subtracts this logarithm or interprets the correction as a continuum limit.

The covariance jets, frozen `N+P/4 <= Lambda` cutoff (even Lambda), normal ordering,
ordered vertex factors, and spatial-parity projection after a complete vertex
are the same as the reference. Physical arithmetic is float64. Exact integer
state counts/ranks select int32 or int64 edge IDs without changing physical
precision. No fastmath, mixed precision, approximate sparsification, fitted
C4--C7 targets, or omitted regulator jets are introduced.

The diagonal correction is

```
D_i(eps) = -1/6 sum_{m even, m+1 <= L < m+1+E_i^0}
                   (2-2 eps)_m / (m! (m+1-eps)).
```

It annihilates reference states p=0,1,2,3 at the prescribed even cutoffs. Raw and
corrected low-order tuning agree through eps^3. Through degree seven, their
third-order trial wavefunctions differ only by

```
psi_plus = psi + eps^3 chi,
chi = R'_0 g1^2 D0 psi1,    g1=1/3.
```

A trial wavefunction correct through third order gives energy through seventh
order, since the Rayleigh-quotient error is quadratic in the O(eps^4) state error.
The additional wavefunction effects at fourth and higher orders cannot affect an
energy through eps^7. This remains a perturbative, not finite-epsilon, statement.

## Do not compute and subtract two entire seventh-order spectra

Let `N=<psi,psi>`, `delta N=2 eps^3<psi,chi>+eps^6<chi,chi>`.
For an operator with raw numerator `A` and quotient `Q=A/N`, the quotient change is

```
delta Q = (delta A - Q delta N)/(N+delta N).
```

For `H0 + eps F1`, the change in numerator is just its cross and quadratic
matrix elements on `psi,chi`, with the appropriate eps shifts. For the mass and
quartic vertices the cross term starts at eps^3 and the quadratic term at eps^6.
Thus only vertex jets through `degree-4` are needed for the response. Degree-seven
raw quotients used in the response require only low-order coefficients: raw
couplings through degree four, and F/M/V coefficients through degree four or less.
No difference of two complete high-order energies is taken.

With `delta F,delta M,delta V` obtained this way and `K=<psi_plus,D psi_plus>/N_plus`,
the retuned energy difference is the coefficient series

```
delta E_p = delta F_p + r_raw delta M_p + g_raw delta V_p
          + delta r (M_raw,p+delta M_p)
          + delta g (V_raw,p+delta V_p)
          + (g_raw+delta g)^2 K_p.
```

At each order set `delta E1-delta E0=0` and `delta E3-delta E0=0` to solve
`delta r_k,delta g_k`. Then `delta C=delta E2-delta E0`. This is a triangular
series computation, not an optimization fit. Both constraints and the independent
C2 identity are checked. Raw calibration is needed only through degree four at
most; the response conditions are checked through the requested full degree.

## Stream annihilation powers

Hermitian conjugation (not commuting B and B-dagger) rewrites the cross terms as

```
<psi,M chi> = <B^2 psi,chi> + 2<B psi,B chi> + <psi,B^2 chi>,
<psi,V chi> = (<B^4 psi,chi> + 4<B^3 psi,B chi>
              + 6<B^2 psi,B^2 chi> + 4<B psi,B^3 chi>
              + <psi,B^4 chi>)/12.
```

The solver streams `B^j psi` and `B^j chi` together, accumulating raw quotients
and response numerators before releasing intermediates. This takes eight ladder
sweeps per reference, rather than four low-order sweeps plus a separate nine-sweep
response vertex. At degree seven the complete item uses 140 ladder calls, versus
248 in the original paired solver. At degree five it uses 88 versus 176.

`D` is diagonal and depends on integer free energy. A fused Numba kernel performs
lookup, polynomial multiplication, and fixed-block reductions without allocating
a dense diagonal vector at each Taylor order. Fixed 4096-row reductions followed
by `math.fsum` remain independent of the local thread count in the tested runs.

## Same perturbatively sufficient support

Every paired difference contains a diagonal insertion of cost at least eps^2.
A closed walk of the remaining degree `d-2` can move at most
`4 floor((d-2)/2)` particles away from a reference. Thus for p<=3:

```
Pmax = 3 + 4 floor((d-2)/2), Qmax = 4 floor((d-2)/2).
```

For degrees 6/7 the caps remain P<=11,Q<=8; for degrees 4/5 they remain P<=7,Q<=4.
These are the SAME correction-only caps as the incoming addon, not a new numerical
truncation. They cannot be used to claim complete raw C6/C7 spectra. Only paired
corrections are exported.

## Memory planning

State counts and **both edge counts** are known without constructing the Fock
space. Removing one particle of mode n bijects lowering edges with states at the
reduced particle, nonzero-particle and energy budget. Summing the corresponding
count-table entries gives the exact edge count.

The planner uses exact edge bytes, suffix-table bytes, 48 bytes/state of metadata
and temporary slack, 64 float64-vector equivalents, and 512 MiB runtime headroom.
An allocation-liveness inspection of the current degree<=7 code finds no more
than 35 large-vector equivalents simultaneously live in its principal phases;
64 leaves headroom for allocator fragmentation and overlooked short-lived copies.
This is a conservative **engineering estimate**, not an OS-RSS theorem. First
calibrate on the target node and reject items exceeding the actual allocation.
Increasing an allocation does not alter a physical cutoff or numerical tolerance.

## Matrix-free finite-parent elimination

The research tool no longer forms H_j as parent-state-squared dense matrices.
For each of the four requested states it solves the P/Q recurrences

```
Q psi_n = RQ [Q H_pert psi_<n - sum_{j<n} E_j Q psi_{n-j}],
P psi_n = RP [P H_pert psi_<n - sum_{j<=n} E_j P psi_{n-j}].
```

The already solved high components feed back into the low equation. This is a
state-specific application of the energy-dependent Schur complement, including
all high-high insertions and folded energy terms. It avoids a high-by-low K(E)
matrix. Memory is O(parent states * order + parent edges), not O(parent states^2).

It **still allocates the finite parent basis**. It is not the missing analytic
infinite-shell kernel, not a distributed-memory implementation, and not a reusable
matrix representation for arbitrary low states. Keep the dense oracle for small
independent comparisons. Both use the same parent couplings, not retuned low
couplings and not physical C4--C7 targets.
