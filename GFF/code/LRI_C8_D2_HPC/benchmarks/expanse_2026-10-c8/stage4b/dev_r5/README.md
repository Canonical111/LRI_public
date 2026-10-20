# Stage 4b development: R5a and R5b on Expanse (branch `opt-r5`)

Development runs for the Stage-4b items R5a (parallel graph loading) and R5b (scheduling defaults). They are not the
plan's J-OPT gate. Results and their reading: `docs/PERFORMANCE.md`, "Stage 4b development: R5a and R5b".

- **Code under test:** commit 2c8b28f, exported to `$C8_DATA/pkg/2c8b28f46538`. `export_check_2c8b28f46538.json`
  shows 5,570 files equal to `git archive`.
- **Baseline:** the Stage-3 workers in `$C8_DATA/pkg/c17688158e2b/bin` (`c8d2_decimal` `3dbd51bb…`, `c8d2_gmp`
  `5c5328af…`), with hashes checked by each job.
- **Environment:** `~/c8d2/env_expanse.sh` `6f85cb50…`, Spack GCC 13.3.0, GMP 6.2.1, Boost 1.77 headers.
- **Scripts:** `scripts/`.
  - `submit_dev_r5.sh` is the Mac driver: export, export check, the H7E-R admission (`../../stage4a/scripts/h7_admit.py`)
    and this agent's Develop-phase share (1 compute node, 8 shared jobs) before each sbatch.
  - `r5_build.slurm`, `r5_bench.slurm` and `r5b_probe.slurm` are the jobs.
  - `r5a_first_error.py` and `r5b_lanes_probe.py` are the checks.
  - The probe ran from a copy outside the export, `$C8_DATA/evidence/2c8b28f46538/r5b_probe_inputs/`, with the same
    sha256 as the committed script (`3b823838…`). It used the export's `tools/`.
- **Admission:** `admission/`: the admission records and squeue snapshots before each sbatch, and the final sacct
  lines with the Lustre file count.

| Job | Where | What it shows | Files |
|---|---|---|---|
| 54666182 `c8d2-r5-build` | `shared` 16 CPUs, 32 GB, <NODE>, 2:16 | The builds (`make`, `gmp inspect`, `profile ratiohist`, `c7ref`; L8 packs hard-linked from the c17688158e2b export and re-hashed). New worker hashes `b36bf334…` (decimal) and `f4ad369c…` (gmp). `tests/validate.py` default parts all passed: describe, 28 refusals, the replay subset of A-RPL-1/2/3 on 117 kernels, invariance, inspector with the order-trace build, class B, diagnostics. `r5a_first_error.py` passed: the first error and the valid rows equal the serial baseline's at 1–16 threads, in 250 candidate runs | `r5build.54666182.0/` |
| 54666183 `c8d2-r5-bench` | `compute` exclusive, <NODE>, 17:20 | P4 16x8 on `p4_L8` with the baseline worker, then with the R5a worker. Load share 1.349% → 0.203%, throughput 114.83 → 116.83, rows digest `16d6ff3d…` in both (= Stage 4a). G-L8SELF on the full L8 sample: exact, both backends. Thread identity: identical, both backends | `r5bench.54666183.0/` (`r5_summary.json`, `p4_before/`, `p4_after/`, `l8self.json`, `thread_identity.json`) |
| 54666372 `c8d2-r5-lanes` | `compute` exclusive, <NODE>, 0:02 | `r5b_lanes_probe.py` on the real sysfs (8 NUMA nodes of 16 cores). The default lanes are 16 × 8 at `--threads 8` and 8 × 16 at `--threads 16`, `numa` is 8 × 16 and `16` is 16 × 8, every lane inside one NUMA node. The sweep's slots are 16 × 8 and 8 × 16 | `r5lanes.54666372.0/` (`lanes_probe.json`, `node.txt`, `sources.sha256`) |

The 32 per-lane logs of the two P4 runs were empty on Expanse and are not copied.

**Allocation:** 37.67 SU in total (`admission/sacct_dev_r5.txt`):
- 54666182: 0.62 SU (136 s × max(16 CPUs, 32 GB/1.95 GB));
- 54666183: 36.98 SU (1,040 s × 128);
- 54666372: 0.07 SU (2 s × 128).

The Lustre file count after the jobs was 1,223,367, shared with the other sessions. This branch added about 5,800 files
(the export, its build and the evidence).
