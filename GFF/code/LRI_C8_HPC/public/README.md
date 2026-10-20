# LRI_C8_HPC: C8(1), the full eighth-order coefficient in one dimension

Thermal scaling dimension of the one-dimensional long-range Ising model,

    Delta_E = sum_n C_n(1) eps^n,  eps = 2s - 1:   C8(1) = 8059767 +- 17000  =  (8.060 +- 0.017) x 10^6.

- **Sampling error.** The sampling standard error is 4210 (bootstrap 4140).
- **Allowance.** The +-17000 is the empirical allowance of a rule fixed before production: the largest of four
  sampling errors, the refinement and check steps, the half-split shift and the loop-five degree step, rounded up to
  two significant figures. It is not a rigorous bound. The number of batches was not fixed in advance: under the
  stopping rule set first, nine batches give 8061480 +- 5300 with allowance +-22000; all fourteen planned batches
  were completed after interim results of five to eight batches had been seen (note Sec. 30.1).
- **How it is computed.** The estimator is the mean of fourteen independent production batches of one frozen design
  (498 work elements each).
  - Loops one to five are deterministic. Loops six to eight are sampled: two randomized Sobol campaigns for the
    power-free sector, and a power sector telescoped through radial degrees 1, 3, 5, 6, 7, 8, with a degree 8 to 9
    check.
  - The method and its checks are Section 30 of the note (`GFF/note/`).
- **Where the code comes from.** The code generalizes the seventh-order package `GFF/code/LRI_C7_HPC` to eight loops.

## Layout in the public repository

| Path | Contents |
|---|---|
| `GFF/code/LRI_C8_HPC/` | the production code, verbatim at commit 1282e37 (src/, tools/, gen/, inputs8/, designs/, cluster/, tests/, validation/, docs/, PLAN.md) plus the public overlay (`public.mk`, `public/`, `REVIEWS.md`); `make -f public.mk setup` links `reference` to `../LRI_C7_HPC/reference` |
| `GFF/results/C8_1/2026-10_ext1/` | the final K = 14 result (`C8_final_A3/C8_final.json`, sha256 115d614f...), the A1 interim (`C8_A1_close/`), the records of both clusters and `REPORT.md` |
| `GFF/results/C8_1/2026-10_expanse/` | the first result, K = 4 (8066723 +- 8015, allowance 33000), with the frozen design, the batch plans, the pilot preview and `REPORT.md` |
| `GFF/data/C8_1/` | merged records of the 14 batches, the exact loop-five campaign, the affine maps, the frozen design, the 4096-point L7 test, and `inputs8/L8_coord.txt.xz` (see `DATA.md`) |

## Commands (from `GFF/code/LRI_C8_HPC/`)

| Command | What | Time, node |
|---|---|---|
| `make -f public.mk test` | tests of the Python tooling, the pipeline and the lane runner (fake integrator) | about 7 min, 2 cores |
| `make -f public.mk replay` | reruns the three quoted combinations with the production `tools/combine8.py` and checks 122 quoted numbers (PASS/FAIL table in `.work/verify_c8.tsv`) | about 20 s, 1 core, 0.3 GB |
| `make CPPFLAGS=-I$BOOST_ROOT/include RPATH=1` | builds the integrator `bin/c8_integrate` for a production rerun (REPRODUCE) | x86-64 Linux |

Requirements: Python >= 3.8 with numpy and scipy (replay and test). A rerun also needs GCC with libquadmath and
OpenMP, Boost headers and Slurm.

## What the replay does and does not check
- The replay recomputes, from the merged replicate streams:
  - the estimator, the covariance, the allowance candidates, the bootstrap, the half splits, the per-batch values and
    their chi-square;
  - the resolution sequence, the zero-pole controls, the pole statistics and the lower-order checks;
  - the coverage guard and the frozen-design checks.
- **Checkpoints are not re-validated.** The 83,380 checkpoint files behind the merged streams are not shipped (about
  34 GB). Their sha256 values are in every `merged/audit.json`.
- **Still checked:** the merge audit of every campaign, the sha256 of every merged stream, and the merged headers.
- **The integrals are not recomputed.** That is the production rerun.
- **Comparisons with other results** (C6(1), C7(1), HT) check consistency inside a shared framework; they do not
  validate the framework.
