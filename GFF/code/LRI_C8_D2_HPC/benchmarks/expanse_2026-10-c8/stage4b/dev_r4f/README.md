# Stage 4b R4f on Expanse: GMP 6.2.1 built for the node (development probe, 2026-10-04)

The results and the decision input are in `docs/PERFORMANCE.md`, "Stage 4b R4f". The knob is documented in
`docs/NUMERICS.md`, "Builds". This folder holds the evidence. Everything ran on Expanse under site deviation U1,
account <ACCOUNT>, with no other site used.

## Scripts and submission

- **`scripts/`.** The job scripts:
  - `r4f_default_build.slurm`: the default build, which must equal Stage 3;
  - `r4f_gmp_build.slurm`: the GMP 6.2.1 builds, `make check`, the install, and the workers with `GMP_PREFIX`;
  - `r4f_validate.slurm`: the replay subset, G-L8SELF, perf and the tier timers;
  - `r4f_speed.slurm`: one exclusive node, at most 30 min;
  - `r4f_control.slurm`: the layout control.

  `r4f_bench.py` is the speed and profile driver, built on `tools/benchkit.py`. `submit_r4f_expanse.sh` is the Mac
  driver.
- **Before every sbatch.** The driver runs the H7E-R admission (`../../stage4a/scripts/h7_admit.py`) and the per-agent
  caps of the development phase (at most 8 live `c8d2-r4f-*` shared jobs and 1 compute node).
- **`admission/`.** The admission records and the squeue snapshots:
  - the jobs of 913e56a, at the top level;
  - the control, in `control_ef705e3/`;
  - the superseded first submission, in `superseded_ef03b93/`.
- **`../../setup/`.** The exports were checked against `git archive`: `export_check_913e56a97a6b.json`,
  `export_check_ef705e395924.json` and the superseded `export_check_ef03b93255a9.json`.

## Jobs

| Job | Commit, where | What it shows | Files |
|---|---|---|---|
| 54666319 `c8d2-r4f-defbuild` | 913e56a; shared, 16 CPUs, 0:37 | `GMP_PREFIX` unset: `c8d2_decimal` `3dbd51bb…`, `c8d2_gmp` `5c5328af…` and `c8d2_gmp_prof` `d1cc6551…` equal Stage 3. The build record names the Spack libgmp (`470e376a…`, not fat, `-march=k8`). | `r4fdef.54666319.0/` |
| 54666320 `c8d2-r4f-gmp` (fat) | 913e56a; shared, 16 CPUs, 1:49 | Tarball sha256 = Spack's pin; `VALIDSIG 343C2FF0…`. `--enable-fat`: `MPN_PATH x86_64/fat`. `make check` 197/197. Installed in `~/c8d2/opt/gmp-6.2.1-fat` (libgmp `3e4c7c41…`). Kernel instruction counts. Workers with `GMP_PREFIX`: decimal = Stage 3, gmp `c0b03496…`, DT_RPATH and ldd on the prefix. | `r4fgmp-fat.54666320.0/` |
| 54666321 `c8d2-r4f-gmp` (host) | 913e56a; shared, 16 CPUs, 1:41 | The same for `--host=zen2-pc-linux-gnu`: `MPN_PATH x86_64/zen2 x86_64/zen x86_64`, `-march=znver2`, 197/197. `~/c8d2/opt/gmp-6.2.1-zen2` (libgmp `4267ffeb…`); gmp `0a77b88e…`. | `r4fgmp-host.54666321.0/` |
| 54666322 `c8d2-r4f-val` (fat) | 913e56a; shared, 32 CPUs, 14:15 | Sections against the baseline: only `.dynstr` changes size. Replay subset passes (22 tests). G-L8SELF passes (2,000 kernels; 214,532 MP points per backend). Profile: MP tier ×1.068 per call; perf tables. | `r4fval-fat.54666322.0/` |
| 54666323 `c8d2-r4f-val` (host) | 913e56a; shared, 32 CPUs, 13:05 | The same: replay and G-L8SELF pass; MP tier ×1.125 / ×1.126 per call. | `r4fval-host.54666323.0/` |
| 54666324 `c8d2-r4f-speed` | 913e56a; compute, exclusive, <NODE>, 23:36 | heavy_free_L8 (socket 0) and heavy_power_L8 (socket 1) at 64 threads, 3 rotated repeats. Medians: baseline 159.94 / 149.72 s, fat 156.09 / 146.09 s, host 154.15 / 143.64 s. The speedups are ×1.0247 / ×1.0248 (fat) and ×1.0375 / ×1.0423 (host). Each block's 9 runs give one rows digest, equal to Stage 4a's P1. `/proc/<pid>/maps` shows which libgmp each run loaded. | `r4fspeed.54666324.0/` |
| 54668998 `c8d2-r4f-ctrl` | ef705e3; shared, 32 CPUs, 18:09 | Layout control: the Spack GMP behind an rpath of the zen2 prefix's length (4 bytes from the host worker). Its MP/binary128 per-call ratio is the baseline's within 0.3%, and so are its perf shares; host gives ×1.10–1.13. The default and host workers were rebuilt bit for bit. Two rounds in opposite orders. | `r4fctrl.54668998.0/` |
| 54666273–75, 54666276/81/82 | ef03b93; superseded | The first submission. Its default build was byte-identical to Stage 3. The GMP jobs were cancelled during `make check`, because the workers' check expected an rpath without Spack GCC's lib64 (fixed in 913e56a), and the dependents were cancelled while pending. Nothing was installed. | `logs/*_5466627[345].out`, `admission/superseded_ef03b93/` |

## Other files

- **`logs/`.** The Slurm logs of every job above.
- **`text_identity.txt`.** The worker's normalized disassembly with and without `GMP_PREFIX`: 26,595 instructions, no
  difference. This is a read-only check, run on the login node.
- **`symmetry_libgmp10_packaging.txt`.** Ubuntu jammy's `debian/rules` for gmp: `--disable-fat` and `--build
  x86_64-linux-gnu` on amd64. It was read from Launchpad; symmetry was not used.
- **`raw_evidence.tgz`.** The two GMP builds' `make.log` and `make_check.log` (sha256s in
  `raw_evidence_listing.sha256`). Run `tar xzf raw_evidence.tgz` here to restore them in place.
- **Not kept.** Each build's `config.log` is kept gzipped in its job directory. perf.data, the staged graphs and the
  package copies stayed on node-local scratch.

## Allocation and files

- **SU.** The R4f probe used 76.5 SU:
  - 913e56a: 66.0, of which speed 50.3, the validations 7.6 + 7.0, and the builds 1.1;
  - the superseded submission: 0.8;
  - the control: 9.7.

  Shared jobs are charged at the larger of their CPUs and memory/1.95 GB.
- **On Expanse.**
  - Exports: `$C8_DATA/pkg/913e56a97a6b` and `$C8_DATA/pkg/ef705e395924`, about 5,600 files each.
  - Workers: `$C8_DATA/work/913e56a97a6b/r4f-{fat,host}` and `$C8_DATA/work/ef705e395924/r4f-ctrl`.
  - GMP prefixes: `~/c8d2/opt/gmp-6.2.1-{fat,zen2,spak}` (`spak` holds only two symlinks).
  - The source and keyring: `~/c8d2/src/gmp`.
  - The superseded exports `336d0dc34845` (partial) and `ef03b93255a9` were removed.
