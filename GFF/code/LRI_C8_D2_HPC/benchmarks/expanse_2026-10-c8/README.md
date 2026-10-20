# C8(2) development evidence on SDSC Expanse (site deviation U1)

**Why Expanse.** On 2026-10-03 the user moved development, validation and profiling compute to Expanse, because
symmetry's compute partitions had been down since 13:06 EDT (`LRI_C8_D2_HPC_loop/PLAN-REVIEW-LOG.md`, "User decisions
after plan approval", U1). The package stays symmetry-ready. The final validation (J-VAL) and the smoke are repeated on
symmetry once it is back. This folder mirrors `benchmarks/symmetry_2026-10-c8/`.

**Environment.**
- Account <ACCOUNT>. `~/c8d2/env_expanse.sh` is a byte copy of `slurm/env_expanse.sh`; each job records it in
  `env_expanse.sha256`. Through Stage 3 part A it was sha256 `b3f044da…` (the file as of 00c675d). From Stage 3 part B
  on it is `6f85cb50…` (the file since ef5a2b6, unchanged at HEAD); every Stage-3B, checkpoint and Stage-4a job records
  that value.
- Spack GCC 13.3.0, Boost 1.77 headers by path (`BOOST_LIB_VERSION 1_77`), Spack GMP 6.2.1.
- Python 3.11.9 venv `~/c8d2/venv`: numpy 2.3.5, scipy 1.17.1, mpmath 1.3.0, sympy 1.14.0, pytest 9.1.1.
- Data live under `<SCRATCH>/temp_project/c8d2/` (`$C8_DATA`): `pkg/<sha12>` (exports),
  `logs/`, `evidence/<sha12>/<job dir>`, `gen/<sha12>/`.
- Every Expanse compute node is a 2 × AMD EPYC 7742 (128 cores).

**Sharing rules (agreed with C63d).**
- At most 4 whole `compute` nodes per session at a time; `shared` is outside that cap.
- The two sessions together stay at or below 22 running and 54 submitted normal-QOS jobs of the whole <ACCOUNT> account.
  Before each submission the account showed 0 to 2 normal-QOS jobs.
- From Stage 3 part B on, the agreed split H7E-R applies (`LRI_C8_shared/inventory/DECISIONS.md`, 2026-10-03), and
  `slurm_submit.py` enforces it: this session may have at most 11 running and 27 submitted normal-QOS `c8d2-*` jobs,
  the whole account at most 32 running, at most 32 live shared jobs, and at most 4 compute nodes.
  - The Stage-3b jobs were submitted with `sbatch` directly, after `squeue -A <ACCOUNT>`. The account then had no
    normal-QOS job other than these.
  - This session never had more than 1 compute node and 4 shared jobs at a time.
- Every job is named `c8d2-*`.

**Packed raw evidence.** `stage1/raw_evidence.tgz` holds the bulky raw files: the cross-node build's `MEMBERS.sha256`
and builder inventories, and J-GEN-2's `gates/coverage.json` and `gates/edge_forests_L{7,8}.json`. The same bytes are
also inside the published tree. `stage1/raw_evidence_listing.json` lists their sha256s. Run `tar xzf raw_evidence.tgz`
in `stage1/` to restore them at their paths.

## Export of the commit under test

| Record | What it shows |
|---|---|
| `setup/export_check_36043bbc2117.json` | `git archive 36043bb \| tar -x` into `$C8_DATA/pkg/36043bbc2117`. All 4,706 files equal the archive by sha256, with no file missing or extra. Every mode equals git's recorded mode (100644 → 0644, 100755 → 0755), and no symlink or special file is present. |

A first export, `00c675d3cfe9`, is superseded. Expanse's bank_limit plugin refused its `compute` scripts, which named
no task count. The fix `--ntasks=1 --cpus-per-task=128` is commit `36043bb`, and every Stage-1 job below ran from that
export.

## Stage 1: the inventory (J-GEN-1, J-GEN-2, A-INV-4) and H1

| Job | Where | What it shows | Files |
|---|---|---|---|
| 54631541 | `shared`, <NODE> | J-GEN-1 on the superseded export `00c675d`. It was cancelled 12 s after it had started (between the queue check and the `scancel` it went from PENDING to RUNNING) and only compiled the generator; 0.03 core-h. | `$C8_DATA/evidence/00c675d3cfe9/gen1.54631541.0` (on Expanse, not copied) |
| 54631551 | `shared` 8 CPUs, <NODE>, 3:05 | **J-GEN-1, A-INV-1/2 passed.** `test_keys` 34/34, including the `-Wall -Wextra` check of `gen/c8gen.hpp` under GCC 13.3. `test_run_l8` 5/5: an injected failing gate stops publication. `test_verify_inventory` 25/25 and `test_handoff_inventory` 6/6. `check_sources` passed. **A-INV-2:** free L7 2,441/2,441 and power L3–L7 840/840 G-files byte-identical to the frozen C7(2) files; every builder `inventory.json` equal field by field; outputs at 1 and 8 threads identical; the subgraph side files equal C8(1)'s `L7_inventory.txt`. The free L3–L6 files differ in their rate lines only (492 files): the frozen files keep the relabelled legacy tables by design, and every entry differs. | `stage1/gen1.54631551.0/`, `stage1/logs/c8d2-gen1-regress_54631551.out` |
| 54631552 | `compute` <NODE>, 128 threads, 3:40 | **J-GEN-2, A-INV-3 passed, every gate at the plan's numbers.** (a) Σw_A = 49985915/768, Σw_B = 33994099/6912. (b) The metadata of all 26,540 classes equal `L8_inventory.txt`; 5,068 keys above 2^64. (c) The zeros 2,511/2,340 equal the articulation sets. (d) 248 primitives. (e) 16,798/4,891 finite kernels, 734/555 with s_G = 4, selections 16,064/4,336. (f) Coverage 2,254/3,886/248/15,816/4,336. (g) Edge forests on 7,231 power classes, 0 failures. (h) Kirchhoff exact on 144 kernels. (i) M ≤ 4,032, T ≤ 280. (j) Rates are half-integers in [0.5, 4] obeying the parity floor. (k) Forests 11,254,373 (L8) and 873,108 (L7), equal per class. The L7+L8 build took 35 s and the gates 32 s. The tree was published into staging with MANIFEST sha256 `46341a3c…`. | `stage1/gen2.54631552.0/` (`gates/`, `MANIFEST.sha256`, `verify_inventory.json`), `stage1/logs/c8d2-gen2-build_54631552.out` |
| 54631553 | `compute` <NODE>, 64 threads, 1:13 | **A-INV-4 on Expanse passed.** A second node at another thread count (<NODE> at 64 threads, against <NODE> at 128) gives a byte-identical `MEMBERS.sha256` (24,839 members, sha256 `e1a77e0d…`) and byte-identical builder inventories. The job refuses to pass on the reference's own host. Same CPU model, so this is a node and thread-count check. The plan's architecture check (J-GEN-3: symmetry Intel debugq, 40 threads) waits for symmetry. | `stage1/gen3.54631553.0/crossnode.json`, `stage1/logs/c8d2-gen3-crossnode_54631553.out` |
| 54631581 | `shared` 2 CPUs, <NODE>, 3:45 | **H1 copy on Expanse.** The staging tree verifies against the pin. `publish_inventory.py copy` publishes `<SCRATCH>/temp_project/LRI_C8_shared/inventory/inventory8_d2`, which verifies against the pin, and a second publication is refused. | `stage1/h1/expanse_copy.54631581/`, `stage1/logs/c8d2-h1-copy_54631581.out` |

**H1 on the Mac.**
- The tree was rsynced to `LRI_C8_shared/inventory/.inventory8_d2.rsync`.
- `publish_inventory.py copy --move` verified it, renamed it to `LRI_C8_shared/inventory/inventory8_d2` and verified
  it again (`stage1/h1/verify_mac.json`).
- A second publication was refused (`stage1/h1/second_publish_mac.txt`).
- `gen/handoff_inventory.py` then wrote `LRI_C8_shared/inventory/HANDOFF_inventory8_d2.json` (sha256 `ad2e716c…`;
  byte copy in `stage1/h1/`). It pins MANIFEST.json (sha256 `46341a3c0f11d74f0cf7c08cdd685d9cf073a142160de5a0ca408e021b4ff099`,
  md5 `a79eb5bf8090272cedefb83340d7bd82`) and records three verified copies, every A-INV record, C63d's C1
  acknowledgment and four notes (site, the pending architecture check, copies, rate-line bytes).
- C63d was notified in `LRI_C8_shared/inventory/NOTE_C62d_to_C63d_H1.md` (copy in `stage1/h1/`).

## On HANDOFF: the assembly HANDOFF f5ff6a35, vendored (Mac)

| Record | What it shows |
|---|---|
| `on_handoff/vendored_isolated_mac.json` | A-ASM-1(a) isolated export: 11/11 on `git archive 342577c`. 342577c is the vendoring commit `1769abc` plus two fixes of the audit harness; no vendored file changed. The export lies outside <PROJECT>. The vendored tests give 30 passed with `LRI_ROOT=<export>/vendor/c8_assembly_fixtures`, 21 passed and 9 skipped without `LRI_ROOT`, and 30 passed with `LRI_ROOT=<PROJECT>`, all equal to the HANDOFF. `exact_check.py` completes in both modes. No file is opened outside the export, the temporary directory and the Python installation (1,189 audited opens in the fixture run), and the export is unchanged. |
| `on_handoff/check_vendored_standalone_mac.json` | A-ASM-1(a): `check_vendored.py --standalone` 12/12 in the checkout: the HANDOFF and its review, the complete deliverable set, the fixture pins, no symlink, the review record, the interface signatures and the vendor/ rule for `prepare_inputs`. |
| `on_handoff/check_vendored_standalone_export.json` | The same in a `git archive` export (11/11, `--no-review-record`, as on a cluster). |

Python on the Mac was anaconda 3.10.11 (numpy 1.23.5, pytest 7.1.2). A-ASM-1(b), the input-manifest pins, is deferred
to G2a (an early HANDOFF, R15).

## Stage 2a: the inputs (J-IN-1, J-IN-2) [G2a]

The job scripts are in `stage2/scripts/`. Each export below was checked against `git archive`: `setup/export_check_*.json`.

| Job | Where | What it shows | Files |
|---|---|---|---|
| 54632984 | `shared` 2 CPUs, <NODE>, 0:02 | **J-IN-1** on export `ec2b058`, `make_lowloop --verify` 16/16 (Python 3.11.9, mpmath 1.3.0). The three low-loop files regenerate byte for byte. **Order 7:** C7(2)'s `gamma_d2_7.txt` and `two_loop.json` are reproduced byte for byte. **A-IN-1:** 7 rows × 9 tokens; rows L=2..7 repeat the order-7 tokens; the L8 norm equals −2/π^8 to 60 digits and ℓ_1 = 8 log 2. **A-IN-2:** 7 strings, the first 6 C7(2)'s; the contours agree to 3.08e-66 and the reference contour to 7.71e-68. **A-IN-6(a):** the Cauchy check agrees to 1.09e-51. **Cross-check:** `gamma_d2_8.txt` is byte-identical to C63d's `inputs_d2_check` copy, and the B2 strings are equal. | `stage2/in1.54632984.0/`, `stage2/logs/` |
| 54632985 | `shared` 16 CPUs, <NODE>, 1:50 | **J-IN-2a.** `make inspect` (GCC 13.3, `BOOST_LIB_VERSION 1_77`, 80-bit long double). `prepare_inputs --regenerate` from the Expanse copy of `inventory8_d2`, with the inspector over all 24,173 kernels (100 s). The L3–L6 packs are at C7(2)'s sha256s; the L7 packs hold 2,441 and 709 members, the L8 packs 16,064 and 4,336. The manifest and inventory are committed as `cf0864e`; this job's copy of `inventory.json` is byte-identical, so only its sha256 is kept. | `stage2/in2a.54632985.0/` |
| 54633090 | `shared` 16 CPUs, <NODE>, 4:22 | **J-IN-2b** on export `7aac898`. `make inputs-l8` (69 s) builds both L8 packs at the committed pins. **A-IN-3/4/5:** `tests/check_inputs.py` 26/26. Every generated file regenerates byte for byte: the twelve packs (both L8 packs present), `inventory.json` with the inspector fields, `manifest.json` and `inputs_mini`. A one-byte pack change fails `verify()`. The one skip is the git-only C7(2) L7-member check, done on the Mac. **A-ASM-1(a)+(b)** on the cluster export: `tests/check_vendored.py` 14/14. `vendored_isolated --in-place` (informational) failed at pytest collection: pytest 9.1.1 built directory nodes from `/`. Fixed with `--confcutdir` in `cb40188`; see job 54633368. | `stage2/in2b.54633090.0/` |

**On the Mac (G2a).**
- `make_lowloop --verify`: 16/16.
- `tests/check_inputs.py` (`C8_ALLOW_NO_L8=1`, the Mac tree, no inspector): 27/27, 2 skipped (the L8 packs, the inspector
  fields). Every pack regenerates, including both L8 packs rebuilt on arm64 at the Expanse pins. The inventory rows
  and the manifest are equal except the inspector fields and the inventory hash. In a git checkout, C7(2)'s 2,298 and
  590 L7 members are among the new ones with the same bytes.
- After the early HANDOFF, A-ASM-1 was re-run in full on the G2a commit: `check_vendored.py` (a)+(b) 15/15
  (`stage2/mac_g2a_check_vendored_full.json`) and `vendored_isolated.py` 10/10 (`stage2/mac_g2a_vendored_isolated.json`).

## Stage 2b: the assembly on the vendored module [G2b]

**On the Mac at `cb40188`** (`stage2/mac_cb40188/`). Every record passes.
- `check_vendored`: 15/15. `vendored_isolated`: 10/10.
- `assembly_checks --exact`: 37/37.
  - A-ASM-2: the order-7 coefficients are bitwise equal to C7(2)'s `assemble.py` and `analyze.py` on 96 sets and the
    2026 production means, with B2 of 6 or 7 entries; the Jacobians are equal.
  - A-ASM-4: the gates at 17 points; `loops=[4,5]` fails. In Fraction mode the 210 second differences vanish, and
    `coefficients` = `ms8_value` in 16 constant cases that also reproduce C4, C5, `c6:RGassembly` and ms7. `ms8_rows`
    equals the RECON polynomial (34 monomials). The hard gates run in `assemble.py`, and an injected violation raises.
  - A-ASM-5: PP1–PP10, one test each; the lower-order pulls; the FLAG line; `error_by_loop`; the half streams and the
    bootstrap against hand values; the test-only view.
  - `--exact`: 33 exact keys equal, 6 float diagnostics within bounds, 1 provenance key.
- `compat_2026` (A-ASM-3): passed. Max relative difference 7.3e-16; C7 is 6 ulp off under numpy 1.23.5.
- `verify_result_tamper`: 22/22 (A-ASM-7 with the coverage guard). `combine_core`: 11/11. `make_lowloop`: 16/16.
- `check_inputs`: the 27/27 Mac run above.

| Job | Where | What it shows | Files |
|---|---|---|---|
| 54633368 | `shared` 4 CPUs, <NODE>, 2:01 | The same suite on the cluster export `cb40188` (pytest 9.1.1, numpy 2.3.5, sympy 1.14.0, mpmath 1.3.0). `check_vendored` 14/14. `vendored_isolated --in-place` 10/10: the cluster part of A-ASM-1, a G3/G5 item run early; vendored tests 30 passed with the fixtures and 21 + 9 skipped without, no outside reads. `assembly_checks --exact` 37/37: the cluster part of A-ASM-4, same verdict as the Mac. `compat_2026` passed and reproduces the published C7(2) **bit for bit** (0 ulp). `verify_result_tamper` 22/22. `combine_core` 11/11. | `stage2/g2b.54633368.0/`, `stage2/logs/` |

## Stage 3, part A: the native kernel (component C) [A-KER-1..5, A-RPL-1..6, A-IN-6(b)]

The commit under test is `7607a9f` (export `setup/export_check_7607a9fc2777.json`: 4,896 files equal to `git archive`).
The job scripts are in `stage3/scripts/`. The two L8 packs were hard-linked from the `7aac898` export, and `make`
re-hashed every pack against `inputs/manifest.json`. Every node is a 2 × AMD EPYC 7742 with Spack GCC 13.3.0, Boost
1.77 headers (`BOOST_LIB_VERSION 1_77`) and GMP 6.2.1.

**Executables** (sha256 prefixes; `stage3/s3build.54637262.0/binaries.sha256`, build records and `--describe` beside it):

| Executable | sha256 | Notes |
|---|---|---|
| `bin/c8d2_decimal` | `3dbd51bb…` | `--describe`: `c8-d2-build-1`, orders [7,8], lmax 8, kmax 6, numerics `exact`, diagnostic false, tail_top 16 |
| `bin/c8d2_gmp` | `5c5328af…` | the same, `mp_backend` gmp350 |
| `bin/baseline/c8d2_{decimal,gmp}` | `3dbd51bb…`, `5c5328af…` | rebuilt independently in a second directory: byte-identical |
| `bin/ref/c7d2_decimal` | `4537dcfd…` | `make c7ref` with C7(2)'s Makefile on this node type. The 2026 production hashes (`e696d7f3…`, `7e3c8c92…`) are symmetry's GCC 11.4 builds; they are checked when symmetry is back |
| `bin/ref/c7d2_gmp` | `6c829386…` | |
| `bin/c8d2_gmp_prof`, `bin/c8d2_gmp_ratiohist` | `d1cc6551…`, `c307f2a3…` | diagnostic (tier timers, ratio histograms) |
| `bin/c8d2_{decimal,gmp}_san` | `cf3b8d1b…`, `e7a53e51…` | diagnostic (sanitize) |

| Job | Where | What it shows | Files |
|---|---|---|---|
| 54637262 | `shared` 16 CPUs, <NODE>, 1:10 | **Build.** Every target from scratch (`make`, `make gmp inspect`, `make profile ratiohist sanitize`, `make c7ref`). The G-L8SELF baseline is built in a second directory and is byte-identical. | `stage3/s3build.54637262.0/` |
| 54637263 | `compute` <NODE>, 128 cores, 3:27 | **`validate.py --full`, all parts passed (125 s).** **A-KER-3:** `--describe` of both backends. **A-KER-1/2:** 28 refusals, each exit 2 with its message: task L=9 and L=1, order-7 L=8, orders 6 and 9, the C7 header, gamma of the other order (both ways), a trailing gamma token, data after the last row, a short row, dim 32, a graph with E > 16, six bad scalar rates, nine bad `@FILE` maps. The valid runs: L=2 at both orders (K=5, K=6) and L=3 at both orders, L=8 at order 8, rows 2(order+1−L) wide, `max_rss_kb` from VmHWM, and an `@FILE` run equal to the scalar run. **A-RPL-1/2/3 on the L=2 graph and all 3,773 L3–L7 kernels**, 2 × 64 points, seed 7738251; rate .8 layout 0, and rates .8/.9 × layouts 0/1/2 at L7; both backends: **G-C7 exact in all 39,048 rows** (22,212 with mp > 0, 111,112 MP and 1,074,943 binary128 points); **G-REF exact** (7,548 rows, decimal exact, gmp exact also in its 4,121 mp > 0 rows); **G-JET exact** (39,048 rows; the new slot finite). **A-RPL-6 (chunks and layouts):** the 3 heaviest L7 and L8 kernels per sector, layouts 0/1/2, both backends; 23-point chunks agree with whole tasks to 2.1e-18 normalized (bound 1e-12); the merged tail fields equal the whole task's (top 16 and argmax identical, `tail_sum` 2.4e-19 relative). **A-KER-5:** on 100 kernels (25 per sector at L7 and L8), the inspector's addends equal the inventory's and the worker's, and the inventory reproduces the worker's in-block order. **Class B:** without the tail fields (`-DC8_NO_TAIL_FIELDS`) every other field of 192 rows is identical (L7 at orders 7 and 8, L8; both backends). **Diagnostic builds:** rows identical to `bin/c8d2_gmp`, and every evaluation counted once. | `stage3/s3val2.54637263.0/validate_full.json` |
| 54637263 | (same job) | **Point checks L3–L8** (`check_points.py`): 172 checks per backend on 43 kernels. The largest scaled MP error is 2.1e-353 (gmp350) and 1.8e-302 (decimal300), against the bound 1e-280; binary128 sharing is bitwise the unshared path. | `stage3/s3val2.54637263.0/point_checks.json` |
| 54637264 | `compute` <NODE>, 128 cores, 7:49 | **A-IN-6(b), the L=2 control** at order 8 (K=6), with fresh seed `7082694491065029298` (to be registered in the forbidden-seed log once `tools/seeds.py` exists). Rates .8 and .9, 32 replicates × 2^16 points, both backends (identical). Every slot j = 0..6 is within 4 SE of B2: the largest pull is 1.22 (per campaign and combined). wa/wb = 6 exactly; \|b_j − 6c_j\| ≤ 1.10e-19·\|b_j\| per row and ≤ 4.8e-20 per replicate sum (bound 2^−60 = 8.7e-19). | `stage3/s3val3.54637264.0/l2_control.json` |
| 54637264 | (same job) | **A-RPL-6, thread identity.** L8 blocks of 64 tasks × 256 points per sector (8 heaviest and 24 random kernels): identical scientific fields at 1, 8, 16 and 64 threads, and split over 8 lane processes × 8 threads on disjoint CPU sets. Both backends; every run wrote a fresh output. | `stage3/s3val3.54637264.0/thread_identity.json` |
| 54637264 | (same job) | **A-RPL-4, G-BK8.** L7 and L8, 400 kernels per sector (100 heaviest, 300 random), 2 × 256 points, decimal against gmp: identical counters and exact values in every row, the 2,779 rows with mp > 0 included (96,064 MP points); the tail fields are exact too. | `stage3/s3val3.54637264.0/bk8.json` |
| 54637264 | (same job) | **G-L8SELF** (the A-RPL-7 machinery) on the L8 sample of 2,000 kernels (1,600 free, 400 power; the 100 heaviest per sector and random ones), 2 × 512 points: the Stage-3 baseline against the candidate is exact in every scientific field, both backends (214,532 MP points per backend). | `stage3/s3val3.54637264.0/l8self.json` |
| 54637264 | (same job) | **A-RPL-5, precision policy** (`forced_tiers.py`): per sector 200 L7 kernels × 256 points and 400 L8 kernels × 64 points (153,600 points), each evaluated in every tier and against an independent 450-digit value. No doubling was needed: free has 29,284 binary128-accepted and 3,541 MP points, power 50,625 and 12,568 (need 10^4 and 10^3). (a) Long-double accepted: \|f − f450\| ≤ 3.3e-18·err_ld (bound 1e-15). Binary128 accepted: ≤ 1.05e-33·err_q (bound 1e-29). The relative errors after acceptance are ≤ 5.1e-10 and ≤ 1.4e-11. (b) MP: ≤ 1.3e-352 (gmp350), ≤ 3.7e-313 (decimal300 on the MP points); bound 1e-280. (c) Zero decision mismatches. | `stage3/s3val3.54637264.0/forced_tiers.json` |
| 54637265 | `shared` 16 CPUs, <NODE>, 9:09 | **A-KER-4, sanitizers** (J-VAL-4). `bin/c8d2_{decimal,gmp}_san` on the L2 graph and the 2 lightest and 2 heaviest kernels of every (sector, L) at L3–L8: 2 × 64 points, layouts 0/1/2, 4 threads, both orders where valid. 144 runs (984 rows) exit 0 with no report. `point_checks.cpp` with the same flags is clean (176 checks per backend). The self-test aborts in each of its three probes with that probe's own report: `_GLIBCXX_ASSERTIONS` on the `std::array` one-past-the-end write, AddressSanitizer stack-buffer-overflow, and UBSan signed overflow. | `stage3/s3val4.54637265.0/sanitize.json` |

**Development runs** (not records, in a hard-linked development tree): 54636974, 54636981, 54636988, 54636996,
54636997 (cancelled), 54636998 (cancelled), 54637006, 54637007, 54637020 and 54637238. Two things they found are
fixed in `7607a9f`:
- `max_rss_kb` now comes from VmHWM, because `getrusage` also counts the forking Python parent.
- The 450-digit reference of `forced_tiers.cpp` uses direct monomial products (6–8× faster). The results were
  identical.

## Stage 3, part B: orchestration, design and statistics (components D, E, F) [G3]

The commit under test is the tag `c8-stage3` = `b4273c5` (export `setup/export_check_b4273c59e911.json`: 4,968 files
equal to `git archive`). Earlier exports of this part: `ef5a2b6` (no job ran; removed), `81aa977` and `1d25d9e` (the
first two rounds below). The tag moved twice, each time after a cluster run found a defect
(`CHANGELOG.md`, "Fixes after the first/second Expanse runs"). The job scripts are in `stage3b/scripts/` and the Slurm
logs in `stage3b/logs/`. `designs/forbidden_seeds.json` mirrors `$C8_DATA/forbidden_seeds.json`, the Expanse seed log.
The symmetry log does not exist yet; the two are merged when symmetry is back.

**Final round on the tag export `b4273c5`** (all three on <NODE>):

| Job | Where | What it shows | Files |
|---|---|---|---|
| 54643359 | `shared` 16 CPUs, 1:00 | **Build.** `bin/c8d2_decimal` and `bin/c8d2_gmp` are byte-identical to part A's (`3dbd51bb…`, `5c5328af…`). The sanitizer builds differ from part A's only in debug-info paths. The seed log is unchanged: the L=2 control seed is already present. | `stage3b/s3bbuild.54643359.0/` |
| 54643360 | `shared` 16 CPUs, 9:55 | **J-VAL-1, all passed.** The commands of `make test`, one by one, with temporary copies on the node-local NVMe. `validate` passed (describe, refusals, replay subset, invariance, inspector, class B, diagnostics). **`unit_orchestration` 38/38 on Linux** (Python 3.11.9). This includes A-ORC-13 with the real `bin/c8d2_gmp` on the Linux fingerprint path: the platform class is exactly `/proc/cpuinfo`, the staged executable's ELF header, the interpreter `ld-2.28.so`, ten libraries (`libgomp`, `libquadmath` and `libgmp` among them) and the `ldd` pipe. Its 29,930,938 bytes equal `fingerprint_bytes`. The launches are `ldd` and the worker. The R18 regeneration ran in a copy of this export. `test_pipeline` 8/8. `ast_scan`: 0 findings. `merge_scale` (2 × 10^4) passed. `check_vendored --no-review-record` 16/16, with the vendor/ rule for `plan` and `run --index`. `vendored_isolated --in-place` 10/10. The delivery-verifier test passed, and `check_inputs` 10/10. The real-worker `workflow` and `staging` passed for both backends. | `stage3b/s3bval1.54643360.0/` (records/, one log per command) |
| 54643361 | `shared` 16 CPUs, 2:01 | **A-ORC-6, the merge-scale part of J-VAL-3.** A group of 1,249,792 rows in 16 shards. `merge --jobs 16` is byte-identical to the serial reference. Peak RSS per merge process is 86 MB (serial 72 MB; bound 1 GB). Phase 1 runs at 639,000 rows/s with 16 processes (40,000 per process); phase 2 at 78,000 rows/s. The 500-shard case is byte-identical to the serial merge in both settings: under RLIMIT_NOFILE = 48 (F = 16, 3 passes) and with `--fan-in 2` (9 passes). RLIMIT_NOFILE = 33 is refused (F < 2). | `stage3b/s3bmscale.54643361.0/merge_scale.json` |

**First round, on export `81aa977`.** Its `tools/`, `src/`, `slurm/` and `inputs/` equal `1d25d9e`'s. The fixes of
`b4273c5` change only `tools/production.py`'s merge (exact sums, spawned workers) and `slurm/run_array.sh`'s trap.

| Job | Where | What it shows | Files |
|---|---|---|---|
| 54638742–54638744 | `sbatch --test-only` (no allocation) | **Lane-worker shapes accepted on Expanse.** The `compute` lane worker as `slurm_submit.py` builds it, with `--exclusive --nodes=1 --ntasks=1 --mem=240G -t 24:00:00`, with and without `--cpus-per-task=128`: both "would start using 128 processors" on one node. The `shared` drill shape (`-c 4 --mem=7G --no-requeue`) is accepted too. | this README |
| 54641702 | `shared` 16 CPUs, 1:07 | **Build.** The same executables as part A. It created the **seed log** `$C8_DATA/forbidden_seeds.json` (`tools/seeds.py init`) and registered the **L=2 control's seed** 7082694491065029298 (job 54637264). | `stage3b/s3bbuild.54641702.0/` |
| 54641704 | `shared` 16 CPUs, 8:54 | **J-VAL-4, A-KER-4, passed.** `tests/sanitize.py --selftest` with `bin/c8d2_{decimal,gmp}_san`: 144 worker runs clean, both backends' point checks clean, and each of the three self-test probes aborts with its own report. The native code is unchanged since part A's J-VAL-4 (54637265). | `stage3b/s3bval4.54641704.0/` |
| 54641706 | `compute` <NODE>, 128 cores, 9:23 | **J-SWEEP-1, R13.** `slurm/sweep.sh` → `tools/sweep.py` in bootstrap mode, seed 516670960489998667: a test-only plan of all 24,173 graphs, both campaigns, 2 × 512 points, `--bootstrap-chunk 512 --shards 8`. It has 176 indices and estimates "unavailable (bootstrap)". The job registered itself in the ledger (role sweep) before any index, then ran 8 NUMA-pinned slots of 16 threads, heaviest first (560 s), and merged with 32 processes. The **first measured cost model** holds all **48,346** `campaign:sector:L:graph` keys (`cost_model.json`; per-(sector, L) table in `docs/PERFORMANCE.md`). The campaign-keyed calibration rows went to `calibration.json` beside it. The seed was added to the seed log. The preliminary proxy was 1.45–4.6 × the measured cost, so no task exceeded its bound. | `stage3b/sweep1.54641706.0/` |
| 54641707 | `shared` 2 CPUs, 0:02 (after the sweep) | **A-ORC-9 on the sweep.** `tools/accounting.py`: the ledger holds one job (the sweep). One `sacct -X --duplicates` record gives 20.02 allocated core-hours (128 × 563 s). Busy thread-time is 7.61 core-hours (from `merged.json`), so η_node = 0.380. 512 checkpoints carry the job id; none is local. Also `ledger.py list` and the seed log. | `sweep1.54641706.0/accounting.json`, `ledger_list.txt`, `seeds_after.txt` |
| 54641703 | `shared` 16 CPUs, 1:18:03, FAILED | **J-VAL-1, attempt 1** (temporary copies on Lustre). `validate` passed. `unit_orchestration` passed 37/38 in 76 min. The A-ORC-13 claim flagged an import lookup of `tools/__pycache__` in the real-executable package copy, a test defect fixed in `1d25d9e`. `make` stopped there. | `stage3b/s3bval1.54641703.0/` |
| 54641705 | `shared` 16 CPUs, 0:32, FAILED | **merge_scale, attempt 1.** The plan of 3.9 × 10^6 tasks must run inside a job, and the test had removed `SLURM_JOB_ID`. Fixed in `1d25d9e`. | `stage3b/s3bmscale.54641705.0/` |

**Second round, on export `1d25d9e`:**

| Job | Where | What it shows | Files |
|---|---|---|---|
| 54643232 | `shared` 16 CPUs, 1:03 | Build (the same executables). | `stage3b/s3bbuild.54643232.0/` |
| 54643233 | `shared` 16 CPUs, 13:04, FAILED | **J-VAL-1, attempt 2** (node-local temporary copies). Everything passed except two `unit_orchestration` tests (36/38). (1) The A-ORC-13 spy did not count the `ldd` pipe, which `subprocess` reads with `os.read` when `communicate` has a timeout: the platform bytes came to 1,188 below `fingerprint_bytes`. A test defect. (2) The run_array launch-boundary test timed out once. | `stage3b/s3bval1.54643233.0/` |
| 54643234 | `shared` 16 CPUs, 1:59, FAILED | **merge_scale, attempt 2.** **Two real merge defects.** At 1.25 × 10^6 rows the parallel merge was not byte-identical to the serial one: `merged.json`'s seconds sums depended on the order of completion. With 16 forked workers under RLIMIT_NOFILE = 48, phase 2 hit EMFILE. Both are fixed in `b4273c5`: `math.fsum` sums and spawned workers. | `stage3b/s3bmscale.54643234.0/` |
| 54643327 | `shared` 8 CPUs, 1:13 | Development run, not a record: the launch-boundary test passed 6 times in a row in isolation, and the fixed A-ORC-13 claim passed on Linux with the real worker. | `stage3b/logs/c8d2-dbg-signals_54643327.out` |

**On the Mac at the tag** (`stage3b/mac_b4273c5/`, `make test-python`, anaconda Python 3.10.11):
- `unit_orchestration`: 38/38. On macOS, A-ORC-13 takes the documented fallback: one `uname -p`, the failed `ldd`
  attempt and the fake worker. The platform cache is cold.
- `test_pipeline`: 8/8.
- `ast_scan`: 0 findings.
- `merge_scale` (39,056 rows; 500 shards): passed.
- `check_vendored`: 17/17. `vendored_isolated`: 10/10.
- The delivery-verifier test (R16 symlink cases) passed. `check_inputs`: 11/11, 2 skipped.
- The Stage-2b assembly tests, rerun at this part: `assembly_checks --exact` 37/37 (A-ASM-2/4/5),
  `verify_result_tamper` 22/22 (A-ASM-7), `combine_core` 11/11 and `compat_2026` passed (A-ASM-3).

## Checkpoint review fixes (ffbc8af): validation and independent verification

The checkpoint Codex review of 601b102 returned 20 findings (`LRI_C8_D2_HPC_loop/artifacts/ckpt_{K,O,T}/`). The fixes
are `127b6e1` (tools: O01–O11, CK-K01 = O05, T-01 = O02) and `ffbc8af` (kernel and tests: CK-K02, CK-K03, T-02 to
T-06). Everything for this step is in `ckpt_fix/`; `ckpt_fix/verdict.json` is the per-finding verdict.

**Expanse: not run (0 SU).** No Expanse session existed during this step: ssh needs MFA, and no ControlMaster socket was
open at any check (last 2026-10-04 06:08 EDT). The runs are ready in `ckpt_fix/scripts/`. (They ran later, on the
follow-up commit `d98e3a1`: see the next section.)
`submit_ckpt_expanse.sh` (run in the checkout once a session is open) does the following, for about 15–25 SU:
- checks the <ACCOUNT> queue (H7E-R);
- exports HEAD and checks the export against `git archive` (`export_check.py`);
- uploads 601b102's `production.py`;
- submits three `shared` jobs:
  - `expanse_ckpt_build.slurm`: all builds, and `bin/c8d2_{decimal,gmp}` against the Stage-3 hashes (`3dbd51bb…`,
    `5c5328af…`); exit 3 if they differ, which calls for A-RPL-1..3;
  - `expanse_ckpt_val1.slurm`: J-VAL-1, the `make test` commands plus `gen/test_regress.py`,
    `verify_result_tamper` and `combine_core`;
  - `expanse_ckpt_mscale.slurm`: `merge_scale --rows 1000000`, the 32 → 256-point scaling with one and four shards and
    peak RSS, and the same scaling with 601b102's `production.py` (expected to fail).

Still owed on a cluster at this point (both done since, on `d98e3a1`; see the next section):
- these three jobs;
- the J-GEN-1 rerun of `gen/regress.py` at L3–L7 with threads 1 and 8 (CK-K02; the kernel fixer could not run it).

**Substitute cluster runs on canonical** (`ckpt_fix/canonical_269/`):
- **Machine.** 2 × Xeon Gold 6226R, 2 cores of the shared box, GCC 11.4, Boost 1_74, Python 3.10.12 venv (numpy
  2.2.6).
- **Why canonical.** personal desktop estimated weeks (FIFO behind 79 or more pending jobs), symmetry has been down since
  2026-10-03, and pi was fully allocated.
- **Limits.** The L8 packs are not staged there, so validate ran its L2–L7 parts only. Canonical's binary hashes are not
  comparable with Expanse's.

| Job | What it shows |
|---|---|
| 269 | **Export.** 5,117 files equal `git archive ffbc8af` by sha256 and path, with git's modes. Canonical's umask 002 sets the group-write bit; the byte-wise listing check in the job log flagged this, and `export_check_ffbc8afe87c0_canonical.json` maps the modes. |
| 269 | **Default workers unchanged.** `make` in a 601b102 export and in the ffbc8af export gives byte-identical `bin/c8d2_decimal` (`230c532b…`) and `bin/c8d2_gmp` (`f5ccc18f…`). The inspector differs (CK-K03). On all 3,773 L3–L7 graphs of both sectors the inspector prints the same lines old and new, and leaves TMPDIR empty. |
| 273 | **Preprocessed workers.** `g++ -E -P` of `c8d2_integrate.cpp` with the Makefile flags, default and `-DC8_USE_GMP`, 601b102 against ffbc8af. Equal with whitespace removed. The one word-level difference is a line break after `;` before `try`, so the C++ tokens are the same and no `__LINE__` changes. This is why the Expanse build should reproduce the Stage-3 hashes. With `-DC8_ORDER_TRACE` the units differ (control). Job 270's word-split comparison counted that line break and is superseded; job 272 was cancelled. |
| 269 | **CK-K03.** `validate.inspector_tempdir` on L7 passes for both sectors (`c8d2_inspect.XXXXXX` 0700 with `g<k>.txt` 0600; SIGTERM and SIGUSR1 clean up; an ignored SIGHUP stays ignored), and the 601b102 inspector fails it. The verifier's own probes (`native_check.py`): SIGINT, SIGHUP, SIGQUIT, SIGALRM, SIGXCPU and SIGPIPE all clean up; SIGKILL leaves the 0700 directory (documented). An unwritable or missing TMPDIR exits 2 and creates nothing; thread counts 0 and 4097 are refused; two concurrent runs get different directories. A symlink planted at the old predictable name is not followed, while the 601b102 inspector writes through it into the target. |
| 269 | **T-04.** `validate.inspector_order` at L7 (50 graphs, 100 tasks): the worker's traced order equals the inventory's prediction, and the trace rows equal `bin/c8d2_decimal`'s. Three mutants of `c8d2_integrate.cpp` each fail with "executed order differs": comparator reversed, loop ignoring the order, and the cost key without the addends (the verifier's own). |
| 269 | **Suites in the export, Linux.** All passed except one flaky test (row below). `validate --only describe bad_inputs replay`: 24 records, G-REF/G-C7/G-JET on L2–L7 with both backends against `make c7ref`. `unit_orchestration`: 34 of 35 tests; A-ORC-13 ran on the Linux path with the real `bin/c8d2_gmp`. Also: `test_pipeline` 11, `ast_scan` 0 findings, `gen/test_regress` 42/42, `merge_scale --rows 20000` (500 shards included), `check_vendored --no-review-record` 16/16, `vendored_isolated --in-place` 10/10, the delivery-verifier test, `check_inputs` 10/10, `workflow`, `staging`, `verify_result_tamper` 54/54, `combine_core` 11/11, `assembly_checks --exact` 37/37 and `verify_delivery --strict`. |
| 269, 271 | **The one failure is a timing flake.** `signals` (the `run_array.sh` launch-boundary case) failed once under the full suite on the loaded node: the scratch directory was not empty within 10 s. Neither that test nor the code under it changed. Rerun alone it passed 9/9: ffbc8af and 601b102, TMPDIR on HDD and SSD (`signals_rerun_271/`). It also timed out once on Expanse in Stage 3 (job 54643233). |
| 269 | **O02 = T-01, memory on Linux.** Group `a_free_L7`, block 256, fan-in 16, `merge --jobs 1`. At 4 → 32 points (19,528 → 156,224 rows) peak RSS grows 1.4 MB (1 shard) and 1.5 MB (4 shards). At 16 → 128 points (78,112 → 624,896 rows) it grows **0.5 MB and 0.4 MB**, and the traced Python heap stays at 9.67 MB. Every merge is byte-identical to the serial one. **With 601b102's `production.py`** the same runs grow **+308 MB (1 shard; heap +278 MB, 590 B per extra row) and +80 MB (4 shards)**, and the gate fails. |

**On the Mac** (`ckpt_fix/mac_ffbc8af/`, anaconda Python 3.10.11, checkout at ffbc8af):
- **Suites.** All passed: `unit_orchestration` 35 tests (45 records), `test_pipeline` 11, `ast_scan`, `gen/test_regress`
  42/42, `merge_scale --rows 20000`, `verify_result_tamper` 54/54, `combine_core` 11/11, `assembly_checks --exact`
  37/37, `check_vendored` 17/17, `vendored_isolated` 10/10, `check_inputs` 11/11, the delivery-verifier test.
- **Mac RSS margin.** The Mac's 4 → 32-point RSS growth was 12.4 MB in one shard, against a limit of 16 MB; the fixer
  measured 4.4 MB. The traced heap growth was 0. This is the macOS allocator, but the Mac gate has little margin.
- **Detection (`old_code_detection/`).** The new tests on 601b102's tools (`tools/`, `slurm/`) fail for the defect
  itself:
  - `chunking`: "the LPT ran before the task-count caps";
  - `cached`: a tampered run reused;
  - `drill`: `--exclusive` in the directives;
  - `roles`: the merge went to amdq;
  - `unverified`: a merge was submitted after the unverified worker;
  - `cancel`: a started merge was cancelled;
  - `ledger`: "design.py accepted incomplete accounting";
  - `verify_result_tamper`: 28 cases accepted;
  - `test_pipeline`: O11's c8-d2 bundle schema, and O09's `FileExistsError`.

  601b102's own drivers show the T-02/T-03 defects:
  - `--only alocation` exits 0, "passed", with 0 tests;
  - `test_pipeline --only part3` exits 0, "passed";
  - `vendored_isolated --in-place` with `.git` records `passed: true` with 0 checks.

  601b102's `ast_scan` misses Codex's del-in-finally example; ffbc8af's reports it. A mutant of `lanes.memory_limit`
  that ignores `SLURM_MEM_PER_NODE` fails both T-06 tests.
- **The verifier's own break attempts (`probes/`).** Every one held except the O11 gap below.
  - O01: two rows' values exchanged across two cached runs, with keys, order and counts kept; the same digit edited in a
    level-1 run and in the level-2 run built from it; a level-2 run replaced by its sibling; CRLF in one line. Each was
    rebuilt, and the tables equal the serial merge.
  - O02: `_phase1` under tracemalloc at 8× the rows of one index: about 21 B per extra row on a 1.1 MB peak.
  - O05: `--exclusive=user`, directive placement after comments and after the first command, an unknown directive
    refused, and no `--exclusive` in any shipped script.
  - O06: malformed sacct lines, a ledger attempt with restart 2, a checkpoint element outside the array spec, and a
    requeued array element.
  - O09: model reuse and refusal, and a corrupt existing model.
  - O10: per-batch SE, `planned`, a duplicated batch, a float `dof`, a string chi-square, a status with a trailing
    space, and `power_correction_se` alone. A coordinated edit of `power_free_se` and the cross covariance that keeps
    the variance identity is accepted. That is the documented limit: no statistics are stored to recompute them.
  - CK-K02: six more comparator cases.
  - T-03: more `--only` forms.
  - T-05: seven more scanner cases.
  - T-02: a malformed HANDOFF JSON.

**Verdict.**
- **Resolved: 19 of the 20 findings.** CK-K01, CK-K02, CK-K03; O01–O10; T-01–T-06.
- **O11 is partial.** The pilot reader, the bundle, report and rate-map schemas, and the parameter checks follow
  `--schema-prefix`. But `design.py`'s η_node path (`tools/accounting.py` → `tools/ledger.py`) accepts only
  `c8-d2-ledger-1` records. A C8(3) pilot keeps its own `c8-d3-ledger-1` ledger (C8(3) PLAN HD7), so a non-test C8(3)
  freeze or report is refused with "submissions.jsonl line 1 is not a c8-d2-ledger-1 record"
  (`probes/probe_o11_ledger.log`). The O11 test's c8-d3 view keeps the copied c8-d2 ledger and so cannot see this.
  - Fix: let the ledger reader take the schema from the prefix (`ledger.read`/`jobs` with a schema argument, used by
    `accounting.account` through `schemas_of`).
  - Test: extend `d3_view` to rewrite the ledger to `c8-d3-ledger-1`.

The default numerics are unchanged: the workers are byte-identical on a personal desktop, and the preprocessed units are
token-identical.

## Checkpoint review fixes on Expanse (d98e3a1): build, J-VAL-1, merge scale, J-GEN-1

**What ran.** The Expanse validation owed by the previous section, on the current HEAD `d98e3a1`. That commit holds the
checkpoint fixes `127b6e1` and `ffbc8af` plus the verifier follow-up: the O11 residual, the signals launch-boundary
race, and the macOS merge_scale bound. Everything is in `ckpt_fix/expanse_d98e3a1/`:
- one directory per job, copied from `$C8_DATA/evidence/d98e3a10c6e9/`;
- the Slurm logs in `logs/`;
- the driver output, with every admission snapshot, in `submit.log`.

All five jobs ran on `shared` nodes (<NODE>; diag on <NODE>) and were named `c8d2-ckfix-*`.

**Export.** `setup/export_check_d98e3a10c6e9.json`: `git archive d98e3a1 | tar -x` into `$C8_DATA/pkg/d98e3a10c6e9`.
- All 5,230 files equal the archive by sha256 and path, with no file missing or extra.
- Every mode equals git's recorded mode, and there is no symlink or special file.

**Driver adaptations.** `ckpt_fix/scripts/submit_ckpt_expanse.sh` exports HEAD, as before. Four things changed; the
script's header lists them.
1. The full H7E-R rule is checked before every `sbatch`, not once. Every snapshot showed 0 c8d2 normal-QOS jobs, at most
   1 running normal-QOS job in <ACCOUNT>, at most 3 live c8d2 shared jobs, and no compute node.
2. The export listing goes to a private temporary directory, not `/tmp`.
3. The J-GEN-1 rerun is submitted too.
4. The wall limits were tightened on the command line (val1 1:30, mscale 2:00), and mscale asks for 32 GB instead of
   48 GB. The Stage-3b merge-scale job had peaked at 0.9 GB; this one peaked at 1.7 GB. The worst case of all jobs stayed
   below 100 SU.

One job was added by hand: `expanse_ckpt_diag.slurm` (below). `compare_gen1.py` compares the two J-GEN-1 records.

| Job | Where | Wall | What it shows | Files |
|---|---|---|---|---|
| 54658871 | `shared` 16 CPUs, 32 GB | 1:01 | **Build. The default workers are byte-identical to Stage 3:** `bin/c8d2_decimal` `3dbd51bb…` and `bin/c8d2_gmp` `5c5328af…` (`binaries_vs_stage3.json`: identical). `bin/ref/c7d2_{decimal,gmp}` are also unchanged (`4537dcfd…`, `6c829386…`). As expected, the inspector changed (CK-K03): `034db6a1…` became `63c194fd…`. The sanitizer builds changed (`d8faf30c…`, `824eea8b…`): they carry debug info and source locations, and T-04 moved lines in `c8d2_integrate.cpp`. No worker binary changed, so A-RPL-1..3 need no rerun; J-VAL-1's replay subset passed anyway. | `ckbuild.54658871.0/` |
| 54658872 | `shared` 16 CPUs, 32 GB | 15:53 | **J-VAL-1, every command passed** (the `make test` sequence, with temporary copies on node-local NVMe). See the list below the table. | `ckval1.54658872.0/` (`records/`, one log per command) |
| 54658873 | `shared` 16 CPUs, 32 GB | 1:18:51 | **Merge scale (T-01/O02, O01) passed; the 601b102 control fails as intended.** See the list below the table. | `ckmscale.54658873.0/` |
| 54658874 | `shared` 8 CPUs, 15 GB | 2:29 | **J-GEN-1 rerun (CK-K02), passed with the original verdicts.** See the list below the table. | `gen1.54658874.0/` (`compare_vs_54631551.json`) |
| 54658970 | `shared` 8 CPUs, 16 GB | 0:19 | **Diagnostic builds** (added: neither the ckfix build nor Stage 3b's built them, so `validate` skipped their part). `make profile ratiohist`: `bin/c8d2_gmp_prof` `d1cc6551…` and `bin/c8d2_gmp_ratiohist` `c307f2a3…`, byte-identical to Stage 3 part A (54637262). `validate --only diagnostics` passed: at L7 and L8 in both sectors, the rows equal `bin/c8d2_gmp`'s, and the tier calls and histogram counts equal the points, quad and MP counts. The two builds were then removed from the export. | `ckdiag.54658970.0/` |

**J-VAL-1 (54658872).**
- `validate` passed: describe, 28 refusals, and the replay subset with G-REF, G-C7 and G-JET on 117 kernels, both
  backends against `make c7ref`. Also passed:
  - invariance: chunks and layouts at L7/L8;
  - `inspector_private_tempdir` on L7: CK-K03's 0700 directory with 0600 files; a normal run, an error exit, SIGTERM
    and SIGUSR1 leave TMPDIR empty, and an ignored SIGHUP stays ignored;
  - `inspector_execution_order`: T-04, 100 graphs at L7 and L8 in both sectors;
  - class B.
- `unit_orchestration`: 35 tests, 45 records, no failure.
  - It includes `signals` with the shell cases `boundary0`, `boundary1` and the new `lost_term0`. They passed under load,
    with mscale running beside them on the same node.
  - A-ORC-13 ran on the Linux real-worker path: `fingerprint_bytes` 29,930,938, with launches `ldd` and the worker.
- `test_pipeline`: 11 tests, including O11's C8(3) view with its own `c8-d3-ledger-1` ledger.
- `ast_scan`: 0 findings in 24 files.
- `gen/test_regress`: 42/42.
- `merge_scale --rows 20000`: passed.
- `check_vendored --no-review-record`: 16/16.
- `vendored_isolated --in-place`: 10/10.
- The delivery-verifier test passed.
- `check_inputs`: 10/10. Two items were skipped: the git-only C7(2) member check and the regeneration from
  `inventory8_d2`.
- `workflow` and `staging` with the real workers passed.
- `verify_result_tamper`: 54/54.
- `combine_core`: 11/11.

**Merge scale (54658873).**
- (1) `merge_scale --rows 1000000 --jobs 16` passed.
  - 1,249,792 rows in 16 shards. The parallel merge is byte-identical to the serial one.
  - Peak RSS: 39.8 MB per merge process; 71.6 MB serial.
  - Phase 1 runs at 597,730 rows/s (16 processes); phase 2 at 80,982 rows/s.
  - The 500-shard cases are byte-identical under RLIMIT_NOFILE = 48 (3 passes) and with `--fan-in 2` (9 passes).
    RLIMIT_NOFILE = 33 is refused.
  - Its 4 → 32-point memory section grows RSS by 0.5 MB, in 1 shard and in 4.
- (2) The 32 → 256-point scaling of `a_free_L7`: 156,224 → 1,249,792 rows, checkpoint size 256, fan-in 16,
  `merge --jobs 1`. Every merge is byte-identical to the serial one.

  | Code | Shards | Peak RSS growth | Traced heap growth | Gate |
  |---|---|---|---|---|
  | `d98e3a1` | 1 | +0.96 MB (0.9 B per extra row) | +0.13 MB | pass |
  | `d98e3a1` | 4 | +0.63 MB | 0 | pass |
  | 601b102's `production.py` (sha256 `a0349405…`) | 1 | +611 MB (586 B per extra row) | +560 MB | **fails** |
  | 601b102's `production.py` | 4 | +163 MB | +139 MB | **fails** |

  The bounds are 16 MB of RSS (the Linux bound) and 2 MB of traced heap. The 601b102 control shows the regression
  test catches the defect on Linux at 8× canonical's rows per shard.
- Wall time 79 min: 6 min for (1), then about 36 min for each code's 32 → 256 run, mostly building the campaigns.

**J-GEN-1 rerun (54658874).**
- `check_sources` passed. `test_keys` 34/34. `test_run_l8` 5/5. `test_verify_inventory` 25/25. `test_regress` 42/42 (new
  in J-GEN-1). `test_handoff_inventory` 6/6.
- `gen/regress.py` (the CK-K02 version) at L3–L7, threads 1 and 8, with the real builders: **A-INV-2 passed**.
- `compare_gen1.py` finds every verdict equal to the original J-GEN-1 record (54631551, export `36043bb`):
  - free L3–L6: 0 identical and rate-only 5, 16, 76, 395, with the same rate-entry counts;
  - free L7: 2,441/2,441 identical;
  - power L3–L7: 1, 3, 20, 107, 709 identical;
  - no relabelling and no "other" file;
  - every inventory equal and byte-identical;
  - threads 1 and 8 identical;
  - every side-file control true.
- The new header checks report no mismatch in either the new or the frozen trees.

**Cost.** 26.6 SU: 0.28 build, 4.34 J-VAL-1, 21.57 merge scale, 0.33 J-GEN-1, 0.04 diag. This uses the `shared` rule:
the larger of the CPUs and memory/1.95 GB, times wall time.

**Files.** The session created about 11,000 Lustre files: 1,166,028 → 1,176,997 against the 2,000,000 limit. Most are
the export, 5,230 files plus builds. The data live in `$C8_DATA/pkg/d98e3a10c6e9` and
`$C8_DATA/evidence/d98e3a10c6e9/`.

**Not done here.** The symmetry repeats of J-VAL and the smoke test, and J-GEN-3, still wait for symmetry (site
deviation U1).

## Allocation used

Expanse total for this session: 310.0 SU (core-h): 131.2 through the checkpoint fixes plus 178.8 for Stage 4a.
`shared` charges the larger of the CPUs and the memory equivalent, about 1.95 GB per core.
- Stage 1 and H1: 11.1.
  - 54631541: 0.03
  - 54631551: 0.41
  - 54631552: 7.82
  - 54631553: 2.60
  - 54631581: ≤ 0.26
- Stage 2: 2.9.
  - 54632984: 0.002
  - 54632985: 0.77
  - 54633090: 1.84
  - 54633368: 0.28
- Stage 3, part A: 37.6 (CPU-based; `shared` memory equivalents add at most 0.1).
  - Development: 10.8.
  - 54637262: 0.31
  - 54637263: 7.36
  - 54637264: 16.68
  - 54637265: 2.44
- Stage 3, part B: 53.0 (`shared` charged at the larger of CPUs and memory/1.95 GB).
  - 54641706 (J-SWEEP-1, 128 cores): 20.02
  - 54641703 (J-VAL-1 attempt 1, Lustre): 21.33
  - 54641704 (J-VAL-4): 2.43
  - 54643233 (J-VAL-1 attempt 2): 3.57
  - 54643360 (J-VAL-1): 2.71
  - merge scale 54641705, 54643234, 54643361: 0.22, 0.81, 0.83
  - builds 54641702, 54643232, 54643359: 0.31, 0.29, 0.27
  - 54641707 (accounting): 0.001
  - 54643327 (development): 0.17
  - 54638742–54638744: `--test-only`, no allocation; 54640082–54640087: cancelled while pending, no allocation
- Checkpoint review fixes (ffbc8af): 0 SU on Expanse, because no session was open. The canonical jobs 269–273 used
  about 2 core-hours, outside the Expanse allocation.
- Checkpoint review fixes on Expanse (d98e3a1): 26.6 (`shared`, the larger of CPUs and memory/1.95 GB).
  - 54658871 (build): 0.28
  - 54658872 (J-VAL-1): 4.34
  - 54658873 (merge scale): 21.57
  - 54658874 (J-GEN-1): 0.33
  - 54658970 (diagnostic builds): 0.04
- Stage 4a, profiles J-PROF-1..4 (c176881): 178.8 (`compute`: 128 SU per node-hour; `shared` as above).
  - 54661715 (build, `shared`): 0.17
  - 54661716 (P1): 18.28
  - 54661717 (P2 and the probe): 12.37
  - 54661718 (P3): 25.32
  - 54661719 (P4, full node): 70.15
  - 54661771 (P4, half node): 52.55

Stage 4b (development, integration and G4b) used 375.6 SU more, so the Expanse total is 685.6 SU. The breakdown is in
"Stage 4b G4b" below. Stage 4c (framework, the four developer branches, integration and the J-FLAG gate) used 205.1 SU
more, so the Expanse total is 890.7 SU ("Stage 4c integration and J-FLAG gate" below).

**Across sites.** The plan's 5,000 core-hour development cap counts Expanse SU as core-hours (host decision,
`PLAN-REVIEW-LOG.md`). Against it, the session had used about 340 core-hours through Stage 4a, and about 716 with
Stage 4b:
- Expanse: 310.0 through Stage 4a, 685.6 with Stage 4b, and 890.7 with Stage 4c (so about 921 core-hours in all).
- symmetry: 28.4. J-GEN-3 569770 used 2.29 CPU-h as Slurm counts them (80 logical CPUs; 1.14 physical-core-hours),
  and the P4 job 569788 used 26.12 core-hours (`../symmetry_2026-10-c8/README.md`).
- canonical: about 2 core-hours (the checkpoint-fix jobs).

## Stage 4a: profiling on the Stage-3 baseline (J-PROF-1..4), 2026-10-04 [A-PERF-1]

The tools, the frozen workloads and the results are in `docs/PERFORMANCE.md`: "Stage 4a: profiling tools and frozen
workloads" describes the tools and workloads, and "Stage 4a: profiles on the Stage-3 baseline" gives the tables and the
Stage-4b/4c decisions. Everything for this step is in `stage4a/`:
- the job scripts in `stage4a/scripts/`;
- one directory per job, copied from `$C8_DATA/evidence/c17688158e2b/`;
- the Slurm logs in `stage4a/logs/`;
- the admission records in `stage4a/admission/`;
- the runner's summary in `stage4a/stage4a_runner_summary.json`.

**Recomputation.** `stage4a/writeup/derive_stage4a.py` recomputes every headline number from the raw files (perf report
texts, perf stat CSVs, tier-timer rows, probe timings, histogram counts, per-shape P4 records, the J-SWEEP-1 cost model
and sacct). It writes `stage4a/writeup/stage4a_derived.json`, and gives the same output under Python 3.9 and 3.10.

**Export.** `setup/export_check_c17688158e2b.json` records `git archive c176881` extracted into
`$C8_DATA/pkg/c17688158e2b`. All 5,353 files equal the archive in content and mode. Every job below ran from that
export. c176881 is the Stage-4a tooling commit; `src/` is unchanged since the Stage-3 baseline.

**Submission.**
- `submit_prof_expanse.sh` submitted the build and P1–P4, with P1–P4 `afterok` on the build.
- The half-node P4 (`c8d2-prof4h`) was submitted by hand on the same export, with `-t 00:40:00`,
  `C8_P4_SHAPES=1x64,2x32,4x16,8x8` and `C8_P4_FRACTION=0.5`. The submit script exports HEAD, which by then was
  7a8aad7, a tools-only parser fix.
- `h7_admit.py` (H7E-R on a fresh `squeue -A <ACCOUNT>`) ran before each of the 6 sbatch calls and admitted every job:
  `admission/h7e_r_admission.jsonl`, with snapshots in `admission/squeue_*.txt`.
- At most 4 `c8d2` compute nodes were in use at a time, and the account had no other running normal-QOS job.
- Every job started at once, with 130+ idle compute nodes.

| Job | Where | What it shows | Files |
|---|---|---|---|
| 54661715 `c8d2-prof-build` | `shared` 16 CPUs, 32 GB, <NODE>, 0:37 | **The Stage-3 binaries rebuilt byte for byte.** `bin/c8d2_gmp` `5c5328af…` and `bin/c8d2_decimal` `3dbd51bb…`, and both diagnostic builds (`_prof` `d1cc6551…`, `_ratiohist` `c307f2a3…`), equal Stage 3; `make probes` built the interleave probe. The L8 packs were hard-linked from the 7aac898 export and re-hashed against `inputs/manifest.json`, and every fixture graph was staged and checked against its inventory sha256. | `stage4a/profbuild.54661715.0/` (`binaries_vs_stage3.json`, `build_records/`, `describe/`, `fixtures_check.json`, make logs) |
| 54661716 `c8d2-prof1` | `compute` exclusive, <NODE>, 8:34 | **P1**: tier split and time per function on the heavy free/power L7 and L8 blocks at 64 threads. perf 4.18, `perf_event_paranoid` 1, 0 samples lost (3.4–9.8 million per block). The tier timers ran on socket 1, with rows identical to the worker's. The source lines come from a `-g` twin that is section-identical to the release binary. The perf summaries are in `p1/p1_reparsed.json` (rebuilt offline after the perf 4.18 IPC-column fix, 651c56f); the job's own `p1.json` is kept unchanged. | `stage4a/prof1.54661716.0/` |
| 54661717 `c8d2-prof2` | `compute` exclusive, <NODE>, 5:48 | **P2**: IPC 1.009 / 1.037 on the promotion-free free L7/L8 blocks (1.004 / 1.038 at 1 thread) and 2.71 on the heavy free L8 block. The lock-step probe gives 1.098 with 2 points (1.032 promotion-free, 1.168 heavy) and 1.083 with 4, all bit-identical. | `stage4a/prof2.54661717.0/` |
| 54661718 `c8d2-prof3` | `compute` exclusive, <NODE>, 11:52 | **P3**: ratio histograms for 6 blocks at rates .8 and .9 (12 runs). Every consistency check passes. | `stage4a/prof3.54661718.0/` |
| 54661719 `c8d2-prof4` | `compute` exclusive, <NODE>, 32:53 | **P4, full node** (4,018 tasks). 16x8 is best at 113.45 cost-model s per node-second, with 8x16 at 0.990, 4x32 0.951, 1x128 0.908 and 2x64 0.899. Load + staging is 1.42% at 16x8 and 10.62% at 1x128. Rows are identical across shapes. | `stage4a/prof4.54661719.0/` |
| 54661771 `c8d2-prof4h` | `compute` exclusive, <NODE>, 24:38 | **P4, half node** (socket 0, 2,010 tasks; the symmetry shapes and task set). 8x8 is best at 58.03, with 4x16 at 0.978, 2x32 0.944 and 1x64 0.935. Rows are identical across shapes and byte-identical to the symmetry run 569788. | `stage4a/prof4.54661771.0/` |

**Results.** The full tables and the decisions are in `docs/PERFORMANCE.md`. In short:
- **Tier split, heavy L8.** First pass / binary128 / MP: free 5.3 / 56.9 / 34.7% and power 4.0 / 48.0 / 42.1%.
- **Tier split, all of L8 (model).** 7.8 / 61.5 / 30.7% in campaign a.
- **Symbols.** `__addtf3` is 33–53% of samples and `__divtf3` 0.5–1.1%. `calculate_reference<ld>` and the shift loop
  are 0%.
- **IPC.** The first pass runs at 1.0, so R6 is a go by its rule. The promoted tiers run at about 2.8, so R3c is a
  no-go.
- **Thresholds.** `C8_DD_RATIO` 1e-20 and `C8_MP256_RATIO` 1e-63.
- **Lanes.** 8-thread lanes on both sites.
- **Packs.** Load + staging is below 2% at the default shapes, so no binary pack is proposed.

**Cost.** 178.8 SU (see "Allocation used"). The planned worst case was about 285 SU, plus the hand-submitted half-node P4
with its 40-minute limit.

**Files.**
- The Lustre file count went from 1,176,997 to 1,188,224 (`lfs quota` at the end, last line of
  `admission/sacct_stage4a.txt`). The count is shared with C63d's jobs.
- No `raw_evidence.tgz` was made. The evidence totals about 1.3 MB; perf.data and the staged graphs stayed on node-local
  `/scratch/$USER/job_<id>`; and the 46 per-lane P4 logs of the two Expanse runs are empty (no lane reported anything; every shape has no error).

The symmetry part of Stage 4a (the P4 lane shapes on amddebugq) and J-GEN-3 are in `../symmetry_2026-10-c8/README.md`.

## Stage 4b R3a development (branch `opt-r3a`), 2026-10-04 [A-PERF-2 evidence for R3a]

Workflow wf_f7916ef0-f06, R3a development agent. Its limits were 1 compute node and 8 live shared jobs at a time, and a
share of 250 SU. The results and decisions are in `docs/PERFORMANCE.md` ("Stage 4b R3a"). Everything for this step is
in `stage4b/dev_r3a/`:
- `scripts/`: the job scripts, the submit driver, `asm_compare.py`, `r3a_speed.py`, `r3a_prof.py`, and
  `summarize_r3a.py`, which writes `r3a_summary.json` from the records;
- `admission/`: the H7E-R admission line before every sbatch, the squeue snapshots and `sacct_r3a.txt`;
- `round1_908bd9d/` and `round2_add273b/`: one directory per job, copied from `$C8_DATA/evidence/<sha12>/`;
- `dev/`: the development jobs' differential, profile and IPA-probe outputs;
- `logs/`: the Slurm logs.

**Exports.** `setup/export_check_908bd9de0265.json` (5,579 files) and `setup/export_check_add273b9ecc7.json` (5,586
files) record that each export equals `git archive` of its commit. The L8 packs were hard-linked from the 7aac898
export and re-hashed by `make`.

| Job | Where | What it shows |
|---|---|---|
| 54669011 `c8d2-r3a-build` | `shared` 16 CPUs | Final version add273b. gmp `dec065ee…`, decimal `156c09a9…`, the tier-timer build, `make quaddiff`, `make c7ref`; the baseline copies `5c5328af…` and `3dbd51bb…` are checked; asm_compare against the 4a export's source |
| 54669012 `c8d2-r3a-val` | `shared` 32 CPUs, 7:50 | `tests/quad_differential.py` passed: 2^32 pairs per operation and the edge lists, with 0 mismatches. G-L8SELF is exact on both backends, and the replay subset passed |
| 54669014 `c8d2-r3a-speed` | `compute` exclusive, <NODE>, 18:29 | ×1.442 (heavy free L8) and ×1.331 (heavy power L8), median of 3, with identical rows. IPC 3.08 against 2.71. Tier timers |
| 54666584, 54666585, 54666586 | as above | The first version (908bd9d), all passed: ×1.220 and ×1.184, IPC 2.83 |
| 54668821 `c8d2-r3a-prof` | `shared` 16 CPUs | `perf record` of the baseline and the first version on 32 heavy_free_L8 tasks |
| 54666187, 54666231, 54666237, 54666255, 54668843, 54668938, 54668954, 54668994, 54669593 `c8d2-r3a-dev` | `shared` 16 CPUs | Development: the differential on 2^26–2^28 pairs per operation, the version comparisons on a 32-task slice, and the IPA-budget probes |

**Allocation.** 94.5 SU in all (compute 80.5, shared 14.0). Every job completed, with at most 1 compute node and 3
shared jobs of this agent live at a time. About 12,000 new Lustre files, almost all of them the two exports.

## Stage 4b R4f: GMP 6.2.1 built for the node (development probe, branch opt-r4f), 2026-10-04

The evidence is in `stage4b/dev_r4f/`, whose README lists every job, and the results are in `docs/PERFORMANCE.md`,
"Stage 4b R4f".
- **Jobs.** 54666319–24 ran from the export of 913e56a, and the layout control 54668998 from ef705e3. The first
  submission (54666273–82, from ef03b93) was superseded.
- **Builds.** GMP 6.2.1 fat and zen2, `make check` 197/197 each, installed under `~/c8d2/opt/`.
- **Exactness.** The default build is byte-identical to Stage 3. The replay subset and G-L8SELF are exact for both
  builds, and the heavy L8 blocks give identical rows in every run.
- **Speed.** host ×1.0375 / ×1.0423 and fat ×1.0247 / ×1.0248 on heavy_free_L8 / heavy_power_L8 (medians of 3, one
  node).
- **Layout control.** It attributes the gain to the library.
- **Cost.** 76.5 SU.

## Stage 4b development of R5a/R5b and R4a, 2026-10-04

Each development folder has its own README listing its jobs:
- `stage4b/dev_r5/`: 54666182, 54666183 and 54666372; 37.67 SU.
- `stage4b/dev_r4a/`: 54666232, 54666233, 54666291 and 54666315; about 41.3 SU.

## Stage 4b integration on c8: J-OPT gates and A-PERF-2, 2026-10-04 [A-PERF-2; A-RPL-1/2/3/6/7]

The evidence is in `stage4b/integration/`, whose README lists every job and file. The results and decisions are in
`docs/PERFORMANCE.md`, "Stage 4b integration".
- **Merges in plan order.**
  - 138d486 (R5), d46e736 (R3a), bc0bedc (R4a) and 7b9aa9c (R4f).
  - The job scripts are d0f0e05.
  - R4a's code is reverted in ea59445.
- **Jobs.** Every job started at once, and the account had no other running normal-QOS job. Each sbatch passed H7E-R,
  with at most 3 compute nodes and 4 shared jobs of this workflow live at a time.
  - Builds and `validate.py` default parts: 54669703–06.
  - Gates: 54669707 (+R5, +R3a) and 54669708 (+R4a and the zen2 builds).
  - Speed: 54669709.
- **Exactness.** Every step passed: G-L8SELF against Stage 3 on both backends, thread identity, and the replay subset
  (in the default parts, and for the zen2 builds on their own). The R4f merge leaves the default build byte-identical.
- **Speed.** Medians of 3 on one node, L8 sweep sample, 16 × 8 lanes:
  - R5a ×1.154;
  - R3a ×1.426;
  - R4a ×1.0093, so it is reverted;
  - R4f ×1.052 over the kept default, kept as the opt-in knob.

  The default path is ×1.646 faster than Stage 3, and ×1.731 with the zen2 GMP. IPC is 3.04, so R3c is not attempted.
- **Final candidate e7ef98d** (jobs 54672108 and 54672109).
  - The default binaries are byte-identical to +R3a's (`99a51c1d…`, `1d2a2181…`), and the zen2 worker to B2f.
  - G-L8SELF, thread identity, the quad differential (2^32 pairs per operation) and the default parts all passed.
  - The zen2 worker passed G-L8SELF, thread identity and the replay subset.
- **Cost.** 85.8 SU: 64.6 for the steps and 21.1 for the final candidate.
  - The Stage-4b total on Expanse so far is about 336 SU: development 250.0 (R5 37.7, R3a 94.5, R4a 41.3, R4f 76.5)
    plus this integration.
  - That is against the workflow's 1,300 SU.

## Stage 4b G4b: the final J-VAL-2 and J-VAL-3 on the final default binary, 2026-10-04 [G4b; A-RPL-1..7]

The evidence is in `stage4b/final/`, whose README lists every job and file. The results are in `docs/PERFORMANCE.md`,
"Stage 4b: default-path optimizations".
- **Commit under test.** b47b008: the integration head a2ef0a2 plus the job scripts, with `src/` and the Makefile
  unchanged since e7ef98d.
  - The export is checked equal to `git archive` (`setup/export_check_b47b0082c0f7.json`, 6,363 files).
  - The L8 packs of the c17688158e2b export were re-hashed against the manifest, then hard-linked.
- **Jobs.** Each sbatch passed H7E-R (`stage4b/final/admission/`). Every job started at once, and the account had no
  other running normal-QOS job.

| Job | Where | Wall | Result |
|---|---|---|---|
| 54672150 `c8d2-g4b-build` | `shared` 16 CPUs, 32 GB, <NODE> | 0:51 | Every executable byte-identical to e7ef98d's build: decimal `99a51c1d…`, gmp `1d2a2181…`, c7ref `4537dcfd…`/`6c829386…` |
| 54672151 `c8d2-g4b-val2` | `compute` exclusive, <NODE> | 4:06 | J-VAL-2 `make test-full` passed: A-RPL-1/2/3 exact on the L=2 graph and all 3,773 L3–L7 kernels, both backends; point checks; check_inputs, workflow, staging |
| 54672152 `c8d2-g4b-val3` | `compute` exclusive, <NODE> | 14:26 | J-VAL-3 passed: L=2 control, thread identity, G-BK8, G-L8SELF exact against Stage 3, forced tiers, the R3a differential, merge scale, `assembly_checks --exact` 37/37 |

- **Against Stage 3.** With run-specific fields removed, the seven records that Stage 3 also has (54637263, 54637264)
  are equal.
- **Allocation.** 39.77 SU: 0.23 + 8.75 + 30.79. At most 2 compute nodes and 1 shared job of this workflow were live
  at a time, and no job is still live.
- **Stage 4b on Expanse in all: 375.6 SU** of the workflow's 1,300.

  | Part | SU |
  |---|---:|
  | Development: R5 | 37.7 |
  | Development: R3a | 94.5 |
  | Development: R4a | 41.3 |
  | Development: R4f | 76.5 |
  | Integration (`stage4b/integration/`) | 85.8 |
  | G4b (this section) | 39.8 |
  | **Stage 4b total** | **375.6** |

- **Session total on Expanse.** 310.0 SU through Stage 4a ("Allocation used") plus 375.6 for Stage 4b gives 685.6 SU.
  On 2026-10-04, `expanse-client project <ACCOUNT>` showed 50,887 SU spent of the 22,080,000 allocation. Of that,
  27,208 SU is <USER>'s: all of this user's work on <ACCOUNT>, not only this package.
- **Lustre.** 1,312,567 → 1,319,443 files (shared with C63d). The export was 6,363 of them.

## Stage 4c framework: opt-in numerics profiles, 2026-10-05 [A-FLAG-1..3, A-RPL-8]

Everything is in `stage4c/` (README there: the commands for the profile developers and the gate agent, and the
evidence). In short: A-RPL-8 holds on the exports of 9870a68 (54672480) and 241baca (54672538), with
`bin/c8d2_decimal` `99a51c1d…` and `bin/c8d2_gmp` `1d2a2181…` byte-identical to the final default binary and the
preprocessed default program token-identical to b47b008's; the all-stub profile executables reproduce
`bin/c8d2_gmp`'s rows; `tests/numerics_flags.py --self-test` and the dd stub pass every F-gate at development scales
with exact identity (54672484, 54672539). Six `shared` jobs, 3.19 SU; at most 2 live shared jobs of this workflow and
no compute node. No job is live.

## Stage 4c development branches, 2026-10-05 [A-FLAG-1..6; development evidence]

Each developer worked on its own branch and worktree from the framework head 64287cb, with its own job tag and share
(at most 1 compute node and 8 shared jobs). Evidence and job tables: `stage4c/dev_<p>/README.md` and
`stage4c/dev_<p>/sacct.txt`; admission records `stage4c/admission/<p>/`. No job of these is live.

| Branch (head) | What | Jobs | SU |
|---|---|---|---:|
| flag-dd (770a0a4) | R3b `dd`: cascade against direct routing, accuracy tests, F1 at full scale, F4 | 9 (7 shared, 2 node: 54673764, 54673842) | 24.0 |
| flag-mp256 (f41ac89) | R4b `mp256`: F1 at full scale, heavy-L8 speed, perf profile | 5 (1 node: 54673625) | 31.2 |
| flag-exp1 (4bfe7a5) | R4c `exp1`: shifted-point census and bound, forced points, timing, F1, F4 | 13 (2 node: 54673787, 54673847) | 26.3 |
| flag-r7 (2d19e91) | R7: A-FLAG-6 statistical validation (map against exact sweeps, complement, freezes) | 7 (2 node: 54673790, 54673843) | 54.3 |

## Stage 4c integration and J-FLAG gate, 2026-10-05 [A-FLAG-1..5, A-FLAG-7, A-RPL-8, A-PERF-5]

The four branches merged onto c8 (c7aa396, 0d75f19, f4d7609, 5e19ca3), then the integration commit 5569c53 (F1-check
chain, plan refusal of development builds). Results: `docs/NUMERICS.md`, "Stage 4c gate: J-FLAG results (A-FLAG-7)"
and `docs/PERFORMANCE.md`, "Stage 4c". Evidence: `stage4c/gate/` (records copied from
`$C8_DATA/evidence/5569c535dcfd/`; the F2 per-row CSVs and the 450-digit references stay on Expanse, pinned by
sha256). Admission: `stage4c/admission/gate/` (every sbatch passed H7E-R and the gate's share, at most 4 compute
nodes).

| Job | Where | Wall | Result |
|---|---|---|---|
| 54673888 `c8d2-s4c-gate-precheck` | `shared` 16, <NODE> | 1:09 | working tree of the merged head plus the integration edits: defaults `99a51c1d…`/`1d2a2181…`; dd, mp256, exp1 equal to the developers' binaries; every F1 tool compiles without a warning |
| 54673898 `c8d2-s4c-gate-build` | `shared` 16, <NODE> | 0:44 | export 5569c535dcfd (`setup/export_check_5569c535dcfd.json`, 7,043 files equal): **A-RPL-8 holds**, preprocessed default program token-identical to b47b008's; profile binaries dd `51614820…`, mp256 `9e884b1b…`, exp1 `0bf3f1a8…`, dd+mp256+exp1 `6bc26966…` |
| 54673899 `c8d2-s4c-gate-baseline` | node <NODE> | 1:15 | full F1 baseline of `1d2a2181…`: 153,600 points with 450-digit references, need met without doubling |
| 54673900 `c8d2-s4c-gate-gate` | node <NODE> | 6:59 | `dd`: **passed** (F1, F2, F4 rows, F5); F4 ×1.389 |
| 54673901 `c8d2-s4c-gate-gate` | node <NODE> | 7:45 | `mp256`: **passed**; bit-identical to the exact path in F1 and F2; F4 ×1.372 |
| 54673902 `c8d2-s4c-gate-gate` | node <NODE> | 5:52 | `dd+mp256+exp1`: **passed**; F4 ×2.168 |
| 54673904 `c8d2-s4c-gate-gate` | node <NODE> | 8:53 | `exp1`: **passed**; bit-identical; F4 ×1.007; then the layout control (all-stub dd `e2eb509f…` of export 241baca924d2, F4 only): ×1.005, rows identical |

- **Allocation.** 66.1 SU (`stage4c/gate/sacct.txt`): precheck 0.31, build 0.20, baseline 2.67, gates 14.90, 16.53,
  12.52 and 18.95 (the last with the layout control). At most 4 compute nodes and 1 shared job of this workflow were
  live at a time; no job is live.
- **Stage 4c on Expanse in all: 205.1 SU** of the workflow's 900.

  | Part | SU |
  |---|---:|
  | Framework (`stage4c/framework/`) | 3.2 |
  | Development: dd | 24.0 |
  | Development: mp256 | 31.2 |
  | Development: exp1 | 26.3 |
  | Development: R7 | 54.3 |
  | Integration and gate (`stage4c/gate/`) | 66.1 |
  | **Stage 4c total** | **205.1** |

- **Session total on Expanse.** 685.6 SU through Stage 4b plus 205.1 for Stage 4c gives 890.7 SU; with symmetry
  (28.4) and canonical (about 2), about 921 core-hours of the 5,000 development cap.
- **Lustre.** 1,467,436 files of the user's 2,000,000 after the gate (shared with C63d); this export is 7,057 files and
  the gate evidence 67. Earlier exports of the developer branches (about 6,500 files each) remain under `$C8_DATA/pkg`.


## Stage 5: the G4c verifier's fixes and the export survey, 2026-10-05 [A-FLAG-1, A-FLAG-6, D9; G4c follow-ups]

Fix commit 5ddf8ee; details and evidence in `stage5/g4cfix/README.md`.

| Job | Where | Wall | Result |
|---|---|---|---|
| 54676839 `c8d2-s5-g4cfix` | `shared` 16, <NODE> | 10:57 | D2: defaults `99a51c1d…`/`1d2a2181…` (A-RPL-8), profile builds without overrides byte-identical to 5569c535dcfd's, override builds (mp256 ratio, exp1 range, dd) marked `"development":true` and refused by plan's checks; D1: `design.py rates --rule one-step` on J-SWEEP-1 reproduces the Stage-4c map and r7_spec.py's record; D3: the F2 seeds registered (7 → 56); D6 survey |

- **Allocation.** 2.92 SU (`stage5/g4cfix/sacct.txt`). One shared job, admitted under H7E-R; no job of this agent is
  live.
- **Lustre and the export pruning (D6).** Before: 39 exports with 242,594 entries in `pkg/` (per export in
  `stage5/g4cfix/README.md`); the user's count 1,524,608 of 2,000,000 (C63d included); this agent's new entries
  7,944 (the work directory of the check, its evidence and log).
  - Kept (9 exports, 55,317 entries): b4273c59e911, c17688158e2b, 7aac898add43, b47b0082c0f7, 5569c535dcfd, and,
    because later jobs read their baseline directory or executable, 138d4866c7e4, bc0bedc3d72b, 6bdc081cc8bd and
    241baca924d2.
  - To delete (30 exports, 187,277 entries, every one `git archive` of a recorded commit plus builds): 00c675d3cfe9,
    10b19d9a0ae3, 18c216e27e4c, 1d25d9e1deec, 2c8b28f46538, 36043bbc2117, 3e9d66490893, 4eb79cde99e6, 6eedd3f55b65,
    7607a9fc2777, 81aa9770e6fe, 8e4ad72661ac, 908bd9de0265, 913e56a97a6b, 964f39d13aec, 9870a68535a7, ab2a822a10e5,
    add273b9ecc7, b4ad81beea16, bb1a3c945482, cb401889a37f, d0f0e05a4c21, d46e7360fe88, d98e3a10c6e9, dd171982f690,
    e7ef98d90487, ebf01f62e833, ec2b0583b6da, ef705e395924, f327bb910151; and the work directory
    `work/g4cfix-5ddf8eef4c29` (7,907 entries).
  - **Not deleted** in this job: the session's permission classifier refused the deletion (irreversible), so the
    after-count equals the before-count. **Later deleted** (29 of the 30) by the host with the user's approval on
    2026-10-05; `pkg/d46e7360fe88` kept (below, "Stage 5 fix round, close-out and the export deletion").

## Stage 5 on Expanse: J-EXP-1..4, the zen2 GMP_PREFIX gates, J-SWEEP-2E and the Expanse pilot plan, 2026-10-05 [A-EXP-3, A-PERF-5, J-PIL-1E]

Details, evidence and the pilot's submit line: `stage5/exp/README.md`; numbers recomputed by
`stage5/exp/scripts/s5e_summary.py` into `stage5/exp/s5e_summary.json`. Export 07ff5c1975e5 (5d7586e plus the job
scripts; `setup/export_check_07ff5c1975e5.json`, 7,195 files equal), L8 packs re-hashed and hard-linked from
7aac898add43. Exact default path in every job (D1); `GMP_PREFIX` only in the zen2 job.

| Job | Where | Wall | Result |
|---|---|---:|---|
| 54676864 `c8d2-s5e-exp1` (J-EXP-1) | debug, exclusive | 6:09 | Build PASS (default `99a51c1d…`/`1d2a2181…`, Boost 1_77); `make test` FAIL in `unit_orchestration.py` group `lanes` |
| 54676898 `c8d2-s5e-exp1b` | debug, exclusive | 17:17 | Every `make test` command to the end: 14 of 16 pass; `lanes` (whole-node affinity) and `test_numerics_flags.py` `f2_profile` (NumPy 2 `repr`) fail; `lanes` passes on 16 CPUs |
| 54676921, 54676926 | shared 16 | 0:16, 0:52 | Diagnosis of `f2_profile`; the one-line fix checked in a copy (8/8) |
| 54676897 `c8d2-s5e-prep` | shared 16 | 5:38 | Test campaigns t2–t4 planned; 22 of t2's 24 indices run |
| 54676902 + 54676904 (J-EXP-2) | shared | 0:19; 0:13 | 2-element array (`--threads 32`, 62G) and the shared merge with assembly: complete, verified |
| 54676924 + 54676925 (J-EXP-3) | debug, 8 × 16 lanes | 4:11; 0:10 | Lane worker and merge: t3 complete, verified |
| 54676911 + 54676912 (J-EXP-4) | compute, 16 × 8 lanes | 4:14; 0:15 | Mandatory compute lane job, k = 2 under the slot rule (snapshot in the log): t4 complete, verified |
| 54676895 `c8d2-s5e-zen2` | compute, exclusive | 9:20 | `GMP_PREFIX=zen2`: full J-VAL-2, G-BK8, forced tiers, L8 sample against the default worker: all exact, records equal to the default build's; cleared on Expanse |
| 54676896, 54676908 `c8d2-s5e-sweep2` (J-SWEEP-2E) | compute, exclusive | 5:07, 4:54 | The final-binary sweep; the second (<NODE>) is `cost_models/gmp_expanse_amd_c8.json`; the first shows <NODE> 14% slow on L7/L8 |
| 54676927 `c8d2-s5e-pilotplan` (J-PIL-1E) | shared 8 | 1:27 | The Expanse pilot planned: 36 indices, 170.3 core-hours, about 205 SU on one node; not submitted |

- **A-PERF-5** (kernel seconds, all graphs): ×1.390 overall; free ×1.443, power ×1.262; L8 ×1.444 / ×1.261, L7 ×1.413
  / ×1.283, L3–L4 ×1.01–1.02.
- **Seeds.** Six new seeds (three test campaigns, two sweeps, the pilot), each checked against both logs before use,
  are in the Expanse log, symmetry's log (one append from here, the rest already synced) and the mirror.
- **Allocation.** 112.3 SU (`stage5/exp/sacct.txt`); 54676866–68 were cancelled while pending. Stage 5 on Expanse so
  far: 115.2 SU (with the G4c-fix job). Session total on Expanse: 1,005.9 SU; with symmetry's development 28.4 and
  canonical's about 2, about 1,036 core-hours plus symmetry's Stage-5 use.
- **Lustre.** 1,524,790 → 1,531,024 files (C63d included); this agent's new entries about 12,600 (the export, kept for
  the pilot, 7,844).

## Stage 5 fix round, close-out and the export deletion, 2026-10-05

**Site rule (user, 2026-10-05):** "symmetry is back, so for the moment only use expanse if symmetry is not enough".
New compute runs on symmetry; Expanse keeps only its own items.

| Item | Where | Status (2026-10-05) | Evidence |
|---|---|---|---|
| G5 fixes F1-F9 (86e15f4, merged as e7e6589) on Expanse: export of 2b3a923, J-EXP-1 rerun, dd+mp256 gate | planned for Expanse | **Blocked, nothing submitted** (login-node Lustre hung from about 15:16 UTC; then C63d reported a scheduled maintenance until 12:00 PDT) | `stage5/fix/README.md`, `stage5/fix/probes.txt` |
| F1-F10 and F12 re-validated | symmetry | **PASS** (fix round: F1-F8; F9 PARTIAL until F12; close-out: A-ORC-13 PASS with d5dfd38, J-VAL-1 PASS) | `../symmetry_2026-10-c8/stage5/fix/README.md`, `../symmetry_2026-10-c8/stage5/close/README.md` |
| The user-required `dd+mp256` J-FLAG gate | moved to symmetry | **PASS** (job 570210, GCC 11.4; F1/F2 equal this site's Stage-4c `dd+mp256+exp1` record 54673902; F4 ×2.530 there vs ×2.168 here). `stage5/fix/scripts/fxe_flag.slurm` is not to be submitted | `../symmetry_2026-10-c8/stage5/close/README.md` |
| F11 (`design.py` split) | Mac | **Fixed** (r from the smallest multiplier) with route (b) for `dd+mp256` | `docs/DESIGN.md`, `../symmetry_2026-10-c8/stage5/pre6/README.md` |
| J-EXP-1 rerun (A-EXP-3) | Expanse only | **Partial**, job 54681003 on `debug`, export 99bbfdd. The build passed: A-RPL-8 decimal `99a51c1d…` and gmp `1d2a2181…`, Boost 1_77 everywhere, `check_venv --strict`. In `make test`, `validate` passed and 12 `unit_orchestration` groups passed. The job was then cancelled because Expanse's Lustre was failing (node drains, build 430 s against 33 s). F1, F3 and F4 in `make test` are still owed. 44.4 SU | `pre6/README.md` |
| Two-log seed sync | Expanse login node | **Done** (2026-10-05, 18:43 and 19:53 UTC). The 3 pending seeds were merged, then the 9 pre-Stage-6 seeds added on symmetry. Expanse's log now holds the same 90 seeds as symmetry's | `pre6/README.md`, `pre6/seeds/` |
| Deletion of the obsolete exports (D6) | Expanse login node | **Done** by the host, user-approved: 29 of 30 | below |

**The export deletion.** The user approved deleting the 30 obsolete exports listed under "Stage 5: the G4c verifier's
fixes" above ("Delete the 30"). The host deleted 29 of them on 2026-10-05 at 10:40 PDT, after re-grepping all evidence
for references to each. **`pkg/d46e7360fe88` is kept:** the completed gate job 54669708 read it as its B2f source tree,
and the approval covered only unreferenced exports. Lustre (the user's file count, C63d included) went from
**1,651,026 to 1,474,822 files**. This package's records show no new Expanse export after 07ff5c1975e5 (the
fix round's export of 2b3a923 never ran).

**Before Stage 6 (2026-10-05, `pre6/`).**
- One new export, `pkg/99bbfddd0719` (`setup/export_check_99bbfddd0719.json`: 8,268 files equal).
- The two-log seed sync is done.
- The J-EXP-1 rerun is partial; `make test` is owed once Lustre recovers. 44.4 SU.
