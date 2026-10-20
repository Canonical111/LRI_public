# Reproducing C7(1)

Three levels, from cheap to expensive. Paths are relative to `GFF/code/LRI_C7_HPC/` unless stated.

## 1. Saved-data replay (no integration)

```bash
make -f public.mk replay          # Tier 1, git only: about 5 s, one core, < 1 GB
make -f public.mk fetch-data      # merged records from the Zenodo data record (338 MB tar.gz, 0.97 GB unpacked) into ../../data/C7_1
make -f public.mk replay-full     # Tier 2: tools/combine.py on the records, about 7 min, one core, < 2 GB
```

Expected: Tier 1 ends with `214 checks: PASS 210, WARN 1, RECORDED 2, SKIP 1` (the SKIP disappears when
`GFF/results/C6_1/C6_final.json` is present; the WARN is one digit of the REPORT that is truncated, not rounded).
Tier 2 expects `combined_assembly.json` and `C7_final.json` byte-identical to `GFF/results/C7_1/`, as on Expanse and on
symmetry Intel nodes. Where the platform's floating point differs in the last bits (symmetry AMD nodes: C7_full and
sampling_se by 1 ulp) it compares the JSON trees instead: floats to 1e-12 relative, the two fields that assemble.py forms as differences of nearly equal numbers (applied_zero_pole_control_C7, lower_order_checks[].difference_over_sampling_se) to 1e-12 of their inputs, bootstrap WARN within 5%.
All three runs end with `C7(1) Tier 2 replay: 14 checks, 0 FAIL`.

## 2. Tests

```bash
make -f public.mk test            # = rm -rf build/validation && make test
```

x86-64 Linux with GCC ≥ 9 (`__float128`, libquadmath, OpenMP), Boost multiprecision headers, Python ≥ 3.8 with numpy ≥
1.24, scipy ≥ 1.9, mpmath ≥ 1.2. Pass Boost and RPATH as for the build, e.g.
`make -f public.mk test CPPFLAGS=-I$BOOST_ROOT/include RPATH=1`. Run it as a batch job on a 16-core node (about
10–20 min; the Expanse test job used `--cpus-per-task=16 --mem=16G -t 00:45:00`):

```bash
sbatch -A <ACCOUNT> -p <PARTITION> --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=16G -t 00:45:00 \
    --output=<SCRATCH>/logs/c7-test-%j.log \
    --wrap "source <ENV_SETUP> && make -C <GFF>/code/LRI_C7_HPC -f public.mk test"
```

`tests/compare_binaries.py --baseline c21b9e8` (bitwise kernels against the delivered source) and
`tests/regenerate_original_baseline.py` need the package's git history, which the public copy does not contain; they
are not part of `make test`.

## 3. Full production rerun (about 2.6×10^5 core-hours)

What ran (September 2026, SDSC Expanse, Slurm 23.02.7, `shared` partition, GCC 13.3, Boost 1.86, Python 3.11 venv):

| Step | Tool | Size | Cost |
|---|---|---|---|
| build | `make RPATH=1 CPPFLAGS=-I$BOOST_ROOT/include` | | |
| pilot (design input, optional) | `production.py plan --multiplier 1 --refine7 ...` then `tools/design.py --pilot ... --archive <assemble.py --original output>` | 28 elements | about 25 core-h |
| 399 batches (b001–b400 except b215) | `production.py plan` with `--design ../../results/C7_1/design_v1.json --refine7 --extra-inputs inputs_extra --threads 16`, array of `cluster/production.slurm`, then `cluster/merge.slurm` (afterany) | 55 elements × 16 CPUs, 16 GB, ≤ 3 h each | about 640 core-h per batch, 2.5×10^5 in all |
| direct primitive P1 | `campaign.py plan --mode qmc --L 7 --selection primitive --points 8388608 --replicates 64 ...`, array of `cluster/campaign.slurm`, `campaign.py merge` | 16 elements × 16 CPUs | about 20 core-h |
| final combination | `combine.py batches/b* --primitive primitive/P1 --output final/v2 --jobs 16` (output two levels below the tree root) | 1 job × 16 CPUs, 1 h 49 min | about 30 core-h (60 with the trial combinations) |

The driver `public/slurm/rerun_production.sh` performs these steps with placeholders `<ACCOUNT>`, `<PARTITION>`,
`<SCRATCH>`, `<ENV_SETUP>`, `<GFF>`:

```bash
export ACCOUNT=<ACCOUNT> PARTITION=<PARTITION> W=<SCRATCH>/c7_hpc C7_ROOT=<GFF>/code/LRI_C7_HPC C7_ENV_SETUP=<ENV_SETUP>
bash public/slurm/rerun_production.sh            # FIRST=1 LAST=400 SKIP=215 by default
```

Site notes:
- Keep the production tree on a durable filesystem shared by all nodes; node-local scratch only for the temporary block
  files (`SLURM_TMPDIR`). On Lustre, avoid copying the campaign trees file by file.
- `MaxArraySize` below the element count needs `C7_INDEX_OFFSET` (see `../README.md`).
- The templates pass `--cpus-per-task` to `srun`; on Slurm 22.05–23.02 a step without it gets one CPU.
- Submit in waves (the production kept at most 20 batches active) and resubmit a failed element once with
  `--array=<id>`; the merge fails closed until every checkpoint exists, then is idempotent.

Seeds and identity of the streams. Batch k uses `int.from_bytes(sha256(b"C7-expanse-2026-09:batch:k")[:8], "little")`,
P1 uses the tag `C7-expanse-2026-09:primitive` and matrix seed `seed ^ 0x17219317`. With these seeds, the same Sobol nets
(SciPy version as recorded in each manifest) and the same executable build (sha256 33bab738...), every replicate value,
and so every number in `C7_final.json`, is reproduced exactly. The file hashes still differ unless the absolute
executable path is the same too, because each campaign manifest records that path and every merged file embeds the
manifest's SHA-256. A different compiler or CPU changes the long-double rounding at about 1e-15 relative, far below the
sampling error. `SEED_TAG=<other>` gives an independent rerun of the same frozen
design; an independent determination should also refreeze the design from a new pilot.

Expanse rerun of the archive build and the Tier 2 replay (one job; run by the maintainer on 2026-10-13 as Slurm job 54901438:
archive 68 min on Lustre, Tier 1 214 checks without FAIL, Tier 2 14 checks PASS in 409 s from the unpacked tarball):

```bash
sbatch public/slurm/archive_and_replay.sbatch     # 1 node, 4 CPUs, 16 GB, -t 04:00:00; about 1-2 h
```
