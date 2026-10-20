# d = 2 finite-coupling HT, campaign prod1 (Expanse, 2026-10-07 to 10-09)

`cluster/expanse/collect.py` wrote these tables on 2026-10-09 from the 348 records in `HT/data/HT_2d/prod1/chains`:
- 13 chains, Δσ = 0.125 … 0.495, with N = 8, 10, …, 24;
- main runs at nz = 16, with nested checks at nz = 20 and 12;
- three reference points (`ref0.126`, `ref0.250`, `ref0.400`) at N = 14 with 32 moving states per parity.

The L column of the code is the cutoff N of the paper.

| File | Contents |
|---|---|
| `points.csv` | one row per record: Δ_E (`Delta_thermal`), five even and five odd gaps, θ, g, r, residuals, cost. `max_jacobian_condition` also counts archived checkpoints, which are not shipped. |
| `nested.csv` | nz-check minus main at the same (chain, N): Δ_E and the ten lowest gaps |
| `descendants.csv` | descendant-spacing diagnostics (free-generator ancestry; `ambiguous` = overlap < 0.5, not a verified descendant) |
| `flags.txt` | 1678 "ambiguous descendant identification" flags; no thermal-jump or Jacobian-condition flags |
| `largest_N.csv` | new for the release: Δ_E at the largest cutoff of each chain, the last two steps, and the record. These are the d = 2 HT values of the paper's Fig. fig:cmp2d3d (left panel, green squares; main.tex, Sec. Results, subsection "Nonperturbative results") and, rounded to five decimals, of the HT column of Table tab:num2 (Appendix "Numerical results"): finite-N values, not continuum values. |

All values are finite-N values of the truncated model. No continuum limit is quoted in d = 2. Replay:
`make -f public.mk replay` in `HT/code/lri_2d_window_hpc`.
