# R3b `dd` development on Expanse (Stage 4c; PLAN A-FLAG-3/4; site deviation U1)

Development evidence of the double-double profile (branch `flag-dd`, worktree `LRI_C8_D2_HPC_wt_dd`), never a gate
record. Design and error analysis: `docs/NUMERICS.md`, "R3b: the double-double tier". Code: `src/numerics/dd.hpp`
(`NX_FLAGS_dd = -mavx2 -mfma`). Tests: `tests/test_dd_profile.py` (Mac, mpmath), `tests/dd_accuracy.cpp` (Expanse,
120 digits), the profile's F1 checks (`C8_NX_F1_CHECKS`).

## Scripts (`scripts/`)

- `submit_dd.sh dev|speed PKG [--after JOB] [NAME=VALUE ...]`: the Mac driver, with the H7E-R admission and the agent
  share of `C8_S4C_TAG=dd` before its only sbatch (records in `../admission/dd/`). The export and its build are the
  framework's (`C8_S4C_TAG=dd C8_S4C_PROFILES=dd bash ../scripts/submit_s4c.sh precheck|build`).
- `dd_dev.slurm` (shared, 32 CPUs, 1 h limit): the accuracy test, the development variants, F1 at `F1_SCALE` (0.25)
  with its own exact baseline, `dd_dev.py summary`.
- `dd_speed.slurm` (one exclusive compute node, 30 min limit): the accuracy test, the variants, F4 (L8 sweep sample,
  3 interleaved repeats, medians) for each executable of `SPEED`, F1 at `F1_SCALE` (1) for `bin/c8d2_gmp_dd` and each
  executable of `F1_EXTRA` against that baseline, summary.
- `dd_dev.py variants|accuracy|summary`: development variants of `bin/c8d2_gmp_dd` compiled from its own build-record
  command plus `-DC8_DD_DEVELOPMENT` and definitions (with build records, so `numerics_flags.py --profile dd
  --profile-exe` accepts them): `dd_direct` (`C8_DD_ROUTING=0`), `dd_dens` (`C8_DD_GUARD=1`), `dd_never`
  (`C8_DD_RATIO=1e300`, `C8_DD_CASCADE_LOW=0`: no dd value accepted, every point continues to `nx::quad_tier`).

## Jobs

Final profile binary: `bin/c8d2_gmp_dd` `51614820…` (commit ab2a822, export ab2a822a10e5, build 54673841). Every build
job checked A-RPL-8: `bin/c8d2_decimal` `99a51c1d…` and `bin/c8d2_gmp` `1d2a2181…`, byte-identical to the final
default binary, and the preprocessed default program token-identical to b47b008's.

| Job | What | Result |
|---|---|---|
| 54673652 (`shared` 16, 0:33) | `precheck` of the working tree | default executables identical; `bin/c8d2_gmp_dd` and its F1 tool compile (`precheck/`) |
| 54673689 (`shared` 16, 0:40), export bb1a3c945482 | `build` | A-RPL-8 holds; `bin/c8d2_gmp_dd` `37cf09b7…` (`s4cbuild.54673689.0/`) |
| 54673690 (`shared` 32, 2:06), export bb1a3c945482 | `dev`: accuracy, variants `dd_direct`, `dd_dens`, F1 at scale 0.25 | F1 development run (would pass) for all three: 38,400 points, 17,713 dd-accepted, 2,231 cascaded to binary128 (all pass), 3,791 to MP (all would fail binary128); no guard trip, so `dd_dens` = `dd`. Accuracy bounds met; the job's status 1 came from the test's `exact_ops` row, whose bound 0 did not allow for the 120-digit reference's own conversion floor (7e-97 u²), fixed in dd17198 (`s4cdd.54673690.0/`) |
| 54673763 (`shared` 16, 0:43), export dd171982f690 | `build` | A-RPL-8 holds; `bin/c8d2_gmp_dd` `37cf09b7…` again (`s4cbuild.54673763.0/`) |
| 54673764 (`compute` <NODE>, 4:42), export dd171982f690 | `speed`: accuracy; F4 `dd` and `dd_direct`; F1 at scale 1 for `dd` and `dd_never` | scalar segment sums. F4 lane-thread s (median of 3): exact 1,205.0 vs `dd` 922.7 (×1.306; free ×1.347, power ×1.221); exact 1,206.3 vs `dd_direct` 1,159.4 (×1.040; free ×1.074, power ×0.970). F1 153,600 points: development run (would pass); `dd_never` identical to the exact path at every point (`s4cddspeed.54673764.0/`) |
| 54673815 (`shared` 16, 0:37), export b4ad81beea16 | `build` | A-RPL-8 holds; `bin/c8d2_gmp_dd` `56ae3ecc…` (the timer code, compiled out, moved the layout by 16 bytes) |
| 54673816 (`shared` 32, 0:48), export b4ad81beea16 | `dev`: variant `dd_timers`, F1 at scale 1 against 54673764's baseline | per call dd ×4.07–4.33 faster than binary128; segment sums 56–83% of the dd time at 5.4 cycles/addend (`s4cdd.54673816.0/`) |
| 54673841 (`shared` 16, 0:37), export ab2a822a10e5 | `build` | A-RPL-8 holds; final `bin/c8d2_gmp_dd` `51614820…` (`s4cbuild.54673841.0/`) |
| 54673842 (`compute` <NODE>, 5:25), export ab2a822a10e5 | `speed`: accuracy; F4 `dd` and `dd_direct`; F1 at scale 1 for `dd`, `dd_never`, `dd_timers` | 4-lane sums. F4: exact 1,210.0 vs `dd` 871.7 (**×1.388**; free ×1.442, power ×1.279); exact 1,209.9 vs `dd_direct` 1,106.4 (×1.094; free ×1.136, power ×1.006): **cascade kept**. F1 153,600 points: development run (would pass), dd max relative error 5.2e-12, forced guards 96,018 × 2 exact, ratio decades split at 1e-23 with no miss; `dd_never` identical at every point; per call dd ×5.86–7.97 faster than binary128, sums 2.3–2.7 cycles/addend. Accuracy test passed (`s4cddspeed.54673842.0/`) |

Cost: 86,304 core-seconds = 24.0 SU for the nine jobs (`sacct.txt`), no job live at the end. One admission record
(`../admission/dd/`, 2026-10-05T05:51Z, a `dev` job) has no submission: its sbatch named a mistyped export path and
was refused by Slurm before any job existed; it was resubmitted as 54673816. The 450-digit reference files of the F1
baselines stay on Expanse (`$C8_DATA/evidence/<sha12>/<run>/f1_*/f1_baseline/refs/`, pinned by sha256 in each
`baseline.json`); the exports bb1a3c945482, dd171982f690, b4ad81beea16 and ab2a822a10e5 (about 6,500 files each)
stay under `$C8_DATA/pkg/`.
