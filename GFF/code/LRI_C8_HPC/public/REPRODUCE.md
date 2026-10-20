# Reproducing C8(1) (GFF/code/LRI_C8_HPC)

Three levels, from cheapest to most expensive. Run everything from `GFF/code/LRI_C8_HPC/`.

## 1. Tests (about 7 min wall, 2 cores; personal desktop: 6 min 37 s)
    make -f public.mk test
`tests/test_c8_tools.py` (verbatim) requires the seven-slot Jacobian to equal the archived C7 affine map bit for bit;
that holds on some platforms (the Mac, numpy 1.23-1.24) and fails by one unit in the last place on others (a personal desktop, numpy
1.26.4; symmetry AMD EPYC 8534P, anaconda numpy 1.24.3).
`public/test_tools_portable.py` repeats the same checks at 1e-15 of the row scale. `tests/test_pipeline8.py` runs plan,
run, merge, assemble and combine with a fake integrator, including the frozen-bundle, partial-combination, extension and
loop-five rejections, and the lane runner. It runs with the Slurm job variables removed, because the lane runner
names its worker after `SLURM_JOB_ID`: inside a job the test's 'local' claims belong to another job and it would wait
for their 30-minute staleness.

## 2. Replay of every quoted number (about 20 s wall, 1 core, 0.3 GB; personal desktop, Python 3.12.3, numpy 1.26.4)
    make -f public.mk replay
- `public/replay8.py` copies `GFF/data/C8_1/c8_hpc` to `.work/`, decompresses the nine-vertex inventory, and runs the
  package's own `tools/combine8.py` (and through it `tools/assemble8.py`) for the three quoted combinations:
  K = 4 (b1-b4), the A1 interim (b1-b9, inclusion set of the A1-close record) and the final K = 14 (`--extension
  runs/ext1/extension.json --closed`).
- The commands are the production ones (`cluster/a3/a3_close.slurm`, `cluster/symmetry/a1_close_combine.sh`).
- The only substitution is the campaign verification: the checkpoints are not shipped, so their re-validation is
  skipped. Every other check (manifest, audit, merged-output sha256, merged headers, frozen design, seeds, coverage
  guard) runs unchanged.
- `public/verify8.py` compares the outputs with `GFF/results/C8_1/` and checks 122 quoted numbers. It writes
  `.work/verify_c8.tsv` and exits 1 on any FAIL.

Reproducibility of the bytes:
- All three `combined_assembly.json` files are bitwise identical to the published ones on every platform tried. The
  K = 4 `C8_final.json` is bitwise identical on a personal desktop (numpy 1.26.4, OpenBLAS) but not on symmetry AMD nodes (anaconda
  numpy 1.24.3: last-bit differences, max 1.3e-11 relative in a derived field).
- In the A1 and K = 14 results, 36 float fields differ in their last bits (at most 1e-15 relative; derived
  differences such as C5 minus exact by up to 2.3e-13 absolute). Those files were produced with numpy 1.24 on
  symmetry. C8_full, the sampling SE and the bootstrap SE are identical. The check is 1e-12 relative plus 1e-9
  absolute.
- Result: 122 PASS, 0 FAIL, 3 INFO (checks updated to the public edition of the note, 97dd353).

## 3. Production rerun (not run in CI)
The production used SDSC Expanse (b1-b4, b12-b14: `shared` partition, elements of 16 AMD EPYC 7742 cores, 24 GB) and
the symmetry cluster (b5-b11: whole Intel Xeon Gold 6148 nodes, 40 cores, `cluster/symmetry/lane8.slurm`). The
calculation used about 9x10^4 physical core-hours (1.4x10^5 as charged, counting hyperthreads on symmetry), including
development, the exact low-loop stage and the pilot. One batch of 498 elements costs about 6.5x10^3 physical core-hours (A1-A3: 64.6x10^3 for b5-b14).

Build (x86-64 Linux, GCC with libquadmath, Boost headers):

    make CPPFLAGS=-I$BOOST_ROOT/include RPATH=1        # bin/c8_integrate
    make inputs                                         # index files of inputs8 (decompress L8_coord.txt.xz first)

The shipped Slurm scripts carry the production account and partition in `#SBATCH` lines. Command-line options override
them: always submit with `sbatch --account=<ACCOUNT> --partition=<PARTITION>` and set
`C8_ENV_SETUP=public/slurm/env_template.sh` (filled in). Steps (README.md of the package, Workflow 1-6):
1. Weights:
   `sbatch --account=<ACCOUNT> --partition=<PARTITION> cluster/weights8.slurm`
   with `C8_ROOT=$PWD` and `C8_OUT=<SCRATCH>/weights8`. One 16-core job, about 1 h. The sha256 of every weight file
   must equal the `input_sha256` entries of the shipped manifests.
2. Exact stage for loops 2-4 and loop 5:
   `tools/production8.py plan <SCRATCH>/runs/exact8 --unit designs/exact8_unit.json --design designs/exact8_design.json --seed <S> ...`,
   then `sbatch --array=0-<n-1> cluster/production8.slurm`. Loop 5 (`designs/exact8_L5_*`) is its own campaign.
   It is deterministic, so the merged vectors must equal `GFF/data/C8_1/c8_hpc/runs/exact8_L5/exact_L5/merged/`.
3. Pilot and `cluster/postpilot8.slurm`. These regenerate the affine map, the frozen controls and the frozen design.
   With the original pilot seeds they reproduce `analysis/v1` and `designs_frozen/prod4_34000`. A rerun with new seeds
   is a new calculation.
4. Production, per batch:
   `tools/production8.py plan <SCRATCH>/runs/prod/bK --unit <BUNDLE>/unit_production.json --design <BUNDLE>/design.json --design-meta <BUNDLE>/design_meta.json --seed <NEW_SEED>`
   (498 work elements), then `sbatch --array=0-497 cluster/production8.slurm` and `cluster/merge8.slurm`.
   Use new seeds: the shipped seeds 80840001-80840014 reproduce the published streams only on the same processor type.
5. Result:
   `tools/combine8.py <batches> --affine analysis/v1/full_affine8.json --exact5 .../N14.json .../N12.json --design-meta designs_frozen/prod4_34000/design_meta.json --output <OUT>`
   (`--extension` for planned extension batches, docs/EXTENSION_A1.md).
- Seeds and pilot or control-training seeds are checked. `combine8.py` refuses a batch planned against another design
  or reusing a forbidden seed.
- Whole-node lanes as on symmetry: `cluster/symmetry/` (`plan_ext.py`, `lane8.slurm`, `tools/lane8.py`).
