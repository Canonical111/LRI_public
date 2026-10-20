# General low-bath matching and explicit overlap renormalization

## 1. Scope and the two cutoffs

This calculation retains the input convention

    epsilon=2s-1, x=(1-epsilon)/4, alpha=2x,
    H=H0-epsilon P/4+r M+g V,
    H0=N+P/4, M=:q^2:, V=:q^4:/12,
    q=sum_n u_n(a_n+a_n^dagger), u_n^2=(alpha)_n/n!.

Reflection is projected after complete vertices. The outer frozen energy cutoff
is Lambda; an auxiliary retained low-space cutoff is denoted **mu**. The high
expansion below requires fixed low states/modes, or mu much smaller than Lambda.
Taking mu=Lambda in a fixed-low-state asymptotic expansion is not justified.

Only the primary gaps x and 1-x fix r,g. No C6, C7 or C8 benchmark appears in any
new algorithm. The thermal combination is E2-E0 after that primary retuning.
All data are perturbative Taylor coefficients, not finite-coupling spectra.

The input Dconn is the self-consistent **disconnected vacuum window**:

    D_i^[mu]=Ec(mu)-Ec(floor_(1/2)(mu-E_i^0)),

with every subcutoff vacuum evaluated in its own H+D problem using the SAME
outer low-space coupling series. This definition is preserved and differentiated
when a source is added. It is not relabelled the full connected Hamiltonian.

The prior study supplied a leading high kernel only for external zero-mode
states and one restricted zero-mode response class. This continuation adds the
fixed-low-BATH kernel and evaluates full low-space linear responses through
order eight. It then derives the overlap asymptotics of the complete first
phase response, rather than only its zero-mode contraction.

The complete physical C6--C8 leading-tail polynomials are still not determined.
The genuinely higher connected hard subgraphs, their overlap subtractions and
finite matching coefficients are not replaced by the susceptibility numbers
computed here.

## 2. Extending the high kernel beyond a zero-mode external block

Let q involve any fixed finite set of low modes and define

    A=sum_low u_n^2, M=q^2-A,
    N=sum_low n a_n^dagger a_n,
    P=sum_low a_n^dagger a_n, H0=N+xP, beta=3alpha.

Fix the external reflection parity nu=0 or 1. Put

    d_nu(p)=2+nu-2 ceil[(p+4nu)/8],
    J_nu^P=q d_nu(P+3) q - A d_nu(P+4).

The required general phase operator is

    J_nu^bath = J_nu^P - {N,M}/2.                            (1)

The exact first omitted high level for the three-high-line term, when the
intermediate low state has occupation P_j and level N_j, is

    n_min=Lambda+d_nu(P_j+3)-N_j.

It has parity nu-N_j mod 2. For the four-high-line subtraction, the extra low
covariance mode k gives d_nu(P_i+4)-N_i-k. These offsets are frozen at epsilon=0:
using physical x in the cutoff shifts would define a different regulator.

Expand the Gamma ratio and the shifted step-two sum in a finite annulus
Lambda<E0<=U. Combining the three-line term with the low-covariance subtraction
from the four-line term gives

    K3(Lambda;E)=g^2 A3 M
      -g^2 B3[(2-beta)^2 M/2 + E M - {H0,M}/2
                                      -(2-beta) J_nu^bath],             (2)
    A3=Lambda^(beta-1)/[3(beta-1)Gamma(beta)],
    B3=Lambda^(beta-2)/[3(2-beta)Gamma(beta)].

The finite annulus is K3(Lambda;E)-K3(U;E), with remainder
O(Lambda^(beta-3)) for fixed low states. A divergent infinite mass sum is not
assigned a finite value. The A3 mass term must be subtracted in a consistent
matching scheme, as in the preceding study.

To obtain (1), use

    q N q = {N,q^2}/2 + sum_low n u_n^2.

The last scalar cancels the k-weighted four-line subtraction. Thus the previously
zero-mode-only phase operator is missing a same-power bath-level anticommutator.
It is not merely a new value of a scalar phi6 exponent.

`annulus.py` compares (2) with direct finite sums for modes 0,1,2, external states
P<=6 and N<=4, both reflection sectors, alpha=.49,.50,.51, and Lambda=32..1024
with U=2Lambda. The full formula has the predicted next-order error. Keeping
J_nu^P but omitting -{N,M}/2 leaves an O(Lambda^(beta-2)) error. These are
operator-annulus tests, not continuum thermal-coefficient fits.

## 3. Which leading operator responses must be calculated

The prior one-contraction kernel is

    K1=-Lambda^(alpha-1)/[2(1-alpha)Gamma(alpha)]
       *[4r^2 :q^2: +(4rg/3):q^4: +(g^2/9):q^6:].

Mass/quartic tangent directions can be absorbed in the two primary-tuned
couplings. A local potential insertion and its canonical energy/metric fold
cancel when their common operators commute. One must not keep the fold by
itself. These facts leave, in the stated two-high-vertex leading sector, the
responses of Phi6=:q^6: and of the full operator (1), in addition to the
separately matched divergent mass and other hard contributions.

For any chosen operator O define the finite low-space susceptibility

    S_O(epsilon;mu) = partial_eta Delta_E[H+eta g(epsilon)^2 O] at eta=0,

where r,g and every Dconn vacuum are differentiated too. This quantity uses
low-space coupling coordinates. It is NOT itself a Wilson coefficient.

The high factors multiply the susceptibilities in the same declared coupling
convention. For the retained two-vertex sector their formal form is

    delta Delta_E = -Lambda^(alpha-1) S_Phi6/[18(1-alpha)Gamma(alpha)]
             +Lambda^(3alpha-2) S_J/[3Gamma(3alpha)] + ... .               (3)

Converting couplings between a high parent and the retuned low model, all
higher hard subgraphs and overlap subtractions remain necessary for a complete
answer. Equation (3) must not be used at mu=Lambda to claim that the full
asymptotic coefficients have been obtained.

`response.py` implements an ordinary Taylor derivative alongside all reference
and subcutoff vacuum wavefunctions. The source contains the BASE g^2; inserting
its eta derivative in the source would be a second-order-in-eta error.
The source perturbation includes all placements, regulator derivatives, vacuum
feedback, primary retuning and energy/normalization terms through epsilon^8.
The energy-space support cap is unchanged: the g^2 Phi6 source costs two epsilon
orders and changes particle number by at most six, no more than two quartics.

For reflection-even references the normal-ordered phase implementation is

    J^P = (Bdag)^2 d0(P+4)
          +Bdag[d0(P+3)+d0(P+5)]B +d0(P+4)B^2.

This avoids corrupting the operator by an intermediate cutoff in q d(P) q.
The number part is -{N,M}/2. Their separate derivatives add to the full response.
For sources g^2 M and g^2 V, primary retuning is an exact reparametrization; the
thermal derivative vanishes. Those are strong non-thermal-target checks.

An independent rational-coordinate implementation enumerates complete small
energy spaces and uses u_n^2, with no square-root numerical matrix entries.
A third finite-epsilon test constructs exact mode weights and solves every
vacuum equation by Schur complement. The high block is checked positive.
It differentiates the Schur equations and then evaluates normalized
Hellmann--Feynman matrix elements; it does not use the Taylor recursion.

## 4. A new exact lower-order response identity

The phi6 susceptibility begins

    S_Phi6,2=-40/9,
    S_Phi6,3(mu)=X(mu)/27 -(80/3)[g2(mu)+C2(mu)],
    X(mu)=sum_(n=0,2,...,mu-2)
              [240/(n+1)+720/(n+1/2)+1_(n>0)240/n].                     (4)

The coefficients follow from the retuned cross Phi6--quartic Wick contraction;
the induced quartic retuning supplies the second term. C2 and g2 here are the
known finite functions, not fitted physical intercepts. Hence

    S_Phi6,3(mu)=(40/3)(log mu+gamma_E)
                       -(20/9)(pi+4log2)+O(mu^-1/2).

This shows at an elementary level why the low response cannot be treated as a
cutoff-independent amplitude. Equation (4) agrees with every new finite-
mu response through mu=28. The higher susceptibilities are computed directly,
not assigned a continuation of (4).

## 5. Complete phase response at first nonzero order

J^P annihilates all states with P<=4. Its first retuned response occurs at order
four and consists of the V--J^P--V contraction on first-order states. Unlike the
prior tagged calculation, ALL intermediate low bath modes are now included:

    S_phase,4(mu)=(1/81) L_p <R_p Vp|J^P|R_p Vp>,
    L_p X=X2-X1-X3/3+X0/3.                                             (5)

All allowed intermediate particle counts are 5,6,7; their maximum even mode
level is mu-2. Thus (5) is identical for raw and Dconn at this order. Later
response coefficients are not identical between those prescriptions.

The exact Wick generator reduces (5) to 38 positive rational coefficients times
kernels

    T_abc^(d,e)(mu) = sum_(k>=0) v_b(k) G_a(k;d) G_c(k;e),
    v_b(k)=(b/2)_k/k!,
    G_a(k;d)=sum_(n even, k<=n<=mu-2) v_a(n-k)/(n+d),
    d,e in {1,1/2}.

This is a one-dimensional convolution representation of the complete double
intermediate sum. No large Fock space or quadrature fit is required. Direct
convolution and longdouble FFT implementations agree at their overlap. The
maximum mu=262144 refers ONLY to (5), not to all C8 susceptibilities or spectra.
All coefficients are positive after primary retuning, so the finite responses
are monotone in mu.

### 5.1 Power and logarithmic mixing

Grouping the exact 38 terms and analysing their different endpoint regions gives

    S_phase,4(mu)=A sqrt(mu)+(log mu)^2/81+B log mu+C+o(1),              (6)
    A=32(pi-2)/(729 pi^(3/2)),
    B=[41+42pi+12gamma_E+24log2+48log(1+sqrt2)]/486.

Numerically A=0.008999301587815558 and B=0.49138877353902566. No coefficient in
(6) was fitted to a cutoff sequence.

The power term is generated only by (a,b,c)=(1,3,1), with total Wick coefficient
8/729. Its continuum integral is

    4 integral_0^1 b^-1/2 acos(sqrt b)^2 db = 8(pi-2).

The step-two parity factors give T131~4(pi-2) sqrt(mu)/pi^(3/2).
Its next possible harmonic term alternates and is convergent; it does not add
a nonalternating logarithm.

The (2,2,0) terms and their reversals give

    T220 = (log mu)^2/8
       -[log2+psi(e/2)]log(mu)/4 + constant +o(1), e=1/2.

Their combined rational weight is 8/81, giving 1/81 in (6). The remaining
logarithmic topologies have coefficients:

    T040: 1/2,
    T130,T031: 1/2,
    T121: pi/4,
    T200,T002 (d=1,e=1/2): 1,
    T210,T012 (d=1,e=1/2): (pi/2+asinh1)/2.

Multiplying by their exact Wick weights and adding the T220 logarithms gives B.
The other topologies converge. The power, endpoint log-squared, and regular
harmonic-log regions therefore all occur in ONE fully evaluated susceptibility.
Replacing this by a constant fitted 'source amplitude' misses its structure.

### 5.2 Finite part from convergent sums, not fitting

For a=0,1 the infinite inner sums are

    G0^infty(k;d)=1_(k even)/(k+d),
    G1^infty(k;d)=[Beta(k+d,1/2)+(-1)^k J(k+d)]/2,
    J(a)=integral_0^1 t^(a-1)/sqrt(1+t) dt
        = hypergeometric(1/2,1;a+1;1/2)/(sqrt(2)a).

The kernel h_k=v_b(k)Ga^infty Gc^infty has an explicit Gamma-ratio expansion,
with alternating as well as nonalternating powers. Subtract its nonalternating
k^-1/2 or k^-1 terms where present; add back zeta(1/2) or gamma_E, respectively.
The remaining convergent sums and their explicit Hurwitz tails are evaluated
independently of finite-mu data. The finite boundary-profile additions are

    T131: 0,
    T121: -(pi/2)log2-7zeta(3)/(4pi),
    T130,T031: -log2.

The T131 term has a fixed nonalternating k^-1/2 leading part and alternating
k^-1 next part; the latter is summed conditionally without discarding parity.
Higher Gamma terms give ordinary convergent and alternating Hurwitz tails.

The a=2 cases have direct special finite parts. Set S=pi/2+asinh1 and

    I=integral_0^1 [u S-asin u-asinh u]/(1-u^4) du,
    D=4 integral_0^1 [log((1+u)/(1-u))+2atan u]
                                 /[u(1+u+u^2+u^3)] du.

Both are integrable. In the given denominator convention,

    finite(T200)=gamma_E+log2,
    finite(T210)=S(gamma_E+log2)/2-2I,
    finite(T220)=[log2+psi(1/4)]^2/8+psi1(1/4)/8-D/4.

Reversals agree. These formulas and the convergent kernels determine

    C = 8.094227411788686348... .                                      (7)

Independent regularized evaluations with cutoffs 256 and 512 differ by about
7.34e-18; the lower-accuracy 128-term/four-asymptotic-order evaluation also agrees
at its expected level. This is numerical evaluation of convergent expressions,
not an interval-arithmetic certification of every displayed digit. The much
slower finite-mu convolution sequence approaches (7), providing a separate test.

No optimized all-mu numerical bound for the o(1) term in (6) is asserted. In
particular, the small error of (7) is NOT an uncertainty on a physical C6,C7,C8.

## 6. What the result implies for the high-order matching

There are two logically different scale dependences:

- Lambda controls the omitted high oscillator states in the physical regulator.
- mu separates those states from an auxiliary low problem whose matrix elements
  are being evaluated. A physical answer cannot depend on this arbitrary split.

The divergent response (6) requires counterterms/overlap subtractions in the
higher hard graphs. Its sqrt(mu), log^2(mu) and log(mu) coefficients fix an
explicit set of such cancellations. They are NOT the entire outer-Lambda
coefficients in C6,C7,C8 and are NOT the fitted source s5 in the previous
one-channel model.

A single scalar exponential using the measured phi6 gap cannot be declared a
complete operator-mixing calculation on the basis of these data. Conversely,
this calculation does not prove a particular nonzero continuum offset: those
hard and soft pieces may cancel after full matching. The correct next operation
is to assemble them in the same subtraction/coupling convention.

At fixed low mu, response.py now gives the actual derivatives through eighth
order for both independent operators, including Dconn. Those replace guesses
about how a new matrix affects C6,C7,C8. The remaining quantities are genuinely
higher high-state Wilson kernels, subtraction pieces such as the earlier B5,
and the finite terms after their overlap cancellations. This delivery does not
claim those have been solved.

## 7. References, provenance and limitations

The supplied archives `lri_1d_independent_coefficients.zip`,
`lri_1d_C8_boundary_counterterm_tails.zip`, and
`lri_1d_C6_C7_C8_analytic_tails.zip` specify the regulator and prior subkernels.
Only the unmodified normalized Space helper is vendored; all new source,
annulus, overlap, finite-part and independent rational algorithms are supplied.
Exact input archive/source hashes are in inputs/PROVENANCE.json.

General effective-Hamiltonian context: arXiv:2212.07266 and arXiv:1706.06121.
Those papers do not supply the 1D numerical coefficients derived here.

No thermal target file is imported. No cutoff or epsilon fit produces a number
reported as an analytic coefficient. Large low-source runs are independent
calculations but not an optimized HPC implementation; its memory guard must not
be removed to infer nonexistent scalability. The finite-epsilon tests use
fixed Taylor coupling/source series and test their O(epsilon^9) remainder,
not a finite-coupling CFT prediction.
