# C7(1): quoted numbers -> records, commands, tolerances

Note = `GFF/LRI_condensed_note/long_range_ising_condensed.tex` at commit fa71533 (abstract l. 63; Section 1 tables
l. 103, 126 and allowance passage l. 139-141; Section 22 l. 8152-8160; Section 27 "Full seventh order in one dimension"
l. 10431-10928; Section 30 table l. 11544; Section 33 row l. 12342). The section numbers are unchanged in the current
edition (01c3f5d, review of 15 October 2026), where the Section 1 allowance passage became a table of rules with the
C7(1) paragraph below it and the Section 27 zero-pole sentence reads "71.6 above the uncontrolled". REPORT = `GFF/results/C7_1/REPORT.md` (68dc6be).
All paths below are relative to `GFF/`. `R` = `results/C7_1/`, `F` = `R/C7_final.json`, `A` = `R/combined_assembly.json`,
`P` = `code/LRI_C7_HPC/`.

Commands: Tier 1 `make -C code/LRI_C7_HPC -f public.mk replay` (git only, about 5 s, one core; 214 checks, table in
`code/LRI_C7_HPC/.work/replay7_tier1.txt`). Tier 2 `make -C code/LRI_C7_HPC -f public.mk fetch-data replay-full`
(hosted records; about 7 min, one core, < 2 GB; run 2026-10-13 on Expanse from the unpacked archive, job 54901438: 14 checks PASS).

Tolerance rules (Tier 1):
- **exact**: integers, strings, lists of labels or seeds, SHA-256 values.
- **sum 1e-12**: re-summation of the stored component means/covariances in the production order (assemble.py); the
  replay reports whether the result is bitwise identical (it is, on the Mac: every row "bitwise").
- **batch 1e-12 / 1e-10**: per-batch values rebuilt as 399 x (combined component) + retained primitive: C7 to 1e-12
  relative, SE to 1e-10 relative (observed max differences 3.5e-10 absolute on C7 ~ 3e5 and 8.5e-14 on SE ~ 200).
- **quoted**: the recomputed value rounded to the quoted number of digits equals the quoted text (rounded up for the
  allowances and the tree-point bounds, which the sources round up); one REPORT digit that is truncated instead of
  rounded is a WARN.
- **RECORDED**: needs the raw replicate streams; Tier 1 checks the recorded value and the arithmetic around it, Tier 2
  recomputes it (floats to 1e-12 relative, bootstrap SE to 1e-12 or WARN within 5% if NumPy's stream differs).

## Headline and estimator

| Quoted | Where | Source / recomputation | Tolerance |
|---|---|---|---|
| C7(1) = −322550 ± 41 (the paper: ± 40, PDG rounding of 40.35; the note rounds the allowance up) | abstract, Sec 1 table, eq. c7f:answer, REPORT | K (P/reference/verification/full_affine_assembly.json) + sum of the 9576 estimator components of F (`components`, order of `sources`); allowance = ceil_2sf(max(4SE, 2\|R6\|+4SE_R6, 2\|R7\|+4SE_R7, half-split shift)+0.01) | sum 1e-12; quoted; allowance exact |
| estimator −322549.8888129889, SE 10.08791295 | Sec 1 estimator table | as above; SE = sqrt(cov77) | sum 1e-12; quoted |
| −322549.889, 10.088; bootstrap 10.111 | c7f:answer text | as above; bootstrap RECORDED (`F.bootstrap_se`) | quoted; Tier 2 |
| ±41 is the pre-registered policy, does not include truncation | Sec 1, c7f | candidates below | exact |
| −322524 ± 38 (truncation-aware, post hoc) | Sec 1, eq. c7f:truncationAware, REPORT | E6 + R7 + R7·r/(1−r), r = R7/R6 (C7 slots of `check_levels.refine7`, `power_levels.refine6`); σ = SE ⊕ SE_R7 ⊕ tail = 18.6; 2σ rounded up = 38 | quoted (ceil for 38) |
| step +10.40 ± 0.43, tail +15.59, ratio 0.600 (10.395/17.329), E7 −322539.5, −322523.9 | c7f, c7f:checks table, REPORT | same | quoted |
| shift +26, +26 + 2SE ≈ 46; intervals [−322591, −322509], [−322562, −322486] | REPORT | same | quoted |

## Production, levels and allowance

| Quoted | Where | Source / recomputation | Tolerance |
|---|---|---|---|
| 399 batches (b001–b400 except b215) | c7f:production, REPORT, R/inclusion.txt | `A.batches` labels; seeds = sha256("C7-expanse-2026-09:batch:k")[:8] LE | exact |
| replicates 128 (power-free), 128/64 (coarse A/B), 128, 128, 64 (1→3, 3→5, 5→6), 64 (6→7 check) | c7f:production | `components[*].replicates` | exact |
| weights: power-free 1/2 each, coarse 2/3 and 1/3, refinements 1, primitive 1 (each /399) | c7f assembly | `A.sources[*].weight` vs P/tools/production.py specs() | exact |
| primitive −696179.472 ± 0.867 (REPORT −696179.47 ± 0.87; variance (0.8667)²); retained −696147.446 ± 25.368; 1.26 combined SE | c7f, REPORT | component `primitive/P1`; `A.retained_primitive_crosscheck` (= P/reference/verification/C7_assembled_result.json) | sum 1e-12; exact; quoted |
| 44 primitive classes; 2^23 points, 64 replicates | c7f, REPORT | P/reference/inputs/L7_coord.txt (primitive && !power); P1 manifest (hosted, Tier 2) | exact |
| about 2.5×10^5 core-hours | c7f:production; REPORT "about 250k core-hours (SU) for all batches, plus about 20 for P1 and about 60 for the combines" | R/production_run.json (recorded text) | recorded |
| resolution sequence −331309.98/6.14, −322614.21/9.21, −322567.22/10.01, −322549.89/10.09 (REPORT one decimal) | c7f table, REPORT | prefix sums K + free + primitive + coarse + refine3 + refine5 + refine6 | sum 1e-12 vs `F.resolution_sequence`; quoted |
| corrections +8695.78/6.86, +46.99/3.93, +17.33/1.21, +10.40/0.43 | c7f table | level sums of the components | sum 1e-12; quoted |
| step ratios 0.37 and 0.60 | c7f | R6/R5, R7/R6 | quoted |
| candidates 40.35, 39.50, 22.49, 12.58 (REPORT 40.4, 39.5, 22.5, 12.6); archived policy ±1000 | c7f, REPORT | 4SE; 2\|R6\|+4SE_R6; 2\|R7\|+4SE_R7; max\|half_i − C7\| (half splits RECORDED) | sum 1e-12; quoted |
| χ² = 348.9 for 398 dof | c7f, REPORT | per-batch C7_b, SE_b rebuilt from components; centre = C7 − (P1 − retained); Σ(C7_b − centre)²/(SE_b² − 25.3678²) | batch 1e-12/1e-10; chi² 1e-9; quoted |
| bootstrap 10.11 vs 10.09 | c7f, REPORT | RECORDED | Tier 2 |
| halves −322537.30, −322562.47 | c7f | RECORDED (`F.half_splits`) | Tier 2 |
| power-free A/B agree within 0.42 combined SE | c7f | campaign aggregates tprodA/B_L5..7 (max 0.422) | quoted |
| 24 spurious poles, max \|z\| 2.31 | c7f, REPORT | `F.spurious_pole_checks` (means RECORDED; z = mean/SE recomputed) | Tier 2 |
| controlled estimate 71.6 ± 41.0 above the uncontrolled −322621.5 ± 41.1 (the record's control field is uncontrolled − controlled = −71.6) | c7f, REPORT | `F.zero_pole_control`, `F.raw_uncontrolled` (RECORDED; total = Σ per L and uncontrolled − controlled recomputed) | Tier 2 |
| flag "C5 differs from its reference by −4.15 SE" | REPORT | regenerated from the lower-order checks | exact |
| 17 transient step failures, each resubmitted once | REPORT | R/resubmitted_elements.txt | exact |

## Lower orders and truncation

| Quoted | Where | Source / recomputation | Tolerance |
|---|---|---|---|
| C5 −731.174185 ± 0.008355 vs −731.139477 (exact); C6 14332.435930 ± 0.305002 vs 14331.687033 | c7f:checks table | coefficients[5,6], sqrt(cov); references from P/tools/assemble.py REFS and the C6(1) result (14331.68703277, optional cross-check with results/C6_1/C6_final.json) | sum 1e-12; quoted |
| z −4.15 / −1.88 / −0.30 (C5), +2.46 / +0.97 / −0.22 (C6, new exact) | c7f:checks, Sec 22, REPORT addendum | (value + step [+ tail] − ref)/own SE | quoted |
| C6 14332.43593 ± 0.30500, 14331.98210, 14331.62055 | Sec 22 (l. 8152), REPORT | same | quoted |
| C6 vs old reference 14331.77075: +2.18/+0.69/−0.49 (own SE), +1.97/+0.63/−0.45 (with SE 0.14344) | REPORT | same | quoted |
| tail ratios 0.408, 0.443, 0.600; C6 correction −0.815; reference's 14332.554 → 14331.755, then −0.007: −0.81 | c7f, REPORT | R7/R6 per coefficient; cited values found in P/reference/long_range_ising_complete.tex | quoted; exact (string) |
| differences from the new C6: +0.74890, +0.29507, −0.06648 | REPORT addendum | same; −0.066486 is truncated in the REPORT (rounded −0.06649) | quoted; WARN |
| C3 = −3.71985632290349, C4 = 45.4248801371166; discrepancies 1.5e-12, 3.4e-8 | c7f:checks | K (deterministic low-loop assembly) vs REFS | quoted |

## Inherited construction (reference/, the September 2026 archive)

| Quoted | Where | Source | Tolerance |
|---|---|---|---|
| 3986 classes, 125894580 labelled graphs, 1091 power, 845 nonzero 3c7−b7, 44 primitive | c7f inventory | P/reference/inputs/L7_coord.txt, L7_inventory.txt (Σ 8!/\|Aut\|), exact_zero_L7.txt | exact |
| 691 exact-zero classes; 151 of the 845 are zeros, 694 integrated; 24 and 132 at L5, L6 | c7f | same, L5/L6 | exact |
| monomial table (1/1 ... 4164/2935), all differences zero | c7f | P/reference/verification/forest_exact_checks_new.json | exact |
| 44 representatives matched to 14 periods | c7f | P/reference/verification/primitive_coverage_new.json | exact |
| 84 exact Jacobians; Z = (L+1)!L for L = 1..7; 32 exact rational tests | c7f | P/reference/verification/affine_and_tree_exact_checks.json | exact |
| 650 digits, 60 cases, 1.18e-14, 3.45e-18 | c7f | P/reference/verification/tree_point_checks.json (1.1734e-14, 3.4420e-18, rounded up) | exact; quoted (ceil) |
| four-loop degree 16 → 20 moves C7 by < 0.001 | c7f | P/reference/verification/lower_resolution_check.json (9.4e-4) | exact |
| binary128 replay on 112 degree-7 elements: 2.8e-12 vs 1.9e-11, worst 4.2e-14 (A5 not met: 9 of 112, 18×) | c7f, REPORT | P/docs/NUMERICS.md (recorded); rerun: `tests/check_quad.py` on a cluster node (C++ build) | cited (string) |

## Archive, v1 and the note README

| Quoted | Where | Source | Tolerance |
|---|---|---|---|
| archive −323405.3, SE 5861.8 (REPORT −323405 ± 5862, ±24000; note README (−3.23 ± 0.24)×10^5) | note README, REPORT | `tools/assemble.py --original` (about 1 s) vs P/reference/verification/C7_assembled_result.json and P/tests/fixtures/assemble_original_0227dc5.json | sum 1e-12 (bitwise on the Mac); exact |
| z = 0.15 against the archive | REPORT; note README "0.15 of its sampling error" | (C7 − archive)/hypot(SE, SE_archive) = 0.146 (also 855.4/5861.8) | quoted |
| v1 (46 batches): −322554 ± 39, ±160; z = 0.11 | REPORT | R/v1_46batches/C7_final.json; z ignores that v1's batches are a subset | quoted |

## Tier 2 only (hosted records)

`replay-full` reruns `tools/combine.py` (verbatim, commit 7320afc) on the merged records with a light campaign verifier and
compares `combined_assembly.json` and `C7_final.json` with R byte for byte (else floats to 1e-12 relative, the two fields that assemble.py forms as differences of nearly equal numbers (applied_zero_pole_control_C7, lower_order_checks[].difference_over_sampling_se) to 1e-12 of their inputs, bootstrap WARN within 5%). Byte-identical on Expanse
(2026-10-13) and symmetry Intel Xeon 6148 (2026-10-14); on symmetry AMD EPYC 8534P C7_final.json differs in the last bits
(C7_full and sampling_se by 1 ulp) and passes at these tolerances; combined_assembly.json is byte-identical there too.
It also checks: every hosted merged stream against the SHA-256 recorded in F; one executable (sha256 33bab738...) and one
design (fd356a15...) in all 399 production.json; the P1 manifest (seed 3929792552365635731, 44 classes × 2^23 points,
64 replicates); each batch's own C7_result.json against combine's per-batch value.
