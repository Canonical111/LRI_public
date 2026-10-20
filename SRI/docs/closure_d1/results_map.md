# results_map: closure_d1

The package carries **no quoted number**. The two arguments are in the SRI note, Appendix D (the paper and the SRI
note's caveat "Two-coupling closure" point there). Their finite claims are checked by `make -C code/closure_d1
-f public.mk test` (also `replay`):

| Claim (SRI note, App. D) | Rule | Tolerance |
|---|---|---|
| every nonzero matrix word in sigma_+, sigma_-, sigma_3 has Q in {0, +-1} and [sigma_3, M] = 2QM (29,523 words, length <= 9; D.5) | exhaustive enumeration with exact 2x2 integer matrices | exact |
| 2 sum_{i<j} q_i q_j = Q^2 - n for alternating charges (D.7) | n = 1..11 | exact |
| O_g O_g = 1/r^2 + (sqrt2/r) O_h + :chi^2: + O(r) (D.6) | midpoint Taylor coefficients with chi = (i/sqrt2) dphi | 1e-15 (coefficients) |
| the shipped files | `public/SNAPSHOT.sha256` | sha256 equal |
| the prescription archive as supplied | `prescription/MANIFEST.json`; `public/NOT_SHIPPED.txt` absent | sha256 equal |
| its supplementary algebra (matrix words, endpoint invariant, radial powers, normal-ordering cancellation, source chain rule, pair integrals at general L, recurrence through g^9, spectator and generator identities; D.15) | `prescription/code/check_prescription.py` rerun | 22 of 22 true, equal to `verification/checks.json` |
| the beta recurrence b3..b9, h4..h8 (D.13; SRI note Eq. (A.47) and App. C.3) | solved from J beta = R_1 order by order (independent of the argument's checker) | exact (sympy) |
