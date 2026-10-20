# Data: c2_closed_d2

No hosted data: everything ships in the package (333 verbatim files, 5.4 MB; about 2.3 MB packed).

| Path | Size | What |
|---|---|---|
| study (`code/`, `inputs/`, `outputs/`, ...) | 37 files, 0.28 MB | the convergence figure (0.12 MB) is the largest; the study's note (TeX and PDF, 0.6 MB) is not shipped since 16 October 2026 (content in the SRI note, Appendix E) |
| `mc/run_A/`, `mc/run_B/` | 2 x 129-130 files, 1.9 MB each | 64 chunk outputs (`out_<i>.txt`, 30 kB: header, counts, per batch the Gaussian-slice histogram `B`, the quartic-slice histogram `BS` and the finite-delta sums `BD`, 120 bins of 0.5 in Lambda from -58; then `HW2` and the ten largest weights), 64 empty `err_<i>.txt`, channel weights |
| `mc/run_C/` | 29 files, 0.46 MB | 14 chunk outputs, 14 empty `err_<i>.txt`, adapted weights |
| `mc/` top level | 5 files + 1 driver, 37 kB | code, drivers, weights of run A |

The Monte Carlo binaries and the production job logs are not shipped (`public/mc_production_logs.json` carries the
lines summ.py printed). Run-time products go to `.work/` (git-ignored by the repository's `.gitignore`).
