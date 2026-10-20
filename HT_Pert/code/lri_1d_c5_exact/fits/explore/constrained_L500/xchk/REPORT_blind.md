# Independent cross-check (workflow wf_2b5fc5bd-0dd, 2026-10-13), agent report verbatim

## Blind constrained-fit cross-check, d=1 LRI exact C_n(Λ) tails

**Result: C5(Λ→∞) = −731.13 ± 0.10.** This comes from the constrained, free-intercept fit with c5top fixed. H holds at C3 to about 1e-7. At C4 it fails by +0.28%(3) in the structure-consistent bases, but cannot be tested decisively with uniform log caps.

**Blindness caveat:** the auto-memory index loaded at session start already shows a recorded c₅ value. I did not read any fit scripts or look anything up. The basis choices and selection rules come from the C2/C3/C4 data and calibrations, but the analysis was not strictly blind.

### Method
- **Solver:** my own Householder QR least squares in mpmath at 60 digits, with columns scaled to unit norm. Repeats at 120 digits agree to 2e-20 relative.
- **Noise:** residuals are strongly correlated (lag-1 autocorrelation 0.5–0.9). σ_noise below is therefore propagated through the exact pseudo-inverse rows, using a white plus random-walk model fitted to the residual increments:
  - C3: random walk only, step 7e-15
  - C4: white 1.1e-13, random-walk step 1.2e-13
  - C5: white 3.6e-12, random-walk step 2.6e-12
- **Tail structure the data support:**
  - C2 contains only odd half-integer powers: Λ^{-1/2}, Λ^{-3/2}, Λ^{-5/2}, Λ^{-7/2} fit to 2e-16.
  - Odd powers j/2 carry log^k up to k = n−2 at order ε^n.
  - Even powers (Λ^{-1}, Λ^{-2}) first appear at ε³ without a log. At C3 the Λ^{-1}·log coefficient is about 0 (≈1e-5), so even powers carry log^k up to k = n−3.
  - I call these the "sparse" caps; "uniform" caps allow log^k up to n−2 for every j.
- **Notation:** basis [a,b,c,…] lists the maximum log power for j = 1, 2, 3, …

### (1) Fixed exact intercept, Λ ≤ 2000 (spread is over fits whose residuals are at the noise floor)
| coef | best | spread | ratio |
|---|---|---|---|
| c2 (Λ^{-1/2}) | −0.27861214002(1) | odd-power and k≤1 fits: −0.278612135 … −0.278612146 | – |
| c3 (Λ^{-1/2} log Λ) | 0.97514250(2) | sparse: 0.97514249–0.97514265; uniform k≤1: 0.9751418–0.9751448 | c3/(−3.5 c2) = 1.0000000(2) |
| c4 (Λ^{-1/2} log² Λ), sparse bases | −1.7112(5) | −1.7105 … −1.7119 | c4/(−1.75 c3) = 1.0028(3) |
| c4, uniform k≤2 | – | −1.7065 (J4, lo 60), −1.7071 (J4, lo 100), −1.7122 (J3, lo 300), −1.7135 / −1.7148 (J5, lo 40 / 20) | 1.000–1.005 |

- **Best single C4 fits:** basis [2,1,2,1] gives −1.711290 ± 6e-5 (lo 150) and −1.711268 ± 1.7e-4 (lo 200).
- **Extra columns are consistent with zero:** adding Λ^{-1}log² at lo 150 gives a coefficient of −0.04 ± 0.06; adding Λ^{-2}log² gives 1.3 ± 1. c4 stays at −1.7112 in both.
- **Where the H value comes from:** −1.7065 appears only in uniform J4. That basis omits the Λ^{-5/2} tower, which is already present in C2 (coefficient −0.0293). Adding it moves the uniform fits to −1.713 … −1.715.
- **With Λ ≤ 500 only,** c4 scatters from −1.7055 to −1.7172.

### (2) C5, free intercept A, c5top = −(3.5/3)·c4 = 1.9964, Λ ≤ 500
The H-chain value c5top = −(3.5³/6)·c2 = 1.99092 shifts A by only +4e-4 to +1.4e-3. Residual rms at the noise floor is about 6.7e-12 (max |r| ≈ 2.2e-11). Each cell gives A (σ_noise).

| basis | lo 80 | lo 100 | lo 120 | lo 150 | lo 200 | dA/dc5top |
|---|---|---|---|---|---|---|
| A [3,2,3], 11 columns | −731.134 (0.02) | −731.089 (0.06) | −731.025 (0.2) | −731.90 (0.9) | −735.8 (10) | −0.08 |
| I [3,1,3,0] | −731.143 (0.008) | −731.120 (0.03) | −731.085 (0.09) | −731.49 (0.5) | −733.6 (6) | −0.12 |
| O [3,1,2] | −731.142 (7e-5, rms 1.8e-11, underfit) | −731.144 (2e-4) | −731.145 (5e-4) | −731.144 (2e-3) | −731.151 (0.01) | −0.23 |
| B [3,2,3,0] | −731.02 (0.2) | −730.62 (0.7) | noise-dominated | | | −0.06 |
| L [3,3,3] | −730.90 (0.4) | −730.18 (1.0) | noise-dominated | | | −0.04 |
| U2 [3,3] (no Λ^{-3/2}) | −731.344 (rms 3e-9, underfit) | −731.301 | −731.274 | −731.247 | −731.218 (rms 8e-12) | −0.2 |
| U2b [3,4] | −730.941 (rms 1.6e-10) | −730.985 | −731.013 | −731.037 (floor) | −731.091 | −0.1 |

I and O lack columns that C3/C4 require, and U2/U2b lack the Λ^{-3/2} tower entirely, so they are reported but not used for the central value.

**Lower lo (residuals at the noise floor):**
- Basis A, Λ ≤ 500: −731.119 (lo 50, σ 0.002), −731.125 (lo 60, σ 0.004), −731.130 (lo 70, σ 0.008). At lo 40 it gives −731.115 (σ 8e-4) but is slightly underfit.
- Basis A, Λ ≤ 400: −731.098 … −731.110.
- With an extra Λ^{-2} tower: B −731.13 … −731.16, C −731.21 … −731.24 (lo 30–40), D −731.05 (lo 30).

**Unconstrained (log³ column free):**
- Basis A: −731.19 ± 0.03 at lo 40 (top 2.8), −731.25 ± 0.07 at lo 50, −730.66 ± 0.7 at lo 80.
- Basis O: −731.17 / −731.16 / −731.14 at lo 80 / 100 / 120, with fitted top 2.10 / 2.07 / 1.98. That is roughly consistent with H at C5.
- Basis U2: −730.54 … −730.97 (underfit).

**Calibration of the same procedure on known orders (Λ ≤ 500, top fixed):**
- C4 with the analogue of basis A: dA = +9e-4, +4e-4, +2.4e-4 at lo 40, 60, 80.
- C3: dA = −6e-6 … −2e-6.
- The error grows about 100–150× per order. Applied to basis A at C5, that suggests 0.01–0.06.

**Best estimate: C5 = −731.13 ± 0.10.**
- Central value: basis A at lo 50–80.
- Error budget: noise ±0.004–0.02; basis and truncation ±0.08 (the spread of all structure-consistent floor-level fits, −731.05 … −731.24, plus the Λ ≤ 400 shift); c5top ±0.001.

### Jobs (symmetry, amdq, <NODE>, all COMPLETED in about 2 min each, job name xchk-c5)
- 574286 (uniform bases)
- 574292 (sparse bases, pseudo-inverse rows)
- 574295 (extra bases plus C3/C4 calibrations)

### Files
Local, in `<TMP>/scratchpad/xchk/cfit_blind/`:
- `xfit.py`
- `make_tasks.py`, `make_tasks2.py`, `make_tasks3.py`, `tasks.jsonl`, `tasks2.jsonl`, `tasks3.jsonl`
- `results_574286.jsonl`, `results_574292.jsonl`, `results_574295.jsonl`
- `summary_c5.json`, `table_c5_hi500.txt`, `table_c5_hi400.txt`
- `common.py`, `an*.py`, `final_table.py`

Remote copy, with `slurm-574286.out`, `slurm-574292.out`, `slurm-574295.out`: `<SCRATCH>/xchk_c5/cfit_blind/`
