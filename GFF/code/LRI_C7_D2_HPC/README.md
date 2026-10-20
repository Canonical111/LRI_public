# C7(2): optimized full-coefficient HPC calculation

This package evaluates the **complete two-dimensional thermal coefficients C0
through C7** in epsilon = 2s - 2. It integrates both the power-free logarithmic
forests and the mixed local-mass/logarithmic forests. **The power correction is
not set to zero.** One- and two-loop inputs are the retained analytic Taylor
jets; loops 3--7 are integrated to regulator order 7-L before fixed-point
assembly.

This is a performance/software delivery, not a new high-statistics determination.
The retained reference is C7(2) = -3953.63362153354 with sampling SE 76.73103617
(empirical reporting allowance +/-310). No physical coefficient or error bar
has been updated by the optimization tests.

## Start here

| Guide | Purpose |
|---|---|
| `docs/PERFORMANCE.md` | Measured bottlenecks, matched benchmarks, scaling limits |
| `docs/NUMERICS.md` | Precision choices, unchanged formulas, tolerances, statistical units |
| `docs/HPC.md` | Slurm submission, restarts, scratch, task sizing and cost calibration |
| `benchmarks/` | Actual test outputs and benchmark commands, not projected speedups |
| `reference/` | Original full C7(2) package, code, raw data, derivations and audits |

## Completed all-in-one delivery

This archive includes the optimized sources, indexed inputs, both original
forest sectors, all 4,329 unmodified reference files, original production data,
TeX/PDF notes, benchmark summaries, and fresh delivery checks. No extra archive
must be downloaded or nested directory assembled by hand.

Verify the unpacked source package before rebuilding:

```bash
python3 tools/verify_delivery.py --strict
```

`DELIVERY_MANIFEST.json` lists every payload file, byte count and SHA-256.
`SHA256SUMS` additionally covers that manifest. The archive's own checksum is
supplied separately. `delivery/DELIVERY.md` distinguishes this packaging work
and its fresh checks from the earlier performance measurements.

No prebuilt executables are distributed: rebuild on the target architecture.
After building, use the verifier without `--strict` to permit added build files.
The kernels, precision thresholds, production planner, covariance assembly and
sampling algorithms are unchanged from the optimization delivery.

## Build on the cluster

Requirements: GNU C++17, OpenMP, libquadmath, Boost headers; long double must
have >=64 significant binary bits and extended exponent range. The tested host
was GNU/Linux x86-64 with GCC 14.2.0. This is not a tested GPU, MSVC or arbitrary
CPU-architecture port.

```bash
cd LRI_C7_D2_HPC
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
make -j4
make test
```

Default `make` builds **`bin/c7d2_decimal`**, retaining the original Boost
300-decimal-digit fallback. The initial long-double and binary128 tiers and
promotion thresholds 1e-9 and 1e-23 are unchanged.

### Faster, explicitly different final arithmetic backend

```bash
# Requires GMP development headers/library (often a site module or libgmp-dev).
make -j4 gmp
make test-full
```

This builds **`bin/c7d2_gmp`**. It replaces ONLY the final fallback by fixed
**350-decimal-digit GMP-backed arithmetic**, exceeding the reference's 300
digits (328 including stored guard digits on the tested build). It does not
lower precision. It does change the arithmetic implementation/rounding, so it
is opt-in and is recorded and checksum-pinned in every planned campaign.

On the delivered matched expensive seven-loop workloads the GMP executable
was about 2.8x--3.1x faster than the original one-thread worker. Both backends
passed all 3,511 required graph-kernel replays and the high-precision tests.
See the detailed report: these are selected-workload/local measurements, not
an end-to-end production or multi-node speedup claim.

## Plan a complete higher-statistics calculation

```bash
export C7_PACKAGE="$PWD"
export C7_RUN="/scratch/$USER/c7-d2-highprecision"
python3 tools/production.py plan "$C7_RUN" \
  --seed 2026093002 \
  --backend gmp \
  --replicates 64 \
  --multiplier 4 \
  --primitive-mode recompute \
  --primitive-points 65536 \
  --shards 32 --threads 8 \
  --chunk-points 65536 --checkpoint-tasks 32
```

**Planning does not launch integrations.** It creates 20 campaign/sector/loop
groups: two independent campaigns, two sectors, loops 3--7. Account, partition,
walltime, CPU binding and array concurrency are site-specific.

```bash
NJOBS=$(python3 -c 'import json,os; print(len(json.load(open(os.environ["C7_RUN"]+"/manifest.json"))["jobs"]))')
JID=$(sbatch --parsable --array="0-$((NJOBS-1))%32" slurm/run_array.sh)
sbatch --dependency="afterok:$JID" slurm/merge.sh
```

Keep the virtual environment active/exported, or activate it in the site job
wrapper. Array limits and dependency syntax are discussed in `docs/HPC.md`.

After every planned job completes, the manual equivalent is:

```bash
python3 tools/production.py merge "$C7_RUN" --scratch /tmp
python3 tools/assemble.py "$C7_RUN" --bootstrap 4096
```

`C7_result.json` contains all coefficients C0--C7, their covariance, the separately
measured power correction and its covariance with the power-free coefficient,
per-loop/sector errors, campaign comparisons, half-stream checks and bootstrap.
It does NOT automatically award new physical accuracy digits or a reporting
allowance from sampling SE alone.

## Precision budget and primitive mode

Default `--primitive-mode recompute` directly integrates all 44 required
seven-loop primitive graph classes. No old Monte Carlo reference limits future
sampling precision. (This deliberately does not use the old product-period
variance reduction; it computes the same expectation.)

Optional `--primitive-mode retained` omits only those seven-loop primitive
strata and adds the archived primitive contribution once. Its common sampling
SE **1.2165092149844356** is included once in the full and power-free covariance,
and cancels in their difference. It is never divided by the number of campaigns,
chunks or nodes. All lower-loop primitive jets are integrated in either mode.
No complete historical C7 value is used as an estimator input.

The supplied allocations were frozen from the prior independent pilots.
`--multiplier` scales every nonzero graph stratum. `--power-multiplier` can
additionally scale the explicitly integrated power sector. All counts remain
powers of two. `--points` overrides all counts for pilot or coverage tests;
`--test-graphs` intentionally drops graphs and therefore forces the final
`C7_full` field to null and labels the result incomplete.

## Reproducibility and safety

```bash
python3 tools/verify_delivery.py           # Verify the received package, before rebuilding.
python3 tools/reassemble_reference.py      # Saved data only; no expensive integration.
python3 tests/validate.py --full           # Every required graph, matched streams.
python3 tests/check_points.py              # 450-digit independent point formulas.
python3 tests/staging.py                   # Relocated runtime and timing-model smoke test.
```

Input hashes, executable hashes, numerical backend, task identities and net
matrices are frozen in the plan. A changed executable requires a new plan.
Checkpoint publication is atomic and no-clobber; missing/overlapping/wrong
intervals or corrupted data fail closed. Resubmitting the same unfinished job
resumes only its missing checkpoints. Threads and node IDs do not change random
streams. Chunks are NOT independent uncertainty samples.

## Files

- `src/`: shared optimized worker and numerical kernel for both sectors.
- `inputs/`: exact low-loop inputs, frozen allocations/index, and indexed packs.
- `tools/`: complete planning, execution, merging, assembly, profiling and audit.
- `slurm/`: independent job-array and dependent-merge templates; no MPI required.
- `tests/`, `benchmarks/`: reproducible regression, point, workflow and timing tests.
- `reference/`: original package preserved; its historic limitations/estimates are
  not new conclusions of this software revision.

The analytic graph construction, local self-energy subtraction, and physical
renormalization argument are retained, not independently rederived here. Kernel
and software equivalence tests do not constitute an independent seven-loop
field-theory validation or rigorous numerical error enclosure.
