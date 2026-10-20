# Reviews of LRI_C5_d2_proof (proofs of the d = 2 closed forms of L2 and K2)

Claude Code session C63d wrote this package on 2026-10-02 in workflow `wf_2604cddc-2ec`. Five independent subagents each
wrote a proof route:
- `L2_singlesums`
- `L2_structural`
- `K2_selberg`
- `K2_d1template`
- `K2_gauss`

All reviewers below were Claude subagents of the same session, each with one lens and a fresh context. No OpenAI Codex
or other external reviewer was involved. The raw review material is not shipped: the lens folders, the verdict file and
the merge review. The exception is the check records listed at the end, which are computations, not prose.

## Stages

| Stage | Reviewer | Rounds | Verdict | What changed |
|---|---|---|---|---|
| Proof routes | three lenses per route: algebra, numerics, rigor | 1 per route; `K2_d1template` 2 | all 15 final verdicts "sound" | see below |
| Merged note text | five lenses of workflow `wf_8e8ab059-5ad`: rigor, consistency, numerics, crosscheck, typesetting; then two rechecks | 1 + 2 rechecks | all "minor-fixes"; recheck 1 "minor-fixes"; recheck 2 "ready" | see below |

### Proof routes

- **`K2_d1template` revision.** Round 0 led to the revision `K2_d1template_fix1/` and `proof_v2.md` (merged into note
  Section 18, not shipped), which supersedes
  `PROOF_K2.md` (not shipped):
  - Theorem 1 is now proved from the position-space integral alone (Riemann bilinear relation, Stokes);
  - the kite factorization is no longer an input;
  - the spectral derivation became Corollary 2.
  Round 1 found no gap.
- **Minor points raised and fixed in the note text:**
  - the domain of the exponential form in Lemma 1.1, |u| < min(x, 1-x);
  - uniform Stirling bounds cited (DLMF 5.11);
  - closing arcs of the K2_gauss contours stated;
  - Thomae at negative argument justified by the identity theorem;
  - the boundary value K(1-x-i0) on the negative axis displayed;
  - the domain of the well-poised Barnes integral stated.
- **Reviewers' own numerics.** The reviewers re-ran the checks at higher precision than the provers: 1e-82 for the L2
  jets; 54 to 68 digits for the K2 master. The note quotes these numbers.
- **Choice of main proofs.** `L2_singlesums` for L2 and `K2_selberg` for K2; the note reproduces both in Sections 18.6
  and 18.7. The other three routes are cited as companion proofs.

### Merged note text

- **Issues raised:** 46, of which 4 major:
  - the series bullet counted -AU/4 twice (rigor 1, consistency 2);
  - a stale sentence after `fp:P5two` (consistency 1);
  - the description of session C62d's three further proofs (crosscheck 1).
- **Fixes:** 44 applied.
- **Rechecks:** recheck 1 found 5 wording points, which were fixed; recheck 2 returned "ready". C63d then merged the
  text into the condensed note.

## Recommendations overruled

One, in the review of the merged text. The numerics lens proposed (optional item 2) to say that the 70-digit K2 check
ran "after the rim deformation". This was rejected because it would misdescribe the computation: that value comes from
the theta -> 0 strip limit of the factorized single sums (`LRI_C5_d2_simplify`). The concern behind it was addressed
by the strip-limit wording proposed by the rigor and crosscheck lenses.

## Never reviewed

- The three further proofs of session C62d (`../LRI_C5_d2_simplify/proof/`) were not reviewed in this workflow. They had
  their own verifiers; see that package's REVIEWS.md.
- The note's own residue proof of the series (`gs:Kseries`) and the identification of `gs:Lseries` with the
  wheel-derivative master were not re-audited as such. The note proves both readings at d = 2 through the routes
  above.
- The release overlay (`public.mk`, `public/*`) was not reviewed by another model. It was tested by running it:
  - replay PASS with Python 3.9.6 and 3.10.11, mpmath 1.2.1, 1.3.0 and 1.4.1, sympy 1.11.1 and 1.12;
  - test PASS with Python 3.10.11, mpmath 1.2.1 and sympy 1.11.1.

## Check records shipped from the review folders

These are reviewers' computations (scripts and their outputs, no prose) that back numbers the note quotes.
`public/replay.py` reads them, or re-runs them where that is cheap.

| Folder (files) | Backs | Replay |
|---|---|---|
| `review_L2_singlesums_numerics_r0/` (`s3_modes.wl`, `s3.log`, `em.wl`, `s1_values.m`, `s3_residuals.m`) | note l.5145-5146 "hold to 10^-82" | read `s3.log`; Mathematica re-run in `replay-wl` |
| `review_L2_structural_numerics_r0/` (`spec_job.py`, `spec_job.sh`, `spec_analyze.py`, `spec_{2_5,1_2,3_5}.json`, `spec_568067.out`) | note l.5181-5182 "2x10^-70" | re-run with `public/spec_analyze_scaled.py`. The shipped `spec_analyze.py` stops with a singular matrix; the scaled copy reproduces the reviewer's 1.5e-71, 1.6e-70 and 5.6e-71 |
| `review_K2_d1template_numerics_r0/` (scripts, `run.sb`, and the `logs/` that the merged proof cites; 10 uncited round-0 logs are not shipped) | note l.5444-5446 "between 38 and 68 digits at seven values of tau"; the `rev/` rows of the merged proof's checks | read `logs/rC*.log` |
| `review_K2_selberg_numerics_r0/` (`partA2_direct2d.py`, `.out`, `partA2_0.3.log`, `spectral_hp.py`, `spectral_hp55*.out`) | note l.5448-5450 "between 18 and 25 digits", "54 digits" | read the outputs; `spectral_hp.py` needs `../LRI_C5_d3/wf_d2check` |
