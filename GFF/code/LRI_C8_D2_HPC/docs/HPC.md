# C8(2) cluster runbook

Stage 3 (PLAN.md components D and E), 2026-10-03. The C7(2) runbook is kept as `docs/c7_historical/HPC_C7.md`.
Every command below is a real entry point of this package; the tools' docstrings (`python3 -B tools/<tool>.py -h`)
are the reference for every option and exit code.

## Execution model

A scientific stratum is (campaign, sector, L, graph, replicate) with its own power-of-two Sobol net. A plan cuts each
stratum into tasks (point intervals), packs tasks into job indices (shards), and writes:

- `manifest.json`: the plan, the 24 groups `<a|b>_<free|power>_L<3..8>`, the pinned tool, executable, inputs and
  rate-map hashes, and one entry per job index (group, shard, blocks, `tasks_file` pinned by sha256 and size,
  `est_core_seconds`, `est_peak_bytes`);
- `groups/<group>/`: `config.json`, `sobol.bin`, `tasks.sqlite` (planning and merge only) and `checkpoints/`;
- `groups/<group>/tasks/s<shard>.tsv`: the per-index task file. `production.py run --index I` reads only its own file, the manifest,
  the group config, the net, the pinned tools and the small inputs (A-ORC-13); it never opens `tasks.sqlite` or
  `vendor/`.

A job index commits checkpoint blocks (`--checkpoint-tasks` tasks each) atomically. A rerun of an index skips its
valid blocks and recomputes missing ones bitwise. Nothing depends on the thread count or the order of completion, nor
on the node within one CPU vendor; the native rows do depend on the CPU vendor (next paragraph), so a campaign stays on
one vendor. `merge` rebuilds every group from its blocks (phase 1: one sorted run per shard, in parallel; phase 2: an
external merge with fan-in F = min(64, RLIMIT_NOFILE - 32), then the Decimal final pass), byte-identical to the serial
reference merge. Phase 1 streams a shard block by block: the per-index task file is read in blocks (checked against
its pin before the first block and hashed again on the way), each block's rows are sorted into a spill run, and the
spill runs are merged with the same fan-in into the shard's run. A merge process therefore holds one checkpoint block
plus F rows whatever the rows per shard (`--shards 1` included); `tests/merge_scale.py` gates this at 8× the rows per
shard (the Python heap flat on every platform; the peak RSS within 16 MB on Linux and 48 MB on macOS, whose allocator
keeps freed memory resident).

**Merge restart.** Phase 1 runs and the final-pass tables are job-private (under `--scratch`) and are always rebuilt;
phase 1 re-validates every checkpoint on each run. When a group has more than F shard runs, phase 2 writes its
intermediate runs to the persistent per-campaign work directory `$C8_RUN/merge_work` (with `--work-dir BASE`:
`BASE/c8d2_merge_<first 16 hex digits of the manifest sha256>`). Each run is named by a hash of its inputs'
identities (the shard runs' sha256s, then the earlier pass's names), is written to a unique temporary file, flushed
and renamed, and ends with an `#end` line. A rerun of an interrupted merge (a wall-time kill, a node failure) skips
the groups already published, rewrites the incomplete runs, and reuses a complete run of the same name ("N
intermediate run(s) reused") only after checking that it holds exactly the merge of its inputs: the inputs' row
count, (rep, graph, begin) order, nothing after `#end`, and the sum mod 2^256 of the keyed BLAKE2b digests of its
lines equal to the sum over its inputs, which come from this merge's own phase 1 (made afresh from the validated
checkpoints); the key is drawn afresh by each merge and never stored, so no edit can be crafted to keep the sum. A run that
fails is reported ("fails verification against its inputs") and rebuilt ("N rebuilt after failing verification"), so
an edited cached run can never reach `merged.json`. A group's runs are removed only after its `merged.json` is published (or found
published and valid), and the work directory itself once it is empty, so a failed merge leaves exactly the runs a
rerun needs. Two concurrent merges of one campaign share the reusable runs; each writes only its own temporary
files and renames them into place.

**One CPU vendor per campaign (F5, Stage 5).** The native rows depend on the CPU vendor at about 1e-16 relative:
glibc's x86-64 `expl`/`logl`, which the kernel's first pass calls, use the x87 `f2xm1`/`fyl2x` instructions, whose
last bits are microcode-specific. Same binary, tasks, seed and net: 4,034 of 4,406 graph-replicate rows of an Intel Xeon
Gold 6148 run differ in their last digits from the AMD EPYC 7543 rows, while an AMD rerun reproduces the AMD rows
exactly, and AMD Zen 2 (Expanse 7742, symmetry 7532) and Zen 3 (symmetry 7543) agree (J-SWEEP-3 and its AMD control,
`benchmarks/symmetry_2026-10-c8/stage5/`). This is statistically irrelevant, but a block run twice on the two vendors
would stop the second run ("Conflicting duplicate execution"), and twin and restart bitwise identity hold only within a
vendor. A vendor-independent `exp`/`log` would change the default numerics (D1) and is a later decision. The package
therefore keeps a campaign on one vendor: the first claim (`production.py run`) publishes `$C8_RUN/cpu_vendor.json`
(vendor, family, model name, the claim's index, host and job; no-clobber) and every checkpoint records its claim's CPU
(`runtime.cpu`); a claim on another vendor stops before any block with exit 64 and a message naming both vendors; a
lane worker refuses (64) before any claim when the pin names another vendor than its node's, and a lane whose run is
refused releases the claim without a failure record and stops. `production.py status` prints the pin. Submit a
campaign to the partitions of one vendor only: on symmetry `amdq`/`amddebugq` (AMD) or `defq`/`debugq` (Intel), never
`-p amdq,defq`.

**One run-time library stack per campaign (X8, Stage-6 fix round 1).** Every checkpoint records the claim's host
fingerprint, and since fix round 1 the campaign also pins its runtime compatibility identity: the glibc version, the
sha256 of the ELF interpreter and of every library `ldd` resolves for the staged executable (keyed by soname: the
content, not the path) and whether `ldd` answered (`common.runtime_identity`). It leaves out the host, the Slurm ids
and the CPU model, so Zen 2 and Zen 3 nodes with the same image stay compatible (the vendor pin above still applies).
The first claim publishes `$C8_RUN/runtime_identity.json` (no-clobber, like `cpu_vendor.json`); a later claim under
another library stack exits 64 before any block, naming the differing fields (its `claim_io` status is "runtime
identity refused"), and the lane worker's exit-64 message names both the CPU vendor and the library stack. Run-skip,
the duplicate-run check, `merge --jobs N` (N = 1 included) and the serial merge refuse a checkpoint whose identity is
not the campaign's; a campaign whose claims predate the pin is held to the identity of its first checkpoint, and a pin
whose key is not the hash of its identity is refused. `production.py status` (and `--json`) prints the pin.

**A complete fingerprint, and one in the first checkpoint (Y6, Y8, Stage-6 fix round 2).** For a dynamic ELF worker
(every production build) a claim publishes the pins and runs a block only when its fingerprint is complete
(`common.fingerprint_problems`): `ldd` answered (not failed or timed out), listed at least one library and resolved
every library it lists to a file with a sha256 (the kernel's virtual DSO, which older glibc lists as `linux-vdso.so.1
=>  (0x...)`, excepted), the ELF interpreter is hashed, and on Linux the CPU vendor was read from `/proc/cpuinfo`
(not the `<platform>-<machine>` fallback both vendors would share). Otherwise the claim exits 64 before any pin or
block, with `claim_io` status "incomplete runtime fingerprint" and a lane releases the claim and stops: two nodes
whose probes both failed can no longer share an identity whatever their libgmp. A static ELF worker, the test
stand-ins and a macOS build keep their probed identity. Before a pilot, survey `ldd bin/c8d2_gmp` on the partition's
nodes: a node whose probe fails now makes its lanes exit 64 (fix round 2 found complete fingerprints on amdq <NODE> and
<NODE> and sharedq <NODE>; the other amdq nodes are not surveyed yet, `benchmarks/symmetry_2026-10-c8/s6fix2/`). Without the pin, the campaign's identity is its first
checkpoint's; a first checkpoint whose fingerprint is missing or malformed (`common.fingerprint_malformed`) makes
`merge --jobs N` and the serial merge refuse, where it used to switch the comparison off for every checkpoint (Y8),
and with the pin a malformed fingerprint is refused instead of crashing the merge.

**Libraries named by path are part of the identity (Z6, Stage-6 fix round 3).** `ldd` lists an `LD_PRELOAD` library or
a dependency named by an absolute path as `/opt/liboverride.so (0x...)`, without `=>`; the fingerprint used to hash
only the `=>` lines and dropped these, so claims under different versions of a preloaded library shared one identity.
`common.fingerprint` now hashes every `/path (0x...)` entry, keyed by its path; the interpreter (matched by path or
realpath) is hashed once as `interpreter`; the vDSO and the "statically linked" line are left out. Any other line of
a successful probe is an unexplained entry, which `fingerprint_problems` refuses for a dynamic worker (the claim exits
64, naming it). An ordinary node's identity is unchanged. Before a pilot, the `ldd` survey of the partition's nodes
must show no unexplained line for the real worker either.

**Dynamic-loader overrides are refused (W7, Stage-6 fix round 4).** Z6 hashed each preloaded object, but the identity
sorted the library map, so `LD_PRELOAD=A.so:B.so` and `B.so:A.so` (two interposers of, say, `expl`) gave one identity.
Now `production.py run` refuses `LD_PRELOAD`, `LD_AUDIT`, `LD_DYNAMIC_WEAK` and any `DYLD_*` variable with exit 64
before anything is staged, pinned or run (`common.loader_overrides`), and the lane worker refuses before any claim; a
campaign's workers never run with a preload chosen by the environment. What a node preloads by itself is ordered: the
fingerprint records `preload_order` (the objects of `/etc/ld.so.preload`, in load order) and `loader_env`
(`GLIBC_TUNABLES`), and the runtime identity includes each only when it is not empty, so the identity, and its key, of
an ordinary node (symmetry's amdq and sharedq nodes have neither) is the one of the tools before the fix.

**A gated executable is bound to its gate's libgmp (W8, Stage-6 fix round 4).** A non-test plan under a profile runs
only a build some J-FLAG gate passed (route (b): the bundle's gates; route (a) and profile pilots: `--numerics-gate`).
The gate validated that build with one libgmp (`check_gate`'s `gmp_library.profile`, the library both F1 tools ran
with), and `production.gate_gmp_binding` now binds the campaign to it: the plan records
`numerics_route.gate_gmp_library`, a non-test plan refuses a build record that names another libgmp, every claim of a
gated campaign checks the libgmp its worker resolves (its runtime identity) before it pins anything or runs a block
(exit 64; lanes release and stop), and run-skip, the duplicate check, both merges and `calibrate.py` refuse a
checkpoint whose fingerprint shows another libgmp. A changed library needs a fresh gate. (The symmetry nodes load
`4dc20a90…`, the libgmp of gates 570536 and 570574; a real gated claim on sharedq <NODE> bound to it, job 570579.)

**Reads per claim (A-ORC-13).** A claim reads the campaign-data allowlist (manifest, inputs manifest, pinned tools,
cost model, small inputs, group config, net, executable, its own task file, and the CPU-vendor and runtime pins
`cpu_vendor.json` and `runtime_identity.json` once they exist; F5, X8) and the platform/runtime class of the host fingerprint (`/proc/cpuinfo`, read once and giving both
the CPU model and the vendor; the staged executable, the ELF interpreter and libraries, the `ldd` probe's pipe;
`fingerprint_bytes` in every checkpoint). Below the Python layer, libc and OpenSSL also read a few system files by
themselves in every claim process: on Linux `/proc/sys/crypto/fips_enabled` (OpenSSL initialization, through
`hashlib`), glibc's `locale.alias` (locale setup) and the `zoneinfo` file of the local time zone. These reads are a
constant set of small files, independent of the task count of any index. The Python-level read spy of
`tests/unit_orchestration.py` does not see them (they happen in C), so they are not in its byte totals; `rchar` on real
Slurm (J-SMK-4) includes them.

**rchar per claim (R07; F9, Stage 5).** Every `production.py run` logs one line `claim_io {json}` at exit (in the lane
index log, or the array element's Slurm log): `rchar` of `/proc/self/io` at exit (this process and its reaped children:
the native worker and `ldd`), the native launches and their own `rchar` (the delta across each launch, measured,
since the claim process reads nothing while it waits), the fingerprint's in-process `fingerprint_bytes` and its
`fingerprint_rchar` (with the `ldd` probe), the claim's own bytes per category (its task file, its checkpoints, the
staged pack members of its blocks: the bytes `stage_graphs` read from the pack, exactly the members' since the F12 fix
below; each block's task file, the native outputs read back), and
`non_own_bytes` = rchar - own bytes - native rchar, also minus `fingerprint_bytes` and minus `fingerprint_rchar`.
Reading `/proc/self/io` is a measurement read outside the two classes above, made only there: at the claim's start,
around the fingerprint, around each native launch and at exit (2 + 2 per launch + 2 reads of a few hundred bytes).
`python3 -B tools/claim_io.py $C8_RUN [--logs ...] [--output report.json]` evaluates the plan's comparison:
`fingerprint_bytes` identical per fingerprint key, and the non-own bytes, with and without the fingerprint, between the
indices of the smallest and the largest group by `tasks.sqlite` size (more than 10× apart) within max(10%, 2 MB)
(exit 0 pass, 1 fail, 2 undecided). It also counts the runs per pack read path (`pack_reads`: records of schema
`c8-d2-claim-io-2` read the pack exactly; records of `c8-d2-claim-io-1`, the tools before the F12 fix, read it through
Python's buffer and are named in `notes`, since their non-own bytes include that over-read). Deviation from the
plan's wording, recorded here: the plan subtracts the claim's task file, checkpoints and staged members from rchar;
the native launches' reads are also measured and subtracted as own work. A native launch reads only the claim's
job-private copies (its block's members and task file, gamma, the net), the executable and its libraries (on symmetry
1.0008-1.0011 native bytes per staged byte at L8: its staged copies once); what is left is everything the claim reads
besides its own work. The report gives the native read factor (native rchar per staged byte) per run. Stage 5's
J-SMK-4 had attributed about 0.7 extra bytes per staged byte (from L6 on; 29.8 MB at L3-L5 against 701.6 MB at L8) to
the native re-reading its staged files; the real-Slurm run below showed they were the claim process's own buffered
pack reads (F12).

**F12: the pack over-read, found on real Slurm and fixed in d5dfd38 (2026-10-05,
`benchmarks/symmetry_2026-10-c8/stage5/fix/`).** On 22 claims of a J-SMK-4-shaped campaign on one amddebugq node (tools
of 2b3a923), every run logged its `claim_io` line and `fingerprint_bytes` was identical (7,007,827), but
`tools/claim_io.py` failed: 22.8 MB of non-own bytes at a_free_L3 against 694-699 MB at b_free_L8. The native was not
the cause (1.0008-1.0011 native bytes per staged byte at L8). The claim process itself over-read the pack:
`stage_graphs` opened it with Python's default buffering, whose buffer is the file system's `st_blksize` (524,288 bytes
on BeeGFS; a buffered `read(length)` after a seek outside the buffer refills one whole buffer), so it read up to
512 KiB of neighbouring pack bytes per member that the own-bytes count did not include: 0.70 bytes per staged byte at
L8, about 0.7 GB of extra BeeGFS reads per L8 index. A replay of CPython's buffer rules over every block's members
predicts that over-read per run (0.4 MB at L3 to 675 MB at b_free_L8); with it subtracted, the non-own bytes of all 22
runs lie in 20.7-23.3 MB and the comparison passes (0.98 MB against 2.23 MB).
**The fix** (`tools/` only, no `src/` change, staged bytes unchanged): `stage_graphs` reads each member with
`production.read_member`, `os.pread` in a loop over short reads with no Python buffer, so a claim reads exactly its
members' bytes from the pack, and the same sha256 checks apply to the same bytes; `stage_runtime.py`'s member copy
(array mode, `C8_STAGE=1`) reads the same way. The claim's own staged-member bytes are the bytes actually read, and its
`claim_io` record has schema `c8-d2-claim-io-2`. Tests (Mac): `unit_orchestration` `pack_reads` (every `os.pread`
counted on a fake pack whose members sit around and above 512 KiB: bytes read = member bytes, short reads, a truncated
pack refused; the pre-fix buffered read with a 512 KiB buffer over-reads exactly as the replay predicts; on Linux,
rchar across `stage_graphs` equals the member bytes), `staging`, `claim` (the A-ORC-13 spy counts `os.pread` and sees
the pack opened only with `os.open`) and `claim_io`; `pack_reads`, `staging` and `claim` fail on the pre-fix read.
**Confirmed on real Slurm (2026-10-05, `benchmarks/symmetry_2026-10-c8/stage5/close/`).** The same 22 claims of a
freshly planned campaign (`io-68ee571ee614`, seed 3934799973789933184; job 570212, export 68ee571ee614 with the tools
of d5dfd38) all log `c8-d2-claim-io-2` records with the exact read path, and `tools/claim_io.py` passes with no
correction: non-own bytes 29.85 MB at a_free_L3 against 30.31 MB at b_free_L8 (difference 0.46 MB, tolerance
2.28-2.99 MB); a b_free_L8 claim reads 671 MB less than before, with the same staged bytes and native reads. J-VAL-1 on
the same export (job 570211) passes, including `pack_reads`' Linux check (rchar across `stage_graphs` = the member
bytes). Campaigns planned with the earlier tools pin them and must be re-planned (as after every `tools/` change).

There are two execution modes for one campaign, never mixed while jobs are live (exit 65):

- **lane mode** (default for symmetry and Expanse `compute`): whole-node `slurm/lane_worker.sh` jobs whose lanes (by
  default NUMA-aligned lanes of the plan's `--threads` cores on AMD, one per socket on Intel) claim indices from
  `lanes/queue.txt`;
- **array mode** (Expanse `shared`, small campaigns): `slurm/run_array.sh` array elements, one index each.

## Environment

Every job sources `$C8_ENV_SETUP` (examples in `slurm/env.sh.example`; Expanse: the installed byte copy of
`slurm/env_expanse.sh` at `~/c8d2/env_expanse.sh`). It provides the compiler, Boost 1.77 headers, GMP 6.2.1, a
Python >= 3.10 venv, the Slurm commands, `C8_SITE`, `C8_DATA` (Expanse) and `C8_SEEDS`. The venv holds
`requirements.txt`, pytest included (F2: `tests/vendored_isolated.py` runs the vendored assembly tests with it). G0's
venv check is `python3 -B tests/check_venv.py --strict` on a compute node (every requirement importable, at its minimum
version); `make test` runs it first without `--strict`, so a missing package stops J-VAL-1 at once, by name.

| Variable | Meaning |
|---|---|
| `C8_PACKAGE` | The package export the jobs run from (a `git archive` export of a tagged commit) |
| `C8_RUN` | The campaign directory |
| `C8_SEEDS` | The forbidden-seed log (`tools/seeds.py`); every non-test plan passes `--forbid-seeds-from $C8_SEEDS` |
| `C8_SBATCH_ARGS` | Site options for every submitted job (one line; checked against an allowlist) |
| `C8_SITE` | `symmetry`, `expanse` or `other`: selects the admission rules below |
| `C8_TIME_POLICY` | `finite` (default) or `unlimited` (pi, personal desktop, canonical: `--time=0`, verified) |
| `C8_LANE_MEM`, `C8_MERGE_MEM`, `C8_MERGE_JOBS` | Lane worker memory (180G; amdq-only 245G; Expanse 240G), merge memory (64G) and processes (24) |
| `C8_LANE_TIME`, `C8_MERGE_TIME` | Lane worker (24:00:00) and merge (02:00:00) wall times |
| `C8_LANES` | Unset (default): on AMD the NUMA nodes split into lanes of at most the plan's `--threads` cores (8 × 8 on symmetry, 16 × 8 on Expanse compute at the default 8), elsewhere one lane per socket; or `numa` (one lane per NUMA node), `socket`, or n equal parts of the node |
| `C8_INPUTS` | Test fixtures only (`tests/fixtures/inputs_mini`); a non-test plan uses `inputs/` |

## Survey first

Before every submission: `sinfo -h -p <partition> -o '%t %D'` (idle and mix nodes only), your own and the account's
load (`squeue -u $USER`, Expanse `squeue -A <ACCOUNT> -h -o '%u %T %P %q' | sort | uniq -c`), and say whether the job starts
now. `slurm_submit.py` prints the idle-node count of each requested partition and `sbatch --test-only`'s start estimate
before it submits.

## Sites: symmetry first (user rule, 2026-10-05)

The user: "symmetry is back, so for the moment only use expanse if symmetry is not enough". New compute runs on
symmetry; Expanse is used only for the Expanse-specific items below or when symmetry's capacity is not enough. A
campaign stays on one site and one CPU vendor (AMD: amdq/amddebugq on symmetry).
- **The `dd+mp256` J-FLAG gate ran on symmetry and PASSED** (2026-10-05, job 570210; `docs/NUMERICS.md`, "The
  `dd+mp256` J-FLAG gate on symmetry"): one whole amdq node (`--exclude=cn112`, inside the H7 cap),
  `make gmp NUMERICS=dd,mp256` from the export 68ee571ee614 (job 570208, `bin/c8d2_gmp_dd+mp256` `d5df32ac…`), A-RPL-8
  before and after, then `tests/numerics_flags.py --profile dd+mp256` at full scale (F1, F2, F4, F5; F2 on the gates'
  fixed base seed 820262401, whose 49 seeds both logs already held, so it added none). F1/F2 equal Stage 4c's Expanse
  values; F4 measured symmetry's own speedup, ×2.530 (F10). Scripts: `benchmarks/symmetry_2026-10-c8/stage5/close/`.
  It was planned on Expanse and moved by this rule; `benchmarks/expanse_2026-10-c8/stage5/fix/scripts/fxe_flag.slurm`
  stays as the record of that plan and is not to be submitted. Since Stage-6 fix round 1 the 570210 record is refused
  by `design.check_gate` (no F1 coverage, build binding or verified team sizes, X1-X3). **The gate was re-run with the
  fixed harness and PASSED** (2026-10-06, job 570373, export `c30bfc5f0bdf`, the same build `d5df32ac…`; F1, F2 and
  F3 equal to 570210's field by field; `benchmarks/symmetry_2026-10-c8/s6fix1/`). Its record
  (`benchmarks/symmetry_2026-10-c8/s6fix1/s1flag.570373.0/jflag_dd+mp256/numerics_flags.json`, sha256 `2eaaebcf…`)
  was the `--numerics-gate` of a route-(b) freeze until Stage-6 fix round 3. **Fix round 3 changed every kernel
  executable** (Z4, `src/kernel.hpp`), the profile build included, and `check_gate` now also requires the libgmp
  provenance of both F1 tools (Z19), which 570373's record predates: the gate ran again on the new build, the profile
  cost model was re-measured and the route-(b) bundles re-frozen (`benchmarks/symmetry_2026-10-c8/s6fix3/`): **the
  gate PASSED on the new build** (2026-10-06, job 570536, export `997639178c1f`, `bin/c8d2_gmp_dd+mp256` `a46f3060…`;
  F1, F2 and F3 equal to 570373's field by field, F4 ×2.517; record `benchmarks/symmetry_2026-10-c8/s6fix3/s3flag.570536.0/jflag_dd+mp256/numerics_flags.json`, sha256 `a8de4037…`).
  **Fix round 4 (W18) requires the authenticated input set** in the record (the inputs manifest the gate ran on,
  every input verified at its start and end, complete; `design.check_gate` compares it with the pilot's or plan's),
  which 570536's record predates: it is refused for exactly that, and **the gate PASSED again** on the same build
  `a46f3060…` with a fresh F1 baseline (2026-10-06, job 570574, export `392ed22d1d02`; F1, F2 and F3 equal to 570536's
  apart from task timings, F4 ×2.574; record `benchmarks/symmetry_2026-10-c8/s6fix4/s4flag.570574.0/jflag_dd+mp256/numerics_flags.json`,
  sha256 `42e6d2d8…`, inputs manifest `3813f24a…`), the `--numerics-gate` of a route-(b) freeze from now on; the
  route-(b) bundles were re-frozen with it (job 570579). A non-test route-(b) plan runs only an executable that a gate in
  its bundle passed (here `a46f3060…`, symmetry's GCC 11.4 build of the fix-round-3 commit, unchanged by fix round 4).
- **Expanse items** (status 2026-10-05, after 32e5f2b; `benchmarks/expanse_2026-10-c8/pre6/README.md`):
  1. **the J-EXP-1 rerun (A-EXP-3): PARTIAL, still owed.** Job 54681003 (debug, <NODE>, `-t 00:30:00`, the
     partition's limit; export `pkg/99bbfddd0719` of 99bbfdd) passed the build, A-RPL-8 (decimal `99a51c1d…`, gmp
     `1d2a2181…`, inspect and c7ref identical), Boost 1_77 in every build record, `check_venv --strict`, `validate` and
     12 `unit_orchestration` groups; it was cancelled after 20:50 because Expanse's Lustre was failing (both debug nodes
     drained by Lustre health checks, the build 430 s against 33 s), so F1, F3, F4 and the rest of `make test` were not
     reached (44.4 SU). This is a site incident, not one of the plan's recorded gaps (an inactive allocation, a job
     not started within 48 h). **A-EXP-3 is to be completed after Stage 6, on the post-inspection commit**: a fresh
     export (`fxe_exp1.slurm` refuses an export that already holds `bin/` or `build/`), then the same job once
     `sinfo -p debug` shows idle debug nodes without a Lustre drain reason (about 20 minutes, about 43 SU). Symmetry
     cannot substitute: A-EXP-3 is Expanse's own acceptance (its GCC 13.3, Boost and GMP modules, venv and zen2 nodes).
     **Owed with it (Y1, Stage-6 fix round 2): the zen2 precision checks.** Job 54676895's forced tiers, point checks
     and class-B builds linked Spack's libgmp, not the zen2 library, so `GMP_PREFIX` is NOT cleared for production
     (`docs/NUMERICS.md`, "Builds"). The same Expanse session re-runs `make test-full GMP_PREFIX=<zen2 prefix>` (the
     point checks and `validate --full` with class B) and `tests/forced_tiers.py`, all with the tools bound to the
     worker's GMP, after `make -B gmp GMP_PREFIX=...`; until then no campaign uses a `GMP_PREFIX` build;
  2. ~~the seed sync~~ **done** (32e5f2b): Expanse's log, symmetry's and the mirror `designs/forbidden_seeds.json` hold
     the same 90 seeds; `benchmarks/symmetry_2026-10-c8/stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt` is marked synced.
     Seeds added on symmetry after it go into Expanse's log before any plan there
     (`benchmarks/symmetry_2026-10-c8/stage5/scripts/seedsync.sh`; "The seed log" below). **Pending again**: the 8
     seeds of the pre-Stage-6b check (job 570302, `benchmarks/symmetry_2026-10-c8/pre6b/`), the 5 of Stage-6 fix
     round 1 (jobs 570376 and 570379, `benchmarks/symmetry_2026-10-c8/s6fix1/`) and the 2 of Stage-6 fix round 2
     (job 570418, `benchmarks/symmetry_2026-10-c8/s6fix2/`) are in symmetry's log and the mirror (105 seeds) and
     listed in `PENDING_EXPANSE_SYNC.txt` for Expanse's;
  3. ~~the deletion of the 30 obsolete exports~~ **done** by the host on 2026-10-05 at 10:40 PDT (user-approved; the
     list in `benchmarks/expanse_2026-10-c8/stage5/g4cfix/README.md`, "D6"): 29 deleted after re-grepping every
     evidence file; `pkg/d46e7360fe88` kept, because the completed gate job 54669708 read it as its B2f source tree and
     the approval covered unreferenced exports only. Lustre went from 1,651,026 to 1,474,822 files
     (`benchmarks/expanse_2026-10-c8/README.md`, "Stage 5 fix round, close-out and the export deletion").

## Admission (R12)

`tools/slurm_submit.py` (behind `slurm/submit.sh` and `slurm/resubmit.sh`) counts every new job, the merge included:
k = N + 1 for `--lanes N`, the array elements plus the merge for arrays. A refusal exits 65 and prints the largest
admissible N. Each job role has its own effective options: work arrays and lane workers take `C8_SBATCH_ARGS` and then
the extra options; a merge takes the same partition, account, QOS, exclusions and other overrides, and only its
memory and CPUs from `C8_MERGE_MEM` and `C8_MERGE_JOBS` (its time, as every job's, is the user's `--time` if given,
else `C8_MERGE_TIME`). Admission counts every new job on the
partitions of its own role, and the ledger records each job's own partition and account. Before each `sbatch` the
job's effective options (the script's `#SBATCH` directives, then the `SBATCH_*` inputs, then the command line) are
checked against its role, and the job's partition and account are passed explicitly (X12, Stage-6 fix round 1):
`Context.selection` resolves each from the user's option, `SBATCH_PARTITION`/`SBATCH_ACCOUNT`, `C8_ACCOUNT`, then the
Expanse defaults (`shared`, `<ACCOUNT>`), and every `sbatch` (and its `--test-only` preview) gets `--partition` and
`--account` after the user's options and before the trailing `--time` (so `--time=0` stays last under the unlimited
policy); on symmetry, with no account selected, no `--account` is added. A job whose effective account differs from the
one admission counted is refused (64), and the ledger records the partition and account the job was submitted with.
The checks per role: a normal lane worker is exclusive with `C8_LANE_MEM`, a drill worker never exclusive, a merge
never exclusive with its own CPUs and memory, the partition the one admission counted; a violation exits 64 before the
job exists. Decisions are serialized by the per-user site lock `~/.c8_site_<site>.lock` (exit 75 while held), taken
after the campaign lock `$C8_RUN/.c8_submit.lock`. The counts come from `squeue -h -r -o '%i|%T|%P|%q|%D|%u|%j'`: the
job name, the only free-text field, is last and the line is split at its first six `|`, so names containing `|` are
counted. A line that still does not parse refuses admission (exit 69, nothing submitted); it is never skipped.

- **Expanse, H7E-R** (`LRI_C8_shared/inventory/DECISIONS.md`, agreed with C63d on 2026-10-03): at most 11 running and
  27 submitted normal-QOS `c8d2-*` jobs of this session, the whole <ACCOUNT> account at most 32 running normal-QOS jobs
  (other users included), at most 32 live `c8d2-*` jobs on `shared`, and at most 4 compute nodes during development.
  A superseded pending merge stays counted until a snapshot shows it gone. A pilot window re-splits the budget only
  through a DECISIONS line: `C8_EXP_RUNNING`, `C8_EXP_SUBMITTED`, `C8_EXP_ACCOUNT_RUNNING`, `C8_EXP_SHARED` and
  `C8_EXP_NODES` are accepted only together with `C8_ADMISSION_REF=<that line>`, which every ledger line records.
- **symmetry, H7** (`C8_AMDQ_CAP` from `env.sh`, 4 by default): during development at most 4 live `c8d2-*` jobs on
  the AMD pool, amdq, amddebugq and amdpreq counted together. `env.sh` supplies 4 only as a default
  (`export C8_AMDQ_CAP="${C8_AMDQ_CAP:-4}"`, X11, Stage-6 fix round 1; the installed `~/c8d2/env.sh` was edited the same
  way on 2026-10-06, `benchmarks/symmetry_2026-10-c8/s6fix1/`), so an explicit agreed window `C8_AMDQ_CAP=<n>
  slurm/submit.sh ...` survives the sourcing, higher or lower; a job counts if any partition it lists is one of them (`-p amdq,defq`
  would count, but it mixes CPU vendors and is never used for a campaign: F5 above). Only a pilot or production needs
  an agreed window.
- `--exclude=cn112` on symmetry's amdq (a known bad node).
- **Memory options follow sbatch's precedence (Z7, Stage-6 fix round 3).** A memory option on the command line or in
  the job script's `#SBATCH` directives resets an inherited `SBATCH_MEM_PER_CPU` or `SBATCH_MEM_PER_NODE`, as sbatch
  itself does, and `slurm_submit.py` removes those variables from that job's sbatch environment; an inherited
  `SBATCH_MEM_PER_CPU` no longer refuses the merge after the arrays were submitted, nor the lane workers. Mutually
  exclusive memory options in one job are refused (64). A user `--mem-per-cpu` for array jobs is refused (64): it
  clashes with the array script's `#SBATCH --mem`; give `--mem`. `Context.preflight` checks every job of `submit`,
  `resubmit`, `lanes` and `window` before the first `sbatch`, so a refusal leaves nothing submitted.

## Lane mode (symmetry, Expanse compute)

```bash
export C8_ENV_SETUP=$HOME/c8d2/env.sh C8_PACKAGE=<export> C8_RUN=<campaign>   # symmetry
export C8_SBATCH_ARGS="-p amdq --exclude=cn112" C8_LANE_MEM=245G
$C8_PACKAGE/slurm/submit.sh --lanes 1            # one whole-node worker + one afterany merge: 2 AMD-pool jobs
python3 -B $C8_PACKAGE/tools/production.py status $C8_RUN
$C8_PACKAGE/slurm/submit.sh --lanes 1            # one more worker; the pending merge is replaced (A-ORC-10): 4 jobs
```

The example fits the default AMD-pool cap (Y16, Stage-6 fix round 2): admission counts every live `c8d2-*` job, and a
superseded merge is cancelled only after its replacement was accepted, so the second command needs room for the live
worker, the old merge, the new worker and the new merge (2 + 2 = 4 = `C8_AMDQ_CAP`). With `--lanes 2` first (three
jobs), adding a worker would need five and is refused (exit 65, which prints the largest admissible N). More workers
at once need an agreed window (`C8_AMDQ_CAP=<n>`, "Admission" above). `tests/unit_orchestration.py` `doc_examples`
replays this block on the fake scheduler with the default cap.

Expanse: `C8_ENV_SETUP=~/c8d2/env_expanse.sh C8_SBATCH_ARGS="-A <ACCOUNT> -p compute" C8_LANE_MEM=240G`.

- `submit.sh --lanes N` rebuilds `lanes/queue.txt` (`lanes.py queue`: completeness from the checkpoint blocks, a new
  generation; a done marker of an incomplete index is removed and logged in `lanes/done_invalidated.jsonl`), releases
  stale claims of finished owner jobs (`lanes.py release-stale`, from a snapshot of the real uid's jobs), then submits
  N workers and one merge with `--dependency=afterany` on every live and new worker. A superseded merge is cancelled
  only after the new merge was accepted, and only while the scheduler still holds it pending: `scontrol hold` (refused
  for a job that started), its state read again (a started one is released and left alone), then `scancel
  --state=PENDING`; the outcome is a ledger note. A RUNNING merge is never cancelled. `--lanes 0` submits only the
  merge.
- Under `C8_TIME_POLICY=unlimited` a job accepted without `TimeLimit=UNLIMITED` stops the submission at once (exit 70):
  no further worker, no merge (it would not wait for that job) and no cancellation. The message lists every job
  accepted so far; inspect the job, then `submit.sh --lanes 0` submits a merge on every live worker, it included
  (array mode: `resubmit.sh` waits on every live element).
- A worker splits the node into lanes (`C8_LANES`). The default (R5b, from the P4 lane-shape profile in
  `docs/PERFORMANCE.md`) is the best measured shape on both sites with one plan: on AMD each NUMA node is split into
  the fewest equal lanes of at most the plan's `--threads` cores (default 8), which gives 8 × 8 on symmetry amdq
  (NUMA nodes of 8 cores) and 16 × 8 on Expanse compute (NUMA nodes of 16 cores; `C8_LANES=numa` there gives 8 × 16,
  1.0% slower in P4); on Intel nodes one lane per socket. The worker log names the shape. The worker reduces the lane
  count or refuses (64) when lanes × the largest `est_peak_bytes` exceeds 0.85 × its memory limit, and never makes a
  lane wider than the plan's `checkpoint_tasks`. The memory limit is the smallest finite cgroup limit over the
  worker's cgroup and every visible ancestor (Y7, Stage-6 fix round 2; v1, v2 and hybrid hierarchies, a malformed
  `/proc/self/cgroup` line skipped), not the first finite one: a step allowing 64 GiB inside a 16 GiB job gives 16 GiB,
  so eight lanes of 4 GiB become three.
- **A claim's memory (W9, Stage-6 fix round 4).** A claim used to read and keep every task row of its index (the
  finding's pilot-shaped example: 16,449,536 rows in one free-L8 index), while `est_peak_bytes` counted one block's
  kernels, threads × 4 MB and 0.5 GiB. Now it copies its task file into its private runtime in 256 KiB pieces, checked
  against the manifest pin, and streams one block at a time (`snapshot_tasks`, `snapshot_blocks`; `stage_runtime.py`
  likewise), so it holds one block of rows whatever its index's size, and `est_peak_bytes` adds min(tasks,
  `checkpoint_tasks`) × 16 KiB for those rows (about 10 KiB measured per row) and 2 KiB per manifest job entry and per
  inventory row (the plan metadata every claim parses; about 50 MB for 24,173 rows). The lane memory guard and the
  array memory suggestion consume the new value. Measured on symmetry: `benchmarks/symmetry_2026-10-c8/s6fix4/`.
- **OpenMP teams (Y2, Stage-6 fix round 2).** Every native launch runs in one controlled environment
  (`common.omp_child_env`): the inherited one without any `OMP_*`, `GOMP_*` or `KMP_*` control, then `OMP_NUM_THREADS`
  = the requested team, `OMP_DYNAMIC=FALSE`, `OMP_PROC_BIND=close`, `OMP_PLACES=cores` and one BLAS thread. An
  inherited `OMP_THREAD_LIMIT=1` or `OMP_DYNAMIC=true` (a module, the submitting shell) used to run a nominal 8-thread
  lane serially while the worker still reported 8 threads and the deadline estimate divided the work by 8. This holds
  for the lane, array (`run_array.sh` unsets the controls as well), sweep and direct `production.py run` entry points.
  `production.py run` also watches each ELF worker's team on Linux (`common.TeamWatch`, `/proc/<pid>/task`): a worker
  that has not shown the requested team after 60 s of wall time while it has used 30 s of CPU time is stopped, nothing
  of its block is kept, and the claim exits 64 (a lane releases the claim and stops); a worker still waiting on I/O is
  not taken for a serial one. Every checkpoint records `runtime.omp_team` and `production.py status` counts the
  verdicts (`omp_teams`). The test harnesses launch the same way (R1, R2, Stage-6 residuals): `tests/validate.py`
  (every worker, inspector and precision-tool run, `harness_env`; the A-RPL-6 1-against-4-thread runs also have their
  teams observed with `common.TeamWatch` and fail without the requested team, or where it cannot be observed),
  `tests/sanitize.py` (`omp_child_env(4)` plus the sanitizer options), `tests/forced_tiers.py`,
  `tests/numerics_flags.py`'s F1 tool, `tests/quad_differential.py` and `tools/prepare_inputs.py`'s inspector. Launches
  that run concurrently without disjoint CPU sets (validate's `--jobs` batches, the ranges jobs) use
  `omp_child_env(..., bind=False)`: no `OMP_PROC_BIND`/`OMP_PLACES`, so they do not all bind to the first cores.
- A lane claims the heaviest unclaimed index that fits the job's remaining time: est × f_class / (threads × 0.9) ×
  1.5 + 300 s, with f_class the cost model's CPU-class factor of the host (1.5 for an unknown class). The remaining
  time comes from `squeue -o %L` (`UNLIMITED` means no deadline under the unlimited policy and falls back to
  `C8_LANE_SECONDS` under the finite one), else `C8_LANE_SECONDS`.
- Failures: an index with 2 failure records (`C8_LANE_MAX_FAILURES`) is skipped; a lane stops after 3 failures in a row.
  The count is read again after the claim is taken (X13, Stage-6 fix round 1): only a claim holder writes a failure
  record, before it releases, so a lane whose scan saw a stale count releases a claim whose index reached the limit
  meanwhile, logs "skipped ... rechecked under its claim" and launches nothing.
- **Stop signals** (F7, A-ORC-8a). `slurm/lane_worker.sh` execs the worker, so a `scancel`, a requeue or the wall limit
  reaches it as SIGTERM (slurmstepd signals the batch process, and SIGKILLs everything left once it exits). The worker
  forwards SIGTERM to its lanes and each lane to its `production.py run`, which stops its native worker, removes its
  job-private runtime and logs "stopped by signal 15" with its `claim_io` line; the lane removes its scratch directory
  and exits 143, its claim left stale (released by the next `release-stale`, `submit.sh --lanes N` or a requeued
  incarnation of the same job) and no failure record written. The worker waits at most `C8_LANE_STOP_SECONDS` (25 s,
  below Slurm's KillWait of 30 s on symmetry) for its lanes, a lane 0.8 × that for its run; a run still alive then is
  killed with its process group (each run is its own session, so its native worker goes too), a lane still alive is
  killed, and the worker removes any `c8d2_lane_<job>_*` scratch of its job left in `$TMPDIR` before it exits 143.
- **Done markers are hints, never evidence** (R03). `status`, `merge` and `assemble` count checkpoint blocks only. A
  deleted checkpoint of a completed index is recovered by the next `submit.sh --lanes N` (the queue rebuild removes
  the marker; a lane recomputes the block bitwise), or by any claim holder that finds the blocks missing. Its merge job
  then publishes the group again and assembles (F8, "Restart, recovery and duplicates" below).
- **Drills** (test-only plans on a shared partition; `C8_LANE_DRILL=1`): no `--exclusive`, `-c` from `C8_LANE_CPUS`
  (2-8), `--mem` from `C8_LANE_MEM` (at most 2,000 MB per CPU), `--no-requeue`; the merge takes `C8_MERGE_JOBS` (≤ 8)
  CPUs and `C8_MERGE_MEM`. `slurm/lane_worker.sh` carries no `#SBATCH --exclusive` (a directive cannot be cancelled
  from the command line); the submitter adds `--exclusive` to normal workers only and refuses a drill whose effective
  options are exclusive.

## Array mode (Expanse shared)

```bash
export C8_ENV_SETUP=~/c8d2/env_expanse.sh C8_PACKAGE=<export> C8_RUN=<campaign>
export C8_SBATCH_ARGS="-A <ACCOUNT> -p shared"      # plan with --threads 32; --mem from the plan's suggestion (or larger)
$C8_PACKAGE/slurm/submit.sh                      # arrays of the incomplete indices + an afterok merge
$C8_PACKAGE/slurm/resubmit.sh                    # after failures: only the missing indices, no duplicates of live work
```

`run_array.sh` takes the plan's memory suggestion (1.5 × the largest `est_peak_bytes` + 1 GiB) and refuses a smaller
user `--mem` (64). `production.py status` prints the resubmission lines (`slurm/submit.sh --window OFFSET:ARRAY`).

## Restart, recovery and duplicates

- A rerun of an index (array element, lane claim or by hand) skips valid blocks and recomputes missing ones bitwise;
  a corrupt block stops the run and the merge.
- A requeued lane worker (same job id, a new restart count) releases its own claims and continues; `release-stale`
  releases the claims of owners that are no longer live (PENDING, RUNNING, REQUEUED and COMPLETING owners keep theirs).
- `submit.sh` refuses (65) while work or a merge of the campaign is live, and never submits a duplicate of live work.
- A merge killed before it finished (`merge.sh` again, or `production.py merge`) resumes from the complete intermediate
  runs in `$C8_RUN/merge_work` ("Merge restart" above).
- **merged.json is a group's commit point** (F8, A-ORC-12). A group's tables (`graph_replicates.csv`,
  `graph_tails.csv`, `graph_costs.csv`) are committed once its `merged.json` exists: a committed table must be
  identical (a changed one stops the merge, "Checksum mismatch"). Tables without a `merged.json` are uncommitted (left
  by a merge whose `merged.json` was removed, as in the recovery of a completed index, or by a merge interrupted before
  it): a different one is replaced atomically and reported ("replaced the uncommitted graph_costs.csv ... timing
  only"; a changed scientific table is reported as "SCIENTIFIC TABLE CHANGED"). `graph_costs.csv` holds the native
  row seconds, so a recomputed block always regenerates it; every reader of a group's tables goes through its
  `merged.json` digests. `assemble.py` (and `combine.py`) keep an identical result, supersede a result whose only
  change is `merged_sha256` (the scientific content unchanged: the re-merged group's `merged.json` differs in timing
  fields only), keeping the old bytes as `C8_[test_]result.superseded.<sha256[:12]>.json`, and refuse any other
  difference. So the recovery of a completed index (J-DRL-8: delete a checkpoint and its group's `merged.json`, then
  `submit.sh --lanes 1`) completes unattended through its merge job.
- An interrupted plan leaves no campaign directory (atomic publication); rerun it.
- **Moving a campaign** (X9, Stage-6 fix round 1). `plan --design BUNDLE` copies the bundle's verified
  `design_meta.json`, `design.json` and `counts/*` into `$C8_RUN/design_bundle/` (manifest `design.pinned_copy`), so
  `assemble.py` and `combine.py` no longer need the bundle at the path recorded at planning: they take `--bundle DIR`
  if given, else the pinned copy, else the recorded path, and whichever they use must have the `design_meta.json`
  sha256 the campaign pinned (which pins every counts file). A batch planned before fix round 1 has no pinned copy;
  combine it with `--bundle DIR`.

## The allocation ledger and accounting (R10)

`$C8_RUN/submissions.jsonl` (schema `c8-d2-ledger-1`; `<prefix>-ledger-1` for a campaign of another schema prefix,
see below) lists every job `slurm_submit.py` submitted. A job that does
campaign work without it registers itself: the sweep (`tools/sweep.py`, right after its plan) and every plan job
(`slurm/plan.sh`, role plan): `python3 -B tools/ledger.py register RUN --role sweep|plan`. Registration is idempotent;
a requeue adds an attempt note.

`python3 -B tools/accounting.py RUN --output FILE` sums ElapsedRaw × physical cores (AllocCPUS / ThreadsPerCore) over
every `sacct -X --duplicates` record of every ledger job and gives η_node = busy thread-seconds / allocated work
core-seconds (roles lane, array, sweep). A checkpoint naming a job that is not in the ledger stops it with "allocation
unknown" (exit 3); checkpoints without a Slurm id are reported as unaccounted local work, which only a `--test-only`
design freeze accepts. The accounting fails closed: an sacct line that does not parse, a ledger job without a record,
an element of a ledger array without one (a never-started range `<id>_[a-b]` counts, at zero time), fewer records
than the attempts the ledger or the checkpoints' restart counts show, or (X15, Stage-6 fix round 1) a live allocation
makes it incomplete: the current (last) sacct attempt of every job and array element must be terminal (COMPLETED,
FAILED, CANCELLED, TIMEOUT, OUT_OF_MEMORY, NODE_FAIL, PREEMPTED, BOOT_FAIL, DEADLINE, REVOKED; `CANCELLED by <uid>`
included) and
every earlier one terminal or a requeue state, so RUNNING, PENDING (a pending array range too), REQUEUED as the current
attempt, COMPLETING, SUSPENDED or an unknown state count as live; historical attempts stay in the sum: the reasons are listed,
η_node is null ("unavailable"), the hours are lower bounds, the tool exits 4 and `design.py` refuses to report or
freeze on it. Both tools take `--schema-prefix` (default `c8-d2`; `design.py` passes its own): the campaign must be a
`<prefix>-production-1` campaign and every ledger record a `<prefix>-ledger-1` record, so a C8(3) pilot is accounted
from its own `c8-d3-ledger-1` ledger, and a ledger of another prefix is refused (exit 2 from `accounting.py`, 64 from
`ledger.py`), never skipped.

## The seed log (D9)

`$C8_SEEDS` is append-only (schema `c8-d2-seeds-1`, lock `<log>.lock`): `tools/seeds.py init` (since fix round 3
under the log's lock, re-checked there and published without replacing a file: an `init` racing an `add` can no
longer erase the added seed, Z11), `tools/seeds.py add RUN` (every campaign's base seed, before any index runs:
**a non-test `production.py plan` registers its own seed** in the log of its first `--forbid-seeds-from`, which must be
a `tools/seeds.py` log, under that log's lock, re-checked there, before the campaign is published, and records the log
as the manifest's `seed_log` (Z15, Stage-6 fix round 3: a direct plan can no longer skip the registration; a seed
registered meanwhile refuses the plan); `tools/sweep.py` registers its sweep's seed itself right after the plan, Y13
(`--seeds-log`, default `$C8_SEEDS`, required inside a Slurm job); `slurm/plan.sh` adds the planned campaign's seed to
`$C8_SEEDS` too ("present" when the plan registered it there); a test-only plan registers nothing, so after a direct
test-only plan run `tools/seeds.py add RUN` before submitting), `tools/seeds.py add --seed S --label
TEXT` (the L=2 control), `tools/seeds.py check S`, `tools/seeds.py merge FROM... [--log FILE]`. Every non-test plan
refuses without `--forbid-seeds-from $C8_SEEDS`, and every seed whose base or derived group seeds collide with a listed,
archived or bundle-forbidden seed. Fresh seeds: `python3 -c 'import secrets;print(secrets.randbits(63))'`.

**Two sites, two logs, one mirror (the two-log rule, Stage 5).** The package runs on symmetry (the plan's site) and on
Expanse (site deviation U1), and each site's `$C8_SEEDS` is a file on that site:

| Site | `$C8_SEEDS` | Set by |
|---|---|---|
| symmetry | `<SCRATCH>/c8-d2/forbidden_seeds.json` | `~/c8d2/env.sh` (the symmetry block of `slurm/env.sh.example`) |
| Expanse | `$C8_DATA/forbidden_seeds.json` (`<SCRATCH>/temp_project/c8d2/`) | `~/c8d2/env_expanse.sh` (`slurm/env_expanse.sh`) |

- **Every new seed goes into both logs and into the mirror** `designs/forbidden_seeds.json`, whichever site ran the
  campaign: `tools/seeds.py add` on the running site, then `tools/seeds.py merge <the other site's log>` on each site
  (copy the other log over first) and `tools/seeds.py merge` of both into the mirror before the evidence commit. A
  plan on one site therefore refuses the seeds used on the other.
- **`benchmarks/symmetry_2026-10-c8/stage5/scripts/seedsync.sh`** (X21, Stage-6 fix round 1) does the three-way sync:
  each round snapshots both site logs and compares them with the mirror; if they differ it builds the union of all
  three locally with `seeds.py merge` and merges it into symmetry's log, Expanse's log and the mirror (each under its
  own lock). It exits 0 only when one snapshot shows all three equal, and after `C8_SEEDSYNC_ROUNDS` rounds (default 5)
  exits 1 listing what each log lacks; seeds added on a site during the sync are picked up by the next round, and
  mirror-only seeds now propagate outward. `C8_SEEDSYNC_PYTHON` selects the local Python. `production.py` still reads
  only the log given with `--forbid-seeds-from`.
- **`merge` makes a log the union** of itself and the given logs, under the log's lock: every (seed, source) pair it
  lacks is appended with its own fields plus `merged_from` and `merged_utc`; nothing is removed or reordered, and the
  result is checked to hold every seed of every input. It also reads the first symmetry log's layout (2026-10-03: an
  empty `"entries"` list instead of `"seeds"`) and rewrites it in the `c8-d2-seeds-1` layout.
- **The J-FLAG F2 campaign registers itself.** `tests/numerics_flags.py` adds its F2 base seed (default 820262401) and
  the derived native and net seeds of all 24 groups to `--seeds-log` (default `$C8_SEEDS`) before F2 starts, under
  fixed labels; a run with F2 and no log, or whose seeds are already logged under another source, is refused before any
  output exists. Re-running the gates on the same base seed (the paired design) adds nothing. Since fix round 4 (W20)
  the check and the appends are one transaction under the log's lock (`tools/seeds.py` `reserve`: the log re-read,
  every collision checked, every missing entry appended before the lock is released), so a production plan that
  registers the same base seed between F2's check and its appends is refused instead of logged beside it.

## The cost-model sweep (J-SWEEP-1/2)

```bash
# Expanse, one whole compute node, 8 x 16 NUMA-pinned process slots (--threads 16; --threads 8 gives 16 x 8, the P4 shape)
source ~/c8d2/env_expanse.sh                     # first, in the submitting shell: it sets C8_DATA and C8_SEEDS (W17)
export C8_ENV_SETUP=~/c8d2/env_expanse.sh C8_PACKAGE=<export>
: "${C8_DATA:?source the site environment}" "${C8_SEEDS:?source the site environment}" "${C8_PACKAGE:?the export}"
sbatch -A <ACCOUNT> -p compute --ntasks=1 --cpus-per-task=128 --mem=240G -t 02:00:00 -J c8d2-sweep1 \
  -o "$C8_DATA/logs/%x_%j.out" --export=ALL "$C8_PACKAGE/slurm/sweep.sh" "$C8_DATA/sweep1" \
  --seed <fresh> --points 512 --replicates 2 --threads 16 --bootstrap-chunk 512 --shards 8 --cost-model-out "$C8_DATA/sweep1.cost_model.json"
python3 -B "$C8_PACKAGE/tools/accounting.py" "$C8_DATA/sweep1" --output "$C8_DATA/sweep1.accounting.json"   # after the job ended
```

The submitting shell expands `$C8_DATA` (the log path, the campaign and the model) before `sbatch` runs, so the site
environment is sourced first and the guard stops an unset variable (Stage-6 fix round 4, W17): before, a fresh shell
gave `/logs/%x_%j.out`, `/sweep1` and `/sweep1.cost_model.json`, and `slurm/sweep.sh`, which sources `$C8_ENV_SETUP`
only inside the job, could not repair them.

The first sweep has no cost model and no campaign-keyed calibration: it plans in bootstrap mode (fixed 512-point tasks,
the 120 s bound checked against the labelled preliminary proxy, no time estimate; R13). Its merged campaign gives the
first measured cost model (every `campaign:sector:L:graph` key) and the calibration rows; J-SWEEP-2 repeats it with that
cost model on the final binary. symmetry: `-p amdq --exclude=cn112 --exclusive --mem=245G` and `--threads 8`. A sweep
stopped anywhere resumes in the same directory with the same command: committed blocks and merged groups are kept, an
existing cost model that is this campaign's (equal to the one recomputed from its merged tables, apart from its time
stamp and note) is kept and the calibration completed; a model of another campaign at `--cost-model-out` is refused by
name. A resume must ask for the campaign it finds (Y12, Stage-6 fix round 2): the seed, backend, numerics, threads,
points, replicates, rates identity (the default rates or a map's sha256), cost basis (the cost model's sha256, the
chunk), shards and checkpoint size are compared with the frozen campaign's, and any difference is refused by name with
the tree unchanged, so a default-rate sweep directory never answers for a map, or one map's for another.
**The sweep registers its own seed (Y13).** Right after the plan is published or validated, before the ledger and any
index, `tools/sweep.py` adds the campaign's base seed to `--seeds-log` (default `$C8_SEEDS`; idempotent, "present" on a
rerun), so a sweep stopped or failing later still forbids its seed. Inside a Slurm job a missing or nonexistent log
refuses the sweep before anything is planned; a local run without a log says that the seed is NOT registered.
`slurm/sweep.sh` passes `--seeds-log "$C8_SEEDS"` and adds the seed again at the end ("present"). Since fix round 4 the
registration is one locked transaction that re-reads the log and refuses a seed logged by another campaign
(`seeds.reserve` with `production.seed_refusal`, W20's class), and a new sweep checks its seed before planning, so a
logged seed never reaches a plan. **A sweep under `--rates` or `--numerics` writes its own calibration file (W11).**
A calibration file holds the rows of one measurement identity (numerics, rates identity; its `identity` key), and
`tools/calibration.json`, which every calibrated-proxy plan reads, only exact default-rate rows: `sweep.py` refuses a
sweep under a rate map or a profile before planning unless `--calibration FILE` names another file (`--plan-only`
writes no row), `calibrate.py --update` refuses a mixed or mismatched destination, and `production.calibration_row`
uses a row only under the numerics and rates identity of the plan, so a default-rate exact plan is never sized by
another map's or profile's speed. `calibrate.py` reads timings only from checkpoints that
`production.validate_checkpoint` accepts against their authenticated task blocks (W10: identity, runtime, payload
digest, rows; a gated campaign's libgmp, W8), and refuses a non-finite, negative or non-numeric timing (exit 2,
nothing written).

## Plan jobs

Plans above 10^6 tasks run inside a job (never on a login node; `production.py` refuses them without `SLURM_JOB_ID`):
`slurm/plan.sh RUN <plan arguments>` publishes the campaign atomically (a non-test plan registers its seed in its
first `--forbid-seeds-from` log before publishing, Z15), adds its base seed to `$C8_SEEDS` (Y13, Stage-6 fix round 2;
"present" after a non-test plan registered it; without `C8_SEEDS` it asks for `tools/seeds.py add RUN`) and registers
the job (role plan); a failed seed add still registers the job, then exits with the add's status and names the
command to repeat. Wait for the plan job to succeed (`sacct -j <id>`, its log) before submitting any worker. A
non-test plan runs only an executable whose build record (`bin/<exe>.build.json`, written by make) describes it
(Z3, Stage-6 fix round 3): never copy a worker without its record. symmetry: `sbatch -p sharedq -c 8 --mem=15G -t 01:00:00
--no-requeue`; Expanse: `sbatch -A <ACCOUNT> -p shared -c 8 --mem=15G -t 01:00:00 --no-requeue`.

## Pilot runbook (A-PIL-2; J-PIL-1 on symmetry, J-PIL-1E on Expanse)

The pilot is a non-test `--pilot` campaign of every graph of both campaigns (4,096 points × 8 replicates per graph) on
the **exact default path** (the user's decision of 2026-10-05: the pilot stays exact; `docs/NUMERICS.md`; since Stage 6
`production.py plan` refuses a non-test pilot under a profile or a rate map unless the user's go is a key of
`production.APPROVED_PROFILE_PILOTS`, which is empty). It measures
the per-graph variances and costs the design needs (`docs/DESIGN.md`, "After the pilot"); its own result is a
diagnostic, never combined with production, and its seed is forbidden there. **One pilot runs, on one site**, chosen
by the user; Stage 5 planned it on both and submitted nothing. It runs only with the user's authorization, after the
Stage-6 inspection, inside a window agreed with C63d.

**Historical reference only (X22).** The table records the two Stage-5 plans of 2026-10-05. Both are superseded:
their exports pin tools that changed since, so they are re-planned after Stage 6 (step 1 below), and no command of
this runbook names their exports or campaigns.

| Stage-5 plans (superseded; reference only) | symmetry (J-PIL-1, the plan's site) | Expanse (J-PIL-1E) |
|---|---|---|
| Campaign (planned 2026-10-05) | `<SCRATCH>/c8-d2/pilot1-20261005` | `$C8_DATA/pilot1e-20261005-07ff5c1975e5` |
| Export (pins the tools and the executable) | `<SCRATCH>/c8d2/pkg/5d7586e9f1ab` (gmp `2cc5e88e…`, GCC 11.4) | `$C8_DATA/pkg/07ff5c1975e5` (gmp `1d2a2181…`, GCC 13.3) |
| Cost model | `cost_models/gmp_symmetry_amd_c8.json` (`a1b6e5d2…`, J-SWEEP-2) | `cost_models/gmp_expanse_amd_c8.json` (`0e1ccfc9…`, J-SWEEP-2E) |
| Seed (in both logs and the mirror) | 5945432546144395546 | 4531889874192435105 |
| Plan job | 570080 (sharedq, `slurm/plan.sh`, role plan) | 54676927 (shared, `slurm/plan.sh`, role plan) |
| Estimate | 179.9 core-h, 39 indices (19 at L8), largest index 4,796 s on an 8-core lane | 170.3 core-h, 36 indices (16 at L8), largest index 5,329 s on an 8-core lane |
| Lanes | 8 × 8 per amdq node (EPYC 7543) | 16 × 8 per compute node (2 × EPYC 7742), `--exclude=<NODE>` (a node 14% slow on L7/L8) |
| Wall and allocation (heaviest index first on the lane that frees first; the merge is extra) | 1 node: 3.59 h, 230 core-h; 2: 2.26 h, 289; **3: 1.33 h, 256**; 4: 1.33 h, 341 | **1 node: 1.56 h, 199 SU** (about 205 with the merge); 2: 1.48 h, 379; 4: 1.48 h, 758 |

The schedules come from each plan's own index estimates (`benchmarks/symmetry_2026-10-c8/stage5/pilot/pilot_lanes.json`,
`benchmarks/expanse_2026-10-c8/stage5/exp/s5e_summary.json`). Both estimates are below the plan's central projection
of about 220 core-hours and below its 300 core-hour threshold, so `--replicates 8` stays (above 300 the runbook gives
`--replicates 6`). Both use measured cost models of the final default binary.

**1. Before the window.**
- The user's authorization of the pilot and of its site (keep the reference for the run's README).
- Stage 6 APPROVED, or its residual findings accepted by the user.
- **Re-plan if any pinned tool or the executable changed.** A plan pins `production.py`, `common.py`,
  `prepare_inputs.py`, `assemble.py`, `lanes.py`, `slurm_submit.py`, `stage_runtime.py` and the executable, and runs
  only with them: `submit.sh` from an export whose files differ refuses it (exit 64), and its own old export would run
  the old tools. Since the two pilots were planned (from 5d7586e), the pinned tools changed five times: the G5 fixes
  (F5, F7, F8, F9; commit 86e15f4, merged into `c8` as e7e6589) changed `production.py`, `common.py`, `assemble.py`
  and `lanes.py`; the F12 fix (d5dfd38) changed `production.py` and `stage_runtime.py`; route (b) (23540b2) changed
  `production.py` (the F11 fix in the same commit changed only `design.py`, which no plan pins); the Stage-6 fix of the
  allow-list scope changed `production.py` (F13's fix in the same commit changed only `design.py`); the Stage-6 policy
  fix (the pilot stays exact; a gated build for every non-exact non-test plan, `--numerics-gate`) changed
  `production.py` again, and Stage-6 fix round 1 changed `production.py`, `common.py`, `assemble.py`, `lanes.py`,
  `slurm_submit.py` and `prepare_inputs.py` (X4, X8-X13). So **both planned
  campaigns must be re-planned with fresh seeds after the Stage-6 approval** (not before: Stage 6 may change code
  again). A campaign planned with the tools of e88bf4f or earlier cannot claim with the new tools (exit 64); merging or
  assembling one needs `--accept-tool-change` (recorded), and combining its batches `--bundle DIR` (it has no pinned
  copy of its bundle, X9).
  Export the approved commit (`git archive` into `pkg/<sha12>`, `make inputs-l8` or hard links to an earlier export's
  L8 packs after re-hashing them against `inputs/manifest.json`, then the build; on Expanse at most one new export per
  workflow, the Lustre file quota being shared with C63d), draw a fresh seed (`python3 -c "import
  secrets;print(secrets.randbits(63))"`), check it against both logs (`tools/seeds.py check SEED`, on each site), and
  plan in a plan job:

  ```bash
  # symmetry: the site environment first, in the submitting shell (W17: it sets C8_SEEDS, which this command expands)
  source ~/c8d2/env.sh
  # name the NEW export and the NEW campaign once; every later command uses these two variables
  export C8_PACKAGE=<SCRATCH>/c8d2/pkg/<sha12 of the approved post-Stage-6 commit>
  export C8_RUN=<SCRATCH>/c8-d2/pilot1-<date>-<sha12>          # a directory that does not exist yet
  : "${C8_SEEDS:?source the site environment}" "${C8_PACKAGE:?}" "${C8_RUN:?}"
  # a sharedq plan job (never on the login node)
  sbatch -p sharedq -c 8 --mem=15G -t 01:00:00 --no-requeue -J c8d2-plan-pilot -o <SCRATCH>/c8d2/logs/%x_%j.out \
    --export=ALL,C8_ENV_SETUP="$HOME/c8d2/env.sh",C8_PACKAGE="$C8_PACKAGE" "$C8_PACKAGE/slurm/plan.sh" "$C8_RUN" \
    --pilot --points 4096 --replicates 8 --threads 8 --checkpoint-tasks 256 --index-hours 1.5 --backend gmp \
    --cost-model "$C8_PACKAGE/cost_models/gmp_symmetry_amd_c8.json" --forbid-seeds-from "$C8_SEEDS" --seed <fresh>
  # Expanse: the same with -A <ACCOUNT> -p shared, C8_ENV_SETUP=$HOME/c8d2/env_expanse.sh, C8_PACKAGE=$C8_DATA/pkg/<sha12>,
  #   C8_RUN=$C8_DATA/pilot1e-<date>-<sha12>, gmp_expanse_amd_c8.json, and a second --forbid-seeds-from with a
  #   read-only copy of symmetry's log (as 54676927 did)
  ```

  The exact cost model must record `numerics: exact` (both committed exact models do): since fix round 1 a non-test
  plan refuses a cost model whose numerics differ from the plan's or that records none (X10).

  The plan itself registers the seed in the planning site's log (its first `--forbid-seeds-from`, Z15; `plan.sh`'s
  own `seeds.py add` then says "present"). Then the seed goes into the other site's log and the mirror
  (`tools/seeds.py add --seed S --label <campaign path>` or `seeds.py merge` on the other, `seeds.py merge` into
  `designs/forbidden_seeds.json`; "The seed log" above). No `--numerics`, `--rates` or `GMP_PREFIX` build: the pilot
  stays exact; production under `dd+mp256` is frozen from it by route (b) (`docs/DESIGN.md`, "Route (b)").
- **The window with C63d** (`LRI_C8_shared/inventory/DECISIONS.md`: H11 on Expanse, H7 on symmetry). Whoever is ready
  first announces it with a NOTE in `LRI_C8_shared/inventory/`, and one DECISIONS line records the window:
  - **Expanse (H11).** The DECISIONS line re-splits the user's 22 running / 54 submitted normal-QOS jobs for the window:
    the pilot session 16 running / 40 submitted, the other session 6 / 14; the <ACCOUNT> account stays at or below 32
    running. Then, **first, a 5-minute one-node start-latency probe** (after the H7E-R survey):

    ```bash
    source ~/c8d2/env_expanse.sh; : "${C8_DATA:?source the site environment}"   # W17: C8_DATA is expanded here
    sbatch -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:05:00 \
      --exclude=<NODE> -J c8d2-pilot-probe -o "$C8_DATA/logs/%x_%j.out" --wrap 'hostname; date'
    ```

    Record its queue wait (`sacct -j <id> -o Submit,Start`). `C8_EXP_RUNNING`, `C8_EXP_SUBMITTED` (and the other
    `C8_EXP_*` overrides) are accepted only with `C8_ADMISSION_REF="<that DECISIONS line>"`, which every ledger line
    records; `C8_EXP_ACCOUNT_RUNNING` (32), `C8_EXP_SHARED` (32) and `C8_EXP_NODES` (4) keep their H7E-R values.
  - **symmetry (H7; the H11 symmetry window of 2026-10-05: the pilot session at most 5 live AMD-pool jobs, the other
    session 3).** The DECISIONS line gives the number of AMD nodes for the window; `C8_AMDQ_CAP` is set to it for
    the submission (k = the workers + 1 merge, counted with every live `c8d2-` job on amdq, amddebugq and amdpreq).
    Since fix round 1 the value given on the command line survives `env.sh`, which supplies 4 only as a default (X11).
    Outside a window the development cap of 4 holds. Never longq. **Then, first, a 5-minute one-node start-latency
    probe** (the agreed prerequisite, `LRI_C8_shared/inventory/DECISIONS.md`, "H11 pilot window on symmetry"; Z17,
    Stage-6 fix round 3), after the survey and inside the cap: it is an AMD-pool `c8d2-` job, so it counts against
    `C8_AMDQ_CAP` while it is live; submit the workers only after it has ended, or count it in k:

    ```bash
    sbatch -p amdq --exclude=cn112 -N 1 --ntasks=1 --cpus-per-task=64 --exclusive --mem=245G -t 00:05:00 \
      -J c8d2-pilot-probe -o <SCRATCH>/c8d2/logs/%x_%j.out --wrap 'hostname; date'
    ```

    Record its queue wait (`sacct -j <id> -X -o JobID,Submit,Start,End,State,NodeList`) in the run's README, with the
    survey; a long wait means the window's wall estimate does not hold yet.
  - Survey first (`sinfo -p <partition>`, `squeue -u $USER`, on Expanse also `squeue -A <ACCOUNT>`) and say whether the
    job starts now or queues.

**2. Submit** (the campaign's own export; AMD nodes only: the native rows depend on the CPU vendor, finding F5; the
first claim pins the vendor in `$C8_RUN/cpu_vendor.json`, and a claim from another vendor exits 64):

```bash
# C8_PACKAGE and C8_RUN are the approved export and the campaign freshly planned from it in step 1 (never a Stage-5
# export or campaign: the table above is reference only). The guard stops here if either is unset.
: "${C8_PACKAGE:?the export of the approved post-Stage-6 commit}" "${C8_RUN:?the campaign planned from it in step 1}"

# Expanse login node, inside the H11 window, after the probe
source ~/c8d2/env_expanse.sh
export C8_ENV_SETUP=$HOME/c8d2/env_expanse.sh C8_SITE=expanse
python3 -B $C8_PACKAGE/tools/production.py status $C8_RUN --fast     # no WARNING about changed pinned tools: its own export
C8_SBATCH_ARGS="-A <ACCOUNT> -p compute --exclude=<NODE>" C8_LANE_MEM=240G C8_LANE_TIME=04:00:00 C8_MERGE_TIME=01:00:00 \
C8_EXP_RUNNING=16 C8_EXP_SUBMITTED=40 C8_ADMISSION_REF="<the H11 window line>" $C8_PACKAGE/slurm/submit.sh --lanes 1

# symmetry login node, inside the agreed amdq window: 3 workers + 1 merge (k = 4)
source ~/c8d2/env.sh
export C8_ENV_SETUP=$HOME/c8d2/env.sh
python3 -B $C8_PACKAGE/tools/production.py status $C8_RUN --fast     # no WARNING about changed pinned tools: its own export
C8_AMDQ_CAP=<the agreed window, at least 4> C8_SBATCH_ARGS="-p amdq --exclude=cn112" C8_LANE_MEM=245G C8_LANE_TIME=24:00:00 \
  $C8_PACKAGE/slurm/submit.sh --lanes 3
```

The node counts below are the Stage-5 plans' schedules; recompute them from the new plan's own index estimates.
- **Expanse:** one node is the choice: the 16 L8 indices fill its 16 lanes, and more nodes cannot shorten the 1.48-h
  indices (a shorter wall needs a re-plan with a smaller `--index-hours`). k = 2 (the worker and its merge).
- **symmetry:** `--lanes 3` gives the 4-node wall (1.33 h) at 256 instead of 341 core-hours, and k = 4 fits even the
  development cap; A-PIL-1 recorded the plan's `--lanes 4` (k = 5).
- `C8_LANE_TIME`: a lane claims an index only if est × f / (8 × 0.9) × 1.5 + 300 s fits the time left, so the 1.48-h
  indices need about 2.3 h at claim time; Expanse's 4 h also covers a slow node.
- Report the log paths: workers `$C8_RUN/slurm_logs/lane-<jobid>.log`, merge `$C8_RUN/slurm_logs/merge-<jobid>.log`;
  the `C8: admission` line of the `submit.sh` output records the snapshot and the decision.

**3. During the run.** About 10 minutes after each worker starts, read its log (the lane shape line, the first claims,
no failure record), then `python3 -B $C8_PACKAGE/tools/production.py status $C8_RUN --fast`. A failed or killed worker:
`submit.sh --lanes N` again (stale claims are released and the pending merge replaced; never a duplicate of live work).
Never submit an array while lanes are live (exit 65). A scancelled worker forwards SIGTERM to its lanes and runs,
which remove their lane scratch and `c8d2_runtime_*` directories (F7, "Lane mode" above; on real Slurm 30 s after a
`scancel` nothing of the worker's 465 MB was left, J-DRL-1 of 2026-10-05); check the node-local scratch path the worker
log names, and record and remove anything left.

**4. After the run.** The afterany merge runs `production.py merge` and `assemble.py`. Then:
- `production.py status $C8_RUN` exits 0 and the 24 groups have `merged.json`;
- `python3 -B $C8_PACKAGE/tools/verify_result.py $C8_RUN/C8_result.json` (since the F6 fix its rounding-level gates
  are bounded by 64 eps M_k, so it verifies on any BLAS kernel family, the login node included; `docs/NUMERICS.md`);
- `python3 -B $C8_PACKAGE/tools/accounting.py $C8_RUN --output <evidence>/accounting.json`: complete accounting, the
  pilot's η_node and its allocated core-hours (they enter `--spent-core-hours`); it is complete only once every ledger
  job's current sacct attempt is terminal (X15), so run it after the merge job has ended;
- `sacct -X --duplicates` of every ledger job into the evidence, the core-hours against the authorization, the window
  closed with a DECISIONS line, and the two-log seed sync checked;
- then the design and decision step (`docs/DESIGN.md`, "After the pilot").

## Storage

symmetry: campaigns under `<SCRATCH>`; Expanse: under `$C8_DATA` on Lustre (`plan` refuses a projected file
count above 10^6, half the quota, under `C8_SITE=expanse`). Code in home. `tools/stage_runtime.py RUN DEST --index I`
stages one index's runtime (tools, executable, small inputs and only its pack members) on node-local scratch
(`C8_STAGE=1` in `run_array.sh`); a whole-pack copy (`--whole-pack`) is refused above 1 GB.
