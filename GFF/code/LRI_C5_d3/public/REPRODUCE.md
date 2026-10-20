# Reproducing C5(3) and the d = 3 masters (GFF/code/LRI_C5_d3)

Run every command from `GFF/code/LRI_C5_d3`. Nothing here writes into the shipped files: the public targets work in
`.work/` (git-ignored). When you rerun a production step, use a copy of the package, because several original scripts
write their outputs into the current directory under the names of the shipped records.

## 1. Environment

| need | used in production (2026-10-02) | tested for the release (2026-10-13) |
|---|---|---|
| Python | 3.x on the cluster nodes, 3.10 locally | 3.10.12 |
| mpmath | 1.3.0 (gmpy2 backend recommended for speed) | 1.3.0 |
| SymPy | 1.x (assemble_c5_d3.py, test) | 1.12 |
| python-flint (Arb) | 0.x (k3flint.py, LLL batteries) | 0.9.0 |

`pip install -r requirements.txt`. Single-core scripts do not need BLAS. Set `OPENBLAS_NUM_THREADS=1` as the job
scripts do.

## 2. Tiers

1. `make -f public.mk test` (2 s): exact d = 3 identities and Horn arrays (`inputs/general_d3/check_exact.py`), and the
   SymPy specialization of gs:C5 and C4 to d = 3.
2. `make -f public.mk replay` (4 s): the package's scripts are rerun on the shipped records and their outputs compared
   byte for byte. Then every quoted number is recomputed and compared with `../../results/closed_forms_3/LRI_C5_d3_quoted.json`.
   Exit status 1 on any FAIL; table in `.work/replay/REPLAY_c5_d3.md`. Tolerances:
   - one unit in the last quoted digit for strings marked `\ldots` in the TeX;
   - correct rounding for table entries;
   - two significant digits for quoted deviations;
   - byte identity for regenerated records. For the reruns it falls back to the stated numeric tolerance if another
     mpmath version changes the last printed digit.
   One check needs the sibling package `../LRI_C5_general_d`: K3 against the 100-digit position-space value. It is
   SKIPped if that package is absent.
3. `make -f public.mk smoke` (15 s): fresh Q3, P4(3), P5(3) at 90 digits and a fresh K3 to about 10⁻¹¹⁰.

## 3. Production chain (documented, not run in CI)

The production ran on one Slurm cluster with 64-core AMD EPYC nodes, plus a workstation. Templates with placeholders are in
`public/slurm/`. Measured wall times are given below; the total is about 120 core-hours.

| step | command (as run) | output | wall time |
|---|---|---|---|
| P0 primitive periods Q3, P4(3), P5(3) | `python inputs/general_d3/verify_d3.py` (bundle code; writes `verification/general_d3/` two levels up) | `period_values.json` (55 and 90 digits) | 5 s + 15 s for the periods; the identity and literal checks take longer |
| P1 spectral masters, run A | `hp_masters_d3.py run_A_dps50.json 50 64 44 64` (`slurm/c5d3_masters.slurm`) | `run_A_dps50.json` | 471 s, 64 cores |
| P2 spectral masters, run B | `hp_masters_d3.py run_B_dps56.json 56 80 52 72` | `run_B_dps56.json` | 657 s, 64 cores |
| P3 run C, b-circle | `hp_part.py run_C_b.json 110 128 110 72 b 0.02` (`slurm/c5d3_part.slurm`) | `run_C_b.json` | 1593 s, 64 cores |
| P4 run C, τ-circle | `hp_part.py run_C_t.json 110 128 110 72 t 0.02` | `run_C_t.json` | 3548 s, 64 cores |
| P5 run C combined | `hp_combine.py run_C_b.json run_C_t.json run_C_combined.json` | `run_C_combined.json` (K3, L3, Z3 to about 96 digits) | 1 s |
| P6 43-digit masters, PSLQ | `pslq_d3.py run_A_dps50.json run_B_dps56.json <BUNDLE>` | `masters_d3.json`, stdout = `pslq_d3.log` | 3 s |
| P7 C5(3) | `compute_c5.py <BUNDLE>` | `c5_value.json` | 1 s |
| K1 K3 to 430 digits | `cd wf_K3; python k3flint.py 1450 400 8000 330 500 run_hp3.json` and `... 1480 360 10000 300 560 run_hp4.json` | `run_hp3.json`, `run_hp4.json` → `K3_value.json` | about 100 s each, one core |
| K2 K3 integer relations | `cd wf_K3; python final_battery.py 420` (reads `K3_value.json`, `consts_480.json`, `lvals_440.json`) | `pslq_K3_results_420.json` | about 20 s of LLL (pslq_K3.log) plus building the constants |
| L1 L3 circles | `cd wf_L3; python pieces.py pA_dps170.json 170 280 116 208 0.04 64` and `pB_dps170.json 170 320 128 240 0.05 64` (`slurm/wf_job.slurm`) | `pA_dps170.json`, `pB_dps170.json` | 130 s and 120 s, 64 cores |
| L2 L3 constants | `python final_form.py pA_dps170.json L3_final_values.json; python tdform.py pA_dps170.json` (and `final_form.py pB_dps170.json L3_final_values_runB.json`) | `L3_final_values.json` | 1 s |
| L3 lattice reduction | `python battery_final.py 155` (and 125) | `battery_final_dig155.json`, `_dig125.json` | not recorded |
| Z1 Z3 circles | `cd wf_Z3; python zcircle.py circA2.json 260 560 170 120 0.001 0` and `circB2.json 270 700 210 128 0.0015 0.0123` | `circA2.json`, `circB2.json` | 215 s and 163 s, 64 cores |
| Z2 Z3 data | `python derive.py circA2.json derived_circA2.json` (and B2) | `derived_circ*.json`; `Z3_values.json` was assembled from these, rounded to 250 digits | 1 s |
| Z3 PSLQ on 𝔱₃'' | `python pslq_z3.py derived_circA2.json derived_circB2.json perB.json` | `pslq_z3_results.json` | not recorded (Slurm jobs) |

`<BUNDLE>` is a directory containing `lri_d3_reduction_update/verification/general_d3/period_values.json`. Use either the
exported `GFF/code/lri_d3_reduction_update` placed under such a directory, or a directory with a link to
`inputs/general_d3/period_values.json` at that path; `public/replay_c5_d3.py` does the latter.
`assemble_c5_d3.py <BUNDLE>` also needs
`lri_d3_matrix_update/code/general_special/coefficient_values_new.json` (the archived 11-digit nonprimitive values; kept in the public
export of that package by the bundle_d3 entry); it prints the symbolic d = 3 assembly that `make test` checks independently.

`wf_L3/L3_final_values.json` also carries `m0_mu1_weighted_h4_0`, `definitions` and `formulas`. These were added by
`check_m0.py` and by hand. The replay compares only the fields that `final_form.py` and `tdform.py` write.

## 4. What a result must satisfy

- C5(3): the high-precision assembly and `c5_value.json` agree with the 50 quoted digits.
- The d = 3 form and the general form of gs:C5 agree exactly (SymPy) and numerically (better than 10⁻¹⁵⁰).
- K3 from runs hp3 and hp4 agree to better than 10⁻⁴³⁰.
- K3, L3 and Z3 agree with the spectral runs A/B (43 digits) and C (about 96 digits).
- The printed reduced forms of Q3, Z3, S'(3/2), L3 and P4(3) hold with the stored values to the stored precision.

## 5. Decisions not to make alone

- Do not quote more digits of C5(3) than 50 without an independent P5(3) beyond 10⁻⁵³.
- Do not present the integer-relation results as independence proofs. They are bounds in the stated bases.
- The general-b half-shift steps behind the L3 and Z3 formulas are derived but not written out. Do not call them proved.
