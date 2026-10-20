# C7(3): every number the condensed note quotes, mapped to a file, a command and a tolerance

Group C7(3) (session C63d), 2026-10-13. Note: `GFF/LRI_condensed_note/long_range_ising_condensed.tex` at `fa71533`
(abstract l.64; Section 1 ll.103, 128, 145-146; Section 26.7 ll.10134-10139; Section 29 `app:C7d3` ll.11225-11370;
Section 33 row ll.12356-12367) and the note README (ll.45, 67, 79). Paths below are relative to `GFF/`.

**Command.** `make -C code/LRI_C7_D3_HPC -f public.mk replay` runs `public/replay_C7_3.py`: pure Python (numpy), about
10 s on one core, no compiler, no hosted data. It writes `code/LRI_C7_D3_HPC/.work/replay/REPLAY.md` and `replay.json`,
prints the table and exits 1 on any FAIL. Each row below names its replay row id. The "replayed" column is the local run
of 2026-10-13 (macOS arm64, Python 3.10.12, NumPy 1.24.4; `replay_local_run.txt`); on AMD EPYC 7532/7543 (AVX2), where the
production assembled, the floats are bitwise those of the records.

**Abbreviations.**
- `R` = `results/C7_3/run1-20260930-m4096` (the production records, byte-identical); `P` = `code/LRI_C7_D3_HPC`.
- **A** = `R/C7_result.json`, recomputed from the 20 `R/groups/*/merged.json` by the production commit's
  `P/tools/assemble.py` (`calculate(..., bootstrap=4096)`, 4de9412). The replay first checks that the manifest binds the
  shipped tools, inputs, configs and merged records (hash chain), then that every field of `C7_result.json` is reproduced.
- **G** = the consistency gates of `P/reverify_a6ce987/tools/assemble.py` (`gate_checks`, a6ce987) with the references
  `P/reverify_a6ce987/references/lower_order_d3.json` (C3-C5: special-function values; C6: the 2026-09-29 C6(3)
  campaign, 33.57542664131543 +- 0.00011855; archived C7(3)); expected values in `results/C7_3/run1_report_bb9d2ca.json`.

**Tolerances and why.**
- Quoted numbers: the replayed value must round to the printed string, i.e. lie within half a unit of the last printed
  digit (plus 1e-12 relative for last-bit noise of another CPU type).
- The 17-digit estimator: 1e-12 relative. The float64 assembly is bitwise on the CPU type that assembled it, but NumPy
  and OpenBLAS SIMD paths change the last bits elsewhere (4 ulp on an AVX-512 node of symmetry; 5e-16 on the Mac). The
  same rule is `tools/report.py`'s (EXISTING_REL).
- Whole-record comparison (`asm.production`): 1e-12 for C7, SE and coefficients; 1e-10 for every other float, scaled by
  the largest entry of its vector (assemble.rounding_difference of a6ce987). The bootstrap bias is a difference of
  numbers of the size of the coefficients and is judged on their scale (on the Mac it differs by 6e-14 absolute).
- Gates (`gates.report`): bitwise on AVX2 AMD; elsewhere 1e-8 relative. The power differences are cancellations (d4 =
  2e-6 is the difference of two numbers near 1.23, so one ulp of them is 1e-10 of d4; on the Mac the largest gate
  difference is 4.5e-11, in d5). The order-3 power difference vanishes in exact
  arithmetic, so its pull is a ratio of rounding noise and is checked only for being at the rounding level.
- Counts, hashes, strings: exact.
- CITED: the number rests on a record that is not recomputable from the shipped files. There are two such rows; the
  source is named.

## Identity and assembly rows (not quoted, but they carry the rest)

| replay row | check | result 2026-10-13 |
|---|---|---|
| `id.manifest`, `id.groups`, `id.merged` | run1 manifest sha256 eefa8432... = C7_result.source_manifest_sha256; 20 configs match the manifest; every merged.json has the right schema, manifest and config hash, payload hash, 64 replicates and jet shape; merged sha256 = C7_result.merged_sha256 | PASS |
| `id.tools`, `id.inputs`, `id.inputs_files`, `id.packs` | manifest tool_sha256 = shipped `P/tools/{production,assemble,common,prepare_inputs}.py`; inputs_manifest_sha256 5048b336... = `P/inputs/manifest.json`; small inputs and (after `setup`) the 10 packs match it | PASS (packs: SKIP before `make -f public.mk setup`, PASS after) |
| `id.cost_model`, `id.reverify_inputs` | `P/reverify_a6ce987/cost_models/gmp_symmetry_epyc7532.json` = run1's cost model (f815b1fa...); the re-verifier's inputs are byte-identical to the production inputs | PASS |
| `id.full_run` | `graph_replicates.csv` digests and byte-identity of the hosted full run directory | SKIP in `replay`; checked by `make -f public.mk reverify` |
| `asm.production`, `asm.metadata` | A: all 25 fields of `C7_result.json` | PASS (15 of 25 fields bitwise on the Mac, largest relative difference 6.4e-12, in the power correction; bitwise on AVX2 AMD per `run1_report_bb9d2ca.json`) |
| `asm.reverify`, `gates.*` | the a6ce987 assembly gives the same result and the gates of `run1_report_bb9d2ca.json`; no gate flagged; the report re-verified the same manifest and merged hashes, bitwise | PASS |

## The quoted numbers

### Abstract and Section 1

| quantity | quoted | replayed | source | tolerance | replay row |
|---|---|---|---|---|---|
| C7(3) = -220.35 +- 0.13 (4 SE rounded up to 0.01) | -220.35 +- 0.13 | -220.35 +- 0.13 | A | exact | `n.reported` |

### Section 1 estimator table

| quantity | quoted | replayed | source | tolerance | replay row |
|---|---|---|---|---|---|
| underlying estimator | -220.35448047392794 | -220.35448047392805 | A | 1e-12 relative (bitwise on AVX2 AMD) | `n.estimator` |
| sampling standard error | 0.0318188006 | 0.031818800575 | A | half a unit of the last printed digit | `n.se` |

### Section 29.1 Result and scope

| quantity | quoted | replayed | source | tolerance | replay row |
|---|---|---|---|---|---|
| 4 sigma-hat | 0.127 | 0.1272752023 | A | half a unit of the last printed digit | `n.4se` |
| power-free C7^pf(3) | -220.3723574 | -220.372357366 | A | half a unit of the last printed digit | `n.pf` |
| power-free SE | 0.0277073 | 0.0277073251594 | A | half a unit of the last printed digit | `n.pf_se` |
| power correction Delta_p C7(3) | 0.0178769 | 0.0178768920536 | A | half a unit of the last printed digit | `n.dp` |
| power correction SE | 0.0156478 | 0.0156478322911 | A | half a unit of the last printed digit | `n.dp_se` |
| complete C7(3) (table) | -220.3544805 | -220.354480474 | A | half a unit of the last printed digit | `n.full7` |
| complete SE (table) | 0.0318188 | 0.031818800575 | A | half a unit of the last printed digit | `n.full7_se` |
| first half-stream deviation from C7(3) | 0.034 | 0.0337990314248 | A | half a unit of the last printed digit | `n.half_dev1` |
| second half-stream deviation from C7(3) | 0.034 | 0.0337990295625 | A | half a unit of the last printed digit | `n.half_dev2` |
| 2D rule (max of 4 sigma and half-stream deviations) gives the same allowance | 0.13 | 0.13 | A | exact | `n.rule2d` |
| previous calculation reported -228 +- 16 | -228 +- 16 | -228 +- 16 (reference/README.md, verification/C7_full_result.json) | `P/reference/verification/C7_full_result.json` and `reference/README.md` | exact | `n.prev_report` |
| previous estimator | -227.6181095 | -227.618109475 | `P/reference/verification/C7_full_result.json` | half a unit of the last printed digit | `n.prev_est` |
| previous sampling SE | 3.8273969 | 3.82739687566 | `P/reference/verification/C7_full_result.json` | half a unit of the last printed digit | `n.prev_se` |
| new estimator minus previous, in previous SE | 1.90 | 1.89779874853 | A; `P/reference/verification/C7_full_result.json` | half a unit of the last printed digit | `n.prev_dist` |
| same, from the gate (archived C7, in archived SE) | 1.90 | 1.89779874853 | G | half a unit of the last printed digit | `n.prev_dist_gate` |

### Section 29.2 Kernel, normalization and coverage

| quantity | quoted | replayed | source | tolerance | replay row |
|---|---|---|---|---|---|
| integrated power-free classes, loops 3..7 | 5,16,76,395,2298 | [5, 16, 76, 395, 2298] | `P/inputs/manifest.json` (counts), `inputs/inventory.json` (primitive flags) | exact | `n.classes_free` |
| seven-loop classes: nonprimitive + primitive | 2254 + 44 | 2254 + 44 | `P/inputs/manifest.json` (counts), `inputs/inventory.json` (primitive flags) | exact | `n.classes_prim` |
| integrated power classes, loops 3..7 | 1,3,20,107,590 | [1, 3, 20, 107, 590] | `P/inputs/manifest.json` (counts), `inputs/inventory.json` (primitive flags) | exact | `n.classes_power` |
| kernels in all | 3,511 | 3511 | `P/inputs/manifest.json` (counts), `inputs/inventory.json` (primitive flags) | exact | `n.kernels` |
| denominators and weights unchanged from the 2D inventory (all kernels checked) | 3,511 checked | passed, 3511 | `P/reference/verification/dimension_checks.json` | exact | `n.structure` |
| b_{2,5} | 26.0214190551330710 | 26.0214190551 | `P/inputs/two_loop.json` (B2[5]) | half a unit of the last printed digit | `n.b25` |
| b_{2,5} digits (Decimal) | 26.0214190551330710 | 26.0214190551330710 | `P/inputs/two_loop.json` (B2[5]) | exact | `n.b25_digits` |
| two 65-digit evaluations, radii 0.04, 0.07, 64 and 80 Cauchy nodes | 0.04/64, 0.07/80 | [('0.04', 64), ('0.07', 80)] | `P/reference/verification/two_loop_checks.json` | exact | `n.b2_contours` |
| the two evaluations agree to | 3.3e-57 | 3.25175698462e-57 | `P/reference/verification/two_loop_checks.json` | half a unit of the last printed digit | `n.b2_agree` |
| agreement with the sixth-order input | 1.3e-54 | 1.31585423799e-54 | `P/reference/verification/dimension_checks.json` | half a unit of the last printed digit | `n.b2_c6` |
| independent Cauchy evaluations of the Gamma factors | 30 | 30 | `P/reference/verification/dimension_checks.json` | exact | `n.gamma_n` |
| Gamma-factor agreement | 8.3e-54 | 8.31788494544e-54 | `P/reference/verification/dimension_checks.json` | half a unit of the last printed digit | `n.gamma` |
| exact rational cases test the assembly | 64 | 64 | `P/reference/verification/assembly_checks.json` | exact | `n.assembly64` |
| C7(3) contains (3 c_{7,0} - b_{7,0})/6561 (Jacobian of the production assembly) | -1/6561, 3/6561 | -0.000152415790276, 0.000457247370828 | Jacobian of `tools/assemble.py` (4de9412) at the run1 means | exact | `n.c7_const` |
| three-loop power graph closed form -16 pi/15 | -16*pi/15 | -16*pi/15 | `P/reference/verification/dimension_checks.json` | exact | `n.b3_exact` |
| -16 pi/15 | -3.3510322 | -3.35103216383 | `dimension_checks.json` and -16*pi/15 computed | half a unit of the last printed digit | `n.b3_value` |
| production b_3^p(0) | -3.3510653 | -3.3510652602 | `R/groups/{a,b}_power_L3/merged.json` (column 0); closed form from `dimension_checks.json` | half a unit of the last printed digit | `n.b3_prod` |
| its sampling SE | 0.0000262 | 2.6214371623e-05 | `R/groups/{a,b}_power_L3/merged.json` (column 0); closed form from `dimension_checks.json` | half a unit of the last printed digit | `n.b3_prod_se` |
| pull from -16 pi/15 | -1.26 | -1.26252786143 | `R/groups/{a,b}_power_L3/merged.json` (column 0); closed form from `dimension_checks.json` | half a unit of the last printed digit | `n.b3_pull` |

### Section 29.3 The 2026 production

| quantity | quoted | replayed | source | tolerance | replay row |
|---|---|---|---|---|---|
| production worker byte-identical to the previous calculation (src/ = reference/src/) | identical | identical | `P/src/` vs `P/reference/src/` (sha256) | exact | `n.worker` |
| promotion thresholds 1e-9 (binary128) and 1e-23 (GMP) | 1e-9, 1e-23 | found in src/kernel.hpp | `P/src/kernel.hpp` line 166 | exact | `n.thresholds` |
| archived production rows replayed (job 566411) | 168,528 | 168528 | `results/C7_3/evidence/replay_report.json` (job 566411); rerun: `make -f public.mk archived-replay` | exact | `n.replay_rows` |
| share reproduced bit for bit, % | 96 | 96.1525681192 | `results/C7_3/evidence/replay_report.json` (job 566411); rerun: `make -f public.mk archived-replay` | half a unit of the last printed digit | `n.replay_bitwise` |
| largest normalized difference of the rest | 1.0e-11 | 1.01457341013e-11 | `results/C7_3/evidence/replay_report.json` (job 566411); rerun: `make -f public.mk archived-replay` | half a unit of the last printed digit | `n.replay_max` |
| identical promotion counts (20 groups) | identical | identical | `results/C7_3/evidence/replay_report.json` (job 566411); rerun: `make -f public.mk archived-replay` | exact | `n.replay_prom` |
| rebuilt previous estimator vs published | -227.61810947469922 vs -227.61810947469945 | -227.61810947469922 vs -227.61810947469945 (= verification/C7_full_result.json) | `results/C7_3/evidence/replay_report.json` (job 566411); rerun: `make -f public.mk archived-replay` | exact | `n.replay_c7` |
| independent high-precision reimplementation reproduced 13 archived rows, L3-L7, both sectors | 13 rows | CITED | `results/C7_3/REVIEWS.md`; rows can be rechecked with `make -f public.mk indep-rows` | not recomputable from shipped files | `n.indep13` |
| 64 vs 16 threads: rows, mismatches, binary128 and GMP promotions | 5,776 rows identical; 255,396 / 20,511 | THREADCHECK rows=5776 mismatches=0 quad=255396 mp=20511 | `results/C7_3/evidence/buildtest-566376.out` (THREADCHECK line) | exact | `n.threads` |
| AMD vs Intel: same rows and identical promotion counts | identical promotion counts | AMD64-vs-INTEL20 rows=5776 mismatches=5452 quad=255396 mp=20511 | `results/C7_3/evidence/intelcheck-566410.out` | exact | `n.cpu_counts` |
| AMD vs Intel: largest normalized difference | 2.0e-11 | CITED | `results/C7_3/CAMPAIGN.md` ("AMD vs Intel identity") | not recomputable from shipped files | `n.cpu_max` |
| 2.0e-11 relative to SE//C7/ (about 1e-7) | 1e-7 | 1.3850583711e-07 | derived: 2.0e-11 / (SE/abs(C7)) | order of magnitude | `n.cpu_rel` |
| 64 randomized replicates for every loop and sector | 64 | all 64 | `R/manifest.json`, `groups/*/config.json`; `P/inputs/inventory.json`, `reference/inputs/allocation.json` | exact | `n.reps` |
| campaign a: 52-bit nets, rate .8; b: 60-bit nets, rate .7 | 52/.8, 60/.7 | all groups | `R/manifest.json`, `groups/*/config.json`; `P/inputs/inventory.json`, `reference/inputs/allocation.json` | exact | `n.bits_rates` |
| frozen per-graph allocation of the previous calculation x 2^12, powers of two | x 2^12 | multiplier 4096 | `R/manifest.json`, `groups/*/config.json`; `P/inputs/inventory.json`, `reference/inputs/allocation.json` | exact | `n.alloc` |
| at least 64 points per stratum (before x 2^12) | 64 | 64 | `R/manifest.json`, `groups/*/config.json`; `P/inputs/inventory.json`, `reference/inputs/allocation.json` | exact | `n.alloc_min` |
| 44 seven-loop primitive classes at 2^22 points each per replicate (flat, 1024 x 2^12) | 2^22 | [4194304], primitive_points 1024 | `R/manifest.json`, `groups/*/config.json`; `P/inputs/inventory.json`, `reference/inputs/allocation.json` | exact | `n.prim` |
| one fresh base seed (delivered arithmetic offsets) | fresh | 4805754955154533039 | `R/manifest.json`, `groups/*/config.json`; `P/inputs/inventory.json`, `reference/inputs/allocation.json` | exact | `n.seed` |
| kernel samples in the two campaigns | 867,784,720,384 | 867,784,720,384 | `R/manifest.json`, `groups/*/config.json`; `P/inputs/inventory.json`, `reference/inputs/allocation.json` | exact | `n.samples` |
| 14 AMD and 14 Intel nodes | 14 + 14 | 14 + 14 | `R/lanes/node-*.out` | exact | `n.nodes` |
| completed on 1 October 2026 | 1 October 2026 | 2026-10-01T03:51:23-04:00 | `R/lanes/node-*.out` | exact | `n.completed` |
| campaign a | -220.3220 | -220.32200204 | A | half a unit of the last printed digit | `n.ca` |
| campaign a SE | 0.0431 | 0.0430751080241 | A | half a unit of the last printed digit | `n.ca_se` |
| campaign b | -220.3870 | -220.386958907 | A | half a unit of the last printed digit | `n.cb` |
| campaign b SE | 0.0468 | 0.0468431355199 | A | half a unit of the last printed digit | `n.cb_se` |
| first half stream | -220.3207 | -220.320681443 | A | half a unit of the last printed digit | `n.h1` |
| second half stream | -220.3883 | -220.388279503 | A | half a unit of the last printed digit | `n.h2` |
| combined | -220.3545 | -220.354480474 | A | half a unit of the last printed digit | `n.comb` |
| combined SE | 0.0318 | 0.031818800575 | A | half a unit of the last printed digit | `n.comb_se` |
| campaigns differ by (combined SE) | 1.02 | 1.02073092511 | G | half a unit of the last printed digit | `n.ab_pull` |
| error of C7 from free L=3 | 0.0000 | 4.17859712275e-05 | A | half a unit of the last printed digit | `n.err_free_L3` |
| error of C7 from free L=4 | 0.0006 | 0.000561789284622 | A | half a unit of the last printed digit | `n.err_free_L4` |
| error of C7 from free L=5 | 0.0034 | 0.00340837425533 | A | half a unit of the last printed digit | `n.err_free_L5` |
| error of C7 from free L=6 | 0.0119 | 0.0118620162592 | A | half a unit of the last printed digit | `n.err_free_L6` |
| error of C7 from free L=7 | 0.0248 | 0.0247981210591 | A | half a unit of the last printed digit | `n.err_free_L7` |
| error of C7 from power L=3 | 0.0000 | 1.56940104241e-05 | A | half a unit of the last printed digit | `n.err_power_L3` |
| error of C7 from power L=4 | 0.0002 | 0.000166116852874 | A | half a unit of the last printed digit | `n.err_power_L4` |
| error of C7 from power L=5 | 0.0014 | 0.00144226564532 | A | half a unit of the last printed digit | `n.err_power_L5` |
| error of C7 from power L=6 | 0.0058 | 0.00575832761904 | A | half a unit of the last printed digit | `n.err_power_L6` |
| error of C7 from power L=7 | 0.0145 | 0.0144769180295 | A | half a unit of the last printed digit | `n.err_power_L7` |

### Section 29.4 Checks

| quantity | quoted | replayed | source | tolerance | replay row |
|---|---|---|---|---|---|
| C3(3) by-product | -0.3535806960 | -0.353580695987 | G | half a unit of the last printed digit | `n.C3` |
| C3(3) sampling SE | 3.59e-7 | 3.59147894386e-07 | G | half a unit of the last printed digit | `n.C3_se` |
| C3(3) pull (reference -0.3535815204331724) | +2.30 | 2.29556065445 | G | half a unit of the last printed digit | `n.C3_pull` |
| C4(3) by-product | 1.2280727249 | 1.22807272492 | G | half a unit of the last printed digit | `n.C4` |
| C4(3) sampling SE | 8.52e-6 | 8.52384937029e-06 | G | half a unit of the last printed digit | `n.C4_se` |
| C4(3) pull (reference 1.2280635453276232) | +1.08 | 1.07693033118 | G | half a unit of the last printed digit | `n.C4_pull` |
| C5(3) by-product | -5.8503454757 | -5.85034547566 | G | half a unit of the last printed digit | `n.C5` |
| C5(3) sampling SE | 1.52e-4 | 0.000151754506044 | G | half a unit of the last printed digit | `n.C5_se` |
| C5(3) pull (reference -5.85035142075) | +0.04 | 0.0391757368838 | G | half a unit of the last printed digit | `n.C5_pull` |
| C6(3) by-product | 33.5738672 | 33.5738671978 | G | half a unit of the last printed digit | `n.C6` |
| C6(3) sampling SE | 0.0019782 | 0.00197818806385 | G | half a unit of the last printed digit | `n.C6_se` |
| C6(3) pull (reference 33.57542664131543) | -0.79 | -0.786907371165 | G | half a unit of the last printed digit | `n.C6_pull` |
| power correction at order 4 | 2.0e-6 | 2.01681068024e-06 | A | half a unit of the last printed digit | `n.pd4` |
| its SE | 2.1e-6 | 2.08277854548e-06 | A | half a unit of the last printed digit | `n.pd4_se` |
| power correction at order 5 | 4.0e-5 | 3.98275503821e-05 | A | half a unit of the last printed digit | `n.pd5` |
| its SE | 6.4e-5 | 6.43855836049e-05 | A | half a unit of the last printed digit | `n.pd5_se` |
| power correction at order 6 | -3.7e-4 | -0.000369881639912 | A | half a unit of the last printed digit | `n.pd6` |
| its SE | 10.2e-4 | 0.00101995121608 | A | half a unit of the last printed digit | `n.pd6_se` |
| order-3 power difference at rounding level | rounding level | -1.1e-16 +- 6.1e-15 | A | exact | `n.pd3` |
| seventh-order power correction | 0.018 | 0.0178768920536 | A | half a unit of the last printed digit | `n.pd7` |
| its SE | 0.016 | 0.0156478322911 | A | half a unit of the last printed digit | `n.pd7_se` |
| bootstrap replicate resamples | 4,096 | 4096 | A | exact | `n.boot_n` |
| bootstrap SE | 0.03204 | 0.0320400823926 | A | half a unit of the last printed digit | `n.boot` |
| covariance SE | 0.03182 | 0.031818800575 | A | half a unit of the last printed digit | `n.boot_cov` |
| previous power correction | -3.836223 | -3.83622337598 | `P/reference/verification/C7_full_result.json` | half a unit of the last printed digit | `n.prev_pc` |
| its SE | 2.007117 | 2.00711725703 | `P/reference/verification/C7_full_result.json` | half a unit of the last printed digit | `n.prev_pc_se` |
| distance in previous SE | 1.92 | 1.92021679577 | A; `P/reference/verification/C7_full_result.json` | half a unit of the last printed digit | `n.prev_pc_dist` |

### Section 26.7 (C6(3) section) by-product sentence

| quantity | quoted | replayed | source | tolerance | replay row |
|---|---|---|---|---|---|
| C6(3) by-product of the C7(3) production | 33.57387 | 33.5738671978 | G | half a unit of the last printed digit | `n.s26_c6` |
| its sampling SE | 0.00198 | 0.00197818806385 | G | half a unit of the last printed digit | `n.s26_c6_se` |
| combined SE from the C6(3) estimator | -0.79 | -0.786907371165 | G | half a unit of the last printed digit | `n.s26_pull` |

### Note README (lines 45, 67, 79)

| quantity | quoted | replayed | source | tolerance | replay row |
|---|---|---|---|---|---|
| estimator | -220.35448 | -220.354480474 | A | half a unit of the last printed digit | `r.est` |
| sampling SE | 0.03182 | 0.031818800575 | A | half a unit of the last printed digit | `r.se` |
| power-free | -220.37236 | -220.372357366 | A | half a unit of the last printed digit | `r.pf` |
| power-free SE | 0.02771 | 0.0277073251594 | A | half a unit of the last printed digit | `r.pf_se` |
| power correction | +0.01788 | 0.0178768920536 | A | half a unit of the last printed digit | `r.dp` |
| power correction SE | 0.01565 | 0.0156478322911 | A | half a unit of the last printed digit | `r.dp_se` |
| previous estimator | -227.618 | -227.618109475 | `P/reference/verification/C7_full_result.json` | half a unit of the last printed digit | `r.prev` |
| previous SE | 3.83 | 3.82739687566 | `P/reference/verification/C7_full_result.json` | half a unit of the last printed digit | `r.prev_se` |
| samples | 8.68e11 | 867784720384 | `R/manifest.json`, `groups/*/config.json`; `P/inputs/inventory.json`, `reference/inputs/allocation.json` | half a unit of the last printed digit | `r.samples` |

## The two CITED rows

- **13 archived rows reproduced by an independent mpmath re-implementation** (Sec 29.3). The code review ran
  `indep_rows.py` (now `P/public/indep_rows.py`, reference path made relative) on 13 rows across L3-L7 and both sectors:
  free rows to 1e-17-1e-19, power rows to <= 9e-13 (`results/C7_3/REVIEWS.md`). The list of the 13 rows was not
  archived. `make -f public.mk indep-rows ROWS='[...]'` rechecks any rows (hosted records needed); on 2026-10-13 three
  rows gave 9.1e-13 (power L3), 5.7e-18 (free L4) and 3.4e-19 (free L3) (`replay_local_run.txt`).
- **AMD vs Intel: at most 2.0e-11 normalized** (Sec 29.3). From `results/C7_3/CAMPAIGN.md` ("AMD vs Intel identity",
  job 566410) and the code review. The shipped log `evidence/intelcheck-566410.out` confirms the 5,776 rows and the
  identical promotion counts (255,396 binary128, 20,511 GMP), but the per-row comparison output was not archived.
  `make -f public.mk smoke` repeats this kind of comparison against run1's own checkpoints.

## Specialist targets that recompute cited evidence (cluster node; not part of `replay`)

| evidence | shipped record | command | node, runtime | tolerance |
|---|---|---|---|---|
| archived-stream replay (Sec 29.3: 168,528 rows, 96% bitwise, rest <= 1.0e-11, identical promotions, -227.61810947469922) | `results/C7_3/evidence/replay_report.json` (job 566411) | `make -f public.mk fetch-data records archived-replay` | x86-64 Linux, 64 cores; 95 s at 64 threads on AMD EPYC 7532 | same rows; identical promotion counts; max normalized difference <= 1e-10; rebuilt C7 and SE within 1e-10 relative |
| thread identity (5,776 rows, 0 mismatches, 255,396/20,511 promotions) | `results/C7_3/evidence/buildtest-566376.out` | not rerun by a target (the delivered thread check used a plan of job 566376); `tests/validate.py` of `make test` checks 1 vs 4 threads | - | - |
| re-verification of run1 by data identity, incl. `graph_replicates.csv` | `results/C7_3/run1_report_bb9d2ca.json` | `make -f public.mk fetch-data reverify` | any machine, Python >= 3.10; about 1 min, 0.6 GB disk | `public/compare_report.py`: identical identity fields; C7, SE, coefficients within 1e-12; gates within 1e-8 |
| production slice (rerun job indices 0, 320, 192 of run1) | run1 checkpoints in the hosted tarball | `make -f public.mk fetch-data smoke` | 64-core x86-64 node with the test toolchain and SciPy 1.17.1; about 2-3 min | `public/compare_smoke.py`: identical task coordinates and promotion counts; values bitwise or within 1e-10 normalized |

## Section 33 paths

`section33_row.tex` gives the public row. Every path it names exists in the export: `results/C7_3/run1-20260930-m4096/`
(C7_result.json, manifest.json, groups/*/config.json, groups/*/merged.json), `results/C7_3/CAMPAIGN.md`,
`results/C7_3/evidence/replay_report.json`, `results/C7_3/REVIEWS.md`, `code/LRI_C7_D3_HPC/` (4de9412),
`code/LRI_C7_D3_HPC/reverify_a6ce987/tools/report.py`, `code/LRI_C7_D3_HPC/reference/`, and the hosted
`data/C7_3/run1-20260930-m4096_full.tgz` and `data/C7_3/reference_records.tar.gz` (`make fetch-data`).
