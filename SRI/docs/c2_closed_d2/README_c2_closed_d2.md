# c2_closed_d2: the crossover coefficient c_2 in d = 2

Near the short-range end of the two-dimensional chain, s_* = 7/4,

    Delta_eps = 1 + c_2 delta^2 + O(delta^3),    delta = (7/4 - s)/2 = Delta_sigma - 1/8,

with c_1 = 0 (Behan, Rastelli, Rychkov, Zan 2017). This package holds the closed form of c_2 and an independent
Monte Carlo check:

- **Closed form** (OpenAI GPT-6 astra, via ChatGPT): c_2 in one Gamma ratio R_Gamma = Gamma(1/4)/Gamma(3/4) and three
  absolutely convergent 4F3(1) values P, Q, T, **c_2 = -4.06627014813252155274...** (paper: Sec. 3.2, Table tab:sr,
  appendix "Crossover in two dimensions", label cf:sec:cr2; `\SRtwoCtwo` = -4.06627). Status: a formal perturbative
  result in a critically tuned analytic minimal-subtraction prescription; a regulator-uniform bound on the remainder
  of the nested subtractions is not proved (stated by the study itself).
- **End-to-end Monte Carlo** (Claude Code review, 2026-10-08): an 8-dimensional Monte Carlo of the full regulated
  integral over the four insertion points, with exact 2D Ising correlators from bosonization and no use of the
  study's reductions; **c_2 = -4.075 +- 0.019** (`\SRtwoCtwoMC`), 0.47 sigma from the closed form. It also tests the
  exchange-of-limits step the study leaves unproved, at the 0.5% level.

The cylinder-Hamiltonian value `\SRtwoCtwoHT` is in the sibling package `c2_cylinder_d2`.

| Path (in `SRI/code/c2_closed_d2/`) | What |
|---|---|
| `README.md` | the study's own README, edited on 17 October 2026 so that its passages on the note and the builder point to the SRI note (re-pinned in `public/RE-PINNED.json`; everything else verbatim). Its 26-page note (`note/C2_final_method.{tex,pdf}`) is not shipped since 16 October 2026 (one note per direction): the derivation, regulator matching and checks are in the SRI note, Appendix E; `public/NOT_SHIPPED.txt` names the two files for the study's own manifest check |
| `code/lri_C2_three_4F3.py` | the final three-4F3 evaluation, the six-to-three identities, the Frobenius moment check, the rational telescoping certificates |
| `code/certificate_boundaries.py`, `analytic_bridge_checks.py`, `lri_C2_renormalization_checks.py`, `source_contact_checks.py`, `independent_c2_checks.py`, `convergence.py` | exact endpoint terms; differential, Landen and reflection certificates; connected kernel, Jacobians, Gaussian finite term, local OPE; source contacts; a separate implementation (Carlson periods, tail signs, direct contact quadrature); convergence of the half-interval evaluation |
| `code/reproduce.py`, `assemble_outputs.py`, `verify_package.py` | the eight-stage runner, the assembly of outputs/ (the note builder `build_note.py` is not shipped since 2026-10-17, with the note), the sha256 verifier of `MANIFEST.json` |
| `inputs/` | working precision and truncations (`calculation.json`), Ising CFT data, two archived reference outputs (comparison only) |
| `outputs/summary.json` | c_2 (pointer `/C2`, 72 digits) and every constant; **read live by Resummation** |
| `outputs/raw/`, `outputs/tables/`, `outputs/figures/`, receipts | the shipped run of 2026-10-08 (80 digits) |
| `mc/c2mc3.c`, `mc/integrand2.h`, `mc/summ.py` | the Monte Carlo (C, extended precision via libquadmath) and its batch-means summary |
| `mc/prod.sbatch`, `mc/prodC.sbatch`, `mc/alpha_e0.05_L16_k35.txt` | the production drivers and the pre-adapted channel weights of run A |
| `mc/run_{A,B,C}/out_<i>.txt` | per-chunk batch histograms: 64 + 64 + 14 chunks of 3e8 samples (4.26e10); A, B on symmetry, C on a personal desktop |
| `public.mk`, `public/` | test and replay tools (new, 2026-10-15): `c2lib.py`, `selftest_c2.py`, `replay_c2.py`, `mc_batch_check.py`, `mc_production_logs.json` (the lines summ.py printed in the production jobs), `mc_combined.json` (the recombination), `SNAPSHOT.sha256`; at publication `SCRUBBED.txt` lists the files whose private paths were replaced by placeholders (checked by presence) |

How the Monte Carlo becomes c_2 (rule of the review, reconstructed and checked by the replay): per configuration, the
batch-means estimate of Omega_4(0) = int_{Lambda > -15} R over S^7 (`summ.py`); the inverse-variance mean of the three
configurations, 66.34 +- 0.24 (chi^2 1.29 on 2 dof); J(0) = Omega_4/(2 pi); z_41 = pi J/16 + b_0 B_31 with
b_0 = 9 pi^2/(8 R_Gamma^2) and B_31 = pi^2 (12 - pi sqrt 3 - 9 log 3)/96 (Gaussian source); c_2 = -4 z_41/b_0^2. The
cut -15 is the deepest cut of summ.py's grid at which the quartic-source control slice is complete (samples have
Lambda > -16). The control: Omega_4(quartic) - Omega_4(Gaussian) = 16.185 +- 0.053 against 32 b_0 (B_Gauss - B_quartic)
= 16.150.

What is not established: a reduction of P, Q, T to Gamma values alone (none is claimed; PSLQ in the review found
none); the regulator-uniform remainder bound (numerical support from the Monte Carlo only). No published O(delta^2)
value exists in d = 2 to compare with.
