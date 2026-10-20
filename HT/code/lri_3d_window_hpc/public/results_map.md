# d = 3 finite-coupling HT: every quoted number → record, command, tolerance

Scope: every d = 3 finite-coupling Hamiltonian-truncation number in the paper and in the HT note's d = 3 sections.
In the paper (main.tex, final text at commit a6772872):
- Table `tab:num3`, column "HT, N = 20", in Appendix "Numerical results" (`app: numerics`; `sections/app_numerics.tex`):
  ΔE at N = 20 for all 15 Ds (row NUM3);
- Fig. `fig:cmp2d3d`, right panel, green squares, in Sec. Results, subsection "Resummation" (`sec: resum`;
  `sections/resummation.tex`);
- the text of Sec. Results, subsection "Nonperturbative results" (`sec: nonpert`; `sections/nonperturbative.tex`),
  which gives the largest cutoff (row NMAX).

The paper uses two d = 3 macros of `numbers.tex`, `\HTnpDthreeNmax` and `\HTnpDthreeSR` (the Table `tab:num3` entry at
Ds = 0.518149). It prints the other 14 entries of the HT column of Table `tab:num3` as numbers. Rows marked "note:"
are quoted only in the HT note. Where such a row names a macro, `numbers.tex` still defines it, but the paper does not
use it. The check id is the row name in `make replay` and in the note's reproduction table.

Paths are relative to `HT/`. Records: `data/HT_3d/campaigns/<campaign>/results/<group>/x<Ds>/window_L<N>.json`
(campaigns `grid18` and `grid18sri` for N = 8–18, `grid20`, `grid20sri` and `l20x06` for N = 20). Commands run from
`code/lri_3d_window_hpc` (`make -f public.mk replay`) or `code/lri_3d_window_indep`, or from `HT/` as
`make replay`.

| check id | quoted (macro) | value | records | command | tolerance / rule |
|---|---|---|---|---|---|
| REC-MANIFEST, REC-RECORDS, REC-SRC | (integrity) | 105 records, 1 source hash | all `window_L*.json` of the table, `data/HT_3d/MANIFEST.sha256` | `make -f public.mk replay` | every file's sha256 as listed; `record_sha256` = sha256 of the record's canonical JSON; accepted; tuning residual ≤ max(1e-10, 5·3e-11); eigenpair residual ≤ 1e-8; measured Δσ = Ds and Δφ³ = 3 − Ds to 1e-9; the seed and basis inputs named in each record are the shipped files (sha256); every record's `source_sha256` equals `ht3d.hpc.source_hash()` of the shipped `code/` |
| TABLE | the note's Table d3:finiteN; its N = 20 row is plotted in Fig. `fig:cmp2d3d` (green squares) and printed in Table `tab:num3` (row NUM3) | ΔE(Ds, N), 15 Ds × N = 8…20 | the 105 records | `make -f public.mk replay` | rebuilt `finite_L_table.csv` identical, byte for byte, to `results/HT_3d/finite_L_table.csv` |
| CONFIG | note: teacher N_t = 6 with 24 states per parity of a 192-level oscillator, 20 kept; n_z = 16; tuning tolerance 3e-11; bath-state limits 1e7 (N = 16), 5e7 (18), 2e8 (20) | as stated | the 15 `teacher_L6.json` and the 105 window records (`configuration`, `basis_input.retained`) | `make -f public.mk replay` | exact |
| SIZE | note: J = 0 inversion-even bath states 110, 371, 1285, 4486, 15 815, 55 859, 196 585 at N = 8 … 20 | same | window records: `dimension` / (2 · `nz_per_parity`) | `make -f public.mk replay` | exact, the same at every Ds |
| PROJECTOR | note: gesdd → gesvd fallbacks in 8 of 17 335 blocks (N = 18) and 62 of 40 033 (N = 20); max \|J₊Q\| = 5.8e-15 | same | `scalar_projector_checks` of the N = 18, 20 records | `make -f public.mk replay` | exact counts; residual < 1e-14 |
| COST-L18 | note: N = 18 point (J = 1 diagnostics, 16 cores) 34–74 min, 38.5 GiB | same | window_L18 records (`elapsed_total_seconds`, `peak_rss_kib`) | `make -f public.mk replay` | integer minutes; 0.1 GiB |
| NMAX | `\HTnpDthreeNmax` = 20 | 20 | 15 × `window_L20.json` | `make -f public.mk replay` | largest N with an accepted record at all 15 Ds; exact |
| NUM3 | Table `tab:num3`, column "HT, N = 20": 1.41924 (`\HTnpDthreeSR`), 1.41951, 1.42026, 1.42182, 1.42435, 1.42923, 1.43511, 1.44218, 1.45062, 1.46053, 1.47192, 1.48486, 1.49360, 1.49674, 1.49993 at Ds = 0.518149 … 0.7499 | ΔE(Ds, 20) | 15 × `window_L20.json` | `make -f public.mk replay` | each ΔE(Ds, 20) rounded to 5 decimals equals the printed value |
| CONV-STEP | note: last step < 10⁻⁷ at Ds ≥ 0.74 (`\HTnpDthreeConvStep`) | 7.34e-8 | `window_L18`, `window_L20` at Ds = 0.74, 0.745, 0.7499 | `make -f public.mk replay` | max \|ΔE(20) − ΔE(18)\| < 1e-7 |
| MONO-STEPS | note: (2.2–6.1)×10⁻⁴ (`\HTnpDthreeMonoSteps`) | 2.218e-4 (0.625) … 6.073e-4 (0.518149) | `window_L18`, `window_L20` at 0.518149 ≤ Ds ≤ 0.625 | `make -f public.mk replay` | min and max of ΔE(20) − ΔE(18) to 2 significant digits |
| MONO-RISE | note: "rise monotonically" | strictly increasing, N = 8…20 | `window_L8`…`window_L20` at 0.518149 ≤ Ds ≤ 0.625 | `make -f public.mk replay` | every step positive |
| MONO-SHRINK | note: 8 to 19 percent (`\HTnpDthreeMonoShrink`) | 7.6 % (0.625) … 18.6 % (0.518149) | `window_L16`, `L18`, `L20` at 0.518149 ≤ Ds ≤ 0.625 | `make -f public.mk replay` | 100·(1 − d₂₀/d₁₈), dₙ = ΔE(N) − ΔE(N−2), min and max rounded to integers |
| NO-SHRINK | note: at 0.65 and 0.675 "the steps do not yet shrink" | d₂₀/d₁₈ = 0.992 (0.65), 1.225 (0.675) | `window_L16`, `L18`, `L20` at 0.65, 0.675 | `make -f public.mk replay` | d₂₀/d₁₈ > 0.99 at both |
| SR-L20 | `\HTnpDthreeSR` = 1.41924 (Table `tab:num3`); note: 1.41924, "still rises" | 1.41924372 | `grid20sri/.../x0.518149/window_L20.json` | `make -f public.mk replay` | ΔE(20) at Ds = 0.518149 to 5 decimals; d₂₀ > 0 |
| SR-GAP | note: "6.6×10⁻³ above the Ising value" | 6.618e-3 | the same record; Ising ΔE = 1.41262528 (cited) | `make -f public.mk replay` | 2 significant digits |
| BP-0.7 | note: continuum 1.47214(3) at Ds = 0.7 (`\HTnpDthreeBPerr` = 3×10⁻⁵) | 1.4721437 ± 2.9e-5 (29 approximants) | C₀…C₇ of d = 3 (main.tex Table `tab:pt`, Sec. Results, subsection "Around the generalized free field"; records in the GFF folder), in `public/bp_x07.py` | `make -f public.mk replay` (or `python3 public/bp_x07.py --x 0.7`) | median 1.4721437 to 1e-7; half-spread (max − min)/2 to 1 significant digit; n = 29 |
| BP-DEV | note: 2.2×10⁻⁴, "lies below it" and "moves away" (`\HTnpDthreeBPdev`) | 2.189e-4 | BP-0.7 and `grid20/.../x0.7/window_L20.json` (plus `grid18/.../x0.7/window_L16`, `L18`) | `make -f public.mk replay` | BP(0.7) − ΔE(0.7, 20) to 2 significant digits; ΔE(16) > ΔE(18) > ΔE(20), all below BP |
| C4-RATIO | note: 60 % (`\HTnpDthreeCfourRatio`) | 60.26 % | C₄ of the consistent window at L = 20, 0.7400078407, from `HT_Pert` (package `lri_ht3d_pert`, `results_expanse_2026-10/SUMMARY.md`), over C₄(3) = 1.228063545 | `make -f public.mk replay` (reads `../../../HT_Pert/results/HT_3d/SUMMARY.md`; set `PERT_SUMMARY=` to another copy) | ratio rounded to an integer percent; SKIP if the HT_Pert record is absent (the number is then replayed in HT_Pert only) |
| INDEP-TUNED | note: 2×10⁻¹¹ at N ≤ 12 (`\HTnpDthreeIndep`) | 1.89e-11 | `code/lri_3d_window_indep/results/cmp_*.json` (23 comparisons, N = 8, 10, 12) | `make -C code/lri_3d_window_indep -f public.mk replay` | max \|ΔE(indep, tuned) − ΔE(production)\| to 1 significant digit |
| INDEP-FIXED | note: "at the production couplings to at most 1.8×10⁻¹², with 16 or 24 local states" | 1.8e-12 | same | same | max over K = 16 and 24 at the production couplings ≤ 3e-12 |
| INDEP-RESID, INDEP-PKG | (integrity) | resid ≤ 9.5e-13 | same, plus the production records | same | every independent tuning converged to ≤ 1e-12; the production (r, g, ΔE) that each comparison used equal the shipped records and `indep_extract.json` exactly |
| COST-L20 | note only: "27–104 min and 84–87 GiB per N = 20 point; 239 min and 328 GiB at Ds = 0.6 with J = 1 diagnostics" | same | the 15 `window_L20.json` (`elapsed_total_seconds`, `peak_rss_kib`) | `make -f public.mk replay` | rounded to integer minutes and GiB |
| — | note: Ising value 1.41263 (`\HTnpDthreeSRexact`) | 1.41262528(29) | literature (bootstrap: Chang et al. 2024; Simmons-Duffin 2016) | not replayed | cited input; 1.41262528, the value SR-GAP uses, rounds to 1.41263 |

Not replayed here, by design:
- the continuum coefficients C₀…C₇ of d = 3 (inputs of BP-0.7): GFF folder (`GFF/results/C6_3`, `C7_3`, closed forms
  in `GFF/code/LRI_C5_d3`);
- C₄(L = 20) of the consistent window (input of C4-RATIO): HT_Pert;
- the comparison of the N = 20 values with the CB8 resummation in Fig. `fig:cmp2d3d`, and the "Resummed" and "MC"
  columns of Table `tab:num3`: Resummation and MC folders. The Resummation replay also checks the HT column of
  Table `tab:num3` against the `window_L20.json` records.
