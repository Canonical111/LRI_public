# Results index

**In preparation.** Every number quoted in the Article and its Supplemental Material will be listed here, generated from `results.json`.

| Macro | Quantity | Value | Status | Folder | Command | Tolerance |
|---|---|---|---|---|---|---|

## What `make replay` covers

`make replay` in a topic folder recomputes the quoted numbers from the records shipped in git. Some checks need more
than that and are not part of the basic replay:

- **MC.** The cited 1D refits need the block archives and merged summaries (`make fetch-data`; hosting planned) and a
  multi-core node. The P1 calibration needs no archive but a 16-core node (about 7 min, `make calibration`). Both are
  documented in `MC/REPRODUCE.md`.
- **GFF.** `make test` and `make replay` need no download. The `replay-full` targets, the C8(3) native tests and the
  production reruns need hosted files (sizes and sha256 in `GFF/data/DATA.md`; hosting planned on Zenodo, no record
  yet). See `GFF/REPRODUCE.md`.
- **NRG.** Every record is in git. `make replay` also reads the MC scan table `MC/data/1d/scan_data/FIT_V3_SCAN.json`
  for the method comparison, so keep `MC/` next to `NRG/`.
- **HT.** Every replay needs only git. `HT/code/lri_3d_window_hpc` reads the d = 3 C4 ratio from
  `HT_Pert/results/HT_3d/SUMMARY.md`, so keep `HT_Pert/` next to `HT/`. A d = 3 production rerun at the largest
  cutoff first rebuilds its static cache (193 GB, about 9 h on one node; `HT/REPRODUCE.md`).
- **HT_Pert.** Every replay needs only git. `test` and `smoke` of the d = 2 and d = 3 solvers need Linux x86-64 (80-bit
  long double) and a C++17 compiler with OpenMP; the `test` of the d = 2 independent check needs python-flint. The
  d = 3 vertex stores are not hosted; a production rerun rebuilds them (`HT_Pert/REPRODUCE.md`).
- **Resummation.** `make test` and `make replay` need no download. `make check-inputs` (also part of `make replay`)
  compares the frozen inputs in `Resummation/data/inputs/` with the live files of `GFF/`, `HT/`, `NRG/` and `MC/`, so
  keep those folders next to it; the short-range inputs are SKIP until `SRI/` is published. `make figures` needs Wolfram
  Language (`wolframscript`); the replay checks the plotted data instead.
