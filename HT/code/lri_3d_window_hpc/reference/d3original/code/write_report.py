from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def main():
    s=json.loads((ROOT/'results/SUMMARY.json').read_text());v=json.loads((ROOT/'results/validation.json').read_text());rv=json.loads((ROOT/'results/response_validation.json').read_text())
    table=(ROOT/'results/table.md').read_text()
    doc=f'''# 3D long-range Ising: direct nonperturbative dressed-sphere calculation

## Result and interpretation

The S^2 generalized-free Hamiltonian has been implemented with its radial tower,
angular harmonics, and exact rotational sectors. This is not a relabeling of the
2D circle code's mode list.

There are **{s['main_curve_points']} accepted primary scan points** at L=4,6,8,10,12,
and **{s['refinement_points']} local-resolution checks**, covering
**{s['x_min']} <= x=Delta_sigma <= {s['x_max']}**. The physical long-range interval
ends at x=3/4 on the free side and at the short-range spin dimension near
0.518148806 on the other side.

The plotted ordinate is a **raw finite product-cutoff thermal gap**. No
continuum fit or physical confidence band is supplied. The protected spin and
shadow gaps are tuning inputs, not independent validation data. The cutoff
curves look close over much of the interval, but independent descendants show
substantial errors and the short-range limit is not reproduced at these cutoffs.

## Directly computed curve

{table}

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

- Maximum primary tuning residual: {s['max_tuning_residual']:.4g}.
- Maximum primary eigenvector residual: {s['max_eigenvector_residual']:.4g}.
- Maximum primary orthogonality residual: {s['max_orthogonality_residual']:.4g}.
- Largest tested local-basis change: {s['max_local_refinement_change']:.4g}.
- Spherical covariance / Gegenbauer identity: {v['gegenbauer_addition_max_abs']:.4g}.
- Angular quadrature refinement: {v['sphere_quadrature_refinement_max_abs']:.4g}.
- Rotationally equivalent M=1 and M=0 vertex matrices: {v['rotation_M1_vs_M0_max_abs']:.4g}.
- Original-coordinate normal ordering: {v['original_coordinate_normal_ordering_max_abs']:.4g}.
- Finite second-order matrix / independent rational shell sum: {v['second_order_matrix_vs_rational_shell_max_abs']:.4g}.
- Moving-subspace response / full spectral finite difference:
  {max(z['response_vs_full_spectral_difference'] for z in rv['response']):.4g}.

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
'''
    a=json.loads((ROOT/'results/diagnostics_L8.json').read_text());b=json.loads((ROOT/'results/diagnostics_L10.json').read_text())
    for z in b:
        if z['spin']!=1:continue
        other=next(t for t in a if t['x']==z['x'] and t['spin']==1)
        doc+=f"| {z['x']} | {other['spin_descendant_error']:+.9f} | {z['spin_descendant_error']:+.9f} | {z['thermal_descendant_error']:+.9f} |\n"
    doc+='''
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
'''
    (ROOT/'REPORT.md').write_text(doc)
if __name__=='__main__':main()
