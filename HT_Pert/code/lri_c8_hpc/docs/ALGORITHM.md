# Exact residual-form optimization of the eighth-order coefficient

This implements exactly the same finite-dimensional frozen-cutoff Hamiltonian as
the supplied C8 code. It does not change a physical regulator, discard an allowed
contribution, complete Dconn, or extrapolate the coefficient.

## 1. Conventions retained

The expansion parameter is epsilon=2s-1, not sqrt(Delta_sigma) at the other endpoint.

\[
H=H_0+\sum_{j\ge1}\epsilon^j H_j,
\qquad H_0=N+P/4,\quad H_{\rm free}=H_0-\epsilon P/4.
\]

The covariance weights obey u_n(epsilon)^2=((1-epsilon)/2)_n/n!.
The interaction is r(epsilon)M(epsilon)+g(epsilon)V(epsilon), with the original
sphere-summed normal ordering. The two calibration gaps remain (1-epsilon)/4 and
(3+epsilon)/4. The output is the fourth reference gap, E_2-E_0.

There are two separate prescriptions: `raw`, and `vacuum_only` including precisely
the original isolated diagonal g(epsilon)^2 D(epsilon). The latter is NOT complete
connected vacuum matching. This optimization does not alter or interpret its
fourth-order logarithm. All required regulator jets and coupling retunings remain.

## 2. Why an eighth-order energy does not require retaining psi_4

Let the reference |p> be nondegenerate in its physical symmetry sector, with free
energy E_p^0=p/4. Adopt intermediate normalization <p|psi_k>=0 for k>0. Let

\[
\psi^{[3]}=|p\rangle+\epsilon\psi_1+\epsilon^2\psi_2+\epsilon^3\psi_3,
\quad R_p=Q_p(E_p^0-H_0)^{-1}Q_p.
\]

The omitted fourth-order residual is

\[
b_{p,4}=Q_p\left(\sum_{j=1}^{4}H_j\psi_{4-j}
                  -\sum_{j=1}^{3}E_{p,j}\psi_{4-j}\right),
\qquad \psi_4=R_p b_{p,4}.
\]

Subtracting the E_{p,4}|p> term is unnecessary after Q_p. The third-order trial
state's Rayleigh quotient is Q_3(epsilon)=<psi^[3]|H|psi^[3]>/<psi^[3]|psi^[3]>.
Stationarity, or a direct expansion with psi^[3]+epsilon^4 psi_4, gives

\[
\boxed{E_{p,8}=[\epsilon^8]Q_3+\langle b_{p,4},R_pb_{p,4}\rangle.}
\]

Proof: for any trial state phi with exact eigenstate psi (both normalized at |p>),
Q[phi]-E=<delta|(H-E)|delta>/<phi|phi> with delta=psi-phi. For phi=psi^[3],
delta=epsilon^4 psi_4+O(epsilon^5), so the first contribution is at epsilon^8 and
equals <psi_4|(H_0-E_p^0)|psi_4>=-<b_4,R_pb_4> because (E_p^0-H_0)psi_4=Q_p b_4.
Hence E_8=[epsilon^8]Q_3+<b_4,R_pb_4>. The identity holds for any fixed series
r(epsilon), g(epsilon), so tuning r_5..r_8 and g_5..g_8 afterwards is consistent.
The order-zero norm is one, so no additional normalization factor is required. Higher
wavefunction errors cannot affect this coefficient. The denominators retain their signs. The p=2 and p=3 reference branches are
not the lowest states of their field-parity sectors; no nonpositivity claim is
made for their total residual correction.

The cubic trial's quotient still supplies all lower coefficients. Unknown r_5,...,
r_8 and g_5,...,g_8 are solved afterward from the same linear triangular gap-tuning
assembly. They are not required to compute b_4. The fourth-order low couplings are
obtained from the retained original solver in its sufficient P<=11,Q<=8 space.

## 3. Exact split of the residual support

The full eighth-order physical support is P<=19,Q<=16, where Q counts nonzero-mode
particles (this Q is not the orthogonal projector Q_p). The cubic wavefunction has
support in the strictly smaller core P<=15,Q<=12. This is exact at order three.

Let S project onto that core inside the full allowed energy-cutoff space. H_0 is
diagonal, so the two residual pieces are orthogonal even after R_p:

\[
\langle b_4,R_pb_4\rangle=\langle Sb_4,R_pSb_4\rangle
                         +\langle(1-S)b_4,R_p(1-S)b_4\rangle.
\]

Counting: psi_k has support P<=p+4k, Q<=4k. For j>=2, H_j psi_{4-j} adds at most
four particles, so P<=p+4(4-j)+4<=p+12<=15 and Q<=12. Only H_1 psi_3 can leave the
core: r_1 M_0 psi_3 vanishes because r_1=0 (asserted in engine.component), and
g_1 V_0 psi_3 reaches P<=p+16, Q<=16. Since r_1=0 and g_1=1/3, every term of b_4
other than g_1 V_0 psi_3 has support inside S. Therefore

\[
(1-S)b_4=g_1(1-S)V_0\psi_3.
\]

This statement remains true for the isolated vacuum correction: its first term is
order epsilon^2 and is diagonal; multiplying psi_2 cannot leave the core.

The outside contribution is NOT dropped. It is evaluated with scalar vectors on
the P<=19,Q<=16 space. This is the main reduction: no high-order jet vector is
needed in the largest space, and no fourth-order wavefunction is retained anywhere.

## 4. Only creation edges are needed outside

Set C=B_0^dagger and u_j=B_0^j psi_3. All u_j are in the core, because annihilation
cannot increase P, Q, or free energy. Normal ordering gives

\[
V_0\psi_3=C^4u_0/12+C^3u_1/3+C^2u_2/2+Cu_3/3+u_4/12.
\]

The last term has no outside part. Evaluate the remaining expression by ordered
Horner operations; do not commute C and B. The last creation sweep is fused with
the physical-sector projection and sum |amplitude|^2/(E_p^0-E_i^0). The corner
P<=15,Q>12 is included, not only states with P>15. The last sweep skips rows
with P>p+16, which is exact because psi_3 has support P<=p+12; OuterSpace.correction
asserts that precondition (O(D3)) before evaluating. Intermediate reflection parities
are retained. Reflection is projected only after a complete vertex.

`stored` keeps a CSR creation graph, but no full-space annihilation graph.
`ranked` reconstructs each creation row from the exact integer rank/unrank tables.
It stores no full-space graph. It is mathematically identical and generally slower,
but saves the O(E_full) edge arrays. Tests compare both paths including int64 indices.

## 5. Exact field-parity packing in the core

Every wavefunction has one field parity. A ladder changes it; M and V preserve it.
We store vectors only on their actual field-parity rows, with separate creation and
annihilation graphs for each output parity. The combined graph still represents
all core states. Both reflection parities are retained between ladder factors.

The integer ordering within each sector is inherited from the original depth-first
rank order. Fixed 4096-row reductions plus math.fsum make the reduction schedule
independent of the Numba team size. Packing changes the grouping relative to the
old uncompressed vector, so comparison is numerical-tolerance, not universal
bitwise agreement. Arithmetic remains float64 with fastmath disabled.

## 6. Work and storage

Writing D3,E3 for core dimensions/edges and D4,E4 for the full residual space, the
original algorithm performs high-order jet operations on D4,E4. The new one performs
those operations on D3,E3, plus four scalar creation/resolvent sweeps per reference
on D4. Production memory remains linear in state and edge counts, never quadratic.

Stored outside: O(E3+E4+D3*j+D4), j the number of live jet columns.
Ranked outside: O(E3+D3*j+D4+integer counting tables), with extra rank/unrank work.

The state cardinality remains unchanged physically. In particular this is NOT the
incorrect P<=15,Q<=12 C8 approximation. Reference jobs can be run independently on
up to four nodes per cutoff and assembled from scalar components. Each job still
needs its complete local core/residual arrays; this is NOT distributed-memory
sharding of those arrays. More nodes do not remove that per-item memory floor.

## 7. Validation boundaries

The tests compare all coefficients, both prescriptions, random-vector operators,
independent full eighth-order SciPy recursions, fresh small exact-rational arithmetic,
thread counts, int32/int64 kernels, and saved larger-cutoff results. The acceptance
gates retain the original thresholds: C2 shell residual <=1e-10, low-order residual
<=1e-7, and tuning residual <=1e-6. Regression comparisons use atol=1e-7, rtol=2e-11;
observed residuals and complete records are supplied separately.

Neither passing those tests nor increasing the cutoff assigns a physical uncertainty
to C8. Connected vacuum matching and continuum extrapolation are outside this release.
