# K_d note fragment: status (session C63d, tag draft, 2026-10-03, after the joint-review fixes, repair rounds 1 and 2, and the final nits)

## The fragment

- File: `K_general/note_fragment/K_d_fragment.tex` (838 lines, md5 da91f60ae8bc38b916e5fbfe23d9ecdd; FINAL), after the
  joint-review fix round of 2026-10-03 (gdk items K1-K12 and decisions D1-D6 of
  `LRI_C5_general_d/review/joint/JOINT_REVIEW.md`) and its repair rounds 1 and 2 (sections "Repair round 2 ..." and
  "Repair round 1 of the joint-review fixes" below), and the final nits (section "Final nits" below).
  Earlier versions:
  - `test_build_joint/prenits/K_d_fragment.tex`: after repair round 2, before the final nits (837 lines, md5
    ee11e66505a2d46fbeebb84d7ddeda7c);
  - `test_build_joint/prerepair2/K_d_fragment_prerepair2.tex`: after repair round 1, before repair round 2 (829 lines,
    md5 bea3aac0de538d15978c714a3b0a3b86);
  - `K_d_fragment_prerepair1.tex`: after the joint-review fixes, before repair round 1 (820 lines, md5
    7e19278944c39d6a9f5de0116e6f571f);
  - `K_d_fragment_prejoint.tex`: before the joint-review fixes (901 lines, md5 b2467347be00a43dfe00c37a4f102ba0);
  - `K_d_fragment_prefix2.tex`: after fix round 1, before fix round 2 (876 lines, md5 976795045ca9fe5df9ecb46a922b55b7);
  - `K_d_fragment_prefix.tex`: before fix round 1 (md5 a02136aaca2d574b09f677049051c05a).
  The joint-review edits are made by `test_build_joint/apply_joint_fixes.py`, which reads the prejoint copy and asserts
  every anchor; the repair-round edits by `test_build_joint/apply_repair1_fixes.py` and
  `test_build_joint/apply_repair2_fixes.py`, which read the md5-checked pre-repair copies (prerepair1 next to the files,
  prerepair2 in `test_build_joint/prerepair2/`) of the fragment, `topmode/PROOF.md` and `../RESULT.md` and assert every
  anchor.
- Format: no preamble. It uses only the note's macros (`\KK \Cat \ii \Res`; the note's `\dd` is not used) and has
  no floats and no theorem environments, as in the note. It has 40 labels, all `gdk:*` (the joint review removed
  `gdk:lemmaG`, `gdk:laplace`, `gdk:exchange` and `gdk:kernel`).
- References: 40 note labels (all in the note's current `.aux`), 12 of C62d's `gdr:*` labels (gdr:kernel, gdr:D,
  gdr:periodization, gdr:top, gdr:BC, gdr:TG, gdr:topG, gdr:mixed, gdr:topless, gdr:kernelBalance, gdr:samples,
  gdr:C5reduced) and its own labels. Citations: `DLMFStirling` and `DLMFGaussUnity`, both in the note. The fragment
  therefore builds only together with `general_d.tex`.
- Layout (decision D1): the top level is `\section`. At the merge the file is pasted inline into the note, without its
  header comments, as Section 21, right after C62d's section `gdr:section` (Section 20) at the end of Part III and
  before `\part{Numerical sixth- to eighth-order coefficients}`. It is not `\input`.
  - **Fallback** (the former HOOK layout; only if D1 is not used): demote one level (`\section` to `\subsection`,
    `\subsection` to `\subsubsection`, "This section evaluates" to "This subsection evaluates") and insert the result
    at the comment `%% MERGE (layout D1 ...)` of `general_d.tex`, before `gdr:C5` inside `gdr:section` (general_d.tex
    no longer has a HOOK marker). That comment lists the extra steps of the fallback: item G-H of the joint review
    (section and equation ranges that skip the inserted subsection, the sentence that Section gdk:section has its own
    status list, the title "... of L_d, Z_d and K_d"), and restricting the S, C, D scope of gdr's Notation paragraph.
- Test build (`test_build_joint/`, run with `bash build_joint.sh`): the note's preamble (extracted from the note), the
  note's labels and citations from its current `.aux` (`note_labels_from_aux.tex`, regenerated from the `.aux` of the
  08:43 edition, note md5 08c37eb3), a snapshot of `general_d.tex` (`gdr_snapshot.tex`) and this fragment, as Sections
  20 and 21. `build_inputs.txt` records the md5 of every input.
  - Last build (10:05, repair round 2): `general_d.tex` snapshot md5 c0c688e9ab2fa6f2a73331cf160e3dda (C62d's file
    of 09:33, still equal to the live file at build time; C62d's gdr fix pass has not yet reported a final md5),
    fragment md5 ee11e665, note 08c37eb3 with `.aux` 3b277c76 (labels regenerated from that `.aux` by the build).
    latexmk/pdfLaTeX with SyncTeX, rc 0: 29 pages, `joint_preview.pdf` and `joint_preview.synctex.gz` verified.
    0 errors, 0 LaTeX warnings, 0 undefined references (all 12 `gdr:` labels cited here resolve against
    `general_d.tex`, all 11 `gdk:` labels cited by `general_d.tex` resolve here), 0 multiply defined labels,
    0 overfull and 0 underfull boxes. Labels: 583 note + 49 gdr + 40 gdk, disjoint (checked by comparison of the
    label lists). The 83 pdfTeX warnings are all hyperlink targets of the note (Sections 4-19 and its bibliography)
    that the preview does not typeset; none is a target of Section 20 or 21.
  - Builds of repair round 1 (09:47, fragment bea3aac0) and of the fix round (09:28, snapshot 2eb62278 of
    `general_d.tex`) were equally clean. The only change from 2eb62278 to c0c688e9 is in gdr:status ("covered the
    statement gdr:topG" became "covered the statements gdr:topG and gdr:topless"), consistent with the fragment.
  - **Final rebuild (after the final nits, see "Final nits" below).** C62d reported its gdr fix pass DONE and READY
    at md5 c0c688e9ab2fa6f2a73331cf160e3dda, the snapshot of the builds above, so that is the final `general_d.tex`.
    The rebuild with the final fragment is recorded under "Final nits".
  - The old single-fragment preview `test_build/gdk_preview.tex` no longer builds cleanly, since the fragment now
    cites `gdr:` labels; it is kept as a record of the pre-joint state.
- Dash audit (physics-notes-no-dashes scanner) on `K_d_fragment.tex`, `joint_preview.tex` and the gdr snapshot: no em
  dashes (rerun after repair round 2; the scanner takes only .tex files, and a grep finds no em dash in `STATUS.md`,
  `topmode/PROOF.md`, `../RESULT.md`).

## Structure

| section | label | content | status |
|---|---|---|---|
| (intro) | `gdk:section` | the three steps; what the section gives in place of the 386 Horn values of gc:finiteClosure; d <= 4/7 caveat | - |
| Conventions | `gdk:conventions` | g_l(s;b), N_b as in gdr:kernel (complex b: analytic continuation); full-Mellin-line trace; r_k, s_k, F, calX_d; inputs (M) mixed trace and (J) jet | inputs stated with their status |
| S family | `gdk:Sfamily` | closed form `gdk:Sclosed` with proof; Laurent (Bell) form `gdk:sk`; its Xi is constant (case r=2 of gdr:topG) | proved |
| Low orders | `gdk:lowOrders` | Delta(tau) = (3/2)U tau + AU tau^2 (`gdk:Delta`); r_{-1..2} (`gdk:rLow`); **K_d = (U/8)[psi(1)+psi(2q)+4psi(q)] + (r3 - s3)/4** (`gdk:Kr3`); <t^2 E2>_d = (3/2) psi_2(d/4) (`gdk:E2`) | Delta exact; Kr3, rLow exact given (M), (J); Ktau given (M); E2 also needs the [tau^2] interchange |
| R family | `gdk:Rfamily` | lattice form, product of three balanced kernels (`gdk:Rproduct`), periodization, growth theorem (H_q, eta_R) with proof outline | proved (growth/PROOF.md); (a) sufficiency, (b), (c) = case r=3 of gdr:topG Step 0, reviewed; sharpness of H_q and explicit constants unreviewed |
| Top modes | `gdk:topmode` | applies gdr:topG (case r=3, parameters via gdr:mixed) to get c_{+-2} = 0 (`gdk:threeModes`); remarks: per-factor balance, the two controls, pointer for the S family and the td correction | case r=3 of the independently reviewed gdr:topG |
| Three-node rule | `gdk:threeNode` | residue functional, rho_k (`gdk:rho`), three-node rule (`gdk:threeNodeRule`), three-block Horn sample (`gdk:sample`, `gdk:arrays`) | proved on H_q with Re tau < 3q/2, tau != q |
| Continuation | `gdk:continuation` | model subtraction, kernels G, S, tilde G, V (`gdk:kernels`), regularized blocks (`gdk:regularized`), hypothesis (H) with exceptional set sfE, K_d and r3 as sample jets (`gdk:Ksample`) | construction exact; (H) uniformity not written out |
| d = 1, 2, 3 | `gdk:special` | d=1 antiperiodicity and closed form of r3(1); d=2 square, gc:K2master, exact r3(2); d=3 half-shift determinant (summand written through tilde Phi), K3 (430 digits), r3(3) | see "Status of the content" |
| Position space | `gdk:positionSpace` | two-fold MB form (`gdk:MB`), K_d = K^Gamma + I_d (`gdk:KMB`), two Barnes identities (`gdk:MBidentities`) | exact derivation, uses none of (M), (J), (H); not independently reviewed; identities given (J) |
| Numerics | `gdk:numerics` | values table (K_d to 32 digits, r3 to 34 digits, at 8 d); deviation table for five routes (three-node column now at 6 d; both jet columns through gdk:Ktau); further checks; caution on the literal gs:Kseries bracket (tested failure at d = 0.8 only) | numerical |
| Status | `gdk:status` | proved / conditional / numerical / open | - |

## Status of the content

The fragment's own Status subsection is authoritative. It says the following.

**Proved.** These have written proofs. Unless noted, none has had an independent review.
- S closed form and its Laurent form. Three workflow verifiers did not refute it.
- Delta(tau): exact Gamma algebra, checked symbolically.
- Lattice and product forms, sample formula, arrays and kernels: exact derivations, not refuted by three
  verifiers, rechecked termwise here.
- Growth theorem (`growth/PROOF.md`). Parts (a) (sufficiency), (b) and (c) are the case r = 3 of gdr:topG (Step 0
  of its proof), which was independently reviewed. The sharpness of H_q and the explicit constants of
  `growth/PROOF.md` are not independently reviewed.
- R-family theorem (modes |k| <= 1, gdk:threeModes) on H_q: the case r = 3 of the product top-mode theorem gdr:topG
  (foundation Theorem 6). gdr:topG has a written proof in `general_d.tex` and was independently reviewed on
  2026-10-03 (`review/lemmaG-proof`, ACCEPT, seven minor items applied; the review checked the R-family parameters
  and (C) <=> tau in H_q) and probed numerically (`review/lemmaG-numeric`, PASS). The proof text of
  `topmode/PROOF.md` was not reviewed as such.
- Residue functional and three-node rule on H_q with Re tau < 3q/2, tau != q.
- Position-space representation gdk:MB, gdk:KMB: exact derivation from gs:Kdefinition; it uses none of (M), (J), (H),
  since gs:Kdefinition defines K_d as the coefficient [t^2]. Not refuted by the three workflow verifiers and
  re-evaluated from the printed formulas (`fragment_checks/check_barnes.py`); not independently reviewed.

This is the single review statement (decision D6) used in the fragment, in `topmode/PROOF.md` and in
`K_general/RESULT.md`.

**Conditional** (decision D5).
- `gdk:rLow` and `gdk:Kr3` are exact given (M) and (J); `gdk:Ktau` given (M) alone.
  - The note proves (M) only at d = 2. At other d it is numerical; the strongest test is the agreement of gdk:Ksample
    with the position-space route, which uses none of (M), (J), (H); on the jet circle that agreement tests (M) and
    (H) together.
  - (J) is the path form of gs:Bjet. The note derives gs:Bjet (Section app:generalSpecial) from completion symmetry
    and analyticity, and gs:C5 itself rests on it; it is listed as an input because its lower orders t^0, t^1 on the
    path are used explicitly (gdk:rLow, gdk:MBidentities).
  - At d = 2 both inputs are proved, so the exact r3(2) is a theorem.
  - Elsewhere, including r3(1), r3(3) and the r3 column of the values table, the values are conditional on (M)
    and (J). At d = 1, (J) is eq:Kpath, on which eq:KprovedFinal itself rests, so there r3(1) is conditional on
    (M) alone.
  - (M) is stated as an identity of meromorphic functions; r_k are the Laurent coefficients of the continuation
    J_{2tau}/C(tau) of the trace, which converges absolutely (Mellin line separating) only for
    max(0, 1/2-2q) < Re tau < 3q/2. This strip is nonempty iff d > 4/7; for d <= 4/7 the trace, and with it r_k,
    rests on the separating-contour construction, which is only sketched.
- `gdk:MBidentities` hold given (J). `gdk:KMB` uses none of (M), (J), (H).
- `gdk:E2` also needs [tau^2] under the trace. gs:Kspectral uses the same step, and the note justifies it only at
  d = 2. So the 430-digit gs:Kseries value of K_3 rests on (M) and that step; the position-space value, which uses
  neither, agrees with it to 3.6e-100.
- On the jet circle, the R-family theorem (modes |k| <= 1), the three-node rule and `gdk:Ksample` need (H), the
  analyticity in tau of the continued samples; the first line of `gdk:Ksample` needs in addition only (M). (H) is
  stated with a bounded connected U, a closed discrete exceptional set sfE meeting the jet disc at most in {0}, joint
  holomorphy in (t, tau), and a radius condition on the poles of the weights w_j. No production circle lies in H_q.
- For d <= 4/7 the strip of (M) is empty; there the residue functional, and with it the definition of the trace
  and of the r_k, is only sketched. For Re tau >= 3q/2 the residue functional is only sketched.
- For C5(d) the only extra conditions are (M), plus (H) when r3 is sampled on the jet circle: (J) adds nothing, since
  gs:C5 already rests on gs:Bjet, and with K_d from gdk:KMB none of (M), (J), (H) enters. The range of
  gdr:C5reduced is 2/3 < d < 4, so the d <= 4/7 caveat never affects C5(d).
- For d != 2, r3 involves tau-derivatives of order at most three of the remainder sums; at d = 2 the triple pole
  of rho_k and the spurious poles of individual pieces at tau = 0 raise the order (open item 3).

**Numerical only.**
- All digit agreements. No interval enclosures: Arb bounds rounding only.
- The d = 3 half-shift determinant form of c_0 (derivation not written out; checked at six points to 1.1e-24).
- Tested ranges: d = 0.8-3 for K_d, d = 0.3-3.9 for the top modes.
- A reduction of r3 at generic d was not attempted. At d = 3 the PSLQ search at 420 digits was negative.

**Open.**
1. Independent review of the sharpness of H_q and of the explicit constants in `growth/PROOF.md`.
2. A proof of (M) at generic d, and a written proof of (H) with uniform remainder bounds.
3. Explicit polygamma-weighted two-variable series for r3, and a d = 2-adapted form.
4. PSLQ on r3 or K_d with the 100-digit values.
5. d < 0.8, and the r = 7 primitive kernel, which gdr:topG does not cover.

## Checks run for this fragment

All checks implement the formulas exactly as typeset. They share no code with R_part, S_part or position_space
unless stated; otherwise only stored numbers are read.

`fragment_checks/`:

| script | checks | result |
|---|---|---|
| `check_delta_symbolic.wls` (Mathematica 15) | Laurent series of Delta(tau) at general q; W_2 = B_d(d-b',2b') = C X_d | exact zero for both |
| `check_laurent.py` (mpmath, 60 digits) | (a) Bell form of s_k vs Taylor of the closed form; (b) Delta Laurent coefficients at 8 q | (a) 4e-57; (b) 5e-21 (Cauchy-circle floor) |
| `check_laurent.py` (continued) | (c) `gdk:Kr3` with R_part's 34-digit r_k vs the 100-digit MB K_d at 8 d | <= 1e-33 relative |
| `check_laurent.py` (continued) | r_0 - s_0, r_1 - s_1, r_2 - s_2 - 3U/2 | <= 5e-32 |
| `check_laurent.py` (continued) | (d) closed forms of r3(1) and r3(2) vs R_part | <= 1e-32 |
| `check_laurent.py` (continued) | MB vs eq:KprovedFinal and gc:K2closed | 2e-59 (dps-limited); 1e-100 at 120 digits in `build_table.py` |
| `check_blocks.py` (40 digits) | lattice factorization, all three Horn arrays (termwise, random complex q, tau, t), d_l Horn form vs gs:spectrum | <= 6e-39 |
| `check_blocks.py` (continued) | kernels G, S, tilde G (formerly T), V by direct summation with Euler-Maclaurin tails | <= 2e-40 |
| `check_blocks.py` (continued) | rho_k vs numerical residues; Laurent form of D_R | 1e-40 |
| `check_barnes.py` (double precision, independent trapezoid) | `gdk:KMB` and `gdk:MBidentities` at 8 d | K_d to <= 7e-14 relative; identities to <= 2e-13 |
| `build_table.py` (120 digits) | the two tables of `gdk:numerics`, recomputed from stored values; r3 from MB K_d (five-node column from the full-precision `R_part/prod/prod_B_d*.json`) | printed digits verified as correctly rounded; typeset table cross-checked against `table.json` (all 8 rows) |

`test_build_joint/` (joint-review fix round):

| script | checks | result |
|---|---|---|
| `check_r3_34.py` (mpmath, 110 digits) | K6: r3 = s3 + 4[K - (U/8)(psi(1)+psi(2q)+4psi(q))] from the 100-digit MB K_d, rounded to 34 significant digits; s3 of gdk:sk vs Taylor of gdk:Sclosed; printed 34-digit r3 through gdk:Kr3 vs the printed 32-digit K | all 8 values equal the joint review's 34-digit strings and are correctly rounded (<= 0.34 ulp); s3 Bell vs Taylor <= 1.4e-107; Kr3(printed r3) vs printed K <= 2.4e-32, vs the 100-digit K <= 9.5e-34 (`check_r3_34.log`) |
| `check_kbracket_d08.py` | K6 "A caution": literal gs:Kseries bracket vs gc:Kcancelled, with the unchanged summand of `refcheck/routeB_residue.py`, at d = 0.8, integer, non-integer and complex indices | equal to the working precision (1e-36 to 1e-41 at dps 40) (`check_kbracket_d08.log`) |
| `check_kbracket_d08_large.py` | the same through the code's own `g_at` at large indices, d = 0.8 and 1.25, dps 40 | equal to <= 8e-50 up to n = 1e20 and l = 1e20 (`check_kbracket_d08_large.log`) |
| `check_kbracket_d08_huge.py` (repair round 1, sections 5-6 added in repair round 2; earlier versions `_r0` and `prerepair2/check_kbracket_d08_huge_r1.py`) | (1) K from both brackets in every stored diagonal route-B run; (2) the reach of the code's n-tail (l = 0, N = 8 as in production); (3) n*literal and n*cancelled up to that reach, dps 60; (4) the same points with the code's constants at 520 digits; (5) as (3) at dps 40; (6) at d = 1.25, max of n*|literal - cancelled| on a 0.25-decade grid, over the whole tail and over the corrupted range (l = 0), and for n <= 1e25 at l = 0, 1, 2, 5, 20, 100 | (1) d = 0.8: literal 70.3 (dps 40) and 2539.5 (dps 60) vs 92.3727702399; d = 1.25-3: the brackets agree to working precision (identical stored strings, or 2e-56 at d = 2.75, 4e-39 at d = 3, dps 40). (2) last node n = 10^394.6 at d = 0.8 (p = 0.2), 10^92.9 at d = 1.25 (p = 0.875), 10^160 at d = 1, dps 60; 10^279.5, 10^66.6, 10^113.9 at dps 40. (3) the literal bracket loses about one digit per decade of n (1.8e-61 at 1e20) and has no correct digit from n = 1e80; at d = 0.8, n*literal = -0.49 at 1e390 and -3.1 at 1e394 against n*cancelled = 3e-310. (4) agreement to 2e-440 (1e80), 2e-420 (1e100): the loss comes from the constants fixed at dps+20 digits in `init`. (5) dps 40, d = 0.8: no correct digit from n = 1e60 (rel. diff 2.8); n*literal = +0.038 at 1e279 and +0.049 at the last node 3.5e279, sign opposite to dps 60, as is the error of K (-22 vs +2447). (6) d = 1.25: n*error <= 7.1e-72 over the whole tail and <= 4.4e-100 beyond 1e80 at dps 60; <= 8.6e-52 and <= 1.4e-74 beyond 1e60 at dps 40; the six spins at n <= 1e25: <= 2.0e-71 (dps 60), <= 9.8e-52 (dps 40) (the round-1 statement "n*error <= 4.4e-100" held only beyond 1e80). Sections 1-4 of the log are identical to repair round 1. The old RESULT.md figure "relative error 0.96" was |K_canc - K_lit|/|K_lit| at dps 60 (`check_kbracket_d08_huge.log`) |
| `check_r3_special.py` (repair round 2; mpmath, 120 digits) | r3(1), r3(2), r3(3) of gdk:special from the formulas typeset there (closed forms eq:KprovedFinal and gc:K2closed; 430-digit K_3), rounded to 34 digits; d = 1 prefactor identity; closed forms vs the 100-digit MB values | the three 34-digit strings now typeset in gdk:special are correctly rounded (0.10, 0.24, 0.07 ulp) and equal the values-table strings; prefactor identity 5e-119; eq:KprovedFinal, gc:K2closed, K_3 vs MB 5.2e-101, 1.5e-100, 3.6e-100; r3 from MB K agrees to <= 8e-99 (`check_r3_special.log`) |
| `check_k3_routes.py` (repair round 1) | K_d from every stored 72-digit tau-circle through gdk:Ktau and through gdk:Kr3 (s3 from the Taylor series of gdk:Sclosed), vs the 100-digit MB values; stored F re-derived | five-node circles through gdk:Ktau: the five-node column exactly (-8.0e-47 ... -1.41e-43); three-node job 569317 through gdk:Ktau: the stored K_d (-8.06e-47, -1.01e-41, -3.53e-44); three-node job 569482 (k3_jets.json): gdk:Ktau -1.41e-45, +4.14e-44, -9.47e-43, gdk:Kr3 +3.78e-45, +5.0e-44, -8.11e-43 (the latter = `e2e_k3.log`); stored F re-derived to <= 7e-70 (`check_k3_routes.log`) |

The three-node values at d = 1.5, 2.5 and 3 in the routes table come from the joint review's circles
(`review/joint/numerics-end-to-end/k3_jets.json`; symmetry job 569482, rblocks.tR3 unchanged, r = 0.08, N = 48,
K = 30, M = 400, 72 digits). Since repair round 1 they are extracted through gdk:Ktau, like every other jet entry of
that table: -1.4e-45, +4.1e-44, -9.5e-43 (`test_build_joint/check_k3_routes.log`). The joint review's `e2e_k3.log`
numbers +3.78e-45, +5.0e-44, -8.11e-43 are the gdk:Kr3 route on the same circles; the routes paragraph quotes them.
The circles at d = 0.8, 2.5, 2.75 and 3 lie entirely outside H_q (Re tau > 0.1, 0.25, 0.375, 0.5 there).

## Notes for the maintainer and for the merge with C62d

- **One theorem, one home (D2).** The product top-mode theorem is gdr:topG of `general_d.tex`. Section
  gdk:topmode applies it to the R family (K1 trial text of the joint review); the fragment has no Lemma or proof of its
  own. C62d shortens gdr's paragraph "The R family of K_d" (gdr:top) to a pointer to gdk:topmode and
  gdk:continuation (joint-review G1).
- **td correction (D3).** That c_{3,2} = c_{4,3} = 0 is not special to d = 3 (gdr states it for 2/r < d < 4, at
  b = d/2) is stated once, in gdr's paragraph "Relation to the earlier sections of the note" and in the replacement of
  the note sentence after td:sevenOddCoefficients (N3). The fragment's Remark (iii) of gdk:topmode only points there
  and, since repair round 2, restates nothing.
- **Symbols (D4).** Renamed here: calT_alpha(j) to `\widetilde{\mathcal G}_\alpha(j)`, the exceptional set E to
  `\mathsf E`, the summand f_l to `f^{\rm R}_\ell`; h_tau of the d = 3 paragraph is written as
  `\widetilde\Phi(n+u-5/8)` at q = 3/4. The optional rename calX_d(tau) to `\mathsf X_d(\tau)` was applied in the
  fix round and undone in repair round 2: the note already has `\mathsf X_r(t)=\Xi_r(t)|_{q=3/4}` (22 occurrences on 15 lines,
  `\mathsf X_3`, `\mathsf X_4`, `\mathsf X_7` in app:threeDimensionalReduction, which the d = 3 paragraph cites), so
  `\mathsf X_3(\tau)` would be the note's glyph for a different object, and the claim of D4 that no new symbol occurs
  in the note fails for it. `\mathcal X_d` occurs in neither the note nor `general_d.tex` (grep; gdr has only
  `\mathcal X_0`, `\mathcal X_{1/2}`, `\mathcal X_T`, functions of b, which the notation sentence after gdk:notation
  separates). The three other renames occur in neither file (grep: `\mathsf E`, `\widetilde{\mathcal G}`,
  `f^{\rm R}` 0 times in the note). If the note turn prefers a fresh symbol, `\mathsf Y_d` is unused in all three
  files (but gdk:regularized has an italic (X, Y) pair). gdr renames its own symbols (tau to tilde t, P_R to P_+,
  calT_3 to frak t_3, S, D, Xi of gdr:TG to S_T, D_T, Xi_T, rho_0, rho_h to xi_0, xi_h, vartheta to eta); the fragment's
  proof of gdk:threeModes uses gdr's S_T, D_T, Xi_T, which C62d's file has (checked at md5 7ed4f41b, 2eb62278 and
  c0c688e9, the file of the last build, gdr:TG; recheck at C62d's final md5).
- **gdr line references.** The pre-joint STATUS cited gdr's R-family paragraph as "l.215-226 at md5 5af3f1ca"; at
  md5 33012d95 it is l.217-224, and C62d's fix pass (G1) shortens it to a pointer. No line number of `general_d.tex`
  is used in the fragment; it uses gdr labels only.
- **Reference file.** `references/reference_values.json` (md5 905dae8d) prints K to 50 digits and agrees with MB to
  2e-49 to 5e-51. The "ref" column in `K_general/RESULT.md` (3e-46...) refers to earlier strings; RESULT.md now
  carries a superseded-in-part banner.
- **Numbers that differ from RESULT.md or R_part_arrays.json** (the fragment uses the corrected values):
  - The d=1 and d=2 reproductions of eq:KproofTwoFunctions and gc:K2master are, at two tau each, 3.6e-22 and
    8.2e-22 (d=1), and 1.5e-20 and 1.4e-19 (d=2), absolute; R_part_arrays quotes 4e-22 and 1.5e-20.
  - The sample-vs-spectral comparison is quoted relative, at most 1.1e-19.
- **Note-merge items** (joint review Section 3, N1-N12) are for the note turn, not for this fragment. With the K7
  removal of `gdk:kernel` the merged note should have 583 + 49 + 40 = 672 labels (the synthesis trial, made before
  K7, counted 673).

## Inputs used (md5)

- `position_space/K_d_values_mb_D100.json`: 715614c6273d5a258c46cdc19ee27957
- `R_part/R_part_results.json`: 1b99440e765e64e2ff0b3bea0719c7b6
- `R_part/R_part_arrays.json`: beeebc0f46120c8b5ca999a813f1de2d
- `R_part/rblocks.py`: 6652a7dd5bf374fddb279690b11b7b7d
- `refcheck/refcheck_values.json`: e1a3a1bade6e40795d054bb0f52c5118
- `refcheck/routeB_residue.py` (read for the K6 caution): 112817556fb921403db1da6cc31116f1
- `../references/reference_values.json`: 905dae8d9e10cf1fbbe4294d6f5fac18
- `../../LRI_C5_d3/wf_K3/K3_value.json`: de57868619ebc7a88c9e71fde39ceb8f
- `growth/PROOF.md`: d7a0f081512597feabd26984cea59339 (unchanged)
- `topmode/PROOF.md`: d0d5a0402beb544649547b2b8fc5aaa8 (after repair round 2; pre-repair-2 copy
  `test_build_joint/prerepair2/PROOF_prerepair2.md`, f8dc38cbafd68e78cdcf7ca576762691, after repair round 1;
  pre-repair copy `topmode/PROOF_prerepair1.md`, bb2c79a2f9625421bdd91d68e4552f7b, after K11; pre-joint copy
  `topmode/PROOF_prejoint.md`, f7901d9a7dafdfb562d5dc7d81b829a7)
- `../RESULT.md` (K_general): 509ca522080ba5c62b22a159f1c0eb5f (after repair round 2; pre-repair-2 copy
  `test_build_joint/prerepair2/RESULT_prerepair2.md`, d85bae8f575a3615ca900c0178a3aae9, after repair round 1;
  pre-repair copy `../RESULT_prerepair1.md`, bada571ab5360d82e7d6b2a14c128a38, after K10; pre-joint copy
  `../RESULT_prejoint.md`, f1e5f1f0dfdaf5c842eba6cab10ec1fe)
- This file before repair round 2: `test_build_joint/prerepair2/STATUS_prerepair2.md`, d1ffd0c9b775d2974e402d5b652448af
- Read for repair round 1: `refcheck/runs/B_d*_dps*_L20.json` (B_d0.8_dps40: c89d43715f2243d7df87bed735788b3a,
  B_d0.8_dps60: 3c2c4e8be6d57d32a402696451342afb); `R_part/prod/prod_B_d*.json` and
  `topmode/results/kjet3_B_d*.json` (concatenated md5 360a5f30bfc4eb53f219bda234d90205)
- `../review/VERIFICATION.md`: 44d95b5a16fd34f38fdc5294f5604667
- `../review/joint/JOINT_REVIEW.md`: b7e0f761f23c047284f5f8bc9440cccb; `joint_reviews_raw.json`:
  2fac2a72cf2fe7ca506dcad1394c4fe8
- `../review/joint/numerics-end-to-end/k3_jets.json`: 8e5572591927f10b2de4d4abb6efbae5; `e2e_k3.log`:
  f9e6b87c62d3ea4b77d1088ee022bc29
- `../foundation/general_b_periodization.tex`: 7d548c0cdf30ce853b4adeaec2568645 when the joint review ran;
  15daf5ee17257846621aca05f9e3bbfe at 09:27, 8d2419637566aa48c0fc8df6c781d984 at 09:33 (C62d's fix pass); read only
- `../general_d.tex`: 33012d9525287622bc8a4f6d1c982c8a when the joint review ran; 2eb62278e8e30f03c15bd7d20a4bde6e at
  09:28; c0c688e9ab2fa6f2a73331cf160e3dda (09:33) in the builds of repair rounds 1 and 2 (still the live file at
  10:15; C62d reported its fix pass DONE and READY at this md5, so it is final); read only
- The condensed note (read-only): `long_range_ising_condensed.tex` 08c37eb3a241b6c6b65e65d7cc0b1145, its `.aux`
  3b277c76f9713fb13db74f372f32accb. The note and C62d's files were not edited.

## Final nits (2026-10-03, after repair round 2)

The three round-2 verifiers of workflow wf_5332f3a4-e4d (status and rigor; notation, layout and build; numerics) all
returned **ready**, with nits only. The coordinator (C63d) applied them with `test_build_joint/apply_final_nits.py`
(md5-checked copies in `test_build_joint/prenits/`, every anchor asserted once):
- Routes table: the last column has the opposite sign convention, (position space minus reference)/reference
  (`fragment_checks/build_table.py`, `MB_vs_exact`); the text now says so. No number changed.
- 'A caution': the end of the 40-digit tail is now n ~ 3.5e279, as in the log (3.474e279) and below.
- D6 label: "foundation Theorem 6" is now "Theorem 6(a)-(c); its wheel case gdr:topless is 6(d)" in the MERGE NOTES,
  `topmode/PROOF.md` and `../RESULT.md`, matching gdr's own wording.
- D3: the `../RESULT.md` banner now gives the ranges (S family on H_q; wheels at b = d/2 for 2/r < d < 4, gdr:top).
- D4: the `\mathsf X` count in the note is 22 occurrences on 15 lines.
- Build bookkeeping: C62d reported its gdr fix pass DONE and READY at general_d.tex md5
  c0c688e9ab2fa6f2a73331cf160e3dda, so the "final rebuild" item is closed by the rebuild below.

Final rebuild (`bash test_build_joint/build_joint.sh`, 10:15): note 08c37eb3 with `.aux` 3b277c76 (labels regenerated),
general_d.tex = snapshot c0c688e9, fragment da91f60a. rc 0, 29 pages, `joint_preview.pdf` and
`joint_preview.synctex.gz` verified; 0 errors, 0 LaTeX warnings, 0 undefined references, 0 multiply defined labels,
0 overfull and 0 underfull boxes; labels 583 note + 49 gdr + 40 gdk. The 83 pdfTeX warnings are all note hyperlink
targets of Sections 4-19 and the bibliography, none of Section 20 or 21. Dash audit clean on the fragment,
`joint_preview.tex` and `gdr_snapshot.tex`; no em dash in this file, `topmode/PROOF.md` or `../RESULT.md`.
Final md5s: fragment da91f60ae8bc38b916e5fbfe23d9ecdd, `topmode/PROOF.md` 06b6da4c32f2f5e4932f896bc3331245,
`../RESULT.md` 2bb27471be6c26ba4cf6716075e8adcd (this file changes when edited).

## Repair round 2 of the joint-review fixes (2026-10-03)

Source: the verifier findings on repair round 1 (10 items: 1 minor, 8 nits, 1 pending). Pre-repair copies in
`test_build_joint/prerepair2/` (fragment, this file, `topmode/PROOF.md`, `../RESULT.md`, and version r1 of
`check_kbracket_d08_huge.py` with its log). Script: `test_build_joint/apply_repair2_fixes.py` (fragment, PROOF.md,
RESULT.md; md5-checked inputs, every anchor asserted); this file edited directly.
- D3 / Remark (iii) (nit), applied: the parenthetical "(c_{3,2}=c_{4,3}=0 in every d)" is dropped, so the remark is a
  pure pointer to gdr's "Relation" paragraph. The MERGE NOTES and the D3 note above now quote gdr's range 2/r < d < 4
  instead of "in every d".
- D6 / PROOF.md l.195 (nit), applied: the Step 4 note names its source, the review of gdr:topG
  (`review/lemmaG-proof`, its items on the endpoint case alpha = 1 and on the integrability list; checked against
  `review/lemmaG-proof/review.json` and the diff of `topmode/PROOF_pre_lemmaG_review.md`), and says that this file's
  text was not reviewed; l.134 uses the same wording.
- S-family domain (nit), applied: PROOF.md §4.2 says the one-mode property holds on H_q (case r = 2 of gdr:topG,
  condition (C) without upper bound), and that Re tau < 2q is the bound of gdk:Sclosed (Re b > 0 for b = d/2 - tau), not
  of the top-mode statement. This matches Remark (ii) of gdk:Sfamily.
- K10 bookkeeping and stale md5 qualifier (two nits), applied: c0c688e9 added to the S_T, D_T, Xi_T check (gdr:TG has
  them); the final rebuild is still due (see "Test build").
- D4 optional rename sfX_d (minor), applied by reverting to `\mathcal X_d` (one of the two fixes the verifier offered):
  the note's `\mathsf X_r(t)` makes `\mathsf X_3` a clash at d = 3; `\mathcal X_d` occurs in neither the note nor
  general_d.tex. 14 occurrences (12 in the text, 2 in the merge notes); the notation sentence after gdk:notation,
  the MERGE NOTES and the D4 note above are updated. No other symbol changed.
- K6 "A caution" (nit), applied: the 40-digit failure is explained by the same mechanism (no correct digit beyond
  n ~ 1e60; n*literal about +0.05 at the 40-digit reach 3.5e279, opposite in sign to dps 60, as is the error of K).
  New sections 5 and 6 of `check_kbracket_d08_huge.py` (sections 1-4 of the log unchanged; md5 of script and log
  340ad9f7, 24047de5); the verifier's `verify_1/dps40_check.log` agrees (n*literal = 0.0381 at 1e279). Section 6
  also showed that the round-1 bound "n times the error below 1e-99" at d = 1.25 held only beyond n = 1e80; the
  caution now says that over the whole tail n times the error stays below 1e-70 (1e-50 at 40 digits; measured at
  most 2.0e-71 and 9.8e-52, the maximum at small n and spin l = 2), far below the working precision. RESULT.md's
  bracketed correction now gives both onsets (1e80 at 60 digits, 1e60 at 40 digits).
- STATUS HOOK wording (nit), applied: the fallback point is the `%% MERGE (layout D1 ...)` comment before gdr:C5, with
  its extra steps (G-H and the S, C, D scope of gdr's Notation paragraph), here and in the fragment's MERGE NOTES.
- r3 lengths in gdk:special (nit), applied: r3(1) and r3(3) printed to 34 digits as in the values table; all three
  strings recomputed from the formulas typeset in gdk:special (`check_r3_special.py`, 120 digits) and correctly
  rounded.
- Build bookkeeping (pending), not closable now: rebuilt at 10:05 with the live `general_d.tex` (still c0c688e9) and
  the regenerated note labels; the final rebuild waits for C62d's final md5.
Numbers changed: the d = 1.25 error bound in the caution (1e-99 to 1e-70 over the whole tail), the added 40-digit
numbers, and the printed length of r3(1) and r3(3). Rechecked: `check_r3_special.py` (new), `check_kbracket_d08_huge.py`
(sections 1-4 identical), combined build clean, dash audit clean, 40 gdk labels.

## Repair round 1 of the joint-review fixes (2026-10-03)

Source: the verifier findings on the fix round below (13 items). Pre-repair copies: `K_d_fragment_prerepair1.tex`,
`STATUS_prerepair1.md`, `topmode/PROOF_prerepair1.md`, `../RESULT_prerepair1.md`. Script:
`test_build_joint/apply_repair1_fixes.py` (fragment, PROOF.md, RESULT.md); this file edited directly.
- PROOF.md "Remark on the foundation text": past tense; found by the foundation review (`review/VERIFICATION.md` F1,
  `review/foundation-rigor/check_laplace.py`); corrected bound gdr:endpoint (Steps 3-4 of the proof of gdr:topG),
  re-reviewed in `review/lemmaG-proof`; "The running review checks the same point" deleted.
- RESULT.md: banner bullet on the conditions of gdk:rLow, gdk:E2, gdk:Kr3 (given (M), (J); E2 also [tau^2] under the
  trace), gdk:Ktau ((M)), gdk:MBidentities ((J)) and gdk:KMB (none).
- gdk:positionSpace and the Status bullet on (M): the agreement with the position-space route tests (M) and, on the
  jet circle, (H).
- Status, C5(d) bullet (and the D5 merge note): "reduce to (M), plus (H) when ...".
- Remark (iii) of gdk:topmode: the td consequences are those of gdr:topless, stated in gdr:top, paragraph "Relation to
  the earlier sections of the note".
- PROOF.md: "Theorem 6(d)" where the wheel statement is meant (l.24, 40, 80, 219, 243, 251).
- "part (c) of the growth theorem of Section gdk:Rfamily".
- Routes table: the three new three-node entries replaced by the gdk:Ktau-route values -1.4e-45, 4.1e-44, -9.5e-43
  (`check_k3_routes.py`), so the column uses one route; the routes paragraph names that route (first line of
  gdk:Ksample, i.e. gdk:Ktau), quotes the gdk:Kr3 values of the joint review, and lists the circles that lie entirely
  outside H_q (d = 0.8, 2.5, 2.75, 3). PROOF.md l.33 and l.377 now quote 4.1e-44 (and 5.0e-44 through gdk:Kr3).
- "A caution": rewritten from `check_kbracket_d08_huge.log` (extended, docstring corrected): the stored failure is at
  d = 0.8 only (70.3 at 40 digits, 2539.5 at 60 digits, vs 92.37; the old "relative error 0.96" was normalized by the
  literal value), the brackets agree for 1.25 <= d <= 3, terms of order n^{-d}, constants of the code at dps+20 digits,
  tail reach 10^394 (d = 0.8) and 10^93 (d = 1.25), n times the error O(1) and < 1e-99 there [repair round 2: < 1e-99
  only beyond n = 1e80; over the whole tail < 1e-70]. RESULT.md l.131 carries
  a bracketed correction.
- r3(2) in gdk:special printed to 34 digits (35.63714944308140680727039972168179...), as in the values table;
  re-evaluated from the closed form at 60 digits (agrees to 2.4e-33, the 34-digit rounding).
- Build bookkeeping (three items): rebuilt with the current `general_d.tex` (c0c688e9) and foundation (8d241963);
  md5 lines refreshed; the final rebuild waits for C62d's final md5.
Numbers changed: three entries of the three-node column, the caution's numbers, and the length of r3(2). Rechecked:
`check_r3_34.py` (log unchanged), `check_k3_routes.py`, `check_kbracket_d08_huge.py`; combined build clean; dash audit
clean; 40 gdk labels.

## Joint-review fix round (2026-10-03)

Source: `LRI_C5_general_d/review/joint/JOINT_REVIEW.md`, Section 2 (gdk fixes K1-K12) and "Decisions taken by this
synthesis" (D1-D6). Pre-fix copies: `K_d_fragment_prejoint.tex`, `STATUS_prejoint.md`, `topmode/PROOF_prejoint.md`,
`../RESULT_prejoint.md`. Scripts: `test_build_joint/apply_joint_fixes.py` (fragment), `apply_proofmd_fixes.py`
(topmode/PROOF.md), `apply_resultmd_fixes.py` (K_general/RESULT.md).
- K1 (major): the Lemma, its proof and `gdk:lemmaG`, `gdk:laplace`, `gdk:exchange` are deleted; gdk:topmode is the
  K1 trial text (applies gdr:topG with r=3 through gdr:mixed; Remark (i) with gdr:kernelBalance; Remark (ii) keeps
  the two controls, with Theta of Step 5 of gdr:topG; Remark (iii) is a pointer). S-family Remark (ii) cites the case
  r=2 of gdr:topG and says that Xi, not S, is constant. Status bullet, Open item 1, "which gdr:topG does not cover",
  and the merge comments are replaced.
- K2: Proved bullet for gdk:MB, gdk:KMB (uses none of (M), (J), (H)); Conditional bullet for gdk:MBidentities.
- K3: growth theorem status; proof outline says that (a) sufficiency, (b), (c) are the case r=3 of gdr:topG Step 0.
- K4: intro: d <= 4/7 caveat, "gives, in place of", periodization of R_tau as in app:generalPeriodization and
  gdr:periodization; step 3 on H_q with Re tau < 3q/2, tau != q, and by (H) on the jet circle.
- K5: (J) says the note derives gs:Bjet and why it is still listed.
- K6: r3 column to 34 digits (verified, `check_r3_34.py`); three-node column at d = 1.5, 2.5, 3 from the joint
  review; "exact" relabelled as eq:KprovedFinal, gc:K2closed and the 430-digit gs:Kseries value of K_3 (conditional
  on (M) and the [tau^2] step), also in the intro, the d = 3 paragraph and "Consistency"; the caution states the cause
  (precision loss of the literal bracket at very large radial index in the Abel-Plana tail) and that it does not bear
  on the convergence statement after gs:Kseries.
- K7: gdk:kernel display replaced by a pointer to gdr:kernel (references retargeted); complex-b reading of the
  eigenvalue (G13); notation sentence on C(tau), gdr:D and the gdr samples; C(tau) written out at the two former bare
  C's.
- K8: tilde G, sfE, f^R, sfX_d renames; h, j and E_2 disambiguation; h_tau dropped at d = 3. [The optional sfX_d
  rename was undone in repair round 2, because the note uses \mathsf X_r(t).]
- K9: descriptive `\paragraph` headings and run-in `\emph{Proof.} ... $\square$`; the merge-note claim about the
  note's proof style corrected.
- K10: this file refreshed (md5s, gdr line references, review statements, D1 layout and HOOK fallback);
  `K_general/RESULT.md` has a superseded-in-part banner and corrected lines on c_{+-2}, d = 3 and open issues 1-2.
- K11: `topmode/PROOF.md` has one review status throughout (statement reviewed as gdr:topG, proof text unreviewed,
  Theorem T a corollary) and makes section 0 item 3 and section 4.1 conditional on (H).
- K12: the "fix check" sentence is gone (replaced by the K1 status bullet, which cites `review/lemmaG-proof`).
- D1-D6 as described in "The fragment", "Status of the content" and the notes above.
Numbers changed: only the r3 column (34 digits) and the three added three-node entries; every other number is
unchanged. Rebuilt (combined test build, see above); dash audit clean; 40 gdk labels.

## Fix round 2 (2026-10-03)

The recheck of fix round 1 (`workflow_result_raw.json`, key "recheck": rigor and consistency lenses, 12 items, all
minor or typo) was applied to `K_d_fragment.tex`. Pre-round-2 copies: `K_d_fragment_prefix2.tex`,
`STATUS_prefix2.md`. Changes:
- (M): the strip max(0,1/2-2q) < Re tau < 3q/2 is nonempty iff d > 4/7; for d <= 4/7 the trace and r_k rest on the
  separating-contour construction (only sketched), and statements involving them are conditional on it. The Status
  bullet on d <= 4/7 now says that the definition of the trace and of r_k is only sketched there.
- After gdk:Ksample: "order at most three" is restricted to d != 2; at d = 2 the triple pole of rho_k and the
  spurious poles raise the order (pointer to the open item).
- Remark (ii) of gdk:topmode: the two controls are described separately (total balance; multiplicities of
  dimension d). "below 1e-15, within the spread".
- d = 3: h_tau written as Gamma(w+1/8)^3/[Gamma(w+7/8)^2 Gamma(w+1/8+tau)], equal to the cube of td's h at
  tau = q = 3/4; no bare h. The h and E clashes are in the MERGE NOTES.
- "(J) enters only" is scoped to the proposition.
- r3(1): the d = 1 paragraph and the Status now both say conditional on (M) alone, since (J) at d = 1 is
  eq:Kpath, on which eq:KprovedFinal rests.
- Status and Open: the four product-form ingredients that are new and unreviewed are named (estimates with
  varkappa, endpoint bound with varkappa, Step 5, continuation in g_i); Step 3 says the product form of the
  endpoint bound is unreviewed. [Superseded by the joint-review round: these are parts of the reviewed gdr:topG.]
- Intro step 3 and the Status bullet: "the Fourier modes |k| <= 1" / "the theorem gdk:threeModes (R family, modes
  |k| <= 1)" instead of "three Fourier modes" / "three-mode theorem".
- MERGE NOTES: the duplicate "The R family of K_d" paragraph of general_d.tex's gdr:top.
- Subscript convention: Omega added to the list of R-family subscripts.
No numbers changed. Preview rebuilt (15 pages, no errors, no undefined references, no over- or underfull boxes; the
44 pdfTeX warnings are all note hyperlink targets absent from the preview); dash audit clean; 44 gdk labels.

## Fix round 1 (2026-10-03)

Fixes from the three review lenses (rigor, numerics, consistency) were applied to `K_d_fragment.tex`; the pre-fix
copy is `K_d_fragment_prefix.tex` (this file's pre-fix copy is `STATUS_prefix.md`). The main changes:
- (M) is an identity of meromorphic functions, and r_k is defined through the continuation.
- (H) and the transfer argument are stated precisely.
- Conditional labels were added: r3(1) and r3(3), the r3 column, gdk:E2, the d = 3 determinant, the intro steps.
- The Lemma proof was tightened: product estimates, Fourier inversion, the measure and the continuation in g_i.
  [The Lemma and its proof were removed in the joint-review round; the fragment cites gdr:topG.]
- Notation: S_T, D_T, Xi_T, gamma_k and omega_j in the Lemma, h_tau at d = 3, and the subscript convention.
- Remark (iii) on d = 3 now matches td:projectedAnswer. [Now a pointer to gdr:top (D3).]
- Numbers were corrected: d = 0.8 and d = 2 jets, the Abel-Plana claim at d = 2.75, the per-spin top modes and the
  position-space contours.
- References now point to the foundation's Theorem 6(d) and (a)-(c) and to gdr:topG.
- The merge notes were extended.
