# Reviews of lri_3d_c4_exact

No AI code review (Codex or other) was run on this package. Its checks are numerical and are replayed:

- **Against an independent code.** The production package `lri_3d_hpc` builds the truncated Hamiltonian explicitly
  (supplied by the author, written by OpenAI GPT-6 astra; Expanse/symmetry port reviewed by Codex in 11 rounds). This
  package sums diagrams. They agree on C2..C5, r, g and the seed energies for every even L <= 20, raw and with the
  vacuum window, to 2.7e-13 or better (`make replay`, VAL-PKG-C4 and VAL-PKG-C5; `make test` repeats it with sums
  recomputed from scratch).
- **Against a brute force on the package's own operators.** The window schemes that the package does not have (W2,
  W3m, Wb, Wc, Zb) are built as explicit operators on the package's reference Hamiltonian at L <= 14
  (`eps5/brute3d_W5.py`) and agree to 4.3e-13; the zero-mode window at L <= 6 (`brute_zm.py`) to 1e-14.
- **Internal.** Window shifts by two independent routes (full engine against the cancellation-free window sums, 5e-9 at
  L <= 600); runs with different maximal cutoffs and quadratures (7e-10 at L <= 300 for C4, 1.4e-9 for the C5 shifts);
  regression of the final, memory-fixed eps^5 engine against the stored L <= 20 run (5e-13) and recomputation of all
  34 reduced L = 40 boxes (bitwise identical).

What the checks do not cover:

- They verify that the stated model is computed, not that the windows are the right ones. The complete window W and
  the eps^5 windows Wc, Wcs were derived in d = 2 after the d = 2 divergences were seen and with the continuum values
  known, and applied to d = 3 after the exact sums had shown the d = 3 divergence at eps^4. The chi window is used in its
  leading-order linear form, not derived for d = 3.
- The extrapolations: fit forms (towers from the d = 2 protocol) and fit windows were chosen after the data were seen,
  with C4(3) and C5(3) known. The C5 extrapolation is provisional: an L^-1/2 term, which L <= 40 cannot exclude, would
  move it by 0.5 to 1.
- This public overlay (`public.mk`, `public/`) was written on 2026-10-14 and was not reviewed by Codex.
