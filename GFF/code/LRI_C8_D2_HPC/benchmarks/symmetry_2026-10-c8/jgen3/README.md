# J-GEN-3 on symmetry: the A-INV-4 Intel cross-platform inventory identity

**Verdict: identical.** The L7+L8 build on an Intel node (symmetry `debugq`, <NODE>, Xeon Gold 6148, 40 threads,
Ubuntu GCC 11.4.0, glibc 2.35) reproduces the published `inventory8_d2` exactly:
- `MEMBERS.sha256` is byte-identical: sha256 `e1a77e0d…`, 24,839 members.
- Every member's hash is equal: 24,839/24,839, and no member is missing or extra.
  - L7_free 2,441, L7_power 709, L8_free 16,798, L8_power 4,891.
- Both builder inventories are byte-identical: `inventory_L7.json` `747b4ea9…` and `inventory_L8.json` `c83252c1…`.

The reference build was J-GEN-2: job 54631552 on Expanse <NODE>, an AMD EPYC 7742 at 128 threads, with Spack GCC
13.3.0 on Rocky 8 (glibc 2.28). The published tree has MANIFEST sha256 `46341a3c…`. Expanse job 54631553 had already
matched it on a second AMD node at 64 threads. This run changes the CPU vendor and microarchitecture (Skylake-SP with
AVX-512, against Zen 2), the compiler (GCC 11.4 against 13.3), the runtime libraries (Ubuntu's libstdc++ and libgomp 12.3
here), glibc (2.35 against 2.28) and the thread count. The builder binaries differ, as they should: `build_free` here is
`99945942…`, the reference is `d291c5ba…`.

A-INV-4 is now met on both architectures. PLAN.md asks for a comparison with the 64-thread AMD build. That build
(54631553) and the published 128-thread tree (54631552) have the same `MEMBERS.sha256`, so this one comparison covers
both.

## Setup

| Step | Record |
|---|---|
| Survey 2026-10-04 15:50 and 15:55 EDT: `debugq` had 24 idle Intel nodes, so the job started at once. No `c8d2-*` job was live; the H7 count (amdq+amddebugq+amdpreq) was 0. Other <USER> jobs (`lri-prod*`) were left alone. | this README |
| Export: `git archive ec5bae0 \| tar -x` into `<SCRATCH>/c8d2/pkg/ec5bae006d93`, with the full id in `ec5bae006d93.commit` beside it. The export check found all 5,314 files equal to the archive by sha256, no file missing or extra, every mode equal to git's, and no symlink or special file. | `export_check_ec5bae006d93.json` |
| Reference: a partial copy of the published tree in `<SCRATCH>/c8d2/ref/inventory8_d2_46341a3c0f11`: `MANIFEST.json`, `SHA256SUMS`, `MEMBERS.sha256`, `inventory_L7.json` and `inventory_L8.json` (19 MB; the 7.8 GB payload was not copied). The job checked it before building: MANIFEST = the pin, sha256(SHA256SUMS) = the MANIFEST's `sha256sums_sha256`, and the three files equal their SHA256SUMS lines. | `jgen3.569770.0/precheck.json` |
| Sources: the builder sources this job used are byte-identical at ec5bae0 to the MANIFEST's `gen_sources_sha256` pins (from 36043bb): `gen/Makefile`, `build_free.cpp`, `build_power.cpp`, `c8gen.hpp`, `check_edge_forests.cpp`, `test_keys.cpp`, `publish_inventory.py` and `slurm/gen/crossnode.slurm`. So are `classes1`–`classes8.txt`. Only tooling the build does not use has changed since: `gen/handoff_inventory.py`, `gen/regress.py`, `gen/test_handoff_inventory.py` and `slurm/gen/{expanse_,}regress.slurm`. | `jgen3.569770.0/precheck.json` |

## Job

| Job | Where | What it shows | Files |
|---|---|---|---|
| 569770 `c8d2-jgen3` | `debugq` <NODE>, `-N 1 -n 1 --exclusive --mem=180G -t 01:00:00`; 1:43, COMPLETED 0:0 | **J-GEN-3, A-INV-4 passed.** The job ran the package's own `slurm/gen/crossnode.slurm` unchanged from the export (sha256 `95e25b70…`, as pinned in the MANIFEST). That script runs `make -C gen`, then `build_free` and `build_power` on classes7 and classes8 at 40 threads into a BeeGFS scratch directory: L7 free 2 s, L7 power 0 s, L8 free 58 s, L8 power 16 s. Then `publish_inventory.py members` writes `MEMBERS.sha256` and the builder inventories, and `cmp` checks them against the reference: all three identical, exit 0. The wrapper then compared member by member (24,839 equal, 0 differing, 0 missing or extra) and class by class (both inventories byte-identical). It recorded the platform and deleted the scratch build tree. | `jgen3.569770.0/compare.json`, `gen3.569770.0/crossnode.json`, `logs/c8d2-jgen3_569770.out` |

**Cost.** One whole Intel node for 103 s. Slurm counts 80 logical CPUs (CPUTimeRAW 8,240 CPU-s = 2.29 CPU-h); that
is 1.14 physical-core-hours (40 cores). Peak RSS was 1.4 GB.

## Files

- `scripts/jgen3.slurm` (sha256 `3c02ded8…`, equal to the spooled `slurm_script`): the wrapper.
  - Precheck, then the platform record, then the package's `crossnode.slurm` run as a child, then builder binaries
    (sha256, `ldd`), then `compare.json`, then deleting the scratch tree.
  - Submitted as `C8_PACKAGE=…/pkg/ec5bae006d93 C8_GEN_REFERENCE=…/ref/inventory8_d2_46341a3c0f11
    C8_MANIFEST_PIN=46341a3c… sbatch --export=ALL jobs/jgen3.slurm`.
- `jgen3.569770.0/` (the wrapper's records):
  - `precheck.json`.
  - `platform.txt`: `lscpu`, `numactl -H`, `/etc/os-release`, `uname`, `g++ -v`, glibc, `dpkg-query` versions of
    gcc-11/g++-11, libc6, libstdc++6, libgomp1, libgcc-s1, libquadmath0 and libgmp, Python, modules and environment.
  - `builders.txt`: the binaries' sha256, their `ldd` and resolved libraries, and the build commands.
  - `compare.json` (schema `c8-d2-jgen3-compare-1`), the comparison record.
  - `scripts.sha256`: the job script, `~/c8d2/env.sh` (`0122a133…`) and `crossnode.slurm`.
- `gen3.569770.0/` (the package script's records): `crossnode.json` (schema `c8-d2-gate-1`, passed) and the four
  `*.build.txt`.
- `logs/c8d2-jgen3_569770.out`: a copy of the Slurm log.
- `verdict.json`: a summary.

**Left on symmetry.**
- `<SCRATCH>/c8d2/evidence/ec5bae006d93/{gen3,jgen3}.569770.0`, 19 MB. This includes this run's
  `MEMBERS.sha256` and `inventories/`, whose bytes equal the published files, so they are not copied here.
- The log `<SCRATCH>/c8d2/logs/c8d2-jgen3_569770.out`.
- The export `pkg/ec5bae006d93` and the reference copy `ref/inventory8_d2_46341a3c0f11`.
- The scratch build tree `gen/ec5bae006d93/gen3.569770.0` (about 8 GB of G-files and the builders) was deleted at the
  end of the job.
