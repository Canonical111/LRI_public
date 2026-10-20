# C8(3) campaign runbook

On symmetry and Expanse, submit through `tools/submit.py` as described in `docs/CLUSTERS.md`. The example `sbatch`
lines below omit the site rules (partition, account, memory, exclusions, caps).

The two independent campaign groups use importance-rate multipliers 0.8 and
0.7 and 52-bit and 60-bit scrambled Sobol matrices, respectively. Their final
weights are fixed at one half each. Within a loop/sector/campaign, graph
identities, replicate identities and point intervals determine the work.
Nodes, thread counts and checkpoint boundaries never enter a seed.

## Finish input generation and build first

The supplied graph payloads and analytic inputs are ready to use. Input
regeneration is optional and must finish before a plan is frozen. A plan
records the native binary hash, the analytic data hashes, the active graph
inventory, every graph payload hash, the coverage certificate and the tools
that define its work. Subsequent changes to those items are refused.

Load the cluster's compiler, Boost and GMP environment, create a Python
environment with `requirements-tested.txt`, and build with `make`. Check the
binary using `bin/c8d3_gmp --describe`. The GMP350 backend is required for a
production plan. Rebuild for the destination cluster's libc and toolchain.

## Freeze a production allocation from an excluded pilot

The delivered pilot's `graph_statistics.json` has each graph's projected C8
replicate variance and timing in both independent streams. A new allocation
can be prepared as follows, choosing an actual available core-hour budget:

```bash
python3 -B tools/allocate.py results/pilot_20261008/graph_statistics.json \
  inputs/production_allocation.json --core-hours 10000 --replicates 32
```

The helper refuses a budget below its estimated minimum-count cost. It
rounds per-graph sample counts to complete powers of two, with a minimum of
4,096, and writes a companion cost report. Its estimate assumes conservative
Monte Carlo variance scaling from the pilot; it does not certify RQMC
convergence or any number of physical digits. A high-precision request should
include a separate larger-net convergence run with a fresh seed.

For scale, the measured native task times in the delivered pilot give the
following estimates for a flat allocation to all 24,173 active graphs:

| Replicates in each of a and b | Points per graph and replicate | Evaluations | Estimated native core-hours |
|---|---:|---:|---:|
| 16 | 4,096 | 3,168,403,456 | 742 |
| 16 | 16,384 | 12,673,613,824 | 2,967 |
| 32 | 4,096 | 6,336,806,912 | 1,484 |
| 32 | 16,384 | 25,347,227,648 | 5,935 |

These timing extrapolations exclude input loading and queueing and assume
the pilot's distribution of arithmetic precision promotions. They estimate
work on the validation host, not a guaranteed wall time or accuracy. The
full values and assumptions are in `verification/pilot_postchecks.json`.
An allocation based on the pilot can concentrate extra points on the graphs
with the largest measured contribution to C8 variance.

Create a new immutable run directory:

```bash
python3 -B tools/campaign.py plan results/production_01 \
  --purpose production --seed 5744183710640629 \
  --replicates 32 --points 4096 --threads 8 --graph-block 8 \
  --chunk-points 65536 --allocation inputs/production_allocation.json
```

The seed above is an example. Each independent production campaign needs a
fresh base seed. Never combine the allocation-training pilot into that
production estimator. The program creates both `a` and `b` campaigns within
one plan using independently hashed stream identities.

## Local execution

```bash
OPENBLAS_NUM_THREADS=1 python3 -B tools/campaign.py run results/production_01 \
  --workers 4 --threads 2
```

This uses four independent native processes with two threads each. The
processes also share the input-loading work. Set the product of workers and
threads to the number of available cores. A single specified job can be run
with `--job INTEGER`, including a retry after an interrupted array element.

## Slurm arrays

Set paths that exist on the compute nodes, and a site-specific module setup
file if needed:

```bash
export C8_PACKAGE=/absolute/path/LRI_C8_D3_HPC
export C8_RUN=/absolute/path/LRI_C8_D3_HPC/results/production_01
export C8_ENV_SETUP=/absolute/path/c8_modules.sh
```

The plan prints its total number of job elements. Submit `slurm/run_array.sh`
with an array covering zero through the last index, within the cluster's
array-size and concurrency limits. For a first group of at most 1,000 jobs:

```bash
sbatch --array=0-999%32 --cpus-per-task=8 --time=04:00:00 slurm/run_array.sh
```

Use the actual last index when fewer than 1,000 jobs remain. For a subsequent
group, set `C8_JOB_OFFSET=1000` and submit array indices beginning at zero;
the script adds the offset. Index ranges must cover each planned job exactly
once. Concurrent duplicate execution is blocked by per-job locks.

The script's resource requests are examples; choose partition, time, memory
and concurrency limits for the destination cluster. Package benchmarks
measure native computation on this validation host, not cluster queue time.
The C7 cluster cost models were not reused as C8 cost guarantees.

## Completion, recovery and assembly

```bash
python3 -B tools/campaign.py status "$C8_RUN"
OPENBLAS_NUM_THREADS=1 python3 -B tools/assemble.py "$C8_RUN" --bootstrap 4096
```

The assembler requires every expected graph, loop, sector, campaign,
replicate and point interval. It rejects missing intervals, overlaps,
changed input hashes, duplicated graph IDs, stale coverage certificates,
wrong jet widths and altered sampling configurations. Complete chunks of
one net are added with 50-digit Decimal arithmetic before any statistics.
The final error unit is the whole graph-summed randomized replicate.

`slurm/assemble.sh` can be submitted after the array jobs succeed, using the
site's dependency mechanism. Missing output remains an error; the assembler
never fills it with zero. A second assembly should use `--output NEW_PATH`
and `--graph-statistics NEW_PATH` to preserve the previous result.

An interrupted native process can leave a `.lock` directory next to its
job files. Check that the job is no longer active before removing that lock
and retrying the same job. A valid `.done.json` checkpoint is reused only
after its hashes and scientific work are checked. Raw native output without
a valid completion receipt is rerun.

## Assess numerical adequacy

Review the combined C8 and sampling standard error, the two independent
campaigns, half-stream estimates, bootstrap error and bias diagnostics,
and the C3–C7 comparison pulls. Review the power correction together with
its covariance with the power-free coefficient. A small correction is not
grounds for setting it to zero.

The full-coverage pilot deliberately uses small L8 nets to measure cost and
variance. At small net sizes rare large contributions may be poorly sampled;
agreement of two small campaigns is not by itself a convergence test. Use
fresh, larger complete nets and require stable estimates before assigning
an empirical reporting allowance. No interval or allowance is assigned
automatically by this package.
