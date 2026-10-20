# K_d at generic d: workflow result (2026-10-03)

> **Superseded in part (joint review, 3 October 2026).** This file records the workflow result of 01:20 and is kept
> as such. The current statements and their status are in `note_fragment/K_d_fragment.tex` and
> `note_fragment/STATUS.md`; the product top-mode theorem is `gdr:topG` of `LRI_C5_general_d/general_d.tex`
> (foundation Theorem 6(a)-(c); its wheel case gdr:topless is 6(d)), independently reviewed (`review/lemmaG-proof`, ACCEPT; probe `review/lemmaG-numeric`, PASS).
> In particular:
> - c_{+-2} = 0 for the R family is proved on H_q (Re tau > max(0, 2q-1, 1/2-2q)) at every 0 < d < 4, as the case
>   r = 3 of gdr:topG; on the jet circle around tau = 0, which lies outside H_q, it rests on hypothesis (H) of
>   gdk:continuation. The S one-mode property (on H_q) and c_{3,2} = c_{4,3} = 0 for the wheels (at b = d/2,
>   for 2/r < d < 4, as stated in gdr:top) are cases of the same theorem.
> - The d = 3 half-shift determinant form of c_0 (section 2, "Specializations") is numerical only: its derivation is
>   not written out, and it is checked at six points to 1.1e-24.
> - Open issues 1 and 2 of section 6 are resolved, up to the independent review of the sharpness of H_q and of the
>   explicit constants of `note_fragment/growth/PROOF.md`.
> - Several items marked **[exact]** below hold only under the inputs of `gdk:conventions`, (M) (the mixed trace
>   J_{2tau} = C(tau) <t^2 R_tau>_d) and (J) (the path form of gs:Bjet). The low-order data, F_2 = <t^2 E_2>_d and the r_3
>   formula of section 2 (gdk:rLow, gdk:E2, gdk:Kr3) are exact given (M) and (J), and F_2 also needs [tau^2] under the
>   trace; K_d = -AU/4 + [tau^2](C F)/4 (gdk:Ktau) needs (M) alone; the two Barnes identities of section 3
>   (gdk:MBidentities) hold given (J); the position-space formula for K_d (gdk:KMB) uses none of (M), (J), (H).

The nonprimitive master K_d (gs:Kdefinition, gs:Kspectral) was studied for 0 < d < 4, with q = d/4.
Notation: A = psi(2q)+psi(1)-2psi(q), U = psi_2(q), R = psi_1(2q)-psi_1(1), c* = psi(1)+psi(2q), C(tau) = Gamma(2q)Gamma(tau)/Gamma(2q-tau).
F(tau) = <t_l^2 (R_tau - S_tau)>_d = sum_k F_k tau^k, and K_d = -AU/4 + (F_3 + c* F_2)/4.
Labels: **[exact]** means an exact derivation that three verifiers did not refute. **[num]** means a numerical identity, not proved. **[neg]** means a negative result.
Agent outputs are in `K_general/{S_part,R_part,position_space,refcheck}/`. Verifier outputs are in the `*_verify*`, `refverify` and `refcheck_adv*` folders.

## 0. Reference file (the C62d request)

- `references/reference_values.json` exists with status COMPLETE (md5 7396e569fbfdf83c5c5fe3a0ea59a86f, 2026-10-02 21:56), and `REFERENCES_PATH.txt` points to it.
- It holds P4, 3Q, L, Z, K and dW3/db at d = 0.8, 1.25, 1.5, 2.5 and 2.75. It also holds off-diagonal W3 and W4 at b = d/2 +- 0.05; at d = 0.8 the offset is +- 0.03.
- Every printed digit of P4, 3Q, L, Z and K is correct (44-45 significant digits, 25 of 25 entries; see section 3).
- **Flag:** the off-diagonal W3 and W4 strings print 55-56 digits but are correct to only 50-56; the first wrong digit is at position 51-56. Use only their first 50 digits.
- The `digits` field sometimes exceeds the number of printed digits (for example P4(0.8) prints 45 digits and claims 48). This is harmless, because the printed digits are right.
- Higher-precision values are available. `K_general/refcheck/refcheck_values.json` has 55 digits for every entry, including the off-diagonal ones. `K_general/position_space/K_d_values_mb_D100.json` has K only, to 100 digits at d = 0.8, 1, 1.25, 1.5, 2, 2.5, 2.75 and 3.

## 1. S part: elementary at every d

- **[exact]** For max(0, 1/2-2q) < Re tau < 2q (and by continuation elsewhere):
  `<t_l^2 S_tau>_d = Gamma(2q) Gamma(tau) Gamma(q-tau/2)^4 / (Gamma(2q-tau) Gamma(q+tau/2)^4)`, so C<t^2 S_tau>_d = C^2 X_d^2 with X_d = [Gamma(q-tau/2)/Gamma(q+tau/2)]^2.
  - Proof: t_l^2 S_tau = [Gamma(q-tau/2)/Gamma(q+tau/2)]^2 t_{l,d/2-tau}^2, combined with Parseval, <t_{l,b}^2>_d = B_d(d-b, 2b).
  - This generalizes C62d's d = 2 identity. No Dixon, Dougall or Thomae evaluation is needed.
  - Checks: 36 spectral points agree to 1e-38..1e-41, and 18 independent lattice-sum points agree to 1e-37..1e-40.
  - Laurent form: <t^2 S> = tau^-1 exp(sum_k eps_k tau^k), with eps_k = [psi_{k-1}(1) - (-1)^k psi_{k-1}(2q) - [k odd] 2^{3-k} psi_{k-1}(q)]/k!.
- **[exact]** Per-spin two-mode periodization, valid for 4kappa > 1 with kappa = q + tau/2 and a0 = q/2 - tau/4:
  `I_l = [sin^2(pi a0) f+ - cos^2(pi a0) f-] / (2 pi sin 2pi a0)`.
  Here f+ and f- are the sums of g_l^2 over the real lattices l/2+Z and (l+1)/2+Z, so the Barnes integral becomes real-axis lattice sums.
  - One of three verifiers refuted this claim. The synthesizer rechecked it independently with controlled nu-tails and lattice tails (`scratchpad/twomode2.py`, not in the project tree).
  - The recheck agrees to 1e-21..1e-28 at d = 1.25, 1.5, 2.5 (l = 0, 1, 2). At d = 0.8 the agreement is 1e-11..1e-13, limited by the nu^-1.3 integral tail.
- **[exact]** At d = 2 the lattice sums factorize into squares of Dougall 2H2 sums. This reproduces C X^2 and makes the spin-summed periodization one-mode, which is the content of C62d's one-mode/Gauss lemma.
- **[num]** At generic d the spin-summed S periodization is still one-mode (c1 = 0), with Xi = pi sin^3(pi mu) W/(2 cos pi mu), mu = q - tau/2.
  - It is exact to 40 digits at d = 1 and holds to 1e-17..1e-26 elsewhere.
  - An equivalent residue-lattice identity is in `S_part/`.
- **[neg]** At q != 1/2 the spin-summed S samples do not factorize into single 2H2 or 2F1 values.

## 2. R part and the structure of K_d

- **[exact]** Lattice factorization: f_l(a_l+n+t) = Gamma(2q)^2 Phi_t(l+n) Psi_t(n). It is one Gamma ratio on two lattices offset by 1 - d/2, with Toeplitz weight d_{m-n}, where sum_l d_l z^l = (1+z)(1-z)^{1-4q}.
  - The half-shift closes only when 2(1-d/2) is an integer, that is at d = 1, 2, 3.
  - **[neg]** At generic d there is therefore no half-shift factorization.
- **[exact]** Finite-mode theorem:
  - Xi_R = D_R S_R, with D_R = sin^2(pi t) sin^3(pi(t+q)) sin(pi(t-q+tau)), is entire and 1-periodic with modes |k| <= 2.
  - <t^2 R_tau>_d = sum_k rho_k c_k, with explicit rho_k, which gives a five-node rule.
  - Each sample is D_R Gamma(2q)^2 [P_R H_R + P_M H_M + P_L H_L]: three two-variable Horn blocks at argument (1,1).
  - The tau-continuation splits each block into a two-variable remainder, which converges near tau = 0 for all 0 < q < 1, plus one-variable remainders plus closed Gamma kernels G, S, T, V.
  - The only pole at tau = 0 is Gamma(2tau). Explicit arrays are in `R_part/R_part_arrays.json`.
  - One caveat: the growth estimate is only sketched, modelled on fp:wheelGrowth.
- **[exact]** Specializations of the generic formula:
  - d = 2: it gives J_{2tau} = pi^2[F(tau)^2 + F(1-tau)^2].
  - d = 1: it gives eq:KproofTwoFunctions.
  - d = 3: Xi(t) + Xi(t+1/2) is a constant 2x2 determinant, and c_{+-1} form the two-variable residual sector. This is the R analogue of td:projectedAnswer. [Correction, joint review: the derivation is not written out; this item is numerical only, checked at six points to 1.1e-24.]
- **[exact]** Low-order Laurent data: since F = O(tau^2), R_{-1} = 1, R_0 = s_0 = psi(1)+psi(2q)-4psi(q), and R_1 = s_1 = s_0^2/2 - R/2.
- **[exact]** By-product: F_2 = <t^2 E_2>_d = (3/2) psi_2(d/4). Numerically, F_2 - 3U/2 is 4e-35..1e-44 in the R_part runs (the size tracks each run's K accuracy).
- **Consequence** (exact given the two items above): the only non-elementary number in K_d is r_3 = [tau^3]<t^2 R_tau>_d, through
  `K_d = (U/8) [psi(1) + psi(2q) + 4 psi(q)] + (r_3 - s_3)/4`, where s_3 = [tau^3] of the S closed form.
  - The synthesizer checked this against the 100-digit MB values at all 8 d. It holds to 1e-32..1e-35, the precision of the R_part Laurent tables.
  - The synthesizer also checked that R_part's r_0 and r_1 equal S_part's exact s_0 and s_1 to 1e-33.
- **[num]** Top modes vanish after the spin sum:
  - c_{+-2} = 0 for the R family at every d tested, so a three-node rule is exact. [Correction, joint review: now proved on H_q at every 0 < d < 4, the case r = 3 of gdr:topG; on the jet circle it rests on hypothesis (H). When this file was written it was proved only at d = 1, 2, 3.]
  - The same loss of the top mode occurs for the balanced wheels r = 2, 3, 4 (c_{3,2} = 0 and c_{4,3} = 0 at d = 0.8 to 3).
  - The cancellation disappears if d_l is taken at the wrong dimension.
  - So fp:finiteFourier is not sharp at generic d. The note's td remark that c_{3,2} = 0 and c_{4,3} = 0 are "special to three dimensions" appears to be wrong; the note was not edited.

## 3. Position-space route

- **[exact]** On the K-path, J_t is a 2-fold Mellin-Barnes integral (star plus bubble). Barnes' first lemma splits off J_pole = Gamma(2q)Gamma(t/2)^2 Gamma(q-t/2)^4/(Gamma(q)^4 Gamma(2q-t)). Then
  `K_d = A^2 s/2 + A(psi_2(2q)-psi_2(q))/2 - R s/4 + s^2/8 + (2psi_3(q) - 7psi_3(2q))/48 + I_d`,
  with s = 2psi_1(q) - psi_1(2q). I_d is a single 2-fold Barnes integral with psi-weights; the formula is in `position_space/position_space_summary.json`.
  - As by-products there are two exact Barnes-integral identities, the [t^0] and [t^1] coefficients.
- **[exact]** General-d kite: it is a sum of four Kampe de Feriet F^{2:2;2}_{2:1;1}(1,1) series plus two Horn double series.
  - This matches the d = 2 KLT formula to 22 digits.
  - On the K-path there is an explicit confluent form, S_I + S_II, valid for d < 2 + 2 Re t.
- **[num]** The mixed-trace step J_{2tau} = C^2 X_d^2 + C F(tau) holds pointwise at complex tau for all five non-integer d, to 4e-32. It was previously proved only at d = 2.
- **[num]** gs:Bjet holds at non-integer d: at d = 1.25 only the z1 z2 coefficient (= K) survives, and the other 14 coefficients are below 3e-12.
- **[neg]** On the K-path, all 60 MB orientations contain a squared Gamma, so there is no derivative-free residue expansion of J_t in this framework. K_d sits in a finite parameter-derivative closure of two-variable hypergeometric functions at unit argument.

## 4. Cross-check of reference values (relative differences)

Five K routes are used:
- **ref:** C63d spectral tau-circle, `hp_general_d.py`.
- **A:** refcheck spectral with Abel-Plana spin tail, dps 60.
- **B:** refcheck residue series, gc:Kcancelled.
- **H:** R_part Horn-lattice tau-jet.
- **MB:** position-space Arb, 100 digits.

All columns are compared against MB, except the exact column at d = 1, 2, 3.

| d | K (MB, 40 digits) | ref | A (= B to <1e-53) | H | exact |
|---|---|---|---|---|---|
| 0.8 | 92.37277023992277163264539189903637646056 | 3.3e-46 | 8.2e-57 | 8.5e-47 | - |
| 1 | 39.33156912825903905750318715159786152304 | - | - | 4.8e-37 | 5.2e-101 |
| 1.25 | 17.20334572992168832708572010654874727422 | 1.0e-46 | 2.4e-55 | 1.0e-41 | - |
| 1.5 | 9.018297401594820547084743104679319203623 | 8.5e-47 | 2.1e-56 | 9.6e-46 | - |
| 2 | 3.518109138590252241649090170307739522623 | - | - | 2.0e-47 | 1.5e-100 |
| 2.5 | 1.840501295428588030730181860272315031185 | 2.2e-45 | 1.2e-55 | 5.4e-44 | - |
| 2.75 | 1.429249188660312000099175536883865557292 | 2.5e-45 | 8.3e-56 | 6.0e-44 | - |
| 3 | 1.148594649527179336556646310810673187634 | - | - | 1.4e-43 | 3.6e-100 (vs 430-digit K3) |

Other entries, ref against A and B (`refverify/compare_output.txt`):
- P4, 3Q, L and Z: maximum relative difference 3.8e-45, every entry within +-0.5 ulp of its last printed digit. A and B agree to <1e-57.
- dW3/db at b = d/2 vanishes on both sides: the reference gives 1e-47..1e-50, and A gives 1e-59.
- The S_part mode route independently confirms 3Q and P4 at d = 1.5 and 2.5, and all 16 off-diagonal W3/W4 entries, to 1e-16..1e-22.

Earlier interim values were wrong and have been superseded:
- K(1.25) = 17.2251... (relative error 1.3e-3).
- K(1.5) (relative error 3.8e-16).
- P4(0.8) had 16 good digits, not the 25 claimed.
- Q(0.8) had 8 good digits.

The cause was the slow per-spin nu-decay nu^{-4q-2Re tau} when the analytic nu-tail is off (`HPG_NUTAIL=0`).

## 5. Negative results (summary)

- No half-shift factorization at generic d (section 2).
- The S samples do not factorize at q != 1/2, but this is irrelevant because S is elementary by Parseval.
- On the K-path there is no derivative-free MB residue expansion (60 of 60 orientations).
- The literal gs:Kseries bracket fails numerically at d < 1 (relative error 0.96 at d = 0.8); use gc:Kcancelled. [Correction, joint-review repair round 1: 0.96 is |K_cancelled - K_literal|/|K_literal|. The literal bracket gives 70.3 (40 digits) and 2539.5 (60 digits) in place of K = 92.37, and d = 0.8 is the only d < 1 tested; the cause is precision loss at radial indices beyond about 1e80 at 60 digits and 1e60 at 40 digits (`note_fragment/test_build_joint/check_kbracket_d08_huge.log`, sections 3 and 5).]
- No reduction of K_d to known constants was attempted at generic d. The d = 3 negative result (`LRI_C5_d3/WORKFLOW_RESULT.md`) stands.

## 6. Open issues

1. Prove the vanishing of the spin-summed top modes at generic d. This covers the S one-mode property and its residue-lattice identity, c_{+-2} = 0 for R, and the wheels r = 2, 3, 4. For r = 2 it is a Dougall-type bilateral double sum. The r = 7 primitive is untested. [Resolved: gdr:topG on H_q, reviewed; on the jet circle given (H). The r = 7 primitive is not covered.]
2. Write out the growth estimate for the R finite-mode theorem. [Done: `note_fragment/growth/PROOF.md`; parts (a) (sufficiency), (b) and (c) are the case r = 3 of Step 0 of the reviewed proof of gdr:topG; the sharpness of H_q and the explicit constants are not independently reviewed.]
3. Give explicit polygamma-weighted two-variable sums for r_3. The current r_3 comes from a numerical Cauchy circle. A dedicated d = 2 form is also missing (the individual pieces have removable singularities there).
4. The confluent K-path series for d >= 2 at small t (the confluent limit of the star-at-y six-family formula) has not been written.
5. Try PSLQ on r_3, or K_d, at generic d, using the 100-digit MB values. Respect n*log10(maxcoeff) <= digits - 10 and confirm at a second precision.
6. Coverage gaps:
   - d < 0.8 is untested.
   - The MB numerics have no rigorous enclosure: two contours agree to about 8e-55, and the result is exact at d = 1, 2, 3 to about 1e-100.
7. Producer action, outside this workflow's write scope: truncate the off-diagonal W3/W4 strings in `references/reference_values.json` to 50 digits, or replace them with the 55-digit refcheck values.
