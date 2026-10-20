# C7(1): profiled, bounded-memory HPC implementation

This package optimizes the **existing one-dimensional seventh-order calculation**.
It does not change the graph set, subtraction prescription, sampled distribution,
quadrature degree, regulator jets, frozen controls, or retained primitive input.
It is a source/data delivery, not a new determination of C7 or of its uncertainty.

**Start here:** [performance measurements](docs/PERFORMANCE.md),
[numerical contract and tests](docs/NUMERICS.md),
[cluster execution](docs/HPC.md), [implementation map](docs/ARCHITECTURE.md).

## What changed

The continuous integrator shares ordered arithmetic prefixes of forest terms,
omits logarithms and Taylor work that are mathematically unused at seventh loop
order, and reuses scratch for all three precision tiers. It retains the original
long-double → binary128 → 100-digit fallback thresholds. The difficult fallback
path, not just the ordinary-precision path, is optimized.

The power-sector integrator evaluates the **same complete tensor quadrature in
bounded tiles**, rather than caching whole tensor geometries. It shares weights
between equal signatures inside each tile and computes logs only where needed.
Compensated per-term accumulation changes floating-point summation order; this is
explicitly documented and replay-tested against binary128, element by element. It
is not uniformly more accurate:
- In aggregate the long-double error is smaller than the original's. The projected
  C7 error is 2.8e-12 vs 1.9e-11 at degree 7, and 1.0e-13 vs 3.5e-12 at degree 3.
- On individual strongly cancelling elements it can be larger: up to 18×, at
  4e-14 relative, in one of 112 degree-7 elements.

All observed differences are at or below 4e-14 relative, far below the sampling
noise (see docs/NUMERICS.md).

The execution layer distributes immutable `(replicate, graph, sample interval)`
work units across OpenMP threads and independent cluster jobs. Seeds and Sobol
indices use global scientific IDs, not process/thread IDs. Sparse checkpoints
with content digests, input/executable checksums, atomic no-clobber publishing,
and a complete-coverage idempotent merger make restart and relocation to larger
clusters practical. There is no MPI runtime dependency or collective
synchronization during integration.

## Measured results

Three repetitions on one constrained Linux VM; medians below. Workloads each use
12 actual seven-loop graph classes spanning forest-term-count quantiles. They
are deliberately diagnostic subsets, **not whole-production timing claims**.
The continuous subset is much heavier than production (about 80 versus 14
forest terms per sample, and far more precision fallbacks). Re-weighted to
production sample counts, its speedup is roughly 3×, not 5.54×.

| Workload | Original wall time | New wall time | Ratio | Original peak RSS | New peak RSS |
|---|---:|---:|---:|---:|---:|
| Continuous, 49,152 points | 9.09 s | 1.64 s | 5.54× | 109.9 MiB | 4.43 MiB |
| Power, degree 1, 3,072 trees | 0.81 s | 0.61 s | 1.33× | 212.8 MiB | 4.06 MiB |
| Power, degree 3, 24 trees | 0.69 s | 0.30 s | 2.30× | 181.5 MiB | 4.41 MiB |
| Power, degree 6, 24 trees | 13.48 s | 7.62 s | 1.77× | 533.0 MiB | 4.38 MiB |

At degree 1, the **integration loop alone is about 17% slower** than the old
warm-cache loop; reduced loading/setup still makes the measured process faster.
That tradeoff is not hidden. At degree 6 the integration loop itself is 1.73×
faster. A four-thread local run gives 3.89× and 3.46× integration speedups over
one thread for continuous and degree-six workloads, respectively. The environment
has a four-core CPU quota. An independent single-thread re-measurement on an
i9-13900K (GCC 13.3) gave 5.9×, 1.65×, 3.0× and 2.3× for the four rows, with peak
RSS 114–548 MB → 6–7 MB. The whole archived design at multiplier 1 costs about
3 core-hours (2.98 measured on the i9-13900K; roughly 1.4–4 depending on the CPU)
and ran end to end through the Slurm templates in about 10 minutes on one 24-core
node. **No multi-node or full-cluster scaling test was made**. See
[PERFORMANCE.md](docs/PERFORMANCE.md) and the full timings, compiler, fixtures
and raw records in `benchmarks/matched/`.

## Build and verify

Tested: x86-64 Linux, GCC 14.2, OpenMP, GNU quadmath, Boost multiprecision
headers, Python 3.13, NumPy/SciPy/mpmath (delivery VM); also built and run with
GCC 13.3 on an i9-13900K workstation. A GNU-compatible compiler with
`__float128` and quadmath is required. The default build rejects fast-math and
requires at least 64 mantissa bits in `long double`. A 64-bit Linux/POSIX
filesystem is assumed.

Minimum versions: GCC ≥ 9 (GCC 8 is supported through the `-lstdc++fs` that the
Makefile and `tools/toolchain.py` add automatically), Python ≥ 3.8. NumPy and SciPy
are needed for planning (Sobol nets), merging and assembly; `campaign.py run` and
`production.py run` need only the standard library. Put include paths in
`CPPFLAGS`, e.g. `make CPPFLAGS=-I/path/to/boost/include` for a module Boost.
`make RPATH=1` embeds the compiler's runtime-library directory, so a binary built
with a module GCC also runs where that module is not loaded. `CXXFLAGS` (default
`-O3 -g`) may be overridden; the required flags
`-std=c++17 -fopenmp -fno-fast-math -ffp-contract=off` are always appended.

```bash
cd LRI_C7_HPC
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
make -j4
make test

# Independently reassemble the archived full C7 estimate, without integration:
OPENBLAS_NUM_THREADS=1 python3 tools/assemble.py --original \
    --output build/archived_C7.json
```

The last command reproduces `C7_full = -323405.3107891946` and sampling standard
error `5861.760221129077` exactly in the tested environment, and the archived
`final_analysis.py` diagnostics and allowance (24000). It is a **saved-data
reassembly check**, not an independent physical calculation. Rerunning it with an
existing output verifies that the recomputed result is identical.

`make test` uses an empty `build/validation` directory and also runs the
pure-Python pipeline tests (`tests/test_pipeline.py`). For another run use
`python3 tests/validate.py --output-dir /your/new/test-directory`. It compiles the
reference executables when needed; the only reference-source change is removal
of hard-coded thread counts for controlled comparisons. In a git checkout that
contains the baseline commit,
`python3 tests/compare_binaries.py --baseline c21b9e8 --out DIR` confirms that
the kernels still produce bitwise-identical rows to the delivered source.

For architecture-specific tuning, `make ARCH=-march=native` is optional. Build on
a CPU compatible with every execution node. Do not add `-Ofast`, `-ffast-math`,
unsafe reassociation, or force extended precision down to double.

## Plan a complete higher-statistics calculation

Keep production data on a **durable filesystem shared by all nodes**, called
`$C7_WORK` below (on SDSC Expanse, for example,
`<SCRATCH>/temp_project/c7`). Node-local `/scratch` is
purged at job end on some sites and is suitable only for temporary files.

This command constructs **all 21 independent campaign groups** used by the
archived final design, including paired quadrature levels and both continuous
campaigns. It does not start expensive integrations:

```bash
export C7_WORK=/path/to/durable/shared/c7
python3 tools/production.py plan "$C7_WORK/b001" \
    --seed 2026092301 --label b001 \
    --multiplier 4 --replicate-multiplier 2 \
    --shards-per-stream 4 --threads 8 \
    --chunk-points 65536 --checkpoint-tasks 32
```

The sample multiplier must be a power of two. It increases samples per graph;
the replicate multiplier increases independent randomizations. Samples are not
made independent by splitting them across machines. Original allocations and
control coefficients are frozen. New campaigns use reproducible fresh seeds.
The primitive input and its uncertainty are inherited exactly once.

The production directory is self-contained. Every input file its campaigns hash
is copied from `--inputs` (default `reference/inputs`) into `<production>/inputs/`,
and all internal paths are relative, so the directory can be moved as a whole.
Further options:

- `--extra-inputs DIR` adds `cw_L*_N*.txt` weights to the snapshot, e.g.
  `inputs_extra/` for degree 7;
- `--refine7` adds the paired degree-6/7 campaigns `power_refine7_L{5,6,7}` as a
  quadrature-convergence **check**; they need the degree-7 weights (e.g.
  `--extra-inputs inputs_extra`) and are reported but never enter the estimate
  (NUMERICS.md);
- `--design FILE` sets per-campaign `multiplier`, `replicate_multiplier`,
  `shards`, `checkpoint_tasks` and `chunk_points` as a JSON object keyed by
  campaign name; unlisted campaigns use the global options. Values must be
  positive integers (`chunk_points` may be 0), QMC multipliers powers of two, and each A/B pair (`tprodA/B`,
  `power_coarseA/B` at one L) must share multiplier and replicate multiplier so
  that its fixed design weights stay valid;
- `--label` names the batch for `tools/combine.py`.

Scale: the whole archived design at multiplier 1 costs about **3 core-hours**
(PERFORMANCE.md), and cost grows roughly with multiplier × replicate
multiplier. Use few shards per stream (1–4) unless the multipliers are large, so
that array elements run for many minutes rather than seconds; size the heavy
campaigns individually with `--design`. Start with `make test` and a
multiplier-1 pilot to measure costs at your site.

Submit it on Slurm using the included scripts:

```bash
export C7_ROOT="$PWD"                        # absolute package directory
export C7_PRODUCTION="$C7_WORK/b001"
# Optional: export C7_ENV_SETUP="$C7_WORK/env.sh"   # modules, venv; sourced with errexit, before `set -u`
# Optional: export C7_PYTHON=/path/to/python3       # default python3; must be >= 3.8
mkdir -p "$C7_WORK/logs"
JOBS=$(python3 -c 'import json,os; print(len(json.load(open(os.environ["C7_PRODUCTION"]+"/production.json"))["jobs"]))')
JOB=$(sbatch --parsable --array="0-$((JOBS-1))%64" \
    --output="$C7_WORK/logs/c7-full-%A_%a.log" cluster/production.slurm)
sbatch --dependency="afterany:${JOB%%;*}" \
    --output="$C7_WORK/logs/c7-merge-%j.log" cluster/merge.slurm
```

Edit partition/account, CPU count, memory and time limit for your site, on the
`sbatch` command line or in the templates. Give absolute `--output` paths on the
command line: the template defaults are relative to the submission directory,
and Slurm does not create a missing log directory. The templates pass
`--cpus-per-task` to `srun`, which Slurm 22.05–23.02 needs (docs/HPC.md), and
the worker refuses to run with fewer allowed CPUs than threads.

`afterany` starts the merge once every element has ended, whether or not it
succeeded. The merge fails closed: if any checkpoint is missing or invalid it
exits nonzero without writing `C7_result.json`. Resubmit only the failed or
timed-out elements (for example `--array=17,42`, with the same offset), then run
the merge again. Valid checkpoints are reused, already audited campaigns are
re-verified, and merging is idempotent. `C7_result.json` is published
atomically, and a rerun verifies it instead of overwriting it. Never rebuild or
mutate inputs inside an active campaign; hashes deliberately prevent mixing
builds. Files are created with modes from your umask (e.g. `umask 002` in a
group project directory); nothing is forced to 0600.

If `JOBS` exceeds the site's `MaxArraySize`, submit several arrays with
indices below it and `C7_INDEX_OFFSET`; the work index is
`C7_INDEX_OFFSET + SLURM_ARRAY_TASK_ID`:

```bash
IDS=()
for ((off=0; off<JOBS; off+=1000)); do        # 1000 = MaxArraySize (indices 0..999)
  n=$(( JOBS-off < 1000 ? JOBS-off : 1000 ))
  id=$(sbatch --parsable --array="0-$((n-1))%64" --export=ALL,C7_INDEX_OFFSET=$off \
      --output="$C7_WORK/logs/c7-full-%A_%a.log" cluster/production.slurm)
  IDS+=("${id%%;*}")
done
sbatch --dependency="afterany:$(IFS=:; echo "${IDS[*]}")" \
    --output="$C7_WORK/logs/c7-merge-%j.log" cluster/merge.slurm
```

The final file is `C7_result.json`. It contains the estimate, propagated sampling
covariance, retained-input uncertainty, a replicate bootstrap check and the
archived diagnostic set: power levels, resolution sequence, C3–C6 lower-order
checks, spurious-pole z-scores, half-splits, and the uncontrolled estimator and
zero-pole control terms with SEs. It applies the pre-registered allowance policy
(`allowance.headline_2sf`, plus the archived `allowance.archived_ceil1000`, with
every component; NUMERICS.md). **That allowance is an empirical policy, not a
proof.** Check the paired last-level correction, the degree-7 check where
planned, and independent batches before claiming more digits. Increasing
sampling alone cannot establish quadrature convergence.

## Independent batches

Several complete batches with distinct seeds and labels, planned from one frozen
design, are combined by

```bash
python3 tools/combine.py "$C7_WORK/b001" "$C7_WORK/b002" --output "$C7_WORK/combined"
```

`combine.py` re-verifies every campaign of every batch and requires a
byte-identical scientific configuration (inputs, executable, design, weights,
affine map, primitive) and distinct labels, batch seeds and campaign seeds. It
writes `combined_assembly.json` and `C7_final.json`, with per-batch results and
the inter-batch χ².

`tools/design.py` derives a per-campaign `--design` file by a Neyman allocation
over campaigns:

```bash
python3 tools/design.py --pilot PILOT_DIR --archive ARCHIVED.json \
    --out design.json --meta design_meta.json
```

It uses only the archived components (`assemble.py --original` output) and a
finished pilot production, never the batches it sizes, and records the predicted
per-batch SE and a batch cap. Freeze the design before the first batch.

### Direct primitive campaign

To replace the retained primitive input (SE 25.4) by a direct, verified integration of the 44 L7 primitive
classes with the package's own sampler:

```bash
python3 tools/campaign.py plan --out "$C7_WORK/primitive/P1" --mode qmc --L 7 --selection primitive \
    --points 8388608 --replicates 64 --seed <seed> --shards 16 --threads 16 --chunk-points 65536
# run every index, merge, then:
python3 tools/combine.py "$C7_WORK"/batches/b* --primitive "$C7_WORK/primitive/P1" --output "$C7_WORK/final"
```

The combiner and assembler guarantee that the primitive sector is counted exactly once; see docs/NUMERICS.md.

## Expanse recipe (one tested site example)

This is the setup used on SDSC Expanse (Slurm 23.02.7) in September 2026. Module
names, partitions, limits and paths are facts of that site, not package
requirements. There, system `python3` is 3.6 (too old) and system Boost is 1.66,
so a module toolchain and a venv are used.

```bash
W=<SCRATCH>/temp_project/c7_hpc     # Lustre: durable and shared
mkdir -p "$W/logs"                                      # package copied to $W/LRI_C7_HPC
cat > "$W/env.sh" <<EOF
module load cpu/0.21.2a gcc/13.3.0 boost/1.86.0
source $W/venv/bin/activate
export CPPFLAGS="-I\$BOOST_ROOT/include" RPATH=1   # the boost module sets BOOST_ROOT
EOF
/usr/bin/python3.11 -m venv "$W/venv"
source "$W/env.sh" && python3 -m pip install -r "$W/LRI_C7_HPC/requirements.txt"
make -C "$W/LRI_C7_HPC"
sbatch -A <account> -p shared --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=16G -t 00:45:00 \
    --output="$W/logs/test-%j.log" --wrap "source $W/env.sh && make -C $W/LRI_C7_HPC test"
```

A batch is planned (metadata only, seconds) and then runs as a
`shared`-partition array with explicit CPUs, memory, wall time and Lustre logs:

```bash
export C7_ENV_SETUP="$W/env.sh" C7_ROOT="$W/LRI_C7_HPC" C7_PRODUCTION="$W/batches/b001"
source "$W/env.sh"
python3 "$C7_ROOT/tools/production.py" plan "$C7_PRODUCTION" --seed <seed> --label b001 \
    --threads 16 --design design.json    # optionally --refine7 --extra-inputs "$C7_ROOT/inputs_extra"
JOBS=$(python3 -c 'import json,os; print(len(json.load(open(os.environ["C7_PRODUCTION"]+"/production.json"))["jobs"]))')
JOB=$(sbatch --parsable -A <account> -p shared --nodes=1 --ntasks=1 --cpus-per-task=16 \
    --mem=16G -t 03:00:00 --array="0-$((JOBS-1))" \
    --output="$W/logs/c7-%A_%a.log" "$C7_ROOT/cluster/production.slurm")
sbatch -A <account> -p shared --nodes=1 --ntasks=1 --cpus-per-task=1 --mem=8G -t 01:00:00 \
    --dependency="afterany:${JOB%%;*}" --output="$W/logs/merge-%j.log" "$C7_ROOT/cluster/merge.slurm"
```

`SLURM_TMPDIR` there is node-local and removed at job end; the templates use it
only for temporary block files. `MaxArraySize` is 1000, so larger plans use
`C7_INDEX_OFFSET`. Before the srun fix, a step on this system received one CPU
(effective parallelism 0.99 of 8 threads).

## A single campaign or custom scheduler

```bash
python3 tools/campaign.py plan --out "$C7_WORK/c7-L7-free" \
  --mode qmc --L 7 --selection free \
  --counts reference/inputs/tree_production_counts_L7.txt \
  --replicates 32 --seed 731944 --matrix-seed 1731944 \
  --multiplier 2 --shards 4 --threads 8 --chunk-points 65536

# Dispatch one distinct index per scheduler worker, on any node
# (an explicit --index or SLURM_ARRAY_TASK_ID is required):
python3 tools/campaign.py run "$C7_WORK/c7-L7-free" --index 0 --threads 8

# Only after every index has completed (fails closed otherwise; safe to rerun):
python3 tools/campaign.py merge "$C7_WORK/c7-L7-free"

# Re-validate a merged campaign: manifest, task files, checkpoint digests, audit.
python3 tools/campaign.py verify "$C7_WORK/c7-L7-free"
```

A checkpoint that fails verification stops `run`, `merge` and `verify` with its
path. After inspecting it, `campaign.py quarantine DIR IDENTITY --reason TEXT`
(identity such as `s000003_p000001_N0`) moves it to `checkpoints/quarantine/`,
and invalidates an existing audit; the next `run` of that index recomputes it
deterministically, and the next merge republishes the audit (no manual deletion).

This example is only the continuous L7 campaign, not full C7. Use `production.py`
for the complete combination. Power mode uses `--mode power --selection power
--degrees 3 5`; the two degrees are paired at identical graph/replicate/tree
indices. `--legacy` on merge additionally streams the original `graph_batches`
array to disk for old analysis scripts; it is not necessary for the new assembler.

## Package layout

- `src/`: optimized C++17 integrands, deterministic samplers, tiling and checked I/O.
- `tools/`: campaign planner/worker/merger/verifier, full-production driver, C7
  assembly, batch combination (`combine.py`), pre-registered batch design
  (`design.py`), compile-command builder (`toolchain.py`), input
  indexing/portable weights, profiling and benchmarking.
- `tests/`: oracle, multithread/shard, malformed-input, pairing and reassembly
  tests; pure-Python pipeline tests (`test_pipeline.py`); bitwise kernel
  comparison against the baseline commit (`compare_binaries.py`); degree-7
  weight checks and validation inputs (`check_weights.py`,
  `make_validation_inputs.py`, `check_degree.py`).
- `inputs_extra/`: admitted degree-7 weights with provenance, used only by the
  `--refine7` check campaigns (NUMERICS.md).
- `cluster/`: Slurm single-campaign, complete-production and merge templates.
- `benchmarks/`: actual profiles, selected-graph timing runs, independent binary128
  replays and validation records. They are not new accepted production samples.
- `reference/`: the original C7 package, including all raw accepted streams,
  finite-scheme inputs, graphs, weights, original code and TeX/PDF derivation.
  Original files are content-preserved. Byte-offset indices are added separately.

## Boundaries

This implementation handles the existing L=2 through L=7 integrands. It is not an
arbitrary-loop generator. Runtime still contains the genuine tensor factor
`(degree+1)^(L-1)`; tiling removes its *memory* growth, not its arithmetic cost.
Power-tree stream seeking retains the original MT19937 generator and costs
O(sample start); whole-stream tasks are preferable when inexpensive seeking is
important. The planner holds task metadata in RAM, while workers and the merger
are bounded/checkpointed. More details and tested tolerances are in the linked
documents. The original research note is not rewritten by this optimization.
