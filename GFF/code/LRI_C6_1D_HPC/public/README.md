# Public scripts for LRI_C6_1D_HPC

These files were added for the public release (2026-10-13). Everything else in this folder is the package at git
commit cef6fa7 as it ran. The production ran at commit 8680864; the code differs from it only in three tools added
afterwards and a three-line change of one diagnostic in `tools/analyze.py`. The package's own `README.md` points
to `../LRI_C6_1D_HPC_loop/PLAN.md`; in this repository the plan is `../../results/C6_1/PLAN.md`.

| File | Purpose |
|---|---|
| `../public.mk` | targets `test`, `replay`, `smoke`, `rerun-lower`, `compare-rerun`, `clean` (`make -f public.mk <target>`) |
| `replay_c6.py` | the checks behind those targets; writes only to `.work/` |
| `requirements.txt` | Python packages for `test` and `replay` |
| `slurm/site.env.example` | site values for a production rerun (placeholders `<SCRATCH>`, `<ACCOUNT>`, `<PARTITION>`, …) |
| `slurm/adapt.py` | writes a site copy of the package with the symmetry lines of `cluster/` replaced (`SITE_CHANGES.txt` lists them) |
| `slurm/analyze_stage.sh` | final-mode analysis and stopping decision after each production stage (copied into the site copy) |

## Inputs

- `../../results/C6_1/`: the final records.
- `../../data/C6_1/levels/`: the 62 level records.
- `../../data/C6_1/runs/`: the 84 run files.
- `../../data/C6_1/analysis/`: resources at N* = 16, 18, 20.
- For the RR-002 rows, `C7_final.json` of LRI_C7_HPC, sha256 `b44b3a13…`. It is searched at
  `../../results/C7_1/` and `../LRI_C7_HPC/results/2026-09_expanse_v2/`; override with `C7_FINAL=<path>`.

## Status words in the tables

- **PASS / FAIL**: as usual. Any FAIL makes the target exit 1.
- **SKIP**: an optional input or platform is absent: `C7_final.json`; x86-64 Linux for `smoke`; an 80-bit long
  double for `rerun-lower`.
- **FLAG**: the shipped record and the wording of the condensed note disagree. The record is authoritative and the
  note text needs a fix. FLAG is not a failure. There is one: note Sec 22.4 says successive five-loop changes of C6
  are below 1e-11 from M = 24 on, but the records give up to 4.35e-9, which is U5/2.

## Expected results

- **Mac arm64, Python 3.10.11, mpmath 1.2.1:**
  - `test`: 41 PASS, 1 SKIP without `C7_final.json`. The package's `tests/test_tools.py` runs first, with 72
    checks.
  - `replay`: 124 PASS, 1 FLAG, about 30 s.
  - `rerun-lower`: 2 PASS and 1 SKIP. The long-double half is skipped on arm64.
- **x86-64 Linux:** `smoke` and the long-double half of `rerun-lower` are still to be run.
