# C8(1): quoted numbers -> record, command, tolerance (C71d, 2026-10-13)

Every row is a check of `public/verify8.py` (run by `make -f public.mk replay` in `GFF/code/LRI_C8_HPC`).
Quoted values are from the condensed note at fa71533 (abstract, Section 1 table, Section 30) and from
`GFF/results/C8_1/2026-10_ext1/REPORT.md`.
- **Recomputed from:** the replayed records in `.work/c8_hpc/results/`. F = `C8_final_A3/C8_final.json` (K = 14),
  A1 = `C8_A1_close/combination/C8_interim.json`, K4 = `C8_final/C8_final.json`.
- **Tolerance:** a rounded quote passes when the recomputed value rounds to it (half a unit of its last digit). The
  Section 1 full-precision values pass at 1e-6 absolute.
- **Result:** 122 checks PASS on a personal desktop, symmetry AMD and the Mac (note at 97dd353).

| Quoted (where) | Value | Record field | Tolerance |
|---|---|---|---|
| estimator, SE (Sec 1 table) | 8059766.723129955, 4209.576151 | F `C8_full`, `sampling_se` | 1e-6 abs |
| C8(1), allowance (abstract, Sec 30.1) | 8059767, +-17000; (8.060 +- 0.017)e6 | F `C8_full`, `allowance.headline_2sf` | 0.5; exact |
| SE, bootstrap (Sec 30.1) | 4210, 4140 | F `sampling_se`, `bootstrap_se` | 5 |
| batches, range, SE range, chi2 (Sec 30.1) | 14; 8041935-8089624; 15090-16343; 8.49/13 | F `batches.per_batch`, `chi2_about_combined`, `dof` | 0.5; 0.005 |
| allowance candidates (Sec 30.1, REPORT) | 4SE 16838.3 (largest), half split 4316, R8 524, R9 499, L5 step 5.5 | F `allowance.candidates` | 0.05 (4SE), 0.5 |
| ratio C8/C7 (Sec 30.1) | -25.0 | F `C8_full` / C7 reference -322549.9 | 0.05 |
| loop-5 contribution, last step (Sec 30.2) | -1297392.1, +2.8 | F `loop5_exact` | 0.05 |
| composition table (Sec 30.4) | 10 means and 9 SEs (free 7879086.8 +- 790.7 ... check -113.3 +- 68.1) | F `free_level`, `power_levels`, `check_levels` | 0.05 |
| K (Sec 30.4 table) | 1531302.35 | `data/C8_1/c8_hpc/analysis/v1/full_affine8.json` `K[8]` | 0.005 |
| resolution sequence (REPORT) | 8429541, 8064559, 8059969, 8059943, 8059740, 8059767 | F `resolution_sequence` | 0.5 |
| controls (Sec 30.4) | uncontrolled 8048689 +- 23730; correction +11078 +- 24734; per loop -663+-316, +2506+-4037, -12920+-24400; SE ratio 5.6 | F `raw_uncontrolled`, `zero_pole_control` | 0.5 |
| pole columns (Sec 30.4) | 30 columns, max abs z 2.18, four above 2 (L7 12/13, L8 1/9), sum z^2 39.8 | F `spurious_pole_checks` | 0.005, exact |
| half splits (Sec 30.4) | 8055451, 8064082 | F `half_splits` | 0.5 |
| lower orders (Sec 30.2, 30.4) | C3 -1.3e-12, C4 1.1e-9, C5 -731.140052 (-5.8e-4), C6 14332.8222 +- 2.52 (+0.45), C7 -322495.6 +- 74.4 (+0.72), 0.4 combined standard errors vs truncation-aware -322524 +- 38 (1 sigma 18.6) | F `lower_order_checks` | last digit |
| vendor split (Sec 30.3, REPORT) | AMD 8063282 +- 5975, Intel 8056245 +- 5918, difference 7037 +- 8410 | F `batches.per_batch` (b1-b4, b12-b14 AMD) | 0.5 |
| HT comparison (REPORT) | -5700, -0.88 sigma | F `C8_full` vs external 8.0655(50)e6 | 50; 0.005 |
| coverage (REPORT) | 21143 active L8 classes | F `coverage` | exact |
| K = 4 result (Sec 30.3) | 8066723 +- 8015, allowance 33000 | K4 | 0.5 |
| A1 result (Sec 30.3) | 8061480 +- 5300, allowance 22000, b5-b9 included | A1 | 0.5; 50 (2 s.f.) |
| inventory (Sec 30.2) | 26540 classes, 7231 power, 248 primitive and power free, 3908 zero, 2507176 terms | `inputs8/L8_coord.txt` (from the .xz), `exact_zero_L8.txt` | exact |
| affine checks (Sec 30.2) | C2 exact, C3 -1.3e-12, C4 1.1e-9, channel ratio -3 | `full_affine8.json` | last digit |
| loop-5 degree sequence (Sec 30.2) | C5 - exact: -0.94, -0.13, -0.019, -0.0032, -5.8e-4 at N = 6..14 | recomputed: K + J5 . v5(N) from `runs/exact8_L5/exact_L5/merged/N*.json` | last digit |
| pilot hazard (Sec 30.3) | C7 production value 16372.8; pilot campaigns (64 points per graph, 16 replicates) A -16793.9 +- 9359.6 and B -13230.8 +- 7406.2, 33166.7 and 29603.7 below, 3.5 and 4.0 of their own SEs; repetition of A with 4096 points per graph (32 replicates) 16838.1 +- 724.1 (the agreement of 16838.1 with the 4SE candidate 16838.3 is a coincidence; the note says so) | `runs/pilot8/tprod{A,B}_L7` and `runs/tailtest_L7/tprodA_L7` via the production `design8.per_graph`; C7: `GFF/results/C7_1/.../C7_final.json` aggregates tprodA_L7 + tprodB_L7 | 0.05; replicates exact |
| kernel validation (Sec 30.3) | power bitwise (0 mismatches), QMC 8e-17, binary128 L8 2.5e-17 | `validation/expanse_2026-10-02/c8_vs_c7_T1-T5_job54592375.json` | last digit |
| cost model (Sec 30.2) | 5, 14 core-hours (degrees 6, 7); 32, 67 at 8, 9 are PLAN.md extrapolations (INFO) | `validation/expanse_2026-10-02/bench8_job54591957.json` | 0.5 |
| core-hours (Sec 30.3) | about 9e4 physical (1.4e5 as charged) | Slurm accounting (`<PAPER>/notes/compute_accounting_2026-10-13_c8ext.md`); not replayed (INFO) | |
| identity (REPORT Files) | K14 sha256 115d614f..., K4 4d4d1865..., A1 62ca9cb0... | replayed files vs `GFF/results/C8_1/` | bitwise or 1e-12 rel |
