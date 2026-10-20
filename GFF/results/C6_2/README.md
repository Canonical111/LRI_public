# C6(2): published results

C6(2) = 362.366 ± 0.004 (estimator 362.36647176375726, sampling standard error 0.0007997307; note Sections 1, 24.6 and
24.9). The allowance is four sampling standard errors rounded up to a multiple of 0.001.

| File | What it is |
|---|---|
| `C6_result.json` | the result of the production's merge job (`tools/assemble.py --bootstrap 4096` of the code at git commit 6aaf656): estimator, covariance, campaigns a and b, error by loop, lower-order checks, bootstrap, and the SHA-256 of the plan, of the 8 merged records and of the assembly inputs |
| `CAMPAIGN.md` | the production record: plan, environment, reporting rule written before the result, preflight, completion, result, checks, later defects, archive |
| `preflight/threadcheck-54508994.out` | the thread-identity check (2,048 rows identical at 64 and 16 threads) |

Inputs: `GFF/data/C6_2/` (plan, configs, merged records in git; the complete run directory hosted). Code and replay:
`GFF/code/LRI_C6_D2_HPC/`, `make -f public.mk replay` (seconds) and, with the hosted data, `make -f public.mk remerge`.

**Precision of re-assembly.** The campaign log says that a re-assembly of the copied run reproduced C6 and its SE "bit
for bit". That holds for the environment it was run in, not in general. Merging is exact: the checkpoint rows are summed
as decimal strings at 50 digits, and the re-merge reproduces every merged record byte for byte on any platform. The
assembly is float64 numpy (covariances, matrix products, a seeded bootstrap), and its last bits depend on the numpy and
BLAS build: on macOS with numpy 1.24 and 1.26, C6 comes out identical and its SE one unit in the last place different;
with numpy 1.23, C6 differs by 3e-16 relative. Replay therefore compares the headline fields to relative 1e-12, the other
fields to relative 1e-7 (pulls and the bootstrap amplify rounding by cancellation) or absolute 1e-22 for entries below
1e-9, and every quoted number at the digits the note prints.
