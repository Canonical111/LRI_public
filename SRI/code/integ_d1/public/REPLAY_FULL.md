# integ_d1: production rerun and hosted data

`make -f public.mk replay-full` prints the first section and `make -f public.mk fetch-data` the second. Nothing here is
run by `test` or `replay`.

## Production rerun

The shipped engine outputs (`results/m2_runs`, `results/m3_runs`, `results/m4_runs`) were computed on the symmetry
cluster, 2026-10-14 to 2026-10-17, in about 2.7e4 allocated core-hours: 1.85e4 on Intel nodes (defq, 2 x Xeon Gold 6148,
40 cores) and 0.82e4 on AMD nodes (amdq, 2 x EPYC 7532, 64 cores). The figure counts every job of the calculation,
pilots and failed jobs included. The node-seconds that entered the records are in the records themselves
(`engine_node_seconds`, `engine_cpu_seconds`). Rerunning everything takes roughly 1.6e4 core-hours (about 400 node-hours of engine time); the steps are below.

The batch files in `code/*.sbatch` are the templates that ran. They contain the original absolute paths: a working
directory `<SCRATCH>/lri_integ/` with `code/`, `code/m3/`, `code/m4/` (engine binaries, inputs and task files),
`results/m3/`, `results/m4/` and `logs/`, and a Python environment `<HOME>/envs/<env>/bin/python` (Python 3.13 with
mpmath and sympy). Copy them, change these paths and the partition names for your cluster, and keep the rest: each
template checks the engine's build id, fingerprints every output (`<out>.fp`: engine sha256, build id, input sha256,
arguments, output sha256) and refuses to overwrite or reuse an output whose fingerprint differs.

1. **Engines** (on the compute nodes, g++ with OpenMP):
   `bash code/build_engine.sh ce_double -DUSE_DOUBLE` (id b0da6f7bc003c829, M4B production and cx),
   `bash code/build_engine.sh ce_dd` (06c88f4c378ed21d, double-double overrides and validation samples), and the
   delta^2 build of M4A from its own source: `public/historic/b2ab7c6/cluster_engine.cpp` with `code/dd.h`,
   `code/sha256.h`, built with `-DLS=13 -DVMIN=-8` (5345fdf1bcec7a5a). The id is the sha256 of the sources and the
   compile command; `code/builds.py` recomputes it, and `make -f public.mk test` checks all three. The M3 outputs
   (`results/m3_runs/s3`, `g2g3`) predate build ids: they come from a binary built from the working tree of commit
   a01ccc3 and are hash-listed in `results/legacy_outputs.json`; that exact source is not shipped, so a rerun of M3
   with the current double-double build is expected to reproduce the M3 record within its gate tolerances, not byte
   for byte.
2. **Inputs**: `python code/cluster_gen.py 4 n4.txt --no-radii` (sha256 = `results/m4_inputs/n4.manifest.json`);
   n = 2, 3 inputs are `results/m3_inputs/n2.txt`, `n3.txt`.
3. **M2** (two bubbles, pure mpmath, no engine): `sbatch code/m2_laurent.sbatch 4 40 0.1 96 0` and `... 1` (the two
   parities of the contour points), concatenated into `m2_laurent_L4_d40_r0.1_n96.jsonl`.
4. **M3** (three bubbles, delta^1; about 375 core-hours): `code/m3_chunks.py` splits the 187 sectors of n3.txt by
   measured cost; `sbatch code/m3_tasks.sbatch TASKFILE` per chunk with the engine arguments of the record
   (`results/M3_flow_coefficients.json` `run`: `-mode ser -k 1 -tau 0.1 -taurat 0.1 -nseg 24 -m 32 -nplain 30`).
   Sector checks: `code/sector_check.sbatch` with the checker (`code/build_checker.sh`).
5. **M4A** (three bubbles, delta^2; about 4.6 node-hours): n3.txt, `-mode ser -k 2 -tau 0.1 -taurat 0.1`, grids
   (12,16,16) and (20,28,24) (`-nseg -m -nplain`), with the delta^2 build; sector ranges as in the headers of
   `results/m4_runs/n3d2_A`, `n3d2_B`.
6. **M4B** (four bubbles, delta^1; 3445 mirror-reduced sectors of 4777): `python code/m4_chunks.py NCHUNKS NAME ENGINE_ARGS`
   writes the task files (cost-balanced sector ranges); `code/submit_q.sh QUEUEFILE` submits them onto idle nodes
   (`code/m4_tasks.sbatch`: one Intel node, 40 threads; `code/m4_tasks_amd.sbatch`: one AMD node, two streams of 32
   threads). The levels, all with `-tau 0.5 -radii rouche -bound 1 -mode ser -k 1`:
   - fine `-taurat 0.2 -nseg 12 -m 14 -nplain 14` (about 4.9e3 core-hours), coarse `-taurat 0.2 -nseg 10 -m 12 -nplain 12`
     (1.8e3), radius `-taurat 0.3 -nseg 10 -m 14 -nplain 12` (3.7e3), with the double build;
   - double-double overrides of the same grids (`m4_chunks.py --only results/m4_inputs/dd_sectors_prod.json ...`: the 8
     sectors at taurat 0.2; the radius level's 14 are `radius_run.dd_sectors` of `results/m4_inputs/fix3_design.json`)
     with the dd build;
   - validation samples at the fine grid with the dd build: the 40 sectors of `fix3_design.json` (`Vdd`) and the 16 of
     `fix3b_design.json` (`Vdd2`);
   - confirmatory complex-K runs, `-mode cx -k 0 -conj 0 -nseg 12 -m 18 -nplain 14 -K 0.92 0.05` and `-K 1.05 0.06`
     (about 3.3e3 core-hours for both).
   Every shipped output's header (`# args`) records its exact arguments and sector range.
7. **Gates and assembly** (minutes, any machine): the commands of `public/replay_integ.py` without `--dry`, `--verify`
   or `--stage2`, in the order M2, M3, M4A, M4B (`m4b_gate.py` with all eight directories), cx (`--amended`), then
   `c8_assemble.py` (stage 1, writes the C8 record once) and `c8_assemble.py --compare --expect-sha <hash>` (stage 2).
   The tools publish write-once records and refuse to overwrite a different existing record, so run them in a fresh
   copy without the shipped records (keep `results/builds.json`, the step-0 maps, `m3_inputs/`, `m4_inputs/`). A rerun
   with the same builds on x86-64-v3 hardware should reproduce the records; if the compiler or libm differ, the values
   change at the level of the roundoff bounds (`test` measures this on five production chunks), and the records then
   differ in their last printed digits.

## End of production rerun

## Hosted data

Nothing: every input of `test` and `replay` ships in this folder (the raw engine outputs of the three M4B levels, the
overrides, the validation samples, the complex-K runs, the M4A, M3 and M2 runs: about 46 MB, 15 MB packed). The pilot
runs and the cost studies of the project are not exported (they enter no record).

## End of hosted data
