# Reviews: c2_closed_d2

**2026-10-08, independent review by Claude Code (four separate reviews: physics and derivation; the special-function
reduction; an end-to-end numerical evaluation from first principles; code, reproduction and consistency).** The study
was not modified. Verdict: c_2 = -4.0662701481325... confirmed.

- End-to-end Monte Carlo of the full regulated 8D integral (bosonized Ising correlators; no Moebius map, elliptic
  cover, contact derivation or sector subtraction): c_2 = -4.075 +- 0.019, 0.5 sigma from the closed form; three
  configurations agree (chi^2 1.29 on 2 dof); stable over cuts -8 to -15; source-shape control 16.185 +- 0.053 against
  the predicted 16.150; validations of b_0, the vanishing O(g^2) energy shift, B_31 and z_21 = -b_0/2 (which gives
  Delta_sigma = 1/8 + delta). This also supports numerically the exchange-of-limits step the study leaves unproved.
  Shipped: `mc/`; replayed by `make -f public.mk replay`.
- The finite source-matching term -pi^2/(4 b_0) = -1.945 is required (without it c_2 = -2.12, excluded by the Monte
  Carlo at about 100 sigma); it is independent of the source shape and of the scheme (it is a_1'/b_0 of the natural
  scheme mapped into minimal subtraction).
- The elliptic finite part I = 4.3447446523188856... evaluated directly from its defining integral, without the
  reduction: agreement to 51 digits (one review) and to 5e-15 (z-plane integration, another). Not shipped (not cited
  by the paper).
- The reduction chain checked step by step at 30 to 80 digits (complex moments, Landen, symmetric moments, the 4F3
  evaluation, the telescoping certificates with their nonzero endpoint terms, P, Q, T to at least 50 digits, the Gamma
  ratio, every printed digit). PSLQ finds no Gamma-only relation, consistent with the study claiming none.
- b_0 = 1.2684043089 matches Behan-Rastelli-Rychkov-Zan (beta_3 = 1.268404, I_{d=2} = -0.403746); the O(g^2) energy
  integral vanishes in d = 2.
- Reproduction exact on Python 3.10, 3.12, 3.14 with the newest dependencies, on Linux, from a self-contained copy and
  at 100 digits; the note rebuilds byte-identically.
- No published O(delta^2) value exists in d = 2 (Behan-Rastelli-Rychkov-Zan, Behan-Lauria-Nocchi-van Vliet,
  later works and all 152 INSPIRE citations of the first give only Delta_eps = 1 + O(delta^2)).

Findings (the study ships unchanged; they qualify how it is read):

- Major: (M1) the regulator-uniform remainder bound for interchanging delta -> 0 with the nested subtracted integrals is
  not proved (disclosed by the study; now supported numerically at 0.5% by the Monte Carlo). (M2) The study's own
  numerical checks share the last step of the derivation (the map 16/R^2 - R^2/9 - ...); the upstream steps (the
  antisymmetric moment, the 16/R^2 term, the reflection matrix, the period formula, the residue interface) are checked
  only by exact certificates and pointwise checks in the package. The review reproduced them independently (C2 to
  7e-17 through the continued periods).
- Minor: a stated premise ("a_1 = 0 makes a_2 scheme independent") is false, the conclusion stands (only a_1(0) = 0 is
  universal; C_2 = a_1'/b_0 + h_0/b_0^2 is invariant); two discrepancy figures in the note are mis-rounded (2.531e-80
  and 1.405e-61 should read 2.530 and 1.404; the README is right); the Carlson discrepancy is set by the u = 200
  cutoff tail (1.74e-61), not by quadrature; inconsistent status labels across files ("candidate", "formal result",
  "unproved here"); `\pgfplotsset{compat=1.18}` blocks builds on TeX Live 2020/2021; one reference file
  (`inputs/reference/renormalization_reference.json`) is never compared by the code (manual comparison: agreement to
  its 5e-41 precision); a table caption overstates the check of I; `reproduce.py` does not clear stale raw outputs and
  fixes the analytic-bridge stage at 50 digits.
- Nits: notation reuse in Secs. 5-11, citations to add (Di Francesco-Saleur-Zuber 1987; the journal version of
  arXiv:2309.12772), the shipped `run_manifest.json` comes from the isolated run and carries the authoring machine's
  absolute paths, `.DS_Store` files (not exported), builder warning regex, an unreferenced figure, the figure PDF is
  not deterministic.

**2026-10-15, package build (Claude Code).** The Monte Carlo's per-chunk outputs of all three configurations survive
(A and B on symmetry, C on the personal desktop); the verbatim `summ.py` reprints the production lines exactly; the
recombination rule, reconstructed from the review's text (its script is lost), reproduces every number the review
prints. Without configuration C the same rule gives -4.0724 +- 0.0197 (not the quoted value). The shipped `c2mc3.c`,
built with the production flags, reproduces batch 0 of chunk A/1 bitwise on an AMD EPYC 7532 node (and to 1.6e-11 on
Intel), so the shipped code is the code that produced the chunks. Observed, not in the
review: the three configurations agree less well on the source-shape control (chi^2 7.6 on 2 dof, configuration C
2.6 sigma high) than on Omega_4 itself; the combined control still agrees with the prediction (pull +0.65).
