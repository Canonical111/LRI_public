# LRI_C6_D3_HPC: the sixth-order coefficient C6(3)

This package computes C6(3), the ε⁶ coefficient of Δε(d = 3, ε) of the long-range Ising model, with ε = 2s − 3.
It integrates the finite forest kernels of all six-loop graphs by randomized quasi–Monte Carlo (RQMC) and assembles
the result with the regulator-dependent fixed-point map. The method is described in the note (`GFF/note/`), Section 26,
"The three-dimensional production of September 2026" (label `prec:d3production2026`).

**Result.** C6(3) = 33.5754 ± 0.0005.
- Estimator 33.57542664131543, sampling standard error 0.0001185495235.
- The allowance is four sampling standard errors (0.00047) rounded up to a multiple of 0.0001. This rounding step is
  Amendment 1 (2026-10-01), made after the result was known. Under the step registered before the result, 0.001, the
  allowance would be ±0.001.
- The allowance covers sampling only. It is not a rigorous bound, and it does not cover the analytic power-sector
  compensation or the graph/renormalization framework, which this package takes over from the earlier calculation
  without redoing them.

| check (pre-registered gate) | value | gate |
|---|---|---|
| campaigns a and b: 33.57562307 ± 0.00015062 and 33.57523021 ± 0.00018311 | 1.66 combined SE apart | ≤ 3 |
| bootstrap SE / covariance SE (4096 resamples) | 0.973 | within ±20% |
| distance from the previous estimate 33.5681968 ± 0.0241840 | 0.30 previous SE | ≤ 3 |
| C3, C4, C5 against their special-function values | pulls −1.69, −1.09, +0.92 | \|pull\| ≤ 4 |

An independent seventh-order calculation in d = 3 (`GFF/code/LRI_C7_D3_HPC`) gives, as a by-product,
C6(3) = 33.57387 ± 0.00198, −0.79 combined standard errors away. It shares the graph and renormalization framework.

## What is where

| path (in `GFF/`) | content |
|---|---|
| `code/LRI_C6_D3_HPC/` | the production code: commit `1c6dfb3`, unchanged, pruned of history and evidence nobody reads |
| `code/LRI_C6_D3_HPC/public.mk`, `public/` | the public targets, the replay and verification scripts, Slurm templates (added for this release) |
| `code/LRI_C6_D2_HPC/reference/` | the archived refinement and baseline calculation that the tests and the replay read. It is shared with the C6(2) package: `make -f public.mk setup` links it as `reference/` |
| `results/C6_3/` | `CAMPAIGN.md` (log, pre-registered rule, result, Amendment 1, errata); `results_run-20260929-m8192/` with `C6_result.json`, `manifest.json` and per group `config.json`, `merged.json`, `graph_replicates.csv` |
| `data/C6_3/` | hosted, not in git (`make -f public.mk fetch-data`): `run-20260929-m8192_full.tgz`, the complete run directory with every checkpoint (74 MB) |

**`../LRI_C6_D2_HPC` must be present.** This package's `reference/` tree (148 MiB) is byte-identical to that of
`LRI_C6_D2_HPC` (the same git tree, `d4203b17…`, at both production commits), so the repository ships it once. The 75
files of it that the C6(3) tests and the replay read are listed in `public/REFERENCE_REQUIRED.txt`. The export of
`LRI_C6_D2_HPC` leaves out the TeX notes of that tree (the method notes of the earlier C6 calculations, copies of the
earlier research note, their templates and LaTeX artifacts; author rule 2026-10-16: one TeX note per direction; their
substance is in the condensed note, Section 26 and Sections 22-25). `public/dropped_paths.txt` names these 21 files, and
no test or replay reads them.

## Quick start

```bash
cd GFF/code/LRI_C6_D3_HPC
python3 -m pip install -r requirements.txt      # Python >= 3.10
make -f public.mk replay        # ~2 s, any OS: recomputes every quoted number, PASS/FAIL table in .work/replay/
make -f public.mk test-python   # ~1-2 min, any OS: pure-Python tests and the shipped-file check
make -f public.mk test          # Linux + GCC/OpenMP/libquadmath/Boost: builds the worker, then the same plus validate.py
make -f public.mk test-all      # ~6 min on 16 cores: every test target, including the archived-stream replay
```

`replay` uses the package's own code: `tools/production.py` checks every hash binding of the records, and
`tools/assemble.py` recomputes the estimator, the covariance, the campaign values, the lower-order pulls and the
bootstrap. It then applies the reporting rule and the gates, and recomputes the superseded estimates and the archived
values that the note compares with. `REPRODUCE.md` (GFF level) lists every step; `results_map.md` maps every quoted
number to its row.

## Changes from the production commit

None to any file of `1c6dfb3` that ships. The public copy:
- adds `public.mk` and `public/`;
- leaves out `reference/` (linked instead), most of `reference_d3/`, `provenance/`, and the benchmark and drill logs
  (`public/NOT_SHIPPED.txt` lists every file of the package checksum list that is not shipped);
- keeps `SHA256SUMS_HPC.json` verbatim. `tools/checksums.py verify` and `make check-delivery` therefore report the
  pruned files as missing; `public/verify_shipped.py` (run by `make -f public.mk test`) checks the shipped files
  against the same list and accepts exactly the documented omissions: `public/NOT_SHIPPED.txt` (including the TeX notes
  of `reference_d3/`) and `public/dropped_paths.txt` (the 21 TeX notes of the linked `reference/` tree, reported in
  one INFO line). Any other missing or changed file fails.

Reviews: `public/REVIEWS.md`.
