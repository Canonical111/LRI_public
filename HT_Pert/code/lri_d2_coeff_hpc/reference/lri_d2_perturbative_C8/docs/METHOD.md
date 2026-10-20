# Direct two-dimensional perturbative Hamiltonian truncation through C8

## 1. Scientific target and source conventions

This calculation expands the Hamiltonian in the newly supplied
`lri_2d_window_hpc_optimized.zip`, rather than reusing one-dimensional mode
weights or fitting the nonperturbative curve at small coupling. The input
`docs/ORIGINAL_METHOD.md` is preserved under `upstream/lri_2d_hpc_optimized/`.

Set

\[
\epsilon=2s-2=2-4x,\qquad x=\Delta_\sigma=\frac12-\frac\epsilon4,
\qquad
\Delta_{\mathcal E}(\epsilon;L)=1-\frac\epsilon6+
\sum_{n=2}^8 C_n(L)\epsilon^n+O(\epsilon^9).
\]

This is the weak-end expansion in **two** dimensions. It is not the 1D
`epsilon=2s-1` expansion or the 1D short-range expansion in sqrt(Delta_sigma).
The independently present `LRI_perturbation_compendium.tex` describes the latter;
it is not used as a two-dimensional source or tuning table.

A circle mode (a,b), a,b>=0, has

\[
e_{ab}=x+a+b,\quad j_{ab}=a-b,\quad
u_{ab}^2=\frac{(x)_a(x)_b}{a!b!}.
\]

Let N=sum(a+b)n_ab, P=sum n_ab, J=sum(a-b)n_ab. The Hamiltonian is

\[
H= N+\frac P2-\epsilon\frac P4+r(\epsilon)M(\epsilon)
+g(\epsilon)V(\epsilon)+D(\epsilon),\qquad
M=\langle:\phi^2:\rangle_\theta,\quad
V=\langle:\phi^4:\rangle_\theta/12.
\]

Normal ordering is Gaussian and unchanged by the basis representation. The
angular average has measure dtheta/(2pi). The primary calibration is exactly

\[
E_1-E_0=x,\qquad E_3-E_0=2-x.
\]

The thermal gap E2-E0 is never a calibration target. Neither thermal C2/C3 nor
any higher coefficient is an input to either coefficient engine. The finite
C2 sum is evaluated in separate validation/reporting code only.

### Regulator distinction

The **uploaded model uses N<=L**, a total positive-mode bath-level bound, with
an independent local zero-oscillator basis. We keep that regulator. We do NOT
replace it by the earlier 1D frozen energy bound N+P/4<=Lambda or by a 2D
individual-mode parent a,b<=K. These are different finite problems and cannot
be combined into one cutoff sequence.

Instead of differentiating the nonperturbative moving/density-selected local
basis, we use exact Gaussian Fock support sufficient for the desired coefficient
order. This eliminates its local-basis approximation at the reported orders.
It is the same analytic finite-bath Hamiltonian, not a different normal-order
prescription. An unexpanded run of the uploaded solver checks this directly.

## 2. Exact symmetries and an additional reachable-state bound

The scalar branches have J=0, spatial reflection even under a<->b, and definite
field parity (-1)^P. The p=0,1,2,3 zero-mode references are isolated in their
respective free-energy and angular blocks. No unresolved degenerate descendant
branch is treated as an isolated primary.

Reflection pairs are represented by (|s>+|Rs>)/sqrt(2), with fixed points unchanged.
At theta=0, both the creation sum and annihilation sum commute with reflection.
Thus this reflection reduction is valid in the auxiliary ladder spaces too.
For a representative parent row i and child orbit j, the ladder weight is the
sum of its ordinary removal weights multiplied by sqrt(orbit_size_i/orbit_size_j).
All identical sparse entries are combined before use. Fresh unreduced tests
check the result.

Every J=0 bath state has even N, since N-J=2 sum b*n_ab. Scalar vacua therefore
need only even subcutoffs. This does not permit inserting a J=0 projector between
the individual creation/annihilation factors of a complete vertex.

### Exact angular envelope (new computational reduction)

An auxiliary state obtained by annihilating modes from a scalar endpoint with
N_end<=L obeys

\[
\boxed{N_{\rm aux}+|J_{\rm aux}|\leq L.}
\]

Indeed, the removed modes have total level at least the absolute value of their
total spin, and that spin must be -J_aux. More directly, annihilating a mode with
level n and spin j (|j|<=n) cannot increase N+|J|:

\[
N-n+|J-j|\leq N+|J|.
\]

Creation is monotone in the reverse direction. A normal-ordered vertex first
annihilates and then creates. Any creation path leaving this envelope cannot
return to an admissible scalar endpoint without another annihilator, so it
cannot contribute to that complete normal-ordered vertex.

The auxiliary envelope is therefore an EXACT reachable-state bound, not a new
physical UV regulator. Sorting its states by N+|J| makes every smaller envelope
an annihilation-closed prefix. Its scalar endpoints are precisely the original
N<=ell states. Nonzero intermediate J values are still retained.

The code can disable this optimization (`--no-envelope`) or the reflection
reduction (`--no-reflection`). Replays through L16 compare the original full-angle
auxiliary space with the envelope, and independent Fraction tests use neither.

### Perturbative particle support

A closed order-d energy path starting at p<=3 cannot reach farther than

\[
P\leq 3+4\lfloor d/2\rfloor,\qquad
Q_{\rm positive}\leq4\lfloor d/2\rfloor.
\]

Each quartic changes P by at most four, each quadratic by two, and the path must
return. Kinetic and window terms change no particles. The vacuum rows obey the
same closed-path reasoning. Degree eight therefore uses P<=19,Q<=16; degree
seven uses P<=15,Q<=12. These are coefficient-specific support bounds, not
nonperturbative occupation cutoffs. An enlarged P<=23 test and a separate
seventh/eighth-order comparison test them.

## 3. Mode-weight Taylor algebra and complete vertices

For v_n=(x)_n/n!, the Taylor arrays obey

\[
v_n(\epsilon)=\frac{n-1/2-\epsilon/4}{n}v_{n-1}(\epsilon),\qquad v_0=1.
\]

The square-root recurrence determines u_n=sqrt(v_n), and
u_ab=u_a u_b. Arrays store coefficients, not unscaled derivatives. All derivatives
of the regulator's Gaussian mode weights are included through the required order.

With B=sum nu_ab a_ab, a normal-ordered degree-k operator is

\[
:\!q^k\!:=\sum_{j=0}^k {k\choose j}(B^\dagger)^j B^{k-j}.
\]

The implementation uses an equivalent Horner recurrence and projects to J=0
ONLY AFTER the complete vertex. An explicit negative control shows that
projecting each ladder separately changes the operator. No small amplitude,
angular momentum, or counterterm iteration is pruned.

## 4. The actual uploaded vacuum-window prescription

Three separately labelled calculations are provided:

* `raw`: D=0;
* `consistent`: subcutoff vacuum energies are from their own corrected models;
* `literal`: a raw vacuum table is inserted into the otherwise corrected main
  Hamiltonian, retained only as a diagnostic.

For even ell,

\[
D^{[\ell]}(N)=E_v(\ell)-E_v(\ell-N),\qquad N\ {\rm even},
\quad
E_v(\ell)=\text{vacuum eigenvalue of }H_{\ell}+D^{[\ell]}.
\]

All subcutoff vacua share the SAME r,g series determined at outer cutoff L.
They are not independently retuned. Every diagonal D(N=0) vanishes.

The new coefficient engine uses the unshifted Gaussian-normal-ordered local
energy, for which Ev(0) need not vanish. The uploaded nonperturbative code
subtracts the local ground energy, so its Ev(0)=0. The difference is one common
scalar at every bath cutoff; it cancels from every D difference and every gap.
The two conventions are therefore identical for these observables.

The vacuum has zero reference expectation of M0,V0 and zero own-window entry.
Its next Taylor energy coefficient depends only on already fixed coupling
orders. Compute the new vacuum row first, update D, then determine r_k,g_k.
This makes the self-consistent series triangular, not a finite-epsilon fixed-point
iteration sampled and fitted in epsilon.

### Which order does the correction enter?

D starts at epsilon^2 and annihilates all zero-bath primary seeds. Its first
energy contribution has a first-order wavefunction on each side, hence starts
at epsilon^4. Raw and consistent C0..C3 coincide exactly.

The consistent and raw VACUUM TABLES first differ at order four. Their diagonal
window difference still annihilates primary seeds, so the literal and consistent
primary coefficients first differ at order SIX. This is confirmed explicitly;
it is different from the earlier frozen-energy 1D reference-row phenomenon.
Neither prescription is truncated at epsilon^5.

## 5. Direct coefficient recursion and the stationary quotient

Use intermediate normalization <p|psi_p>=1. At order k, before the new r_k,g_k,
let R_p,k denote the residual energy. The reference matrix elements are

\[
\langle p|M_0|p\rangle=2p,\qquad
\langle p|V_0|p\rangle=\frac{p(p-1)}2.
\]

Then

\[
r_k=\frac{t_{\sigma,k}-R_{1,k}+R_{0,k}}2,\qquad
g_k=\frac{t_{\chi,k}-R_{3,k}+R_{0,k}-6r_k}{3},
\]

where t_sigma,1=-1/4, t_chi,1=1/4, and higher target coefficients vanish.
The first solution is r1=0,g1=1/3, and the thermal first coefficient is -1/6.
The reduced free resolvent updates each wavefunction. Lower-energy coefficients
and all vacuum/normalization feedback are retained.

For an analytic Hermitian finite Hamiltonian and an approximate wavefunction
phi_m correct through order m,

\[
\frac{\langle\phi_m|H|\phi_m\rangle}{\langle\phi_m|\phi_m\rangle}-E
=\frac{\langle\phi_m-\psi|(H-E)|\phi_m-\psi\rangle}
{\langle\phi_m|\phi_m\rangle}
=O(\epsilon^{2m+2}).
\]

Thus four wavefunction orders suffice for eighth-order energies, provided the
Hamiltonian, coupling, and window jets are all supplied to order eight. The
higher-order Rayleigh quotient is assembled from normalized moments and the
same triangular tuning. It does not omit eight-vertex contributions. The option
`--full-order` uses ordinary recursion instead and is checked independently.

The zero-mode support is finite only to make the requested coefficients exact;
no assertion is made that its nonperturbative truncated spectrum is exact.

## 6. Independent analytic checks

### 6.1 The full second-order thermal coefficient

Set K=L/2 and c_n=(1/2)_n/n!. The exact finite result is

\[
\boxed{C_2(L)=\frac{17}{81}+
\sum_{n=1}^{K}c_n^2\left[
\frac{2}{81(2n-1)}+\frac1{9n}+\frac2{9(2n+1)}+\frac1{81(n+1)}
\right].}
\]

This same finite check is in the uploaded weak-check script. Its limit can be
verified independently using

\[
\begin{array}{ll}
\sum_{n\geq1}c_n^2/(2n-1)=1-2/\pi,&
\sum_{n\geq1}c_n^2/n=4\log2-8G/\pi,\\
\sum_{n\geq1}c_n^2/(2n+1)=4G/\pi-1,&
\sum_{n\geq1}c_n^2/(n+1)=4/\pi-1.
\end{array}
\]

The Catalan constant G and the rational/pi terms cancel, leaving
C2(infinity)=4 log(2)/9. In particular C2(L)-C2(infinity) has leading tail
-40/(81*pi*L), so even the lowest nonlinear coefficient is visibly unconverged
at the largest new cutoff. That known tail is not copied to higher coefficients.

### 6.2 Vacuum coefficient and the first window shift

The scalar four-particle vacuum spectral weight in shell N=2n is
(4!)/(12^2)*(n+1)^2. Its free energy is 2(n+1). Including g1^2 gives

\[
E_{v,2}(L)=-\frac{(K+1)(K+2)}{216},\qquad
D_2^{[L]}(2n)=-\frac{n(2K+3-n)}{216}.
\]

Combining the first-order wavefunction norms with the two primary retunings gives

\[
\boxed{\delta C_4(L)=C_4^{\rm consistent}-C_4^{\rm raw}
=\frac1{972}\sum_{n=1}^{K}n(2K+3-n)c_n^2 b(n),}
\]

\[
b(n)=\frac1{9(2n-1)^2}+\frac1{4n^2}+\frac1{(2n+1)^2}
+\frac1{36(n+1)^2}.
\]

This is independently derived from <psi1|D2|psi1>, not fitted to the new energies.
It matches every calculated raw/consistent difference at order four.

One caution follows analytically. Put
A=(1/972) sum_{n>=1} n c_n^2 b(n). Then

\[
\delta C_4(L)= A L-\frac5{8748\pi}\log L+O(1),
\quad A=0.0002207292996452666338602081\ldots.
\]

An independent closed representation is

\[
972A=\log2+\frac19-\frac2{9\pi}
-\frac12\,{}_4F_3\left(\tfrac12,\tfrac12,\tfrac12,\tfrac12;
1,\tfrac32,\tfrac32;1\right).
\]

This is a statement about the WINDOW DIFFERENCE ALONE, not the full corrected
thermal coefficient. Its growing terms may cancel corresponding raw artifacts;
this study does not derive the entire raw/connected fourth-order large-L sum.
A small finite window correction must not be extrapolated as an arbitrary constant.
The 1D window asymptotics are not transplanted to two dimensions.

## 7. Independent checks and input independence

`exact_circle.py` enumerates separate (a,b) occupation states, without reflection
or envelope compression, in the epsilon-dependent polynomial coordinates
prod(nu_ab a_ab^dagger)^p. Creation coefficients are one, annihilation coefficients
are p*nu_ab^2. It calculates ordinary full-order eigenvalue recursion using exact
Fractions. The similarity transformation changes wavefunction coordinates, not
energies. It reproduces raw and consistent coefficients at L=0,2,4,6 through C8.

`test_finite_uploaded.py` instead invokes the unmodified nonperturbative ZIP
solver at epsilon=.08,.04,.02, L=2,4. It uses the directly computed Taylor coupling
series evaluated at epsilon, without a new fit or retuning. Fully unexpanded mode
weights, dressed local diagonalization, and nonlinear vacuum solves supply a third
check. The eighth-order thermal remainder decreases by factors approaching
2^9=512; at the finest pair the observed factors are about 498..501. That is a
validation of coefficient extraction, not how coefficients were extracted.

Additional tests cover enlarged particle support; seventh/eighth-order overlap
at L16 and L20; full-order versus stationary recursion; reflection reduction;
auxiliary-envelope removal; independent subcutoff batching; exact normal-order
reference diagonals; Hermiticity; and an exact rational stationary-quotient
identity with an insufficient-order negative control.

Main vectors and sparse vertices are float64, matching the uploaded numerical
precision. Several scalar contractions accumulate in longdouble. No fastmath
or amplitude pruning is enabled. The Fraction oracle is separate exact arithmetic.
Differences reported in the tests are numerical implementation tolerances, NOT
statistical or physical uncertainty intervals on continuum coefficients.

## 8. Limits of the result

This release supplies raw and consistent-window C0..C8 at every even L=0..20,
with L=0 a local-only diagnostic, and selected literal controls. It does not
supply a justified C3..C8 continuum extrapolation or a complete effective Hamiltonian.
The recent factorizing-parent cubic matching results are not silently inserted
into the uploaded product-regulator calculation. A physical high-order result
requires a common-regulator high-state matching and controlled tails.

The new scripts are a separate research branch, not a replacement for the HPC
lease/manifest dispatcher. The original ZIP is preserved byte-for-byte (ignoring
runtime-generated caches, which are not redistributed). The L20 memory and time
measurements are local observations, not cluster performance guarantees.

## References and provenance

1. Supplied lri_2d_window_hpc_optimized.zip: original method, symmetry conventions,
   complete-vertex construction, and direct finite-coupling validation oracle.
2. Supplied 1D independent-coefficient and whole-coefficient-flow archives:
   parent algorithms for full and stationary Taylor recursion. Their unchanged
   code snapshots are in vendor_reference/ for attribution, not imported as 2D physics.
3. Elias Miro and Ingoldby, arXiv:2212.07266, effective Hamiltonians/counterterms:
   general context for the distinction between finite-model accuracy and physical
   high-state matching, not a source of the new coefficients.
4. Cohen et al., arXiv:2110.08273, Hamiltonian Truncation Effective Theory:
   general high-state matching background, not a 2D long-range coefficient table.

No independently supplied 2D continuum C6,C7,C8 table is used. The older 2D note
is not part of the current uploaded ZIP. Its historical numerical comparisons
are not reclassified as new computations or silently inserted into this solver.
