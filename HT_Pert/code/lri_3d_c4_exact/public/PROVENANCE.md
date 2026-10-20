# Provenance of lri_3d_c4_exact

## Who wrote it

Written for the author by Claude Code (Claude Opus 5.5), session HT3dPert, through a forked sub-agent, on
2026-10-12 (C2..C4) and 2026-10-12/13 (C5). The model-independent eps^5 modules (`eps5/rs.py`, `chains.py`,
`assemble.py`, `windows5.py`, `windowsW.py`, `schemeW.py`, `bloch.py`), the window definitions (W, Wc, Wcs) and the fit
library were ported from the d = 2 exact-sum package written by the Claude Code session HT2dPert (shipped in
`HT_Pert/code/lri_2d_coeff_independent_check`), with the d = 3 changes listed in `README.md` Sec. 7.1. The model is
pinned to `lri_3d_hpc/reference` (supplied by the author; written by OpenAI GPT-6 astra via ChatGPT).

## History (git)

| Commits | Date | What |
|---|---|---|
| `fa696f6` .. `07f93c0` | 2026-10-12 | C2..C4 engine, validation against the package, windows, brute force with a zero-mode window, fits |
| `667e052` | 2026-10-12 | C2..C4 results to L = 600 and window shifts to L = 8000; the complete window W converges to C4(3) |
| `bcb4b8c` .. `ef7f042` | 2026-10-12 | eps^5 engine, brute force with explicit window operators, leg response, tagged channels, C5 to L = 20 |
| `c7a23fe` .. `d45be4c` | 2026-10-12/13 | engine speed-ups (exact Racah sum, streaming, cached 4-vertex boxes) and memory fixes |
| `2e4ae6f` .. `d5afa4f` | 2026-10-13 | raw C5 to L = 40, analysis, README; regression of the final engine |

Shipped at `d5afa4f` (code identical to `d45be4c`, the engine of the L = 40 run; later commits change only results,
README and `eps5/fits5.py` output). Two production files changed after the C2..C4 runs: `c4lib3d.py` (mode tables
generalized to higher eps order for eps^5, `bcb4b8c`) and `c4_run3d.py` (selectable multiprocessing start,
`e3ab454`). `make test` recomputes C2..C4 at L <= 40 with the shipped code and compares with the production
`results/c4_L600.npz` (2.4e-12 measured; tolerance 1e-9 for the different angular quadrature).

## Production runs (symmetry cluster)

| Job(s) | Partition | Output |
|---|---|---|
| 573804 | debugq | `results/c4_L200.npz`, `c4_L300.npz` (34 s, 174 s) |
| 573808 | debugq | `results/windows_L8000.npz`, `offdiag_L8000.npz` |
| 573812, 573817 | debugq | `results/dchi_L600.npz`, `dchi_L1000.npz` |
| 573841 | preq | `results/c4_L600.npz` (C2..C4 at every even L <= 600; 1953 s on one node) |
| 573888 | sharedq | `results/c5_L12.npz` |
| 573920-573923, 573933 | sharedq | `results/c5_L20.npz` (every scheme, L <= 20; four shards and the assembly) |
| 573948 | sharedq | `results/c5raw_sp_L20.npz` |
| 573899, 573993 | sharedq | `results/dC5_L200.npz`, `dC5_L600.npz` (scheme shifts; 3 min, 2 h 56 min) |
| 573893 | sharedq | `results/eps5/legw_L400.npz` |
| 573892, 573905, 573931, 574289 | sharedq | brute force (`results/brute`, `tag`), descendant checks (`results/eps5/desc_L*.json`, L <= 16), tagged chi channel |
| 574287 | defq | `results/c5raw_all_L40.npz` (raw C5 at every even L <= 40; 1 h 45 min on one 80-thread node, 20 workers) |
| 574029, 574030, 574365 | sharedq, defq | regressions of the final engine (`results/regress/`): L <= 20 to 5e-13; all 34 reduced L = 40 boxes bitwise |

Failed and cancelled attempts (out of memory at L = 20 and 40 before the memory fixes, and at L = 56 after them; profiling) are listed in
`README.md` Sec. 7.5; none produced a shipped result. The analysis scripts (fits) ran on a personal desktop. The
longest shipped runs are 573993 (2 h 56 min on 8 cores), 574287 (1 h 45 min on one node), the L = 16 brute force
574289 (1 h 34 min) and the regressions 574030, 574365 (1 h 18 min, 37 min); the others took minutes.

## Later use

- 2026-10-14: the author adopted the extrapolated C2..C4(3) and the C5 footnote for the paper's d = 3 column of
  Table htpert, replacing the finite-cutoff ratios of `lri_3d_hpc`. The values were rounded by the PDG rule from the
  shipped fit summaries; `make replay` recomputes them.
- 2026-10-18: the author moved C5(3) from the footnote into Table 2 (delta 3e-2, marked provisional in the caption).
  The paper is final at `a6772872`: Table 2 (`tab:htpert`, Sec. 3.1), d = 3 column.
- The comparison with the production package (`validate_pkg.py`, `eps5/validate5.py`) is the d = 3 independent-code
  check: the package (GPT-6 astra) builds the truncated Hamiltonian explicitly; this package sums diagrams.
