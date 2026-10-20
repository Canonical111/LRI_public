# Two-dimensional port of the agreed dressed-window Hamiltonian

## Scope and distinction from earlier work

This release implements a **new direct, fixed-coupling calculation in 2D**, using the
choices adopted for the 1D solver: the Gaussian-normal-ordered phi4 Hamiltonian,
a total positive-bath-level cutoff, a self-consistent full-vacuum window, and an
optional state-averaged local basis. Standard dense/ARPACK eigensolvers are used.
There is no selected-tail backend, Schur replacement, fitted energy scale,
kinetic-moment calibration, angular buffer, or individual-mode factorizing parent.
The earlier 2D cubic matching/source studies are not inserted into this model.
The ultraviolet completeness of this scalar window in 2D is not assumed.

## 1. Coordinates and circle modes

Write x = Delta_sigma = (2-s)/2 and epsilon = 2s-2 = 2-4x. The interacting scan
uses 1/8 < x < 1/2; the endpoint pairs are (1/2,1) and (1/8,1). The independent
thermal output is denoted Delta_E, avoiding confusion with epsilon.
The radius-one cylinder covariance is

    G_x(tau,theta) = q^x (1-q exp(i theta))^(-x)(1-q exp(-i theta))^(-x),
    q=exp(-tau).

There is one oscillator for every (a,b) with a,b >= 0:

    e_ab=x+a+b; j_ab=a-b; u_ab^2=(x)_a (x)_b/(a! b!).

The field is sum u_ab [a_ab^dagger exp(i j_ab theta)+a_ab exp(-i j_ab theta)].
This replaces the single 1D index; merely changing x would not be a 2D port.
With occupation numbers n_ab,

    N=sum (a+b)n_ab; P=sum n_ab; J=sum (a-b)n_ab; H0=N+xP.

The zero oscillator (0,0) is treated separately. Every positive-mode bath
partition with N<=L is retained, with no extra particle cap. Field parity is
(-1)^P. Scalar primary calculations use J=0 and reflection even under a<->b.
At J!=0, reflection maps J to -J; it is not an additional projection in a fixed-J
sector. The code retains nonzero intermediate J inside each complete vertex.
Since N-J is even, every scalar bath state has even N. The scalar vacuum and its
Hamiltonian are therefore identical at ceilings 2m and 2m+1.

## 2. Interaction and zero-mode normalization

The interaction convention, identical to the previous 2D solver, is

    Hraw=H0+r average_theta(:phi^2:)+(g/12) average_theta(:phi^4:).

Normal ordering is always Gaussian, not redefined by the interacting local basis.
Let q0=a00+a00^dagger, p0=(a00-a00^dagger)/i (commutator [q0,p0]=2i), and
A=x/4+r-g/2. Up to a common scalar the local Hamiltonian is

    hz = x p0^2/4 + A q0^2 + g q0^4/12.

If Wj is the circle-averaged normal-ordered degree-j positive-bath vertex,

    Hraw=hz+Hb+sum_{j=1}^4 Lj tensor Wj,
    L1=(2A-x/2)q0+g q0^3/3,
    L2=(A-x/4)I+g q0^2/2, L3=g q0/3, L4=g I/12.

The same coupling coordinates are used as the 1D implementation:

    g=192 exp(3 theta1)/x^2,
    A=4 exp(2 theta1) theta0/x,
    r=A+g/2-x/4.

A common even-local-ground-energy shift is removed from every cutoff, so Ev(0)=0.
Every q0 power is formed BEFORE auxiliary truncation and projected independently.
In particular U^dagger q0^4 U is not replaced by (U^dagger q0 U)^4.

## 3. Exact projected bath vertices

Let B=sum_positive u_ab a_ab and S_J embed the retained fixed-J/reflection space
in the full bath Fock space. For degree k,

    Wk = sum_{j=0}^k binom(k,j) (B^j S_J)^dagger (B^(k-j) S_J).

This constructs only the required projected vertices. All angular sectors survive
between individual annihilators. Normal-ordered annihilation-then-creation paths
never exceed both endpoint bath levels. This is exactly the projected operator,
not an intermediate-shell approximation. The alternative shared-ladder backend
uses the same algebra without storing Wk. Tests compare both and the original
full-matrix vertex construction, including explicit Fourier averaging.

## 4. The proposed full-vacuum window in 2D

For an even scalar bath ceiling ell, define

    D_ell(N)=Ev(ell)-Ev(even_floor(ell-N)),
    Hwindow,ell=Hraw,ell + D_ell(N) tensor I_local.

D_ell(0)=0. Every Ev uses the same x,r,g and the same local space as the top-cutoff
solve; sub-cutoff vacua are NOT retuned independently. Both the zero mode and bath
are included. For scalar N even, this is simply Ev(ell)-Ev(ell-N).
This is the 2D extension of the adopted numerical window, not a theorem that all
connected high-state effects are represented by it.

At each ell, solve the scalar equation F(s)=lambda_min(Hraw+D(s))-s=0. The unknown
s multiplies the projector onto nonzero bath levels, and Hellmann--Feynman gives
F'(s)=-p_bath0. Newton's update is s <- s + F(s)/p_bath0. The absolute fixed-point
acceptance ceiling remains 1e-11, with working tolerance 1e-12. Small bath-vacuum
weight, nonconvergence, and eigensolver failures are rejected, not accepted by
loosening the gate. Complete lower-cutoff vacua are recomputed at changed couplings.

For a coupling coordinate theta,

    d Ev(ell) = [<d Hraw,ell> - sum_{N>0} p_N d Ev(even_floor(ell-N))]/p_0.

This is propagated to dD and to the two tuning equations. On J=1,2 diagnostic
sectors, the SAME top-cutoff table D_L(N) is applied. No angular-dependent cutoff
buffer or sector retuning is introduced.

The prescription is evaluated at finite x. It is not an epsilon^5 polynomial.
Self-consistency is not a proof of complete physical matching at fifth order or
at any finite coupling. It is a scalar bath-level correction, identity in local
space, and lacks general off-diagonal, local-state-dependent high-state response.

## 5. Calibration and outputs

Only two gaps are imposed:

    E_sigma-Ev=x, E_chi-Ev=2-x.

The output is the first excited even scalar gap Delta_E=E_even,1-Ev. The zero-mode
primary expectation values are <p|M|p>=2p and <p|V|p>=p(p-1)/2, giving r1=0,g1=1/3
and Delta_E=1-epsilon/6+... near x=1/2. A coupled root solve is repeated for every
cutoff, x, local space and prescription. Thermal/endpoint/descendant data are not
fit targets. Seeds copied from the old 2D scan are Newton initial guesses only.

The expansion of the vacuum window starts at order epsilon^2 and vanishes on the
zero-bath primary seeds. Its diagonal primary effect is therefore absent through
order epsilon^3; it first can change the primary gaps at fourth order. The supplied
weak_check.py tests the O(epsilon^4) raw/window difference without extracting a
coefficient by fitting. It does NOT establish the new physical C4 or higher terms.

## 6. Optimized local representation

At training cutoff Ltrain=2m, form the normalized reduced density

    rho=(rho_vac,Ltrain+rho_sigma,Ltrain+rho_chi,Ltrain)/6
          +sum_{ell=0,2,...,Ltrain-2} rho_vac,ell/(2m).

Within each local parity keep the largest density eigenvectors. Only these vacuum
and calibration states enter selection. The thermal state is not a basis target.
The implementation saves the physical isometry, primitive scale, density spectra,
weights, x, teacher resolution and residuals. A kept20 artifact supplies nested
12-,16-,20-state subspaces. There is no cross-x basis transfer.

During each smaller solve the primitive span is fixed, although the local H may
be diagonalized inside it for coordinates. The Jacobian uses the full local reduced
density and full off-diagonal dH, not only derivatives of local energy eigenvalues.
Warm vectors rotate with the whole within-span rotation. All changed-coupling
windows and both primary gaps are recomputed. A small discarded density weight
is not a bound on the held-out thermal energy; independent larger-reference and
nested-size comparisons test it explicitly. Teacher training is at L=6 in the main
campaign; target calculations at L=8,10,12 never train that artifact.

## 7. Untuned spectral checks and their limitations

The free chiral translation is

    A0=sum_{a,b} sqrt((a+1)(x+a)) a_(a+1,b)^dagger a_(a,b),

with B0 raising b. The zero-mode part uses the directly projected primitive
annihilator; this remains valid in a non-invariant optimized subspace. At the
same L and vacuum table, compare the largest-overlap eigenstate with A|O>,
A^2|O> and BA|O>. Their expected energy increments are 1,2,2, and spins 1,2,0.
The reported norm probabilities are probabilities within the full translated
candidate, not renormalized to the few computed roots. A maximum below 0.5 is
flagged ambiguous; six roots per sector are tested. These are FREE-generator
ancestry checks, not exact interacting conformal charges.

Near strong coupling, BA|O> can overlap most strongly with the original primary.
The resulting flagged `spacing_error=-2` is a failed assignment, not an identified
negative-energy descendant. Such entries must not be used as physical spectral
errors or fitted targets. The first-angular energies and all overlap metadata
remain visible. Better operator labels cannot move a pole at the wrong energy.

## 8. Reproduction, numerical gates and scope

The new port uses float64, no fast-math, no amplitude pruning, and standard
ARPACK/dense eigensolvers. All accepted scalar solutions are recomputed with five
roots and checked; diagnostics independently use six. Main tuning tolerance is
3e-11, eigensolver tolerance 1e-12, independent eigenvector gate 1e-8, orthogonality
gate 1e-9. Actual residuals are tabulated. The full 1D cluster dispatcher, artifact
leases and cluster validation receipts are NOT ported here. This is a standalone
research port, requiring one writer per output and separate deployment validation.
No new physical continuum curve, all-orders matching, C4-C6 verification, or
short-range-end spectrum is inferred from passing finite-matrix tests.
