# Reference values used for comparison only

None of these values enters any fit, selection or label. They are used only in the comparison tables of the note.

| file | content | provenance |
|---|---|---|
| `theory_1d_CB8.csv` | d = 1: eight-loop resummed Δε at the 20 MC couplings, with band | Copied from the resummation package of the accompanying article, `resummation/update_2026-10-13/C8_1_ext/pipeline_K8/plot_data_1d_K8.json` (SHA-256 `0976ecc4…`), derived from `results/curve_K.csv` there (`54feec33…`). Prescription: K = 8 CB8 baseline, endpoint-v construction (v = 1 − 2√Δσ), N = 8, b_L = 3, α = 0, with the final C8(1) = 8 059 766.72. The band is the union of the core bands of K = 5…8 (N = 6–8, b_L = 2–4, α = −1, 0, 1). |
| `theory_2d3d_CB8.csv` | d = 2, 3: eight-loop resummed Δε at the 16 MC couplings, with band | `resummation/{2d,3d}/results/curves.csv` (2026-10-12; SHA-256 in the file). 2D: `curvature_CB8` with `curvature_core_low/high`. 3D: `slope_CB8` with `slope_core_low/high`. 3D s = 1.95 is linearly interpolated between neighbouring grid rows. |
| `literature_1d.csv` | published 1D Monte Carlo values, converted to Δε = 1 − 1/ν where ν is quoted | Uzelac–Glumac–Aničić 2001; Angelini–Parisi–Ricci-Tersenghi 2014; Luijten, PhD thesis 1997 (Table 5.4); Tomita 2009 (nonequilibrium relaxation) |
| `literature_2d.csv`, `literature_3d.csv` | published 2D/3D values (Monte Carlo, bootstrap, functional RG), each row with source, location in the source, method and caveat | compiled for the article's comparison section |

**The bands are sensitivity ranges, not confidence intervals.** Do not call them errors and do not convert them to σ. Two further caveats:
- In 2D the band excludes the dependence on the endpoint construction, which can move the curve by up to 7.5 × 10⁻³ for
  0.15 ≤ Δσ ≤ 0.30. At the eight MC couplings, the largest deviation of the other constructions of `curves.csv` (`direct_CB8`,
  `value_CB8`, `tangent_CB8`) from `curvature_CB8` is:

  | s | 1.05 | 1.1 | 1.2 | 1.3 | 1.4 | 1.5 | 1.6 | 1.7 |
  |---|---|---|---|---|---|---|---|---|
  | max deviation | 0.0000 | 0.0000 | 0.0005 | 0.0023 | 0.0047 | 0.0057 | 0.0070 | 0.0055 |

- The 3D baseline uses the short-range crossover slope c₁ = 0.27315, which is itself conditional (working range 0.269–0.276).

The frozen pre-campaign reference `data/1d/reference/published_and_epsilon_reference.csv` (six-loop, older C6(1)) is kept unchanged as
part of the record. `data/DATA.md` describes its columns.
