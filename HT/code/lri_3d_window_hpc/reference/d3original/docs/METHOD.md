# Direct spherical Hamiltonian truncation in three dimensions

## Observable, conventions, and scope

This is the **classical three-dimensional long-range Ising family**, represented
by radial quantization on S^2 times the cylinder time. It is not a 3+1-dimensional
quantum transverse-field Ising calculation. Put

\[
x=\Delta_\sigma=(3-s)/2,\qquad \epsilon=2s-3=3-4x.
\]

The long-range interval is \(\Delta_\sigma^{SR}<x<3/4\). The reference bootstrap
values are \(\Delta_\sigma^{SR}=0.518148806(24)\) and
\(\Delta_{\mathcal E}^{SR}=1.41262528(29)\), from arXiv:2411.15300. The crossover
condition is \(s_*=3-2\Delta_\sigma^{SR}\). These external numbers appear only in
comparison plots and the scan-domain check. The free endpoint is (3/4,3/2).

All numerical curves in this package are **raw, finite product-regulator
spectra**. The only Hamiltonian couplings are r and g. No complete effective
Hamiltonian, vacuum-window correction, continuum extrapolation, or interpolation
onto an endpoint is inserted. The tiny tuning and eigenvector residuals are not
physical error bars.

## Spherical generalized-free modes

For q=exp(-tau), the cylinder covariance is

\[
G(\tau,\gamma)=q^x(1-2q\cos\gamma+q^2)^{-x}.
\]

Let \(Y_{\ell m}\) be complex spherical harmonics with integral norm one, and
\(\mathcal Y_{\ell m}=\sqrt{4\pi}Y_{\ell m}\). Their spherical-average norm is one
and their addition formula is
\(\sum_m\mathcal Y_{\ell m}(\Omega)\mathcal Y_{\ell m}^*(\Omega')=(2\ell+1)P_\ell(\cos\gamma)\).
The mode expansion has radial label n>=0 and angular labels ell,m:

\[
E_{n\ell}=x+2n+\ell,\qquad
u_{n\ell}^{\,2}=\frac{(x)_{n+\ell}(x-1/2)_n}{n!(3/2)_{n+\ell}}.
\]

The field is the sum of \(u_{n\ell}\mathcal Y_{\ell m}a_{n\ell m}\) and its
Hermitian conjugate. The test suite checks the equivalent Gegenbauer identity
for each level independently. We require x>1/2, which includes the physical LR
interval. At x=1/2 radial descendants become null; that limiting representation
is not handled by this code.

There are (k+1)(k+2)/2 one-particle modes at total level k=2n+ell. Changing only the
field dimension in the old one- or two-dimensional oscillator list would be
incorrect.

## Product regulator and rotations

The n=ell=0 oscillator is kept separately. All positive-mode Fock states obeying

\[
N=\sum_{n\ell m}(2n+\ell)N_{n\ell m}\le L
\]

are enumerated. No additional particle cap is used. The bath state count is the
sum through q^L of
\(\prod_{k\ge1}(1-q^k)^{-(k+1)(k+2)/2}\).

Scalar primaries live in total spin J=0 and even spatial inversion parity.
Merely selecting M=0 is insufficient, since that also contains all higher
integer spins. We construct the kernel of J_+ at M=J, separately at each N and P.
The raising operator is

\[
J_+=\sum_{n\ell m}\sqrt{(\ell-m)(\ell+m+1)}
 a^\dagger_{n,\ell,m+1}a_{n,\ell,m}.
\]

J_+ preserves each (n,ell) species occupation. Resolving these exact blocks
before the null-space calculation avoids huge disconnected SVDs. Each resulting
basis vector has definite N, bath particle number P, and spin J. For the scalar
calculation we keep N even. For first-descendant tests J=1 and N odd are used;
the stress candidate uses J=2 and N even. The zero mode carries no angular spin.

The numerical nullspace threshold is 5e-13 relative. J_+ and orthonormality
residuals are recorded. The nonzero singular values represent nonzero spin and
are well separated from the nullspace in all completed calculations. A separate
test lowers J=1 states from M=1 to M=0 and checks invariant vertex matrices.

The number of scalar bath states is 10,33,110,371,1285 at L=4,6,8,10,12,
respectively. The full bath counts are 171,1407,9801,60566,341241. Projection
removes representations not belonging to the requested physical angular sector,
not small-amplitude states.

## Normal ordering and the dressed zero mode

Use the volume-rescaled coupling convention

\[
M=\int\frac{d\Omega}{4\pi}:\phi^2:,
\qquad V=\frac1{12}\int\frac{d\Omega}{4\pi}:\phi^4:,
\qquad H=H_0+rM+gV.
\]

The normalization is chosen so zero-mode reference states obey
\(\langle p|M|p\rangle=2p\),
\(\langle p|V|p\rangle=p(p-1)/2\). An overall sphere-volume factor has been
absorbed into r,g; this is not a physical tuning input.

For q0=a0+a0^dagger and p0=(a0-a0^dagger)/i, set A=x/4+r-g/2. Up to a scalar,

\[
H_z=x p_0^2/4+Aq_0^2+gq_0^4/12.
\]

Let X be the positive-mode field and
\(W_j=\int d\Omega/(4\pi):X^j:\). Then

\[
H=H_z+H_b+\sum_{j=1}^4 L_jW_j,\quad H_b=N+xP,
\]

\[
\begin{aligned}
L_1&=(2A-x/2)q_0+gq_0^3/3,\\
L_2&=(A-x/4)I+gq_0^2/2,\\
L_3&=gq_0/3,\qquad L_4=gI/12.
\end{aligned}
\]

The omitted common scalar is -x/2-r+g/4. A common local ground energy is also
subtracted before the many-body calculation; both cancel in all reported gaps.
The original normal-ordering polynomials q0^2-1, q0^3-3q0, q0^4-6q0^2+3 are
preserved. We do not re-normal-order relative to the interacting local ground
state.

H_z is diagonalized with an adaptively scaled oscillator basis. The lowest nz
states per parity are retained. Its auxiliary oscillator resolution `osc` is
independent of nz. Polynomial matrices are formed in an enlarged auxiliary space
before projection, so top-row polynomial matrix elements are correct. These
are two independent, explicitly varied local resolutions.

## Angular integration

At azimuth zero, the spherical harmonics are real. For a fixed-M external
basis S, put A_j(theta)=B(theta)^j S, where B annihilates bath modes with the
correct u*Y coefficient. The projected normally ordered vertex is

\[
W_k=\frac12\int_{-1}^{1}dz\sum_{j=0}^k\binom{k}{j}
 A_j(z)^T A_{k-j}(z).
\]

All intermediate magnetic sectors are retained in B; projection occurs only at
the two external ends of the complete vertex. Equal external M makes the
azimuthal integral exact. Between retained N<=L states, a normally ordered
matrix element has angular degree at most 2L. Therefore L+1 Gauss--Legendre
nodes exactly integrate it in exact arithmetic. Doubling the quadrature is an
independent numerical test. No angular discretization approximation beyond
floating-point evaluation is introduced for these finite vertices.

## Direct nonlinear spectral solve

The two field-parity matrices are applied without global Kronecker assembly.
The scalar problem is tuned by

\[
E_{\sigma}-E_0=x,\qquad E_{\chi}-E_0=3-x.
\]

The output is the first excited even scalar gap E_E-E0. This identifies the
branches by continuation from weak coupling; a complete strong-coupling
operator/OPE identification is not provided.

Positive g is parameterized by
\(g=192e^3/x^2\), \(A=4e^2\kappa/x\), with root coordinates (kappa,log e).
The weak-coupling expressions provide only an initial guess, not a thermal
target. The response Jacobian differentiates the parameter-dependent projected
local Hamiltonian, including its moving-subspace response. Its comparison with
full spectral differences is recorded. Warm-vector phase alignment changes
only eigensolver initialization.

Dense subset diagonalization is used for small matrices and matrix-free ARPACK
for larger ones. All physical arithmetic is float64, no fastmath or reduced
precision. Five low levels are recomputed at acceptance; tuning, eigenvector,
and orthogonality gates are checked before publication.

## Independent weak-coupling check

The free endpoint has (Delta_sigma,Delta_E)=(3/4,3/2). At first order the tuning
conditions give r1=0, g1=1/3 and Delta_E=3/2-epsilon/6+....

At epsilon=0 let

\[
h_n=\frac{(3/4)_n(1/4)_n}{(3/2)_n n!}.
\]

An independent sum of zero-mode transition probabilities and rotationally
averaged bath-shell norms gives, for even L,

\[
C_2(L)=\frac{34}{243}+\sum_{n=1}^{L/2}h_n
\left[\frac{4}{9(4n+3)}+\frac{4}{81(4n-3)}
 +\frac{2}{81(2n+3)}+\frac1{9n}\right].
\]

The code computes these finite sums as exact rational numbers. It derives them
from the full contraction sums, not by entering this already-collected formula
into the matrix calculation. The leading omitted tail is
\(-40/(243\sqrt\pi)L^{-3/2}\).

The generating function of h_n is
\(H(q)={}_2F_1(3/4,1/4;3/2;q^2)=\sqrt{2/(1+\sqrt{1-q^2})}\).
It turns the sum into a convergent integral. An independent high-precision
integral agrees with the note's value

\[
C_2(3)=\frac{2-\pi+4\log2}{9}=0.1812217854055542\ldots.
\]

The recorded high-precision residual is not a rigorous enclosure or a new
proof of all higher-order coefficients. The direct small-epsilon spectra agree
with the independently computed finite-cutoff C2(L) polynomial up to a residual
scaling as epsilon^3. No fit in epsilon supplies a numerical input to the solver.

## What is not controlled

1. No continuum limit of the complete thermal gap has been established.
2. No S^2 product-regulator high-state matching has been implemented.
3. Existing d=1 or d=2 vacuum counterterms are not portable numerical corrections.
4. Local refinement and eigenvalue residuals do not control omitted bath states.
5. Descendant and spin-two endpoint candidates show significant untuned errors.
6. The endpoint benchmark is a numerical bootstrap estimate, not an exact
   thermal condition. Its uncertainty is far below the currently observed
   regulator effects and is invisible at the main plot's scale.

The next scientific task is regulator-specific matching and boundary analysis,
validated on untuned rotational sectors and weak-coupling coefficients, before
attempting a physical continuum extrapolation.

## External references

- Behan, Rastelli, Rychkov, Zan, *Long-range critical exponents near the
  short-range crossover*, https://arxiv.org/abs/1703.03430 .
- Paulos, Rychkov, van Rees, Zan, *Conformal Invariance in the Long-Range Ising
  Model*, https://arxiv.org/abs/1509.00008 .
- Chang et al., *Bootstrapping the 3d Ising Stress Tensor*,
  https://arxiv.org/abs/2411.15300 .

These references establish benchmark and field-theory context. They do not
certify the new finite-cutoff numerical calculations or supply their missing
regulator-specific counterterms.
