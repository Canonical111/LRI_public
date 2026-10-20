# Reviews of closure_d1

Since 16 October 2026 the two notes reviewed here are not shipped; their content is in the SRI note, Appendix D ("The two-coupling closure and the prescription"; the review's checks in App. D.15). Below, "the note" and "the first note" mean the closure argument, "the second note" the prescription argument.

**SRI assessment (Claude Code, 15 October 2026), at the author's request.** Verdict: *narrowed* (the operator content
is closed formally; the matching of the archived prescription is open).

1. The proof is sound as a standard perturbative (power-counting, Epstein-Glaser) argument; no gap found that changes its
   conclusion. It is a careful sketch: the uniform scaling bounds in the shape sectors and the sufficiency of a finite
   Taylor jet are asserted, not estimated in detail; the forest/extension step is invoked from the cited theorems.
   Checked independently: the classification at dimension <= 1 under shift symmetry, internal reflection and parity;
   the charge selection rule for all word lengths (29,523 words of length <= 9 enumerated); the radial-power identity;
   the O_g O_g product; the delta-log deformation coefficientwise; symmetric extensions by group averaging; the h <-> b
   frame change, identical to the archive's.
2. The archive's prescription does not obviously implement the local subtraction; the audit is genuinely open. Risks:
   (i) the beta functions are solved from exactly two projected responses (a square system), so a mis-assigned
   endpoint or external-insertion logarithm would be absorbed silently; (ii) all responses live on one unit interval,
   with the current resummed into endpoint sources and no endpoint hard core, so endpoint and bulk logarithms are not
   separated by construction; (iii) the finite-delta matching is the exact normal-ordering factor, coefficientwise a
   regular redefinition, but its equivalence to the local scheme is unproved; (iv) current resummation and (v) vacuum
   normalization are low risk.
3. Empirically, NRG at Delta_sigma = 0.01 agrees with the series through C^SR_5 at the size of its error (the residuals
   after C^SR_2 .. C^SR_5 are 4.7e-3, 9.8e-4, 2.4e-4, 5.3e-5; the NRG error there is 4.7e-5, so the last residual is 1.1
   times it), so C^SR_3 to C^SR_5 are confirmed by a description that knows nothing of the dual; C^SR_6 and beyond are
   at or below its resolution. (Corrected 15 October 2026: the last residual was first given as 5.0e-5, computed from a
   rounded NRG value; 5.3e-5 is the full-precision value the paper quotes.)

The author approved the resulting caveat (SRI note, Sec. "Caveats", item "Two-coupling closure") on 15 October 2026.

**SRI assessment of the second note (Claude Code, 15 October 2026).** Verdict: the prescription link is *closed at the
formal level*, at the same level of rigour as the first note. Checked: the endpoint power counting (one fewer free
coordinate, so endpoint divergences only for reference dimension <= 0); the endpoint classification (the invariant
dimension-zero sector is the identity, so endpoint ultraviolet factors are scalars that cancel in the normalized
responses); that the finite endpoint-source terms survive and are the archive's j and lambda terms (b3 = C3,1 + 2 v j1
= 1, against 5 without j1); the exact normal-ordering cancellation (sqrt2 b0 h - h^2 + (b0 - sqrt2 h)^2/2 = b0^2/2) and
eta = sqrt2 b0 h - 2h^2; the two-kink interval integrals at general L, a (the endpoint logarithm in the identity
channel, the current logarithm in the bulk); and the beta recurrence b3..b9, h4..h8, re-derived from J beta = R_1 and
equal to the archive's formulas. The logic is not circular: local renormalization for arbitrary spectators is
constructed first, and invertibility of the response system is used only for uniqueness. Stated rather than shown in
detail: the sharp-edge limit from smooth switching, the recursion relating the hard-core regulator to the local
subtraction when exclusion regions do not factorize, and the far-field probe projection. The author approved the
strengthened caveat on 15 October 2026.
