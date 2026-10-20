# Reviews of LRI_C5_d2_simplify (discovery and three further proofs of the d = 2 closed forms)

Claude Code session C62d wrote this package on 2026-10-01 and 02. It has two parts, reviewed differently.

## 1. The discovery (top level)

The discovery is:
- the exact square-lattice factorizations;
- the 70-digit Euler-Maclaurin single sums (job 567346, `confirm_dps70.json`);
- the PSLQ identification of L2 and K2.

No review lens examined it as such. It was checked independently twice:
- Session C63d evaluated L2 and K2 from the spectral kernel with a separate code. These are `GFF/code/LRI_C5_d3/wf_d2check` and the note's residuals 1.7e-79 and 3.1e-62. A first pass agreed to about 1e-12.
- Session C63d's five proof routes (`../LRI_C5_d2_proof`) compared their closed forms with the 70-digit record, to 3e-70 and better.

The note uses the discovery only as a numerical confirmation, not as a proof step.

## 2. The three further proofs (`proof/`)

Workflow `wf_6fd83950-f9b` of session C62d (2026-10-02, about 10:15 to 12:15) used three prover subagents:
- `L2-fourier`, by a Fourier (Cauchy beta) representation;
- `L2-elliptic`, by Hardy-space Parseval pairings and Landen;
- `K2-parseval`, by rim regularization of the spectral form.

Each route had two verifier subagents with fresh contexts. All six verdicts are ACCEPT:

| Route | Rigor verifier | Numerics verifier |
|---|---|---|
| L2-fourier | ACCEPT, no fatal or major gap | accept, every lemma to 1e-37..1e-41 at 40 digits (job 567989) |
| L2-elliptic | ACCEPT, no fatal or major gap; minor points m1, m2, m4, m5 | every displayed identity at 30 to 50 digits (job 567970) |
| K2-parseval | ACCEPT as a conditional theorem: the statements for `gs:Kseries` and `gs:Kdefinition` are conditional on the per-spin residue identity (S) and the mixed-trace step (T) | accept; per-spin families 1.2e-38, Laurent coefficients 5e-43, direct spectral sums 1e-31..1e-35 (job 568005) |

A synthesizer subagent then:
- wrote the synthesis `proof/PROOF_STATUS.md` and the merge-ready fragment `proof/proof_d2.tex` (both now merged into
  note Section 18 and not shipped);
- re-did the exact algebra (`proof/synth/`, all residuals 0);
- corrected the finder. Its PSLQ collapse form of L2 holds only through two lemmas, so the structural, lemma-free form is the one to quote.

The four minor points of the L2-elliptic rigor verifier were resolved in the fragment:
- the uniform Stirling citation;
- the chain rule in the collapse;
- the wording "Z-linear relation";
- the gs:* definitions listed as inputs.

Other terse points, which do not affect the claims, were listed in that synthesis.

**What happened to the fragment.** It was not merged into the note as text. The note merged C63d's insert and cites
these as "three further proofs". C63d's proof of the mixed-trace step at d = 2 (note Section 18.7) removes the condition
(T). C63d's merge review (`wf_8e8ab059-5ad`, see `../LRI_C5_d2_proof/REVIEWS.md`) corrected the note's sentence
describing these routes.

## Recommendations overruled

None.

## Never reviewed

- **The discovery scripts.** `factor_*.py`, `parallel_eval.py` and `emsum.py` were not code-reviewed. Their outputs are
  checked independently (see part 1), and the factorizations are re-derived term by term by
  `../LRI_C5_d2_proof/L2_singlesums/verify_symbolic.py` (48 terms identical).
- **The release overlay.** `public.mk` and `public/*` were not reviewed by another model. They were tested by running
  them:
  - test PASS with Python 3.10.11, mpmath 1.2.1 and 1.3.0, sympy 1.11.1 and 1.12;
  - replay PASS with Python 3.9.6 and 3.10.11, mpmath 1.2.1, 1.3.0 and 1.4.1.

## Not shipped

The verifier reports and the verifiers' numerical scripts and outputs:
- `proof/*/verify_rigor.md`, `verify_numeric.md`;
- `proof/*/verify_numeric/`, `verify_rigor_*.py`.

The note quotes none of their numbers. The verdicts are summarized above.
