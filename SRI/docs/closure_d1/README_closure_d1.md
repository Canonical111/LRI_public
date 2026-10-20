# closure_d1: checks of the two-coupling closure and prescription arguments (d = 1 dual)

Two formal arguments by OpenAI GPT-6 astra (via ChatGPT), supplied by the author on 15 October 2026, bear on the
d = 1 dual: that two couplings close under its renormalization, and that the archive's prescription (package
`dual_d1`) extracts the local beta functions. Both arrived as separate notes. Since 16 October 2026 (author: each
direction of the release has exactly one TeX note) their content is in the SRI note, **Appendix D, "The two-coupling
closure and the prescription"** (`SRI/note/sri_short_range.tex`), and the two notes are not shipped. This package holds
the checks. It carries no quoted number.

What the arguments establish, and what they do not (SRI note, App. D.14):
- **Argued (formal, coefficientwise in g, h, delta; symmetry-preserving local subtraction; recursive forest
  construction):** every required bulk ultraviolet counterterm lies in span{1, O_g, O_h} (App. D.2), so only two
  nontrivial bulk counterterm directions occur at any order (h and b are two coordinates on one direction).
- **False, with a counterexample (App. D.6):** a literal two-operator Wilsonian truncation. O_g O_g generates
  :chi^2: (finite, irrelevant), and finite irrelevant terms feed the marginal beta functions.
- **Argued (formal) for the prescription (App. D.3, D.10 to D.13):** a collision at a fixed interval endpoint can only
  multiply the identity, so endpoint ultraviolet factors cancel in the vacuum-normalized responses, while the finite
  endpoint-source terms remain and are the archive's j and lambda terms; the two-response system then has the local
  beta function as its unique solution, up to a regular finite change of the two couplings, which leaves the
  stability invariants unchanged.
- **Not claimed:** a second numerical computation of C^SR_3 to C^SR_7, an audit of every historical integration, the
  identification of the dual with the chain, convergence at fixed delta, or the C^SR_8 zeta formula.

The SRI assessment (docs/closure_d1/REVIEWS.md; SRI note, App. D.15) agrees at the formal level; NRG confirms C^SR_3
to C^SR_5 independently of the dual.

`make -f public.mk test` (seconds; sympy for the last three rows) checks:
- the dated snapshot of the shipped files (`public/SNAPSHOT.sha256`);
- the closure argument's finite algebra, independently of its own companion script (not supplied): the charges of all
  29,523 matrix words of length <= 9, the radial-power identity, and the O_g O_g product;
- in `prescription/`, the prescription argument's archive as supplied, without its note: its `MANIFEST.json` (the two
  note files it lists are named in `public/NOT_SHIPPED.txt` and must be absent), its own checker
  `code/check_prescription.py` rerun (22 exact checks, equal to `verification/checks.json`), and an independent
  re-derivation of the beta recurrence b3..b9, h4..h8 from the finite-response system.
