# Results: full C7(2) (note Section 28)

    C7(2) = -3876.1 +- 2.1   (epsilon = 2s - 2)
    estimator -3876.1260927949925, sampling standard error 0.5244496691

The allowance is the rule of the previous two-dimensional calculation: max(4 sampling SE, largest half-stream deviation),
rounded up, here to a multiple of 0.1 (4 SE = 2.098; half-stream deviations 0.36). It is empirical, not a confidence
interval, and does not bound an error shared by the graph and renormalization framework.

| File | What it is |
|---|---|
| `C7_result.json` | the result written by the package's `tools/assemble.py --bootstrap 4096` at commit fb64c47 (Slurm job 566530, 2026-09-30). Canonical cross-package path: the C6(2) and C8(2) checks compare with it. sha256 `5c7a331874e48039…` |
| `CAMPAIGN.md` | the production log: plan, environment, build and tests, execution, result and checks |
| `evidence/buildtest-566254/` | build and test records of the production host before the run: `full_validation.json` (both backends against the original executable at all 3,511 kernels), `validation.json`, the test logs |
| `evidence/buildtest-566254.out` | the job's summary: binary hashes, test timings and the 64-versus-16-thread identity check (THREADCHECK) |

**The `lower_order_checks` block of `C7_result.json` is not the one the note quotes.** The delivered assembly compares C6
with the archived Monte Carlo value 362.3489137997967, without its standard error and without a pull (review finding M2).
The record ships byte for byte as the production wrote it. The pulls the note quotes (C3 -1.08, C4 +0.36, C5 -1.67 against the exact
values; C6 +0.73 against the C6(2) production 362.36647176375726 +- 0.0007997306822612242, both SEs combined) are
recomputed by `make -f public.mk replay` in `GFF/code/LRI_C7_D2_HPC`, from the merged records in `GFF/data/C7_2/` and the
C6(2) result in `GFF/results/C6_2/C6_result.json`.

The record holds a field `scope`, which says what the number is: sampling precision only, both sectors integrated, no
lower coefficient imposed. Its `empirical_allowance` is null: the allowance was set by the rule above after the result.
