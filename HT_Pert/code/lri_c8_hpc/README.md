# Optimized C8 Hamiltonian truncation for HPC

This release computes the **same frozen-cutoff eighth-order coefficients** as
`lri_phi4_C8_calculation.zip`, with substantially less full-space work. It supports
`raw` and the original `vacuum_only` (isolated g²D) prescription. It does **not**
implement complete Dconn matching or change the continuum extrapolation.

The principal improvement is exact algebra, not reduced numerical resolution:

- Store wavefunctions only through order three in a P<=15,Q<=12 core.
- Restore the complete eighth-order effect of the fourth-order wavefunction using
  a scalar free-resolvent quadratic form on the full P<=19,Q<=16 support.
- Pack field parity exactly; keep both reflection parities between ladder factors.
- Store only full-space creation edges, or generate them on demand to save memory.
- Compute references 0,1,3,2 sequentially or on four independent nodes, then perform
  the same final coupling tuning using their scalar components.

**The full physical support has not been reduced to the old seventh-order caps.**
The extra states contribute explicitly to the residual. See `docs/ALGORITHM.md`
for the derivation and the assumptions used in the exact support argument.

## 1. Install and validate

Linux/POSIX is the production target. On the symmetry cluster use `docs/SYMMETRY.md`
(run from source with `module load anaconda3/2023.07-2`; no pip install there).
Python >=3.10, NumPy>=1.24, Numba>=0.57, SciPy>=1.10, threadpoolctl>=2.2 and, for
validation, pytest>=7 are required. The numerical
production arithmetic is float64. `fastmath` is disabled, and there is no
amplitude cutoff, mixed precision, or automatic tolerance relaxation.

```bash
cd lri_c8_hpc
python -m pip install -e '.[validation]'
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1
export NUMBA_NUM_THREADS=4
# Key the cache by source digest: Numba does not notice edits to _core/basis.py
# functions compiled into residual.py kernels.
export NUMBA_CACHE_DIR="$PWD/.numba_cache/$(PYTHONPATH=src python -c 'from lri_c8.io import source_digest;print(source_digest()[:16])')"

python tests/verify_manifest.py
python scripts/validate_release.py --output validation/local.json   # pytest with a fresh cache
python -m lri_c8 warmup --threads 4
```

The test suite exercises compiled int64 edge kernels on small matrices. It does
not allocate a billions-of-states test on the local machine. Compilation/cache
warmup is separate from the numerical timings in `PERFORMANCE.md`.

Generate a new validation receipt on the target compute-node architecture and
software environment (`slurm/submit_defq.sh validate` on symmetry). Do not use the
bundled local receipt as evidence of a compute-node validation; `make_campaign.py`
accepts only a full compute-node receipt for the current source and Python stack.
Output and checkpoint fingerprints include source,
software versions, numerical prescription, backend, and threading configuration.

## 2. Run one cutoff

```bash
python -m lri_c8 run \
  --cutoff 50 --scheme raw --outer-backend stored \
  --threads 4 --memory-limit-gib 4 \
  --output-dir runs/raw --resume
```

For the original isolated vacuum term:

```bash
python -m lri_c8 run \
  --cutoff 50 --scheme vacuum_only --outer-backend stored \
  --threads 4 --memory-limit-gib 4 \
  --output-dir runs/vacuum_only --resume
```

Every output is a checksummed JSON envelope. The numerical dictionary is under
`payload`. Complete results contain C[0:9], r[0:9], g[0:9], the four energy series,
independent shell and low-order checks, residual components, and resource timings.
The clock on a resumed call is that call's elapsed time, not the total campaign
cost including earlier failed attempts.

`vacuum_only` is NOT a fully vacuum-matched physical C8. Existing terms and their
iterations are preserved; no correction is added merely to fit a physical target.

## 3. Memory versus runtime

```bash
python -m lri_c8 plan --cutoffs 40 50 60 80 100 118 --outer-backend stored
python -m lri_c8 plan --cutoffs 40 50 60 80 100 118 --outer-backend ranked
```

State and edge counts are exact integer-DP counts. No Fock rows or edges are
allocated by planning. The **memory envelope is conservative and uncalibrated**;
it is not measured cluster RSS or a runtime forecast. Calibrate progressively on
your target nodes before submitting the largest cases. The requested memory limit
must be the usable allocation, not the total physical memory of an unrelated node.

- `stored` is normally the faster backend. It retains a full-space creation graph,
  but no full-space annihilation graph and no high-order full-space jet vectors.
- `ranked` reconstructs the creation rows from rank/unrank tables each sweep.
  It saves the large creation-edge arrays at the cost of additional integer work.

Both paths compute the same scalar residual and are directly compared by the
regression suite. The core still uses stored packed creation/annihilation graphs.
The planner checks signed-int64 overflow; sparse indices switch widths above the
relevant index limit. Physical caps cannot be silently reduced by the CLI.

## 4. Multi-node parallelism through reference shards

The four reference contributions depend only on a common independently calculated
low-order calibration. They can be evaluated on separate nodes and assembled
without exchanging large wavefunction arrays.

For example, submit one job for each p=0,1,3,2, replacing the reference argument:

```bash
python -m lri_c8 run \
  --cutoff 50 --scheme raw --reference 0 \
  --outer-backend stored --threads 4 --memory-limit-gib 4 \
  --output-dir runs/shards --resume
```

Once all four have completed:

```bash
python -m lri_c8 assemble \
  --inputs runs/shards/raw_L50_d8_ref0.json \
           runs/shards/raw_L50_d8_ref1.json \
           runs/shards/raw_L50_d8_ref3.json \
           runs/shards/raw_L50_d8_ref2.json \
  --output runs/assembled/raw_L50_d8.json
```

Assembly rejects duplicate references, mixed source/runtime/prescription, and
nonidentical low-order calibration inputs. Use a consistent CPU/software
configuration across the shards. This is a split of the exact perturbative
calculation, not averaging several estimates of C8.

**This is not row-distributed MPI.** Each job still allocates its own complete
core and scalar-residual spaces. There are at most four independent reference
jobs per cutoff, plus arbitrary parallelism over cutoffs and the two prescriptions.
Multi-rank launches are rejected to avoid silently replicating a huge allocation.
No GPU implementation is included.

## 5. Slurm campaigns (symmetry defq)

`docs/SYMMETRY.md` is the runbook; `docs/HPC.md` explains the design. In short, on
the symmetry login node:

```bash
slurm/submit_defq.sh validate          # one exclusive defq node, ~1 h; writes the receipt
python scripts/make_campaign.py --cutoffs $(seq 52 2 92) --schemes raw vacuum_only \
  --outer-backend auto --threads 40 --memory-limit-gib 170 \
  --receipt <SCRATCH>/lri_c8/validation/receipt_<src16>.json \
  --output <SCRATCH>/lri_c8/campaigns/c8_L52-92.json
slurm/submit_defq.sh lanes <SCRATCH>/lri_c8/campaigns/c8_L52-92.json \
  <SCRATCH>/lri_c8/runs/c8_L52-92
```

Each lane (array task) gets an exclusive node and runs one solver process at a time,
bound to the 40 physical cores with memory interleaved over both sockets. The
numerical solver holds a flock and, because BeeGFS flock is node-local, an O_EXCL
owner file on its item; the lane supervisor holds one on its lane journal. The submit
wrapper refuses while any job writing to the same output directory is queued or
running, and only then moves aside owner files whose recorded job is not live. Restart uses `--resume`;
source/runtime mismatches are rejected. There is no blind automatic retry of
correctness or memory failures: a lane whose last attempt failed is not
resubmitted unless `C8_RETRY_FAILED=1`.

SIGUSR1/SIGTERM/SIGINT requests a stop at the next safe scalar boundary: after
low-order calibration or after a completed reference. A hard kill inside a
reference loses that reference's in-flight work, not the previously completed
scalar components. No multi-gigabyte wavefunction checkpoints are written.
The defq lane script requests the warning 1800 s before the limit; whole items are
projected at minutes to about an hour on defq, so a 24 h allocation has ample margin.
A signal that arrives while the solver is still importing is honoured at the first
boundary (exit 75).

## 6. Export for the existing analysis

```bash
python -m lri_c8 export --inputs runs/raw/raw_L*_d8.json \
  --output exports/raw_coefficients.json
```

This emits a flat JSON list with the original C/r/g/energy fields plus new metadata.
It revalidates numerical outputs and produces a SHA-256 provenance sidecar. It
refuses incomplete reference shards, duplicate cutoffs, incompatible sources or
prescriptions, and overwriting an existing export. Cutoffs computed with different
thread counts or outer backends may be exported together (both are bitwise
invariant and stay recorded per row); resume and shard assembly still require them
to match. The extrapolation model is not
modified by this package.

## 7. Benchmarks and regression replay

```bash
python benchmarks/run_suite.py                     # -> validation/benchmarks/
python benchmarks/summarize.py                     # -> validation/summary.json
python scripts/regression_saved_grid.py --threads 4 \
  --compare benchmarks/REGRESSION_GRID.json        # -> validation/regression_grid.json
```

The bundled `benchmarks/results/`, `benchmarks/SUMMARY.json` and
`benchmarks/REGRESSION_GRID.json` are manifest-listed historical references; the
scripts write fresh measurements elsewhere by default and never reuse those records
(`summarize.py --input-dir benchmarks/results` re-summarizes the bundled ones).

`run_suite.py` runs independent processes serially so competing benchmarks do not
share the available CPU quota. Each measured case warms its compilation at cutoff
4, then times the complete calibration, basis construction, four references and
final assembly at the requested cutoff. Checkpoint I/O and imports are excluded
from that timer; imports/warmup count in process peak RSS. Separate cProfile
snapshots are under `benchmarks/profiles/` and are NOT included in the clean timing
medians. The scripts do not write into the original retained input files.

`PERFORMANCE.md`, `VALIDATION.md`, and machine-readable records describe the actual
local measurements. There is no claimed multi-node scaling speedup. The `reference/`
directory supplies the unmodified C8 baseline and original SciPy/rational oracles;
those historical files are not the new production entry points.

## 8. Directory map

- `src/lri_c8/engine.py`: cubic trial states, core residual, scalar assembly.
- `src/lri_c8/residual.py`: full-space scalar residual, stored/ranked creation.
- `src/lri_c8/packed.py`: field-parity packed jets and fused vertex helpers.
- `src/lri_c8/planning.py`: exact dimension/edge counts and resource envelope.
- `src/lri_c8/io.py`, `cli.py`: locks, checksums, acceptance, resume, shards, export.
- `src/lri_c8/_core/`: retained ranked kernels and lower-order reference machinery.
- `reference/`: original C8, independent SciPy and exact-rational tests, campaign
  and numerical-scope documents. No external graph-integral archive is implied.
- `inputs/raw/`, `inputs/vacuum_only/`: all retained finite-cutoff C8 reference outputs.
- `tests/`: numerical, type-width, exact-support and process-safety regressions.
- `benchmarks/`: measured records, profiles, replay checks, capacity probes.
- `scripts/`: validation receipt, frozen manifests, lane supervisor, campaign status,
  original-solver comparison, file-system probe, manifest regeneration.
- `slurm/`: symmetry defq environment, validation and lane batch scripts, submit wrapper.
- `docs/`: derivation (`ALGORITHM.md`), HPC design (`HPC.md`), symmetry runbook (`SYMMETRY.md`).

## 9. Scientific limitations

This is a performance and resource rewrite, not a new physical prediction. It does
not improve the conditioning of extrapolating raw C8(Lambda), certify any continuum
coefficient, or complete the connected-vacuum counterterms. Those uncertainties
must remain separate from the small implementation comparison residuals.
