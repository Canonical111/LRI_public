# 3D long-range Ising: direct nonperturbative dressed-sphere calculation

## Result and interpretation

The S^2 generalized-free Hamiltonian has been implemented with its radial tower,
angular harmonics, and exact rotational sectors. This is not a relabeling of the
2D circle code's mode list.

There are **80 accepted primary scan points** at L=4,6,8,10,12,
and **8 local-resolution checks**, covering
**0.5182 <= x=Delta_sigma <= 0.7499**. The physical long-range interval
ends at x=3/4 on the free side and at the short-range spin dimension near
0.518148806 on the other side.

The plotted ordinate is a **raw finite product-cutoff thermal gap**. No
continuum fit or physical confidence band is supplied. The protected spin and
shadow gaps are tuning inputs, not independent validation data. The cutoff
curves look close over much of the interval, but independent descendants show
substantial errors and the short-range limit is not reproduced at these cutoffs.

## Directly computed curve

| x | L=4 | L=6 | L=8 | L=10 | L=12 |
|---:|---:|---:|---:|---:|---:|
| 0.7499 | 1.499933361239 | 1.499933361624 | 1.499933361823 | 1.499933361941 | 1.499933362018 |
| 0.749 | 1.499336109096 | 1.499336146242 | 1.499336165290 | 1.499336176539 | 1.499336183819 |
| 0.745 | 1.496734468815 | 1.496735258443 | 1.496735648578 | 1.496735871682 | 1.496736011980 |
| 0.74 | 1.493596999438 | 1.493599529851 | 1.493600711243 | 1.493601349046 | 1.493601727580 |
| 0.725 | 1.484852349790 | 1.484858643982 | 1.484860552161 | 1.484860822933 | 1.484860475058 |
| 0.7 | 1.471989789656 | 1.471976064382 | 1.471964000605 | 1.471951056429 | 1.471939792051 |
| 0.675 | 1.460512724468 | 1.460460532644 | 1.460438024790 | 1.460417265510 | 1.460407876229 |
| 0.65 | 1.449867282396 | 1.449843191228 | 1.449889671900 | 1.449930466243 | 1.449990769467 |
| 0.625 | 1.439863409052 | 1.440011251695 | 1.440249866560 | 1.440439531546 | 1.440635324728 |
| 0.6 | 1.430482407060 | 1.430930169957 | 1.431448956117 | 1.431834001570 | 1.432190937584 |
| 0.575 | 1.421641486854 | 1.422440503838 | 1.423273050463 | 1.423861753704 | 1.424380341098 |
| 0.55 | 1.413050175269 | 1.414197084065 | 1.415359347866 | 1.416152647142 | 1.416834567530 |
| 0.535 | 1.407780246802 | 1.409146733011 | 1.410532144107 | 1.411459102359 | 1.412249489486 |
| 0.525 | 1.404100076830 | 1.405638989991 | 1.407199060601 | 1.408227033856 | 1.409099675962 |
| 0.52 | 1.402180042732 | 1.403820726101 | 1.405480513396 | 1.406564540012 | 1.407482686524 |
| 0.5182 | 1.401472414006 | 1.403153294618 | 1.404851560770 | 1.405956895292 | 1.406892290979 |


Every entry comes from nonlinear coupling tuning and direct eigenvalue solves;
no thermal epsilon-series coefficient enters the tuning. The 12 decimal places
identify numerical finite-cutoff records, not physical accuracy. The actual
spin and shadow tuning targets are x and 3-x. The finite matrix dimensions are
recorded with every point.

At x=0.5182 the largest bath-cutoff result is 1.406892290979, whereas the
limiting 3D short-range benchmark is 1.41262528(29). The finite-x result and
limiting benchmark are not literally the same observable, but their visible
separation, together with the untuned tests below, prevents a claim of a
matched endpoint curve. A zero slope is NOT imposed in 3D; the 2D endpoint's
special vanishing leading correction must not be transferred to 3D.

## Spherical implementation

The modes are (n,ell,m), with free energies x+2n+ell and weights
(x)_(n+ell)(x-1/2)_n/[n!(3/2)_(n+ell)]. They follow from the Gegenbauer expansion
of the sphere covariance. All positive-level modes and Fock states with N<=L
are included. The zero mode is treated in its interacting local eigenbasis.

The scalar bath is constructed as the kernel of J_+ at M=0, resolving each
radial/angular species before taking the kernel. Selecting M=0 alone would
include higher-spin states and can misidentify the tuning levels. For L=12,
341,241 full bath states reduce to 1,285 rotational singlets. The two field
parity blocks total 51,400 states with 20 dressed local states per parity, and
71,960 states in the 28-state refinement.

The angular integral of every retained normal-ordered vertex is exact up to
floating-point evaluation: L+1 polar Gauss nodes and the fixed-M azimuthal
selection integrate all its polynomials. Intermediate ladders retain all
magnetic sectors. No perturbative particle cap is imposed in the direct solve.

## Numerical consistency

- Maximum primary tuning residual: 1.85e-11.
- Maximum primary eigenvector residual: 2.142e-12.
- Maximum primary orthogonality residual: 2.866e-14.
- Largest tested local-basis change: 8.586e-12.
- Spherical covariance / Gegenbauer identity: 1.11e-15.
- Angular quadrature refinement: 7.105e-15.
- Rotationally equivalent M=1 and M=0 vertex matrices: 8.882e-15.
- Original-coordinate normal ordering: 6.484e-13.
- Finite second-order matrix / independent rational shell sum: 4.996e-16.
- Moving-subspace response / full spectral finite difference:
  1.041e-09.

These are tests of the implemented finite problem, not errors on continuum CFT
data. Different numerical refinements should not be combined into an unjustified
statistical interval.

## Weak-coupling checks

The exact free endpoint (3/4,3/2) is reproduced. The primary tuning gives
r1=0, g1=1/3, and hence Delta_E=3/2-epsilon/6+....

The new independent rational shell calculation gives, for example,
C2(4)=0.1745140308508364, C2(8)=0.1781760975924427, and
C2(12)=0.1794017859181168. A convergent integral of the derived infinite shell
sum agrees with (2-pi+4 log 2)/9=0.1812217854055542..., the note's C2(3).
This numerical integral check does not constitute a proof of all higher orders.
The leading second-order omitted tail is -40/(243 sqrt(pi)) L^(-3/2).

Direct spectra at epsilon=.02,.01,.005,.002 agree with the independent
finite-cutoff second-order polynomial with a residual starting at epsilon^3.
For L=8, epsilon=.005, the difference is -3.67666e-8; at epsilon=.002 it is
-2.36691e-9. No fitting in epsilon is used to set C2(L) or tune a spectrum.
The exact rational formula and tests are in code/check_second_order.py and
code/second_order_analysis.py.

## Untuned rotational diagnostics

The same accepted scalar couplings were used in the J=1 and J=2 sectors, without
retuning. The following J=1 quantities should vanish for correctly identified
conformal descendants:

| x | spin spacing error, L=8 | spin spacing error, L=10 | thermal spacing error, L=10 |
|---:|---:|---:|---:|
| 0.745 | +0.000069331 | +0.000087971 | +0.000175139 |
| 0.7 | +0.010457882 | +0.013490491 | +0.022501705 |
| 0.65 | +0.051594650 | +0.064644207 | +0.092150590 |
| 0.6 | +0.112496365 | +0.134872919 | +0.172209710 |
| 0.55 | +0.175585183 | +0.203903519 | +0.239829453 |
| 0.5182 | +0.212626350 | +0.243105302 | +0.273531926 |

The candidate descendants are followed from weak coupling; a complete
strong-coupling OPE/operator identification has not been performed. The lowest
even J=2 candidate at x=.5182 is 3.275344953 at L=8 and 3.302477593 at L=10,
not close to its expected short-range stress-tensor limit of 3. These diagnostics
are substantially less satisfactory than the thermal curve alone suggests.
Increasing the cutoff does not make all these errors smaller in the tested
range. This is precisely why no physical error band is inferred from adjacent
thermal curves.

## Open work

The required next step is the high-state effective Hamiltonian appropriate to
this S^2 product regulator, including its spectator and disconnected
cancellations. The old total-energy cutoff's vacuum-window formula is not
silently applied. One should validate new counterterms on the weak shell
calculation and untuned angular sectors before a continuum fit. Larger cutoffs
and more parameter points alone will not establish that matching.

This release is a tested local research implementation. There is no MPI backend,
cluster performance claim, or Expanse validation receipt. A dense block nullspace
prototype at L=12 hit a development time limit; splitting the exact (n,ell)
species blocks removed that bottleneck, and the complete L=12 curve was then
calculated. No output from the incomplete development attempt is used.

## References and provenance

- Behan et al., arXiv:1703.03430: LR interval, protected dimensions, crossover.
- Chang et al., arXiv:2411.15300: numerical 3D short-range endpoint benchmark.
- The supplied long_range_ising_condensed.tex: weak-expansion comparison C2(3).
- The previous 2D direct package: local oscillator implementation and nonlinear
  spectral scaffold. All 3D sphere modes, rotational projections, and results
  are newly calculated here.

README.md gives dependencies, execution commands and output mapping.
docs/METHOD.md gives the formulas and cutoff definitions. The plot shows all
calculated cutoffs, with endpoint benchmarks separately marked.
