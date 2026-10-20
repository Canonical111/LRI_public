# Three-dimensional spherical window Hamiltonian: derivation and implementation

## 1. Parameter and operator conventions

Let x=Delta_sigma=(3-s)/2, epsilon=2s-3=3-4x. The weak endpoint is x=3/4;
the physical short-range boundary is the numerical Ising value x_SR~0.518148806.
The latter is not supplied as a tuning condition. The radius-one scalar covariance
is G(tau,mu)=q^x(1-2q mu+q^2)^(-x), q=exp(-tau). Its oscillator decomposition is

    E_(n,l)=x+2n+l,
    u_(n,l)^2=(x)_(n+l) (x-1/2)_n / [n! (3/2)_(n+l)].

Each species has magnetic indices m=-l,...,l. The angular field factors are
sqrt(4 pi) Y_lm with normalized average dOmega/(4 pi). Equivalently, each shell
obeys the independently tested addition identity

    C_k^x(mu) = sum_(2n+l=k) (2l+1) u_(n,l)^2 P_l(mu).

The positive modes exclude (0,0,0); its weight is one. The parent Hamiltonian is
H0 + r average(:phi^2:) + g/12 average(:phi^4:), in the original Gaussian normal
ordering. H0=N_b+x P_b plus the zero oscillator. The local decomposition is

    hz=x p^2/4 + A q^2 + g q^4/12,   A=x/4+r-g/2,   [q,p]=2i,
    Hraw=hz+Hb+sum_(j=1)^4 Lj tensor Wj,
    L1=(2A-x/2)q + g q^3/3,
    L2=(A-x/4)I + g q^2/2,   L3=g q/3,   L4=g I/12.

The local even-ground energy is subtracted uniformly at all cutoffs. Hence Ev(0)=0
in this convention. Every q power is formed in the primitive oscillator space
with sufficient padding and then projected; the fourth power of projected q is
not used in place of projected q^4. No normal ordering with respect to the dressed
vacuum is introduced.

## 2. True angular sectors and the numerical bath cutoff

Retain all occupation configurations with N_b=sum(2n+l) k_nlm <= L. No separate
particle cap is used in the direct solver. Field parity is (-1)^(P_b+P_local),
spatial inversion is (-1)^N_b, and rotations supply total J.

M=0 alone is not a scalar sector. We construct the kernel of J_+ in the M=J
subspace, independently in every species-occupation block. A species is (n,l);
rotations preserve its total particle count. Columns of S_J are orthonormal and
have definite N_b and P_b. Scalar primaries use J=0 and inversion even; diagnostic
J=1/2 sectors use inversion odd/even. The natural inversion sectors are the ones
in this study; it is not an exhaustive all-spin/parity spectrum atlas.

The new graph uses the exact old DFS order, a dynamic-programming partition count,
and combinatorial rank/unrank. Numeric parent/last-mode/occupation tables replace
the old list of full occupation tuples and global dictionary. Tuples and species
signatures are constructed only where needed for angular projection. This reduces
construction overhead, but does not change exponential/combinatorial Hilbert-space
growth or remove nullspace costs. All int-size and user-state limits are checked.

## 3. Spherical vertices and performance choices

At azimuth zero define B(z)=sum u_nl sqrt(4 pi)Y_lm(arccos(z),0) a_nlm. In a fixed
external magnetic sector, the azimuthal integral is imposed by angular-momentum
selection. The remaining polar quadrature gives

    Wk = sum_q wq sum_(j=0)^k binom(k,j)
                   [B(zq)^j S_J]^T [B(zq)^(k-j) S_J].

All intermediate magnetic sectors in each complete normal-ordered vertex survive.
Never project each annihilator separately onto J=0. With retained endpoint levels
<=L, the integrated polar polynomial degree is <=2L. L+1 Gauss-Legendre nodes are
therefore sufficient in exact arithmetic. In a definite inversion sector, the
integrand is even, so opposite nodes are paired exactly. The particle-block
implementation avoids multiplying contributions whose particle numbers cannot
match. Its results are independently compared with full original vertices,
increased quadrature order, and rotationally equivalent M=0/M=J representations.

The default tensor backend stores only four bath matrices Wj, not the full
Kronecker many-body Hamiltonian. Matrix-vector work is sparse gathers plus local
contractions, with local field parity fixed by total field parity XOR bath parity.
Compiled row-owned kernels parallelize large contractions without race-dependent
reductions. Float64 summation order differs from some original routines, so tests
use tolerance, not a universal bitwise assertion.

The optional Gram backend stores annihilation images for each polar node. It is
algebraically equivalent and useful as a check. Unlike the circle case, repeated
polar images cost substantial memory/work. In our L10/12 benchmarks it is inferior
to tensor. Auto thus selects tensor; no unmeasured high-L Gram switch is imposed.
The code does not claim all 2D performance improvements transfer quantitatively.

## 4. Self-consistent full-vacuum window

For an even scalar bath ceiling ell, define

    D_ell(N)=Ev(ell)-Ev(2 floor((ell-N)/2)),
    Hwindow,ell=Hraw,ell + D_ell(N_b) I_local.

Ev is the lowest eigenvalue in the scalar inversion-even field-even sector of
this corrected Hamiltonian. The even-floor rule follows here from inversion,
not the 2D N-J identity: the vacuum sector contains only even N_b. An odd ceiling
therefore has the same vacuum space as the previous even ceiling. Every sub-vacuum
uses the same couplings and local representation; they are not retuned separately.

With all lower even vacua known, the unknown v=Ev(ell) shifts nonzero bath levels.
F(v)=lambda_min(Hraw+D(v))-v has derivative -p0, where p0 is the ground state's
bath-vacuum probability. Thus the scalar Newton update is v<-v+F(v)/p0. Vanishing
p0 or failed convergence is rejected. The working tolerance is 1e-12 and the
absolute acceptance ceiling is 1e-11. The top iteration requests only one root;
afterward the expanded even spectrum must satisfy the same fixed-point gate.
An exactly equal local Hamiltonian/vertex set may reuse a stored table. Changed
couplings must be solved again; this is not a lagged-window approximation.

For a coupling variation, the derivative obeys

    p0 dEv(ell) = <dHraw> - sum_(N>0) p_N dEv(even_floor(ell-N)).

The local-ground subtraction is differentiated too. The same resulting D_L(N)
is used on untuned J=1 and J=2 sectors, with the same L. There is no angular buffer.

This prescription models a disconnected vacuum-window artifact. It is identity
in local space, lacks general off-diagonal and energy-dependent connected response,
and is not a proof of exact all-orders or continuum conformal matching. It is
evaluated directly at finite x, not truncated at epsilon^5.

## 5. Local basis and root solve

The moving local teacher uses the lowest nz eigenstates in each local parity.
From its coupled vacuum, spin, shadow, and lower-cutoff vacua, form at Ltrain=2m

    rho=(rho_vac,top+rho_sigma,top+rho_chi,top)/6
                 +sum_(ell=0,2,...,Ltrain-2) rho_vac,ell/(2m).

Keep the largest eigenvectors in each parity of rho. No thermal state enters the
selection. The saved primitive isometry and scale are fixed in subsequent solves.
Local diagonalization within this span is only a coordinate rotation. The full
local reduced density and off-diagonal projected derivatives enter Hellmann-Feynman;
differentiating only the local energy eigenvalues would be incorrect. Warm vectors
are transported by the full within-span rotation. All vacuum tables are recomputed.

The only two calibration equations are E_sigma-E0=x and E_chi-E0=3-x. The first
excited field-even scalar gap is the thermal candidate. Normalized local parameters
are g=192 exp(3 theta1)/x^2 and A=4 exp(2theta1) theta0/x. Use safeguarded Newton with
original raw 3D seeds, then adjacent-cutoff continuation. No desired thermal value
or endpoint benchmark enters. Root uniqueness and operator identity at strong
coupling are not established just by a small calibration residual.

Accepted scalar results request five roots in each field sector; dense eigh is
used for dimension<=650, otherwise eigsh/ARPACK. Tuning tolerance3e-11, eig_tol1e-12,
independent residual1e-8, and orthogonality1e-9 are unchanged from the current 2D
port. The delivered spectra have substantially smaller achieved residuals.

## 6. Independent weak-coupling checks

At x=3/4, h_n=(3/4)_n(1/4)_n/[(3/2)_n n!]. A separate exact rational formula is

    C2(L)=34/243 + sum_(n=1)^(L/2) h_n [4/(9(4n+3))
                 +4/(81(4n-3))+2/(81(2n+3))+1/(9n)].

Direct finite-matrix perturbation and this expression agree for L=2,4,6,8,10.
The known comparison is C2(infinity)=(2-pi+4 log2)/9. This release checks that
normalization and the direct quadratic weak limit; it does not determine a new C4.
The primary window difference begins at epsilon^4 because its order-epsilon^2
operator vanishes on the zero-bath primary seeds. Independent eps=.04,.02,.01
spectra test the expected approximately sixteenfold decrease when epsilon halves.
No coefficient is extracted by fitting those finite-epsilon values.

## 7. Rotational diagnostics and limits of interpretation

The free P_z raises total level by one. It connects one-particle species to
(n,l+1,m) with coefficient

    (2n+2l+3) sqrt(((l+1)^2-m^2)/(4(l+1)^2-1)) u_(n,l+1)/u_(n,l),

and to (n+1,l-1,m), l>0, with coefficient

    2(n+1) sqrt((l^2-m^2)/(4l^2-1)) u_(n+1,l-1)/u_(n,l).

The zero-oscillator creation of (0,1,0) has coefficient sqrt(2x), multiplied by
the directly projected physical local annihilator. Highest-weight angular bases
are lowered to M=0 before applying this component; omitting that rotation would
compare inequivalent magnetic representations.

We form projected P_z images, spin-two P_zP_z images, and the scalar trace
3 Pi_(J0) P_z Pi_(J1) P_z. The latter factor of three follows from scalar rotational
invariance. Independent free tests give ||P_z O||^2=2 Delta_O and
||P^2 O||^2=24 Delta_O(Delta_O-1/2).

Interacting eigenstates are assigned by largest overlap among six tested roots.
The quoted overlap is normalized to the full image in the specified projected
target sector, not just the captured six roots. A probability below0.5 is flagged
ambiguous. A trace selecting its own primary is marked as a failed assignment,
not evidence of a physical descendant with spacing error -2. These are free-charge
ancestry diagnostics, not a construction of exact interacting conformal charges.
A smooth trajectory and small tuning residual do not certify a full family.

## 8. External benchmarks and attribution

- Original project 3D raw source and saved spectra: `reference/d3original/`.
- Optimized 2D source/window/density/HPC templates: `reference/d2/`.
- Particle-block spherical vertex source and original translation derivation:
  selected files in `reference/`; provenance gives archive/member hashes.
- Behan, Rastelli, Rychkov, Zan, *A scaling theory for the long-range to short-range
  crossover and an infrared duality*, arXiv:1703.05325. Protected dimensions,
  crossover interpretation, and distinction from local stress-tensor conservation.
- Chang et al., *Bootstrapping the 3d Ising Stress Tensor*, arXiv:2411.15300,
  JHEP03(2025)136: x_SR=0.518148806(24), Delta_E,SR=1.41262528(29).

The Ising values are published numerical estimates and independent plot references,
not exact constants or calibration inputs. The free endpoint (.75,1.5) follows
from the Gaussian dimensions. The finite-x=.5182 datum is not literally an endpoint
measurement. Nothing in the present cutoff sequence supplies a physical error bar
of the size of its eigensolver or local-basis residual.
