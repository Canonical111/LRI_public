# Results map: Monte Carlo

Every Monte Carlo number the paper quotes: the text as printed, its status, the record it comes from (paths relative to `MC/`), the
command that recomputes it (run from `MC/`) and the tolerance. Checked against the final paper text, commit f496d39a. Sources of the
printed text: `../paper/numbers.tex` (macros `\MC*`), `../paper/main.tex` and `../paper/sections/` (Sec. `sec: nonpert`; the MC columns of
Tables `tab:num1`, `tab:num2`, `tab:num3` in the appendix of numerical results, `app: numerics`; Figs. `fig:cmp1d`, `fig:cmp2d3d`).
"printed" = the paper shows it; "defined only" = in numbers.tex but not printed (listed for completeness, not a claim of the paper).
The paper has one table per dimension, with each method's best value per coupling; the d = 2 infinite-size values and the d = 3
finite-size exponents are not printed there (they are in the MC note, Part VI of the Supplementary Material).

`make replay` runs steps R1 to R6 of REPRODUCE.md §3 and the checks C1 to C8 of §7, and writes `.work/reproduced/VERIFY.md`
(any FAIL exits non-zero). The step and check named in each row are the ones that recompute and compare that number:

- R2 / C2: 2D/3D labels and values under amendment P1, recomputed from `data/{2d,3d}` with the released calibration, compared with
  `results/{2d,3d}/evaluation_P1_*/evaluation_*.json` at rtol 1e-9.
- R3, R4 / C4: the 20-point 1D table, recomputed from the per-coupling records in `data/1d/scan_data`, compared with
  `data/1d/scan_data/FIT_V3_SCAN.json` (rtol 1e-9) and `results/1d/tables/*` (by text).
- R6 / C8: every table body and plot coordinate of the MC note (`note/lri_mc_note.tex`), regenerated and required verbatim.

The paper prints the records rounded as stated in the tolerance column: Delta_epsilon to 5 decimals with both errors in units of
1e-5 (d = 1, 3; the rule the paper states in the lead-in of Sec. `sec: pert`), and in d = 2 the finite-size exponent to 4 decimals with
its error in units of 1e-4, half-up. Brackets mark values
whose label is not ACCEPTED. The two 1D labels marked P in Table `tab:num1` (Delta_sigma = 0.1625, 0.1727335)
depend on the computing platform: a refit elsewhere may change them (check C5, KNOWN-PLATFORM-SENSITIVE, not a failure).

Comparisons of MC with other descriptions (`\CMPmcCB`, `\CMPmcNrgRel`, `\CMPhtMcRel`, `\CMPmcGauss`, `\CMPtwoUfour`,
`\CMPtwoUfourEnds`, `\CMPthreeMC`, `\CMPthreeMCsr`) are mapped in `../Resummation/results_map.md`, which reads copies of the records
below (`Resummation/data/inputs/MC/`). The statement that Hamiltonian truncation, NRG and MC "agree at the sub-percent level"
(Secs. `sec: compare`, `sec: discuss`) prints no number; the values behind it, `\CMPmcNrgRel` and `\CMPhtMcRel` (defined only), are in
that map. MC against NRG in detail (`\NRGmc*`, none printed) is in `../NRG/results_map.md`.

## 1. Macros

| macro | printed text | status | rule | record | command | tolerance |
|---|---|---|---|---|---|---|
| `\MCnAcceptedword` | `nine` | printed | number of rows with decision ACCEPTED*: 9 | `results/1d/tables/final_table.csv` | `make replay` (R3, R4; C4) | equal (number word of the count) |
| `\MCthreeD` | `1.47314(118)(230)` | printed | points["1.6"].quoted: Delta_epsilon 1.473144, sigma_stat 0.001181, sigma_sys 0.002297; decision ACCEPTED [sigma_stat above target] (amendment P1) | `results/3d/evaluation_P1_54387089_20260930_215057/evaluation_3d.json` | `make replay` (R2; C2) or `make eval-p1` | value to 5 decimals, errors in units of the last digit, half-up |
| `\MConeL` | `2^{10}\text{ to }2^{19}` | printed | smallest and largest chain length N = L of the d = 1 campaigns: 1024 = 2^10, 524288 = 2^19 | `data/1d/scan_data/ds*/campaigns.json` (field `sizes`) | size command below | equal |
| `\MCtwoL` | `64\text{ to }1024` | printed | smallest and largest L of the 2 400 tasks of the d = 2 production campaign: 64, 1024 | `data/2d/prod/manifest.json` (field `tasks[].L`) | size command below | equal |
| `\MCthreeL` | `8\text{ to }128` | printed | smallest and largest L of the 2 400 tasks of the d = 3 production campaign: 8, 128 | `data/3d/prod/manifest.json` (field `tasks[].L`) | size command below | equal |
| `\MCstatRange` | `(2.0\text{--}5.5)\times10^{-4}` | defined only | min, max sigma_stat over the 9 accepted rows: 0.00020, 0.00055 | `results/1d/tables/final_table.csv` | `make replay` (R3, R4; C4) | both ends rounded to 2 significant digits |
| `\MCsysRange` | `(0.8\text{--}9.6)\times10^{-3}` | defined only | min, max sigma_sys over the accepted rows: 0.00078, 0.00959 (fit-model half-range, not a standard deviation) | `results/1d/tables/final_table.csv` | `make replay` (R3, R4; C4) | both ends rounded to 2 significant digits |
| `\MCapr` | `0.48368(52)(78)` | defined only | row 0.1727335: value(sigma_stat)(sigma_sys) | `results/1d/tables/final_table.csv` | `make replay` (R3, R4; C4) | as the table rows |
| `\MCaprDs` | `0.1727335` | defined only | the published comparison coupling Delta_sigma = 0.1727335 | `results/1d/tables/final_table.csv` | `make replay` (R3) | equal |
| `\MCaprLit` | `0.494(14)` | defined only | literature value (Angelini et al.), published_MC column | `results/1d/records/published_and_epsilon_reference.csv` | none (literature input) | equal |
| `\MCchains` | `10\,240` | defined only | chains of stages A, B, N2: 5600 + 2400 + 2240 = 10240 | `data/1d/scan_data/ds*/campaigns.json` | count command below | equal |
| `\MCfive` | `0.61987(55)(220)` | defined only | row 0.05: value(sigma_stat)(sigma_sys) | `results/1d/tables/final_table.csv` | `make replay` (R3, R4; C4) | as the table rows |
| `\MCfiveDs` | `0.05` | defined only | Delta_sigma = 0.05 | `results/1d/tables/final_table.csv` | `make replay` (R3) | equal |
| `\MCgainMax` | `15` | defined only | precision gain over the literature at 0.1727335 (stat and sigma_sys combined in quadrature) | `results/1d/tables/final_table.csv` | none | not checked |
| `\MCgainRange` | `4\text{--}15` | defined only | do not use (combines a fit-model half-range in quadrature) | `results/1d/tables/final_table.csv` | none | not checked |
| `\MCmaxN` | `2^{19}` | defined only | largest N of the 1D campaigns: 2^19 = 524288 | `data/1d/scan_data/ds*/campaigns.json` | count command below | equal |
| `\MCnAccepted` | `9` | defined only | as \MCnAcceptedword: 9 | `results/1d/tables/final_table.csv` | `make replay` (R3, R4; C4) | equal |
| `\MCnPoints` | `20` | defined only | rows of the 1D table: 20 | `results/1d/tables/final_table.csv` | `make replay` (R3) | equal |
| `\MCsweeps` | `2.05\times10^{10}` | defined only | 10240 chains x 2e6 measured sweeps = 2.048e10 | `data/1d/scan_data/ds*/campaigns.json` | count command below | rounded to 3 significant digits |

Count command (manual check, not part of `make replay`; reproduces 10240 chains, 8000 in stages A and B, 2.048e10 sweeps,
N up to 2^19 = 524288):

```
python3 -c "import json,glob; c={'A':0,'B':0,'Bx':0}; m=0; sw=0
for f in sorted(glob.glob('data/1d/scan_data/ds*/campaigns.json')):
    d=json.load(open(f))
    for x in d['campaigns']:
        if x.get('stage') in c: n=len(x['sizes'])*d['replicas']*d['beta_points']; c[x['stage']]+=n; sw+=n*d['measurements']; m=max(m,max(x['sizes']))
print(c, sum(c.values()), sw, m)"
```

Stage Bx is campaign N2 of the MC note (Table `tab:campaigns`).

Size command (manual check, not part of `make replay`; prints `1024 524288`, `64 1024`, `8 128`):

```
python3 -c "import json,glob
n=[N for f in glob.glob('data/1d/scan_data/ds*/campaigns.json') for x in json.load(open(f))['campaigns'] for N in x['sizes']]; print(min(n), max(n))
for d in (2, 3): L=[t['L'] for t in json.load(open(f'data/{d}d/prod/manifest.json'))['tasks']]; print(min(L), max(L))"
```

## 2. Literal numbers and statements in the text

| where | printed text | record | command | tolerance |
|---|---|---|---|---|
| Sec. `sec: nonpert` | "20 couplings in d=1 and eight each in d=2,3" | `results/1d/tables/final_table.csv` (20 rows); `results/2d/evaluation_P1_20260930_215057/evaluation_2d.json`, `results/3d/evaluation_P1_54387089_20260930_215057/evaluation_3d.json` (8 points each) | `make replay` (R2, R3) | equal |
| Sec. `sec: nonpert` | "A fit protocol accepts or rejects each value (SM, Part VI)" (pointer) | Part VI of `../Supplementary Material.pdf` is the MC note, `note/lri_mc_note.pdf` (Secs. `sec:labels`, `sec:rules`, `sec:v3`, `sec:proto23`, `sec:p1`); the protocols in `protocols/` | none (pointer) | -- |
| Sec. `sec: nonpert` | "In d=2 no infinite-size value is accepted" | `results/2d/evaluation_P1_20260930_215057/evaluation_2d.json` (decisions of all 8 points: none ACCEPTED) | `make replay` (R2; C2) | equal labels |
| Sec. `sec: nonpert` | "In d=3 one value is accepted, ... at s=1.6, under an amended protocol" | `results/3d/evaluation_P1_54387089_20260930_215057/evaluation_3d.json` (decisions of all 8 points: only s = 1.6 ACCEPTED, under amendment P1); `protocols/AMENDMENT_PROFILED_SIGMA.md` | `make replay` (R2; C2) | equal labels |
| Table `tab:num3`, caption | "the value at Ds=0.7 is accepted only under an amendment of the protocol written after the evaluations" (no number) | `protocols/PROTOCOL_HISTORY.md` (column "data seen"), `protocols/AMENDMENT_PROFILED_SIGMA.md`; MC note Sec. `sec:rules` | none (history record) | -- |
| App. `app: numerics`, lead-in; Fig. `fig:cmp1d`, caption | "Only the MC statistical errors and the errors of the effective MC exponents are standard deviations"; "Except the MC statistical errors, no bar or range is a standard deviation" (no number) | sigma_sys is the half-range over the admissible fit models (d = 1) or extrapolation series (d = 2, 3): MC note Sec. `sec:labels`; `protocols/FIT_MODEL_V3_rev14.md` (d = 1), `protocols/FIT_MODEL_2D.md`, `protocols/FIT_MODEL_3D.md` (d = 2, 3) | none (definition) | -- |

## 3. Table `tab:num1` (d = 1), column MC

Printed cell = row of `results/1d/tables/final_table.csv`: Delta_epsilon(sigma_stat)(sigma_sys), errors in units of 1e-5, in brackets
unless the label (column `decision`) starts with ACCEPTED, with superscript P at the two platform-sensitive couplings. The table has
rows only where some method has a value: the MC cell at 0.2 is empty, and 0.2125 and 0.2375 have no row; the caption names all three
("no fit passes"). Command `make replay` (R3, R4; C4); the note table is also checked by R6/C8. Tolerance: the printed cell equals the
record rounded as stated; the record equals the recomputation at rtol 1e-9.

| Delta_sigma | s | printed MC cell | label (record) |
|---|---|---|---|
| 0.0125 | 0.975 | [0.78404(77)(1003)] | CROSS-CHECK UNAVAILABLE |
| 0.025 | 0.95 | 0.71115(49)(959) | ACCEPTED (sigma_sys-dominated) |
| 0.0375 | 0.925 | [0.65904(51)(425)] | CROSS-CHECK UNAVAILABLE |
| 0.05 | 0.9 | 0.61987(55)(220) | ACCEPTED |
| 0.0625 | 0.875 | [0.59003(35)(150)] | CROSS-CHECK UNAVAILABLE |
| 0.075 | 0.85 | 0.56694(37)(139) | ACCEPTED |
| 0.0875 | 0.825 | 0.54761(32)(194) | ACCEPTED |
| 0.1 | 0.8 | 0.53248(20)(242) | ACCEPTED (sigma_sys-dominated) |
| 0.1125 | 0.775 | 0.52020(25)(217) | ACCEPTED (sigma_sys-dominated) |
| 0.125 | 0.75 | 0.50710(35)(193) | ACCEPTED |
| 0.1375 | 0.725 | 0.49856(30)(180) | ACCEPTED (sigma_sys-dominated) |
| 0.15 | 0.7 | [0.49325(41)(306)] | CROSS-CHECK FAILED |
| 0.1625 | 0.675 | [0.48761(58)]^P | CONDITIONAL (sigma_sys coverage absent) |
| 0.1727335 | 0.654533 | 0.48368(52)(78)^P | ACCEPTED |
| 0.175 | 0.65 | [0.48460(35)(67)] | CROSS-CHECK FAILED |
| 0.1875 | 0.625 | [0.48263(30)] | CONDITIONAL (sigma_sys coverage absent) |
| 0.2 | 0.6 | (empty) | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE |
| 0.2125 | 0.575 | (no row) | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE |
| 0.225 | 0.55 | [0.47912(68)] | CONDITIONAL (sigma_sys coverage absent) |
| 0.2375 | 0.525 | (no row) | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE |

## 4. Tables `tab:num2` (d = 2) and `tab:num3` (d = 3), column MC

Rows are keyed by Delta_sigma = (d - s)/2. Records: `points["<s>"]` of the P1 evaluations,
`results/2d/evaluation_P1_20260930_215057/evaluation_2d.json` and `results/3d/evaluation_P1_54387089_20260930_215057/evaluation_3d.json`.
Command `make replay` (R2; C2, rtol 1e-9); the note tables are also checked by R6/C8.

`tab:num2` (column "MC, L = 512 -> 1024"): no infinite-size value is printed in d = 2. The cell is the finite-size exponent
Delta_eff(U4) of the largest pair (`largest_pairs[-1]`, pair `512->1024`) with its bootstrap error `sigma_U4` in units of 1e-4.
Tolerance: 4 decimals, half-up (the same digits as the PDG rule for these errors, 0.0017 to 0.0025). The column is also checked by
`../Resummation` (its replay, against a copy of these records).

| Delta_sigma | s | printed MC cell | label (record, not printed) |
|---|---|---|---|
| 0.475 | 1.05 | 0.9702(25) | CONDITIONAL |
| 0.45 | 1.1 | 0.9659(23) | CONDITIONAL |
| 0.4 | 1.2 | 0.9631(22) | CONDITIONAL |
| 0.35 | 1.3 | 0.9584(20) | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE |
| 0.3 | 1.4 | 0.9627(20) | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE |
| 0.25 | 1.5 | 0.9661(18) | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE |
| 0.2 | 1.6 | 0.9698(18) | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE |
| 0.15 | 1.7 | 0.9773(17) | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE |

`tab:num3` (column "MC"): the cell is `quoted.Delta_epsilon(sigma_stat)(sigma_sys)`, both errors in units of 1e-5, in brackets unless
the label starts with ACCEPTED. The cell at s = 1.6 is the macro `\MCthreeD` (Sec. 1). Where no fit passes (MODEL-LIMITED) the cell is
empty and the caption names the coupling. Tolerance: 5 decimals, half-up.

| Delta_sigma | s | printed MC cell | label (record) |
|---|---|---|---|
| 0.525 | 1.95 | (empty) | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE |
| 0.55 | 1.9 | [1.45449(720)(452)] | CROSS-CHECK UNAVAILABLE |
| 0.575 | 1.85 | [1.45830(103)(9064)] | CROSS-CHECK FAILED |
| 0.6 | 1.8 | (empty) | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE |
| 0.625 | 1.75 | (empty) | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE |
| 0.65 | 1.7 | [1.47375(174)(5237)] | CROSS-CHECK FAILED |
| 0.7 | 1.6 | 1.47314(118)(230) | ACCEPTED [sigma_stat above target] (amendment P1) |
| 0.725 | 1.55 | [1.48118(1632)(2716)] | CROSS-CHECK FAILED [sigma_stat above target] |

## 5. Figures

| figure | MC content | record | command |
|---|---|---|---|
| `fig:cmp1d` | accepted (filled) and other (open) MC values with inner bar sigma_stat and outer bar sigma_sys; published MC (Uzelac et al., Angelini et al.) | `results/1d/tables/final_table.csv`; literature: `results/1d/records/published_and_epsilon_reference.csv` | values: `make replay` (R3, R4); plot: `../Resummation` (its results_map, figure rows) |
| `fig:cmp2d3d` | the d = 3 value at s = 1.6 (accepted under P1) | `results/3d/evaluation_P1_54387089_20260930_215057/evaluation_3d.json` | values: `make replay` (R2); plot: `../Resummation` |

## 6. Not covered by `make replay`

- The lattice sizes and counts in §1 (L ranges; chains, sweeps, N): the size and count commands above.
- The P1 calibration itself (`make calibration WORKERS=16`, about 7 min on 16 cores; check C3) and the cited 1D refits (`make fetch-data`,
  then `make refit-cited`; check C5). Neither changes a printed number unless a label at Delta_sigma = 0.1625 or 0.1727335 changes
  (platform-sensitive, see above).
- The robust-ladder study of the MC note (§6.4.2): reported only, quoted nowhere in the paper.
