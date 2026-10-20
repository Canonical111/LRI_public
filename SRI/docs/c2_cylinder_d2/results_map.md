# results_map: c2_cylinder_d2

Every quoted number of this package: the macro of the paper's numbers.tex, its text as printed, the record it is
recomputed from, the rule, the command and the tolerance. Commands run from `SRI/code/c2_cylinder_d2/`
(`make -C code/c2_cylinder_d2 -f public.mk <target>` from `SRI/`). Generation `G` =
`results/continuum_2026-10/generations/20261015T000632Z_99019_1e66b9` (named by `results/continuum_2026-10/CURRENT`).
Macro tolerance: the recomputed value, rounded half-up to the digits the macro prints, equals the printed value
(`SRI/verify/sri_lib.py`; for value(uncertainty) texts the uncertainty is in units of the last digit).

| Macro | Printed | Status | Record | Rule | Command |
|---|---|---|---|---|---|
| `\SRtwoCtwoHT` | `-4.0670(24)` | printed | `G/C2_estimate.json` `/final/C2` = -4.067049763363875, `/final/dC2` = 0.002358013619761603; recomputed from `G/continuum_points.json` (25 PRIMARY points) | joint fit of the three regulator orders, shared intercept h0 (outcome branch 4); C2 = -pi^2/(4 b0) + h0/b0^2, dC2 = E/b0^2, b0 = 9 pi^4/(4 Gamma(1/4)^4); E is the linear sum of the propagated point components and the joint regulator-model spread | `make -f public.mk replay`; from the raw records `make -f public.mk replay-full` |
| `\SRtwoCtwoHTDev` | `2\times10^{-4}` | printed | `G/C2_estimate.json` `/final/C2`; the closed form evaluated with mpmath (30 digits) = -4.06627014813252155 | \|C2 - c2_closed\| / \|c2_closed\| = 1.917e-4 | `make -f public.mk replay` |
| `\SRtwoCtwoHTNmax` | `1024` | note only (INFO row) | `G/continuum_points.json` `/primary_points/*/N` | largest N of the points (and of every record) | `make -f public.mk replay`, `replay-full` |

The C^SR_2(2) (c_2) row of `tab:htpert` and the table's caption are checked by `make -f public.mk replay`. The
replay reads them live from `results/quoted_numbers.json` (key `tab_htpert_c2`, generated from the paper source);
`public/tab_htpert_c2.json` is a fallback copy. The paper's footnote (f) of 2026-10-14 was folded into the caption and
the text of the Hamiltonian-truncation results on 2026-10-15; the facts it stated are still checked, marked "(note)":

- Row: `$C^{\rm SR}_2(2)$ & & & \ptClosed{\SRtwoCtwoHT} & $\SRtwoCtwoHTDev$ & & \\`, in the d = 2 columns, with
  delta = \|C^HT/C - 1\| taken against the closed form.
- Caption: "except for C^SR_2(2), whose error sums systematic diagnostics; none is a standard deviation".
- N_max: the largest N of the points is 1024 (`\SRtwoCtwoHTNmax`; the paper no longer prints it, the note does).
- (note) "a linear sum of systematic diagnostics, not a standard deviation": E equals the sum of its seven
  components, and `error_budget.status` says so.
- (note) "mostly the choice of regulator model": eps_model / E = 64.3 % (more than 50 %).
- (note) "the closed form enters it in no way": `meta.proposed_closed_form_used` is false, and the analysis code
  contains no closed-form digits.
- (note) "the error rule was revised after the first result had been seen, which left the central value unchanged":
  the rev-4 estimate (`results/continuum_2026-10/evidence/rev4/C2_estimate.json`: -4.067049763363875 +- 2.211) and
  the rev-7 estimate have the same C2, bit for bit.

Also checked by `replay`:
- the 154 regulator fits of the three orders, the 84 joint variants, the outcome table, every error component and
  E. Each is recomputed from the shipped points twice, with the verbatim functions and with an independent
  numpy/mpmath implementation (1e-9 relative);
- the per-order values, reported as INFO: -4.067386 +- 0.010061, -4.066531 +- 0.004168 and -4.066217 +- 0.003458;
- |C2 - c2_closed| / dC2 = 0.33 (INFO).

`replay-full` reruns the analysis from the 16 production, 25 extraction-check and 17 archived records and the
auxiliary-input job. It compares every leaf of the three result files and of REPORT.md with the shipped generation:
- the inputs are identical (160 files and their sha256);
- every discrete leaf is equal;
- tier A, the chain to the quoted number, agrees to 1e-7 absolute;
- tier B, the fit diagnostics, agrees to 1e-6 + 1e-3 |x|, and condition numbers to 1e-2 relative.

On the production platform the rerun is bit-identical.
