# Whole-model cutoff flow: what this continuation does and does not determine

## 1. Scientific scope

The requested objects are the complete large-cutoff leading polynomials of the
thermal C6, C7 and C8, not the tails of a tagged overlap response. Those complete
analytic polynomials are **not derived here**. No formula in this release
relabels a fitted amplitude, a finite-parent coefficient, or a partial graph as
one of them.

This continuation instead evaluates the entire specified Dconn coefficient
problem over a larger cutoff range and subjects the previous asymptotic models
to genuinely new high-order coefficient data. A second, explicitly exploratory
calculation tries to extract every logarithmic coefficient of the postulated
leading power directly from whole-coefficient shell differences. It fails to
supply stable physical intercepts; the failure is retained rather than hidden.
No OPE/source-subgraph calculations are extended in this release.

All numerical data refer to the frozen cutoff

    E0=N+P/4 <= Lambda, Lambda=2,4,...,
    epsilon=2s-1, x=(1-epsilon)/4,
    Delta_thermal=1/2-epsilon/6+sum C_n epsilon^n.

The Hamiltonian is H0-epsilon*P/4+r M+g V+Dconn, with
M=:q^2:, V=:q^4:/12 and u_n^2=((1-epsilon)/2)_n/n!.
Reflection is imposed after complete normal-ordered vertices, never between
ladder factors. The only coupling conditions are the spin and shadow gaps x
and 1-x. The vacuum correction is the supplied consistent disconnected-window
model, not a newly derived full connected physical Hamiltonian.

## 2. Exact half-order compression of the full problem

For any analytic, Hermitian finite-dimensional H(epsilon), a nondegenerate
reference branch E and its intermediate-normalized eigenvector psi, let
phi_m=sum_(a=0)^m epsilon^a psi_a. Write delta=phi_m-psi. Then

    <phi_m|H|phi_m>/<phi_m|phi_m> - E
        = <delta|(H-E)|delta>/<phi_m|phi_m> = O(epsilon^(2m+2)).

The identity is exact before Taylor expansion. Thus psi through m=4 determines
energies through order 8 (and indeed through 9 when the corresponding Hamiltonian
jets/support are supplied). We do not implement or claim a degree-nine run.
For degree seven m=3 suffices. This is the stationary Rayleigh-quotient/Wigner
property, not an approximation that omits the highest hard interaction orders.

Let psi_a=0 beyond m and define coefficient moments

    N_k = sum_(a+b=k)<psi_a|psi_b>,
    M_k = sum_(a+b+c=k)<psi_a|M_b|psi_c>,
    V_k = sum_(a+b+c=k)<psi_a|V_b|psi_c>.

For a free reference energy e0, the order-k residual before the new r_k,g_k is

    R_k = sum_(a+b=k)<psi_a|(H0-e0)|psi_b>
          +sum_(a+b=k-1)<psi_a|(-P/4)|psi_b>
          +sum_(j=1)^(k-1) [r_j M_(k-j)+g_j V_(k-j)-E_j N_(k-j)]
          +sum_(j=2)^(k-1)sum_(a+b=k-j)<psi_a|D_j|psi_b>
          +<psi0|D_k|psi0>.

All those moments use the actual finite matrices, not an assumed local
counterterm basis or selected hard graphs. Higher hard interactions, energy
folds and repeated low returns are present through the exact quotient identity.

The two primary equations determine

    r_k=(t_sigma,k-R_1,k+R_0,k)/2,
    g_k=(t_chi,k-R_3,k+R_0,k-6r_k)/3.

Thermal coefficients are then E2,k-E0,k. No thermal C_n reference is read by this
engine. All four low references are nondegenerate in their retained field and
reflection parity sectors. This claim is not extended to arbitrary descendants.

## 3. Self-consistent vacuum rows are preserved

For each vacuum grid index q=0,...,2Lambda, and each state i,

    q_lower=max(0,(2q-(4N_i+P_i))//2),
    D_i^[q]=Ec(q/2)-Ec(q_lower/2).

The same outer r,g series is used for every vacuum subproblem. At order k,
Ec,k has no diagonal contribution from the new r_k,g_k, and its own window entry
vanishes. Consequently Ec,k is obtained first, then the main order-k window rows,
then r_k,g_k. For k>m the quotient uses the already constructed psi0..psi_m and
the evolving E,r,g,D arrays. It is the same triangular finite model as the
full-order upstream recursion, not a frozen-window approximation.

Each vacuum channel stores only states actually allowed by its energy and
symmetry mask. States are globally sorted by frozen energy so sparse prefix
matrices are exact lower-cutoff spaces. The source matrices are applied in small
batches; the normal-order Horner recurrence consumes annihilation powers one at
a time. These two storage changes reduce memory without removing a physical
state. Support is P<=3+4 floor(d/2), Q_nonzero<=4 floor(d/2), exactly as in the
input. Degree eight therefore uses P<=19,Q<=16, while degree seven uses 15,12.

The stored wave coefficients and sparse operations use float64, as in the
reference. Some scalar sums use longdouble accumulation before export to
float64. No precision is reduced, no fastmath is used, and no amplitude is
pruned. This remains a research implementation, not a validated cluster port.

## 4. What was generated

The new engine evaluates every even cutoff 2..44 at degree eight in Dconn.
Previously the complete C6,C7 sequence stopped at 28 and C8 at 24. Therefore
C6,C7 at 30..44 and C8 at 26..44 are new, not inherited values. The remaining
points are independent replays. The largest basis has 2,006,277 states including
all auxiliary ladder parities; that is not the dimension of one physical sector.

Raw controls at Lambda=28,36,44 agree with the independently supplied high-cutoff
arrays. Complete Dconn C4,C5 agree with the earlier closed-sum correction data.
A degree-seven run at Lambda=44 supplies a separate support/order check against
the first seven coefficients of the degree-eight calculation.

There were memory-exhausted development attempts before the ragged and sequential
Horner memory paths were finalized. No point from an incomplete run is accepted.
The final successful Lambda44 Dconn run uses about 2.39 GiB peak process RSS
locally. This is not a promise of the same resource use on an HPC node. There is
a 2.3-million-state guard; larger runs need independent resource planning and
validation, not blind removal of the guard.

## 5. Fixed forecasts test the whole model, not a tagged graph

Before generating new high-order coefficients, freeze_forecasts.py read only
inputs/scheme_data.json and the independent gap inputs. It generated 16 model
configurations: lower edges 4/8; bases S/A; homogeneous, source5, sources567,
and free_omega leading models. Its forecast JSON was hashed. No later step
alters its training data or coefficients.

The training reach is deliberately stated per order: C3,C4,C5 through 118;
C6,C7 through 28; C8 through 24. Thus this is prospective withholding of NEW
high-order coefficients, not a claim that the lower-order data at the same
cutoffs were unseen. Forecasting higher orders propagates fitted lower orders
rather than substituting newly calculated C6/C7 at those cutoffs.

C2,C3 and separately computed phi6-gap exponent coefficients are declared
controls. No C4..C8 continuum value is read by the fit. The benchmarks were
visible in earlier conversations, so this is target-excluded rather than
prospectively blind to the reference physics.

The fit engine preserves the earlier analytically linked log/source shapes.
Those shapes still contain fitted nuisance amplitudes and an assumed leading
channel. Passing a nearby-cutoff test does not prove its continuum value or
make the uncomputed Wilson coefficients known.

## 6. A separate whole-leading-polynomial extraction attempt

Without imposing a single exponent's relations among log coefficients, test

    F_n(L)=L^-1/2 sum_(j=0)^(n-2) a_nj [log(L/32)]^j
            +sum optional b_j L^(-1-j/2),
    C_n(L+2)-C_n(L) = F_n(L+2)-F_n(L).

The first term retains ALL monomials of the proposed leading polynomial.
It is a hypothesis about the leading expansion, not a proof that other
nondecaying terms/channels vanish. Optional subleading powers are L^-1 and
L^-3/2. Every model and failed sample-count guard is retained. These exploratory
fits use new data only through L=36 and predict L=38,40,42,44. An anchor fixes the
additive constant afterwards, without a thermal reference value.

The calculations use scaled 80-digit QR. Their tail amplitudes/intercepts vary
strongly with lower edge and subleading basis even when finite-cutoff predictions
are accurate. They are NOT reported as analytic amplitudes or physical confidence
intervals. The condition and bounded-input-noise sensitivity are published.
The synthetic bound 3e-13*max(1,|C_n|) is a numerical stress, not a certified
noise law or physical error model.

## 7. Highest-log dominance is not a justified substitute

For the conditional homogeneous highest monomial a L^-1/2 log^d L,

    d/dL [a L^-1/2 log^d L]
      = a L^-3/2 log^(d-1)L [d-(log L)/2].

The sign changes at L=exp(2d). For d=4,5,6 these values are about 2981,22026,
162755. At the current cutoff range, the highest-log-only slopes have the
OPPOSITE signs from the actual whole-model increments. This rules out using
that monomial alone there. It is not a claim that these huge cutoffs are needed
when all lower logs are known, nor a proof that the homogeneous highest-log
coefficient itself is unconditional.

## 8. What remains

No complete analytic leading polynomial for C6,C7,C8 is obtained in this work.
The new data include all finite-cutoff contributions, and the fit tests now use
new whole-model coefficients rather than reassembled tagged sources. The missing
analytic calculation is still the uniformly matched higher hard-vertex regions
and their finite coefficients, including the counterterm/window/energy pieces.
A reference solver extension and a successful forecast must not be substituted
for that calculation.

Provenance: the supplied lri_1d_independent_coefficients.zip and
lri_1d_asymptotic_fit_tests.zip provide the unmodified vendored reference routines
and finite datasets. The previous lri_1d_complete_order_kernel_assembly.zip gives
the complete hard-sector bookkeeping. None of these provides the missing final
analytic tail amplitudes. General HT matching background is arXiv:2110.08273;
its formulas do not determine the regulator-specific constants studied here.
