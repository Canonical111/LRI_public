# review_indep: two independent re-implementations of a0, b0 and c_1

Written by Claude Code review agents on 2026-10-07 for the review of this package; shipped verbatim (sha256 in
`../public/SNAPSHOT.sha256`). Neither imports the package: each reads a spectrum file given on the command line and
prints a0, b0 and c_1 = a0/b0 of the retained 60-primary spectrum.

| Folder | Blocks | Integrals | Command (the review's finest settings) |
|---|---|---|---|
| `indep/` | `indep_blocks.py`: the Dolan-Osborn quadratic Casimir equation derived with sympy and solved as a double power series in z or rho | `indep_a0b0_v2.py`: the note's integrals with its own quadrature in (r, theta) and its own subtraction radius | `python indep_a0b0_v2.py ../../data/inputs/retained_spectrum.json 128 0.2 44` (about 45 s; also writes `indep_a0b0_n128_r0.2_K44.json` here) |
| `physics_review/` | `kps_blocks.py`: the Zamolodchikov-type recursion of Kos, Poland and Simmons-Duffin (arXiv:1406.4858), d = 3 | `indep_a0b0.py`: the other arrangement of Behan, Rastelli, Rychkov and Zan (arXiv:1703.05325, Method 2), power divergences subtracted analytically | `python indep_a0b0.py ../../data/inputs/retained_spectrum.json --NS 34 --nr 160 --na 160 --r0 0.3 --q 4` (about 25 s; run it from this folder) |

`make -f public.mk replay` (from `..`) runs both in a copy and requires |c_1 - c_1(package)| <= 1e-12 for each and
between the two (the SRI note, Table 2: two independent implementations agree to 10^{-12}; \SRthreeConeImplDev is note only). Measured on symmetry (Intel Xeon
6148 and AMD EPYC 7532): c_1 within 6e-14 (indep) and 5e-13 (physics_review) of the package's 0.2731524238260165,
and the two within 4e-13 of each other; a0 and b0 within relative 2.3e-13 (indep) and 2.1e-12 (physics_review).
