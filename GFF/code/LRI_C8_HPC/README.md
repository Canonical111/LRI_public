# C8(1) of the one-dimensional long-range Ising model: HPC package

Order-eight generalization of the reviewed C7(1) package (`docs/c7_historical/`, `reference/`): the same finite
coordinate scheme, forest kernel, binary-cluster trees, meromorphic radial Chebyshev quadrature, zero-pole controls
and affine assembly, extended to NW = 8 Taylor slots and loops up to 8. The plan, method and pre-registered
allowance are in [PLAN.md](PLAN.md); validation evidence is in `validation/`.

## Layout
- `gen/`: inventory generators for up to nine vertices (128-bit keys), regression scripts, exact certificates.
- `inputs8/`: graph inventory L = 1..8 (L ≤ 7 byte-identical to C7), forest polynomials and certificates.
- `src/`: the integrator `bin/c8_integrate` (`--mode qmc|power|exact`, `--quad-bits 64|113`).
- `tools/`: `campaign.py` (plan/run/merge/verify one campaign), `production8.py` (one batch: plan/run/merge),
  `affine8.py` (K, J5..J8), `controls8.py` (frozen zero-pole controls), `design8.py` (frozen production design),
  `assemble8.py`, `combine8.py` (final result), `preview8.py` (pilot preview), `regenerate_weights.py` (weights).
- `designs/`: unit designs of the exact stage and the pilot. `cluster/`: Slurm templates for Expanse.

## Build and test
`make CPPFLAGS=-I$BOOST_ROOT/include RPATH=1` (GCC with quadmath, Boost headers, x86-64 long double).
`make test` runs the fast local checks of the Python tooling: `tests/test_c8_tools.py` (affine map, channel rule,
tree counts) and `tests/test_pipeline8.py` (plan/run/merge/assemble/combine with a fake integrator, including the
frozen-bundle, partial-combination and loop-5 rejections; needs numpy and scipy). The kernel regressions
against the C7 binary (`tests/c8_vs_c7.py`) and the cost/precision benchmark (`tests/bench8.py`) need x86-64 Linux,
the C7 package and the inputs; they run on the cluster (see `validation/`).

## Workflow (SDSC Expanse; every job sources `cluster/env_expanse.sh` through `C8_ENV_SETUP`)
1. Weights: `sbatch cluster/weights8.slurm` (C8_ROOT, C8_OUT): every (loop, degree) the unit designs require.
2. Exact stage: `tools/production8.py plan RUN --unit designs/exact8_unit.json --design designs/exact8_design.json
   --seed S --inputs INPUTS --executable bin/c8_integrate`, then `sbatch --array=0-(n-1) cluster/production8.slurm`
   (C8_ROOT, C8_PRODUCTION=RUN) for loops 2–4; loop 5 is its own campaign (`designs/exact8_L5_*`, the only loop-5
   input). The post-pilot job merges or re-verifies these deterministic campaigns before building the affine map.
3. Pilot: the same with `designs/pilot8_unit.json` / `pilot8_design.json` and a new seed.
4. `sbatch cluster/postpilot8.slurm` (C8_RUNS, C8_ANALYSIS, C8_BUDGETS, C8_BATCHES, C8_PILOT_JOB = every pilot
   submission attempt as JOBID[:OFFSET], C8_DESIGN_PREFIX): merges, `affine8.json`, frozen controls
   `full_affine8.json`, the pilot preview and one frozen design bundle per candidate budget.
5. Production: per batch `tools/production8.py plan BATCH --unit BUNDLE/unit_production.json --design
   BUNDLE/design.json --design-meta BUNDLE/design_meta.json --seed NEW_SEED`, then the Slurm array as in 2, then
   `sbatch cluster/merge8.slurm` (C8_PRODUCTION=BATCH).
6. Result: `tools/combine8.py BATCH... --affine full_affine8.json --exact5 exact_L5/merged/N{top}.json
   exact_L5/merged/N{previous}.json --design-meta BUNDLE/design_meta.json --output RESULT`.
