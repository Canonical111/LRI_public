# Two-dimensional dressed HT: full-vacuum window and optimized local basis

## Main result and scope

The agreed 1D numerical setup has been ported to the actual 2D circle spectrum and run at fixed Delta_sigma. It retains the total bath-level regulator and adds the full self-consistent scalar vacuum window. The optimized local basis is trained only on vacuum/spin/shadow and lower-cutoff vacua. There is no selected-tail solver, individual-mode parent, fitted energy normalization, kinetic-moment counterterm, or angular buffer.

This release contains 66 completed finite-cutoff numerical solution records, including 50 main-grid runs, four initial probes, and selected larger-bath/local checks. One alternate nonlinear solution is retained separately and is not a curve point. Eight additional small-epsilon solves constitute the separate weak-order test. Some larger-bath local checks contain scalar spectra only, explicitly recorded in their requested configuration.

**The port and local compression pass independent numerical tests. The window substantially changes the angular discrepancies and the near-endpoint cutoff sequence, but does not establish a controlled physical continuum curve or complete conformal families.**

## 1. The 2D Hamiltonian and regulator

Use x=Delta_sigma=(2-s)/2, epsilon=2s-2=2-4x. The branch studied is 1/8<x<1/2. The field on the circle has modes (a,b), energies x+a+b, angular momenta a-b, and squared amplitudes (x)_a(x)_b/(a!b!). The interaction is r average(:phi^2:) + (g/12) average(:phi^4:), with the original Gaussian normal ordering. Only E_sigma-E0=x and E_chi-E0=2-x are tuned. Delta_E=E_even,1-E0 is an output.

Positive-mode states obey N=sum(a+b)n_ab<=L with no extra particle cap. The (0,0) oscillator is represented separately. J=0 reflection-even sectors supply the primary spectrum; J=1,2 sectors supply untuned checks. Intermediate angular momenta are retained inside complete vertices.

For even L, the new window is D_L(N)=Ev(L)-Ev(even_floor(L-N)), identity in local space, with D_L(0)=0. Every Ev is the vacuum of the same corrected model, at the same x,r,g and local basis. Scalar N is even because N-J is even. Thus the even-floor convention is derived for the circle rather than assumed from 1D. The fixed point is solved directly at finite x, not by a fifth-order epsilon polynomial. The derivative F'(Ev)=-p_bath0 and all lower-vacuum derivatives enter the Newton equations.

## 2. Direct curve results

Main teachers have L=6, 24 local functions per parity and auxiliary dimension 192. Their density artifacts are transferred to L=8,10 with 16 retained functions. At L=10, 12-function runs independently check nested local convergence. The raw comparison is a fresh 24/192 calculation at L=10. Selected L=12 points use the same L=6-trained 16-function artifacts.

| x | Raw L=10 | Window L=6 | Window L=8 | Window L=10 | Window L=12 |
|---:|---:|---:|---:|---:|---:|
| 0.126 | 1.022361570 | 1.033828473 | 1.024801167 | 1.019025128 | 1.009449834 |
| 0.15 | 1.006730630 | 1.019232027 | 1.016608085 | 1.015090009 | 1.011709670 |
| 0.2 | 0.983172704 | 0.989258862 | 0.991445111 | 0.993162186 | not run |
| 0.25 | 0.966906936 | 0.967533014 | 0.970131598 | 0.972069148 | 0.973427878 |
| 0.3 | 0.957229975 | 0.955991841 | 0.957749014 | 0.959059163 | not run |
| 0.35 | 0.955126932 | 0.954207841 | 0.954973325 | 0.955557815 | not run |
| 0.4 | 0.961194172 | 0.960986715 | 0.961140645 | 0.961257422 | 0.961359826 |
| 0.45 | 0.975239207 | 0.975193418 | 0.975225899 | 0.975243461 | not run |
| 0.475 | 0.985791058 | 0.985761986 | 0.985780506 | 0.985791310 | not run |
| 0.495 | 0.996779554 | 0.996777149 | 0.996778617 | 0.996779554 | 0.996780203 |

Digits identify finite-dimensional solutions. Cutoffs are not continuum error bars. At x=.126 the raw L=10 value is 1.022361570, while the continued window L=12 value is about 1.009449834. The limiting SRI benchmark is 1 at x=1/8, not an exact target at x=.126. The window L=10->12 shift is about -0.00958, so apparent endpoint proximity does not imply precision. Away from the endpoint the correction can raise the curve; it is not selected by proximity to an assumed thermal answer.

## 3. Independent descendant diagnostics

Define W_A=Delta_AO-Delta_O-1. These are finite-x gaps, not perturbative coefficients. The following comparison uses the SAME L=10 cutoff and window table in every J sector; there is no angular buffer.

| x | Family | Raw W_A | Window W_A | Window free-generator overlap probability |
|---:|---|---:|---:|---:|
| 0.126 | sigma | 0.415385749 | -0.070938964 | 0.1600 |
| 0.126 | thermal | 0.297441709 | -0.117402149 | 0.2759 |
| 0.126 | chi | 0.394021378 | 0.024810015 | 0.4531 |
| 0.25 | sigma | 0.222724353 | -0.004081942 | 0.2661 |
| 0.25 | thermal | 0.219852123 | -0.002043198 | 0.4386 |
| 0.25 | chi | 0.280420800 | 0.064472669 | 0.5516 |
| 0.3 | sigma | 0.154222442 | 0.006930778 | 0.3341 |
| 0.3 | thermal | 0.169632234 | 0.024474439 | 0.5046 |
| 0.3 | chi | 0.213930791 | 0.070750531 | 0.5978 |
| 0.4 | sigma | 0.038872863 | 0.008374422 | 0.6185 |
| 0.4 | thermal | 0.057005822 | 0.026863937 | 0.7162 |
| 0.4 | chi | 0.074537046 | 0.044561591 | 0.7591 |
| 0.495 | sigma | 0.000044005 | 0.000019710 | 0.9991 |
| 0.495 | thermal | 0.000106534 | 0.000082240 | 0.9989 |
| 0.495 | chi | 0.000199500 | 0.000175207 | 0.9986 |

**The discrepancies are reduced substantially in many cases, but they are not eliminated and need not decrease with cutoff.** Strong-coupling free-translation overlaps can be below 0.5. These entries are flagged ambiguous in the CSVs and are not verified conformal descendants. The first-angular comparison largely reproduces the previously used energy-rank candidates, but the new overlap record exposes the uncertainty.

The main runs also evaluate A^2 and BA candidates. For several strong-coupling BA images the largest low-root overlap is the original primary itself; the flagged W=-2 records are FAILED identifications, not physical negative-energy descendants. All such records remain in all_ward_candidates.csv. No full interacting charge construction is claimed.

## 4. Local-basis convergence and transfer

The density selects 12/16/20 functions separately in each local parity. The thermal state never enters the density. Every transferred solve recomputes all windows and retunes both gaps. Independent references use the original moving local-energy basis with 32 states and auxiliary dimension 256.

| x | L | Comparison | Thermal-gap difference | Largest common scalar-gap difference |
|---:|---:|---|---:|---:|
| 0.126 | 10 | transferred density16 versus independent moving32/256 | +3.686e-12 | 7.431e-12 |
| 0.126 | 12 | density16 versus window_L12_z20_x0.126.json | +1.519e-13 | 1.499e-12 |
| 0.126 | 12 | density16 versus refine_L12_z32_x0.126.json | -5.089e-13 | 1.786e-12 |
| 0.25 | 12 | density16 versus window_L12_z20_x0.250.json | +3.175e-14 | 5.222e-13 |
| 0.3 | 10 | transferred density16 versus independent moving32/256 | -8.331e-12 | 1.910e-11 |
| 0.495 | 10 | transferred density16 versus independent moving32/256 | +1.249e-13 | 1.474e-13 |

The agreement is relative to finite references, not to the continuum. A small discarded target-density weight alone is not accepted as an error bound. No repeated end-to-end performance benchmark or target-cluster speedup is claimed. The auxiliary/local and bath limits remain independent.

## 5. A nonlinear branch warning

An L=12, x=.15 solve initialized directly from the L=6 teacher converged to an alternate numerical solution with Delta_E=0.4698047524, r=206.0328315 and g=347.6758580. Its primary residual was small. Using the adjacent-cutoff L=10 solution instead gave Delta_E=1.0117096701 on the continuous branch. The alternate result is preserved as alternate_L12_x0.150.json, but is excluded from curve.csv; that choice uses continuation, not a fitted thermal value. It was identified after observing the initial result, not by a pre-registered selection rule. Small residuals of the two calibration equations alone are therefore insufficient to select the intended trajectory.

At the alternate parameters, an independent moving 32/256 local-space evaluation (without retuning) has primary residuals [-9.353370855613719e-11, -1.6405796721130628e-09] and thermal gap 0.469804752295. This check must be interpreted before assigning that branch a physical meaning.

A stop request occurred just as the original L=12 refinement finished and started another child. The completed .15 result is retained as the alternate above; the orphaned unseeded .126 job was terminated. The published .126 file is verified to belong to the separately seeded first-angular-only continuation. The attempt journal records this scheduling issue; no incomplete output enters the tables.

## 6. Independent implementation checks

Sixteen numerical tests check original versus projected circle vertices, explicit Fourier averaging, both tensor and ladder actions, Hermiticity, Gaussian normal ordering, raw spectra, dense self-consistent vacuum roots, moving/fixed-density Jacobians, free-window zero, and invalid configuration rejection. The separate saved-output audit checks all completed records, every window-table identity, and embedded basis provenance.

* Maximum replay difference in the 10 fresh raw L=10 thermal gaps: 1.297e-13.
* Largest primary tuning residual in the saved direct runs: 1.963e-11.
* Largest scalar eigenvector residual: 7.442e-12.
* Largest vacuum fixed-point residual: 2.190e-12.

These are observed numerical discrepancies, not physical errors. The optimized fixed-span Jacobian is checked against complete spectral finite differences. The working window tolerance is 1e-12 with an absolute acceptance ceiling 1e-11; it is not relaxed on difficult points.

The weak-order study calculates raw/window energies at epsilon=.04,.02,.01,.005. Their differences approximately divide by 16 when epsilon is halved, as expected because the scalar window first affects zero-bath primary energies at fourth order. No polynomial fit extracts any coefficient. This is not a new C4 verification; the previous C2/C3 benchmarks remain separate.

## Assessment

The agreed setup has been genuinely implemented and tested in 2D, including the density basis and full window recomputation. It provides a better numerical baseline and substantially alters several untuned spacings. Its remaining strong-coupling discrepancies, seed-dependent roots and cutoff sensitivity prevent a precision continuum claim. The next tests should converge L and local resolution together, track the intended branch, and check the thermal family independently. A scalar vacuum window must not be advertised as the earlier complete cubic factorizing-parent matching prescription.

All files required for these calculations are included. This is not a drop-in symmetry-cluster production release; the 1D integration archive was not overwritten.
