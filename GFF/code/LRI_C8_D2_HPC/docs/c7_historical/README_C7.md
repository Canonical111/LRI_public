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
has been updated by the optimization tests or by this revision.

**Revision 2026-10-02** (see `CHANGELOG.md`): the job-handling layer of the C6
packages (job-private runtime, status and recovery, guarded Slurm submission
with a campaign lock, resumable merge), fixes for the review findings M1-M4 and
L1-L21, and two opt-in allocation options. The integrand, both precision tiers
and backends, the Sobol/digital-shift stream for a given (seed, net, layout,
rate), the default allocation, the fixed-point assembly and the campaign
weights are unchanged. The only `src/` change is a Boost compatibility hunk
(A-L18; it lets the kernel compile with older Boost such as 1.66, see below).
Campaigns planned by the delivered tools (manifest schema
`c7-d2-production-1`, such as the 2026-09-30 production) are re-run, merged or
assembled only from a checkout of commit `fb64c47`; this revision refuses them.

## Start here

| Guide | Purpose |
|---|---|
| `CHANGELOG.md` | Every change of this revision, by review finding and acceptance criterion |
| `docs/HPC.md` | Slurm submission, status, recovery, wall-time policy, task sizing, allocation options |
| `docs/NUMERICS.md` | Precision choices, unchanged formulas, Sobol export checks, tolerances, statistical units |
| `docs/PERFORMANCE.md` | Measured bottlenecks, matched benchmarks, production cost shares, scaling limits |
| `benchmarks/` | Actual test outputs and benchmark commands, not projected speedups; `benchmarks/symmetry_2026-10/` holds the cluster validation of this revision |
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
`SHA256SUMS` additionally covers that manifest. `--strict` also rejects unlisted
files, apart from build outputs and caches (`bin/`, `__pycache__/`, `.venv/`,
`.git/`, `.DS_Store`). `delivery/DELIVERY.md` distinguishes the packaging work and
its checks from the earlier performance measurements.

No prebuilt executables are distributed: rebuild on the target architecture.

## Build on the cluster

Requirements:
- GNU C++17 with OpenMP and libquadmath on GNU/Linux x86-64; long double must
  have >=64 significant binary bits and extended exponent range;
- Boost headers: the 2026 builds and validation used 1.77 (GCC 11.4 on symmetry,
  GCC 13.3 on Expanse); the kernel also compiles with 1.86 (symmetry GCC 11.4,
  Expanse GCC 13.3) and, after the A-L18 hunk, with the old 1.66 that the
  delivered code could not use. Check which Boost a build really sees:
  `bin/<exe>.build.json` records `BOOST_LIB_VERSION`. Some module systems only
  set `BOOST_ROOT` (Expanse's `boost/1.86.0`): then add
  `CPPFLAGS=-I$BOOST_ROOT/include` or `CPATH=$BOOST_ROOT/include`, otherwise the
  compiler silently uses the system Boost in `/usr/include`;
- GMP development files for the optional `gmp` backend (tested 6.2.1);
- **Python >= 3.10** with `requirements.txt` (this revision: 3.10 locally, 3.11
  on symmetry; the delivery was tested on 3.13). The
  tools and the Slurm scripts refuse older interpreters (Expanse's system
  python3 is 3.6: use a module or venv).

This is not a tested GPU, MSVC or arbitrary CPU-architecture port.

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
promotion thresholds 1e-9 and 1e-23 are unchanged. `make` also writes
`bin/c7d2_decimal.build.json` (compiler, flags, Boost and GMP versions,
executable hash), which `plan` records.

Flags: `OPTFLAGS` (default `-O3`), `CPPFLAGS`, `CXXFLAGS`, `LDFLAGS` and `LDLIBS`
are hooks; the numerical flags `-std=c++17 -fopenmp -ffp-contract=off
-fno-fast-math` are always appended after the compiler options. `LDFLAGS` and
`LDLIBS` come later still and accept only link words (`-L*`, `-l*`, `-Wl,*`,
`-pthread`, `-static*`, `-rdynamic`, `-fuse-ld=*`, `*.a`, `*.so`, `*.o`). For example `make CPPFLAGS=-I/opt/boost/include`
keeps `-O3`. An unoptimized build warns and is recorded as `optimized: false`.
With default settings the compile commands are exactly the delivered ones.

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

## Plan a complete higher-statistics calculation

`C7_RUN` must be on a **shared filesystem** that every compute node sees (never
node-local scratch; node-local storage is only for `--scratch`/`SLURM_TMPDIR`).

```bash
export C7_PACKAGE="$PWD"
export C7_RUN=/shared/filesystem/$USER/c7-d2/run1     # e.g. <SCRATCH>/... on symmetry
python3 tools/production.py plan "$C7_RUN" \
  --seed <FRESH_RANDOM_SEED> \
  --backend gmp --replicates 64 --multiplier 4 \
  --primitive-mode recompute --primitive-points 16384 \
  --shards 32 --threads 32 --checkpoint-tasks 1024 --chunk-points 65536
```

**Use a fresh random seed** for every campaign, for example
`python3 -c 'import secrets; print(secrets.randbelow(2**63))'`; never copy a seed
from documentation. Per-group seeds are SHA-256 functions of (seed, campaign,
sector, loop, role) by default. `--seed-scheme legacy` reproduces the delivered
additive arithmetic and refuses every archived or 2026 seed.

**Planning does not launch integrations.** It creates 20 campaign/sector/loop
groups (two independent campaigns, two sectors, loops 3--7), verifies every
input file first, and prints estimated core-hours per group and in total, the
largest shard's wall time at `--threads`, and a suggested `--time`. Estimates
use a per-backend calibration (`tools/calibration.json`), measured on symmetry's
AMD nodes at 64 threads: the gmp rows from the 2026-09-30 production (M=4096,
lanes on EPYC 7532 and EPYC 7543 nodes), the decimal rows from a small M=16 plan
on an EPYC 7543 node (job 567667). On matched hardware (the same plan run with
gmp on an EPYC 7543 node, job 567730) decimal costs 0.82-1.14x gmp per proxy unit
up to L6 except power L5 (1.30x) and power L6 (1.67x), and 1.29x (free L7) and
2.00x (power L7) at seven loops.

## Run, monitor and recover with Slurm

```bash
export C7_ENV_SETUP=/path/to/env.sh        # modules + venv; see slurm/env.sh.example
export C7_SBATCH_ARGS="-p <partition>"     # site options (allowlisted)
slurm/submit.sh                            # work arrays (<= C7_MAX_ARRAY each) + afterok merge
python3 tools/production.py status "$C7_RUN"   # committed blocks; resubmission lines for missing indices
slurm/resubmit.sh                          # recovery: missing, non-live indices + a dependent merge
```

`slurm/submit.sh`, `slurm/resubmit.sh` and the lines printed by `status` all go
through `tools/slurm_submit.py`, which validates every option, holds a campaign
submission lock, checks the queue first so no live work is duplicated, splits
arrays above `C7_MAX_ARRAY` (default 1000) with offsets, and sets the wall time
by `C7_TIME_POLICY` (`finite` by default; `unlimited` gives `--time=0` where a
site requires it). Details, exit codes and the merge-only recovery are in
`docs/HPC.md`.

The merge job checks completeness, merges every group (already merged and
valid groups are skipped) and assembles. The manual equivalent is:

```bash
python3 tools/production.py merge "$C7_RUN" --scratch /local/scratch
python3 tools/assemble.py "$C7_RUN" --bootstrap 4096
```

`C7_result.json` contains all coefficients C0--C7, their covariance, the separately
measured power correction and its covariance with the power-free coefficient,
per-loop/sector errors, campaign comparisons, half-stream checks and bootstrap.
It also holds the **lower-order checks**: C3--C5 against the archived 13-digit
values of their exact results, C6
against the C6(2) production value 362.36647176 +/- 0.00080 (the archived
362.3489 +/- 0.153 kept as a secondary entry), each with the pull computed from
both SEs, and null tests of `power_differences[3..6]`. `assemble.py` prints all
pulls and flags |pull| > 3 as a diagnostic (not a hard gate). Assembly is
idempotent: an identical existing result is kept, a different one is an error.
It does NOT award new physical accuracy digits or a reporting allowance from
sampling SE alone.

## Precision budget, allocation and primitive mode

Default `--primitive-mode recompute` directly integrates all 44 required
seven-loop primitive graph classes. Optional `--primitive-mode retained` omits
only those strata and adds the archived primitive contribution once; its
common sampling SE **1.2165092149844356** enters the full and power-free
covariance once and cancels in their difference. All lower-loop primitive jets
are integrated in either mode. No complete historical C7 value is an input.

The supplied allocations were frozen from the prior independent pilots.
`--multiplier` scales every nonzero stratum and `--power-multiplier` scales the
power sector up; `--primitive-points` sets the recompute-mode primitive count
(times `--multiplier`). All counts remain powers of two. `--points` overrides
every count, the primitives included, for pilots and tests; `--test-graphs`
drops graphs and writes `C7_test_result.json`, whose physical keys are null
(partial values only under `test_partial`).

**Opt-in allocation options (allocation only, never the integrand or the
estimator; the defaults give exactly the delivered counts):**
- `--power-divisor K` (power of two, default 1) divides every power-sector count
  after the multipliers, `max(4, points x M x P / K)`; `plan` refuses a K that
  would take a stratum below 4 and prints the projected core-hour change.
- `--primitive-allocation neyman` (default `uniform`) splits the primitive budget
  `primitive_points x M x 44` by a frozen variance/cost table
  (`inputs/primitive_allocation_c7d2.json`, from the archived primitive records);
  budgets below primitive_points x M = 64 are refused. `plan` prints the
  projected primitive-block SE of the counts it uses and, at the same budget, of
  the other allocation (labelled hypothetical).

Measured in the 2026 symmetry production (M=4096, R=64, gmp, primitive points
16384; 8,892 task core-hours on mixed AMD/Intel lanes; C7 SE 0.524): the power
sector took **59.9%** of the task CPU for **0.76%** of Var(C7), and the 44
primitive classes **14.4%** of the CPU for **7.4e-5** of Var(C7) (primitive SE
0.0045). The review's estimates were about 55% and 0.5% (power) and 12-27%
(primitives). Derivation: `benchmarks/symmetry_2026-10/production_shares.py`.

Projections by MC scaling from those measured shares (not measurements), at
M=4096, R=64, as SE x sqrt(core-hours) (lower is better; production 49.5):
`--power-divisor 16` 34.6; the plan's recipe `--power-divisor 16
--primitive-allocation neyman` 33.8; adding `--primitive-points 512` 28.5
(2,650 core-hours for SE 0.554: the same SE for one third of the core-hours).
**Recommended efficient recipe:** `--power-divisor 16 --primitive-allocation neyman
--primitive-points 512`. The primitive saving comes from the smaller primitive
budget (uniform at 512 gives 28.6); Neyman adds under 1% there, and at an
unchanged budget it cuts the primitive cost by 14% with a slightly smaller
primitive SE. The power correction's own SE grows by a factor 4 with K = 16.

## Reproducibility and safety

```bash
python3 tools/verify_delivery.py --strict    # Verify the received package (build outputs allowed).
python3 tools/reassemble_reference.py        # Saved data only; no expensive integration.
python3 tests/unit_orchestration.py          # Pure Python: orchestration, Slurm tooling, allocation, nets.
python3 tests/check_inputs.py                # Inputs and the Neyman table regenerate byte-identically.
python3 tests/validate.py --full             # Every required graph, exact replay gate (native).
python3 tests/check_points.py                # 450-digit independent point formulas (native).
python3 tests/staging.py                     # Relocated runtime and timing-model smoke test (native).
```

Tests write records only with `--output`; nothing is written into the package.
Input hashes, pinned tool hashes, executable hashes, numerical backend, task
identities and net matrices are frozen in the plan. A changed executable
requires a new plan; a changed post-processing tool is accepted by `merge` and
`assemble` only with `--accept-tool-change`, which records both hashes. Every
work block runs from a verified job-private copy of the executable, and each
checkpoint records the executable, input and net digests and the node's
library fingerprint. Checkpoint publication is atomic and no-clobber;
missing/overlapping/wrong intervals or corrupted data fail closed. Threads and
node IDs do not change random streams. Chunks are NOT independent uncertainty
samples.

## Files

- `src/`: shared optimized worker and numerical kernel for both sectors.
- `inputs/`: exact low-loop inputs, frozen allocations/index, indexed packs, Neyman table.
- `tools/`: planning, execution, status/recovery, Slurm submission, merging,
  assembly, calibration, profiling and audit.
- `slurm/`: work-array, merge, submit and resubmit scripts and an environment example; no MPI required.
- `tests/`, `benchmarks/`: reproducible regression, point, workflow and timing tests.
- `reference/`: original package preserved; its historic limitations/estimates are
  not new conclusions of this software revision.

The analytic graph construction, local self-energy subtraction, and physical
renormalization argument are retained, not independently rederived here. Kernel
and software equivalence tests do not constitute an independent seven-loop
field-theory validation or rigorous numerical error enclosure.
