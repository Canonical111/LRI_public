# Reviews of LRI_C5_general_d (note Sections 20 and 21)

This package holds the generic-dimensional reduction of 𝓛_d and Z_d with the reduced C5(d) (note Section 20; Claude
Code session C62d) and the master 𝒦_d at generic d (note Section 21, `K_general/`; Claude Code session C63d).

**Who reviewed.** Every reviewer was a Claude agent, launched as a workflow subagent by session C62d or C63d on
2026-10-02 and 2026-10-03. There was no OpenAI Codex/GPT review and no human referee.

**What ships.** Raw reviewer outputs do not ship: `review/reviews_raw.json`, `review/joint/joint_reviews_raw.json`, and
the workflow transcripts and review folders under `K_general/`. Three kinds of material ship:

- **Two synthesized check reports that the note text cites**, as records:
  - `review/VERIFICATION.md`, the claims table with fixes F1–F23 and O1–O3;
  - `review/lemmaG-proof/review.json`, the verdict record. It is the only record of the numerical tests of that review,
    because those scripts saved no logs.
- **The check code and outputs behind numbers the note quotes:**
  - `review/{foundation-rigor,topmode-numeric,L-rigor,Z-rigor,formula-from-text}/`;
  - `review/lemmaG-numeric/` and `review/lemmaG-proof/*.py`;
  - `review/joint/{numerics-end-to-end,status-consistency,conventions}/`.
- **The cited K_general check files**, listed in the second part below.

## Section 20 (𝓛_d, Z_d, reduced C5(d); session C62d)

### 1. Five-lens independent review

Workflow wf_1498e507-418, 2026-10-03, 00:00–02:08. Record: `review/VERIFICATION.md`.

**Lenses:**

| key | lens | method |
|---|---|---|
| FR | foundation-rigor | proofs, checked against brute-force lattice sums |
| TN | topmode-numeric | own 50-digit lattice code |
| LR | L-rigor | |
| ZR | Z-rigor | |
| FT | formula-from-text | sympy rederivation and exact big-integer samples |

**Verdict.** All five ACCEPT: "ready for the note after the listed fixes". No printed formula was wrong. The top-mode
theorem was confirmed at about 50 digits by independent code.

**Errors found:**

- One false intermediate estimate, the endpoint exponent in Steps 3–4 of the top-mode proof (F1). It was corrected, and
  the same strip b < b_max suffices.
- Wrong control numbers in a remark (F2). The true value is 1.7% of the largest mode.

**Other findings:**

- rigor gaps for complex b;
- a missing citation of Pattern T for ∂_bW_3 = 0;
- the wording of 𝔇_L against C63d's P̂′;
- an overcount in the Z inventory (4 → 3);
- status labels.

**What changed.**

- All fixes F1–F23 and O1–O3 were applied by the fix-and-draft workflow wf_a382bd41-c4f.
- A separate fix check, by an agent of that workflow, found every item applied, with one wording slip that was fixed at
  the merge.
- The fix check's record, `review/fixcheck/`, is not shipped; the note no longer cites it (joint-review item G10).

**Caveats.**

- The proof had one full reader and one spot read.
- The corrected Steps 3–4 are the reviewer's own wording. They were re-reviewed later in product form (review 2 below).

### 2. Proof review of the product-form top-mode theorem

The theorem is gdr:topG, which is foundation Theorem 6(a)–(d). Folder: `review/lemmaG-proof/`.

**Verdict.** ACCEPT, with no fatal or major issue. Every step was rederived by hand. Steps 1–6 were tested numerically in
unbalanced cases: 2e-13 to 2e-8, and 3e-12 in the lower half-plane.

**What changed.** Seven minor wording and documentation items, all applied. They were not re-read after insertion.

**Not covered:**

- C63d's proof text `K_general/note_fragment/topmode/PROOF.md` (merged into the note, not shipped), as such;
- the sharpness of ℍ_q;
- the explicit constants of `K_general/note_fragment/growth/PROOF.md` (merged into the note, not shipped).

### 3. Numerical probe of gdr:topG

Folder: `review/lemmaG-numeric/`. Independent 48-digit lattice-sum code, run on the symmetry cluster (jobs
569336–569347 and 569461).

**Verdict.** PASS.

**Results:**

- top modes 2.8e-48 to 4.7e-44 at 12 mixed wheels;
- 6.5e-47 to 5.2e-45 at four R kernels;
- at most 9.3e-54 in the 54-digit reruns;
- controls switch on linearly with the per-factor imbalance.

### 4. Joint review of the Section 20 and Section 21 fragments (gdr + gdk)

Folder: `review/joint/`. Four lenses (status consistency, conventions, end-to-end numerics, note integration) plus a
synthesis.

**Verdict.** "Ready after fixes", with no numerical mismatch:

- 10 major items: 6 for gdr, 1 for gdk, 3 for the note merge;
- about 35 minor items.

**End-to-end results:**

| quantity | agreement |
|---|---|
| C5(1) | 3.2e-34 |
| C5(2) | 2.0e-50 |
| C5(3) | 7.8e-46 |

The code for these sits in `review/joint/numerics-end-to-end/` and is rerun by `make -f public.mk replay`.

**Decisions D1–D6:**

- the layout: two sections pasted inline;
- one home for the product theorem, gdr:topG;
- one copy of the correction to the note's d = 3 section;
- symbol renames;
- one vocabulary for the 𝒦_d conditions (M), (J), (H);
- one review-status statement.

**What changed:**

- The gdr items G1–G16 were applied by C62d.
- The gdk items were applied by C63d (see the second part below).
- The note items N2–N10 were applied in the merge (C63d, 2026-10-03).

**Not applied:**

- G-H, which was needed only for the fallback layout, which was not used.

**Kept against the editorial rule that removes exploratory searches:**

- Section 20.6, "Further reductions tried" (G15), because Section 17 cites it.

The synthesized report `JOINT_REVIEW.md` is not shipped; only a TeX comment of the note cites it.

### 5. Post-merge check

Session C62d, read-only, 2026-10-03.

- Sections 20–21 equal the final fragments apart from comments.
- An independent build is clean (179 pages).
- `check_note` passes.

Re-verified on 2026-10-13 against note commit fa71533: Section 20 differs from the fragment `general_d.tex` in no
non-comment line.

### 6. Public-release replay (2026-10-13)

`public/replay.py` runs 115 checks, all PASS. Every number Section 20 quotes for this package is recomputed from the
records at its printed digits, and e2e.py, e2e_k3.py, check_d3.py, check_special.py, check_topG.py and the lemmaG
summaries are rerun.

It found two problems in the note:

- Section 20.7 prints 3·10⁻²¹ as the upper end of the pole-node check, but the record reaches 4.76·10⁻²¹. The text
  change is N9.
- The 10⁻⁵⁷ identity 𝔇_L = P̂′ − … of Section 20.4 had no record. `public/check_DL_Phat.py` now gives 2.2e-65.

### Recommendations not followed

None in substance. Where reviewers offered options, two choices were made:

- F23: the general-b theorems are stated and proved in Section 20 itself, rather than added to the note's
  periodization appendix.
- G-H: not needed under the layout chosen in D1.

### Never independently reviewed

- the derivation steps that the fragment only sketches (full derivations in L/, Z/, specialize/; rederived symbolically by
  the review);
- the literal summation of the differentiated pole-node series gdr:taylorLZ (confirmed only through b-derivatives);
- the d = 3 inputs from LRI_C5_d3: the Gamma form of ĉ₀ and the half-shift extension. These are numerical
  confirmations, not proofs (note Section 20.8).

## Section 21 (𝒦_d, `K_general/`; session C63d)

*This part was written by session C63d (`GFF/d3/K_general_for_C62d/REVIEWS_K_d.md`) and is merged unchanged.*

The dropped folders are:

- `K_general/*verify*`, `R_part_v*`, `refcheck_adv*`, `refverify`;
- `note_fragment/review_*`, `note_fragment/test_build_joint/verify_*`;
- the `workflow_result_raw.json` files.

All reviewers were Claude agents launched as workflow subagents by sessions C63d and C62d. There was no Codex review and
no human referee.

| review | reviewers, rounds | scope | verdict | what changed |
|---|---|---|---|---|
| Workflow wf_cdc3d90c-0ba (2026-10-02) | research agents for the S part, the R part, position space and the reference check, with three adversarial verifiers per claim (`R_part_verify*`, `R_part_vmodes`, `R_part_vnumK`, `S_part_verify`, `refverify`, `refcheck_adv*`, `refcheck_verify*`, `verify_*`) | S closed form, lattice and product forms, sample formula and arrays, finite-mode theorem, position-space representation gdk:KMB, the reference values of `references/reference_values.json`, 100-digit 𝒦_d | three verifiers per item failed to refute the exact items. One verifier refuted the per-spin two-mode periodization; the synthesizer rechecked it with controlled tails (agreement 1e-21..1e-28; at d = 0.8, 1e-11..1e-13). | Interim values were found wrong and superseded before use: 𝒦(1.25) = 17.2251… (relative error 1.3e-3), 𝒦(1.5) (3.8e-16), P4(0.8) (16 good digits) and Q(0.8) (8 good digits). The cause was the per-spin ν-tail with `HPG_NUTAIL=0`. The off-diagonal W3/W4 strings in `reference_values.json` are good to only 50 digits (flagged in `K_general/RESULT.md`). |
| Fragment reviews, three lenses (2026-10-03 03:00–03:14) | rigor (`note_fragment/review_rigor`), numerics (`review_numerics`, own Mathematica and Python checks), consistency (`review_consistency`, three independent test builds); then a recheck of the fixes (rigor and consistency, 12 items) | `note_fragment/K_d_fragment.tex` | fixes required (status labels, (M) as an identity of meromorphic functions, (H), several numbers); the recheck found 12 minor or typo items | Fix round 1 changed the d = 0.8 and d = 2 jets, the Abel–Plana claim at d = 2.75, the per-spin top modes and the position-space contours. Fix round 2 added the d ≤ 4/7 caveat, made r3(1) conditional on (M) only, and set the scope of "order at most three". |
| Joint review of gdr + gdk (2026-10-03; `review/joint/`, C62d's folder) | four lenses (status consistency, conventions, numerics end to end, note integration) and a synthesis | Sections 20 and 21 together, against the note | "Ready after fixes": no fatal issue, no numerical mismatch; for gdk, items K1–K12 (one major: the fragment's own Lemma duplicated gdr:topG); decisions D1–D6 | K1: the Lemma and its proof were deleted; the fragment cites gdr:topG (foundation Theorem 6), whose proof was independently reviewed (`review/lemmaG-proof`, ACCEPT) and probed (`review/lemmaG-numeric`, PASS). K6: r3 column to 34 digits (`check_r3_34.py`); three-node column at d = 1.5, 2.5, 3 from the joint review's circles; "exact" relabelled. Other items: wording and labels. |
| Repair rounds 1 and 2 of the joint-review fixes (2026-10-03 09:47 and 10:05) | Claude verifier agents on the fixed fragment (13 items, then 10 items) | the fixed fragment, `topmode/PROOF.md`, `K_general/RESULT.md` | all items resolved | All jet entries extracted through gdk:Ktau (`check_k3_routes.py`); the "A caution" paragraph quantified (`check_kbracket_d08_huge.py`; the old figure "relative error 0.96" corrected); r3 of 21.8 to 34 digits (`check_r3_special.py`). Then final nits (10:15). |
| Post-merge check (2026-10-03) | session C62d, read-only | note Sections 20 and 21 against the final fragments | PASS: identical up to comments, independent build clean, check_note passes | none |
| Public-release replay (2026-10-13) | `public/replay_K_d.py` (C63d) | every quoted 𝒦_d number of Section 21 | 70/70 PASS; 73/73 with `--recompute` | one body-text correction in 21.10: the "2e-13" of the double-precision identities |

Not independently reviewed, as note Section 21.11 states:

- the sharpness of H_q and the explicit constants of `note_fragment/growth/PROOF.md`;
- the proof text of `note_fragment/topmode/PROOF.md` as such;
- the position-space derivation gdk:MB and gdk:KMB.

Recommendations not acted on: none recorded.
