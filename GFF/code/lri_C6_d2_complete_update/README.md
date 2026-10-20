# Complete numerical C6(2), 14 September 2026

**Result:** C6(2) = 362.20966952522036; propagated sampling standard error 0.4803334907952837. Recommended report: **362.2 ± 2.0**, an empirical numerical allowance, not a rigorous enclosure. Convention: epsilon = 2s - 2.

The complete coefficient is computed in the existing graph/critical-mass framework. No Padé prediction, dimension interpolation, or constraint fitted to the known C3–C5 is used. This is not independent external field-theory validation.

## Reading

- `long_range_ising_complete.tex` and `.pdf`: entire note. Appendix U is the new complete calculation. Every pre-existing displayed equation is preserved.
- `C6_d2_complete.tex` and `.pdf`: standalone calculation and cited references.
- `verification/C6_d2_result.json`: canonical result, all four runs, covariance, lower-order controls and scope.
- `verification/power_sector_audit.json`: canonical power-sector coverage and correction. At sixth order only 3c6-b6 is asserted complete; separate b6 and c6 entries in raw audits may omit zero-combination graphs.

## Reassemble the published estimate, without rerunning integrations

```bash
cd reproduction
python -m pip install -r requirements.txt
python mom_final_analysis.py
```

This reads the original `mom_prod_a3.json` through `mom_prod_d6.json`, exact two-loop coefficients, and the independently measured known-sector input. The four-run combination retains the common known-sector covariance of runs C and D. It does not average that uncertainty down as if it were independent. `mom_full_C6_result.json` is the resulting output.

Run `bash run_exact_checks.sh` for the finite-regulator coefficient extraction, exact Kirchhoff/kernel comparison and analytic coverage audit. The remaining special-function checks are `klt_checks.py` and `fresh_two_loop_mom.py`; these perform new higher-precision calculations and are separate from simple result reassembly. To recompute the power correction from the saved counterterms use `python power_cancellation.py` and `python power_cancellation.py --high`.

## Reintegrate a production configuration

The C++ sampler uses a GNU-compatible C++17 compiler, OpenMP, Boost headers and quadmath.

```bash
cd reproduction
bash compile_sampler.sh
python rerun_production.py C 6
```

`production_manifest.json` records every seed, sample count, graph file, proposal and allocation used. A short execution test can use `--samples 12800`; it is not the production result or an accuracy check. Reruns write into `reruns/`, not over the retained samples. Four threads reproduce the original batch splitting; different compiler/library versions can alter floating-point rounding. No hard runtime estimate is implied.

## What is complete, and what is historical

The finite-scheme graph calculation evaluates the **complete physical combination**. Some individual MS counterterms remain separately unevaluated; none remains as an unknown contribution to the reported coefficient. `analytic_extension_audit.json` is a historical intermediate audit and therefore still lists the individual-MS remainder and a null full coefficient; it is superseded for the physical coefficient by `C6_d2_result.json`. Old directories deliberately retain their partial results and limitations unchanged.

The supplied complete power correction is evaluated rather than set to zero by assumption. The value is numerically consistent with cancellation at two high-precision settings; this is not claimed as an all-orders theorem. At order six, the correction needs only the complete 3c6-b6 power combination.

The 2.0 allowance covers observed integration behavior and checks, not truncation of the physical epsilon series or an unrecognized shared theory/graph error. The standalone note explains why the old 1D integration engine does not transfer unchanged, and why local forest subtraction plus explicitly epsilon-dependent finite renormalization made the 2D computation usable.
