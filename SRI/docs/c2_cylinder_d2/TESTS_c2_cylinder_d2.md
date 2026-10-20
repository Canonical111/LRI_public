# Tests: c2_cylinder_d2 (simulated export, 2026-10-15)

## Setup

The simulated export used the repository's `.maintainer/export.py`, copied into a scratch `sri_sim/c2_cylinder_d2/.maintainer/`.
- `source_root` was `<PROJECT>`, with the real `global_exclude`.
- The entries were those of `maint/entries_c2_cylinder_d2.json` (the commit 98e1935, the `outputs/` snapshot, the
  `public` overlay), plus `SRI/verify` and `SRI/results` from the SRI patches.

The exported package has 295 files, 78 MB unpacked:

| Measure | Size |
|---|---|
| `tar czf` of `SRI/code/c2_cylinder_d2` | 16.4 MB |
| git pack (`git repack -adq --window=50 --depth=50`) | 28.7 MiB |
| git pack without `outputs/` | 2.5 MiB |

Paths are clean: no case collisions, no symlinks, and no file over 2 MB.

The tarball of the exported `SRI/` tree was copied
to `<SCRATCH>/sri_test/c2_cylinder_d2/` on symmetry and unpacked in each job into node-local storage,
`/local1/<USER>/<job>/SRI` (a path containing "local1").
- Interpreter: the acceptance venv (Python 3.12.9, numpy 2.3.5, scipy 1.17.1, mpmath 1.3.0, sympy 1.14.0,
  matplotlib 3.11.2), used read-only.
- Each job ran `make -f public.mk test`, `replay` and `replay-full` with `PY=<venv python>` from
  `SRI/code/c2_cylinder_d2/`.

## Final runs

The final tree (tarball sha256 `b3330847...`) adds the unlisted-file rule to the verifier and its selftest case. It
was tested in job 575643: sharedq, Intel Xeon Gold 6148, same commands. Job 575636 gave the same results on a tarball
(`dc4c1f14...`) that also held a stray `public/__pycache__` from a local run; the verifier ignores that directory.
- test PASS in 170 s: selftest 8 PASS, including the unlisted-file rule (9 of 9 cases); suites 5 PASS with 5 stated
  skips.
- replay PASS in 3 s (28 PASS, 5 INFO).
- replay-full PASS in 10 s (10 PASS, 1 INFO).

The runs below used the previous tree (sha256 `cba7da59...`). It differs only in `public/verify_manifest_public.py` and
`public/selftest_c2cyl.py`.

| Job | Partition, CPU | test | replay | replay-full |
|---|---|---|---|---|
| 575620 | sharedq, Intel Xeon Gold 6148 | PASS, 182 s (selftest 7 PASS; suites 5 PASS, 5 stated skips) | PASS, 3 s (28 PASS, 5 INFO) | PASS, 12 s (10 PASS, 1 INFO) |
| 575612 | amdpreq (requeue), AMD EPYC 7532 | PASS, 152 s | PASS, 3 s | PASS, 9 s |
| 575621 | sharedq, Intel; tree with a simulated scrub (below) | PASS, 204 s | PASS, 3 s | PASS, 12 s |

Suites in the final runs:

| Suite | Tests run | Skipped |
|---|---|---|
| `test_continuum` | 36 (44-58 s) | 2: 'needs the git checkout (pristine commit 474487c)', the A6-2 same-platform check and IR2-003 |
| `test_cluster` | 9 | none |
| `test_sitekit` | 84 (95-110 s) | 3: 'needs the git checkout', the `make_tarball.sh` tests |
| `test_expanse` | 4 | none |
| `test_symmetry` | 7 | none |

The GNU-only sitekit tests ran on Linux. No scheduler was contacted.

`replay-full` on the acceptance machines. The rerun took 6-8 s.
- Inputs: 160 files with their sha256, identical to the shipped `meta.inputs_sha256`.
- Discrete leaves: all equal (22841 + 8096 + 405).
- Bit-identical floats: 12203 of 27970 on Intel, 12211 on AMD.
- Tier A, the chain to the quoted number: largest difference 1.1e-8, a joint-variant h0 and a per-order ratio.
- Tier B, the fit diagnostics: within 1e-6 + 1e-3 |x|.
- REPORT.md: 77-79 printed numbers differ, all within one unit of their last digit.
- Rerun result: C2 = -4.0670497633 +- 0.0023580131 (Intel) and +- 0.0023580132 (AMD). The shipped value is
  -4.0670497634 +- 0.0023580136.

On the production platform the rerun is bit-identical. This was checked on the authors' personal desktop, with
the interpreter of the production run (macOS arm64, CPython 3.13.5, numpy 2.3.5), on the simulated export, a few
seconds of CPU: 27970 of 27970 floats are identical and REPORT.md is identical apart from the run-description line.

## Simulated scrub (jobs 575648 and 575621)

Job 575648 (sharedq, Intel Xeon Gold 6148) ran the final tree with the public repository's substitutions applied.
Each substitution was applied to every file that is listed only in `MANIFEST.sha256` and carries a private string, a
node name or the Expanse account. A test-only `public/SCRUBBED.txt` listed those files.
- `<HOME>` became `<PROJECT>`, and the cluster user names became `<USER>`.
- The compute and login node names of symmetry and Expanse became `<NODE>`.
- The one account rule (the Expanse allocation name -> "<ACCOUNT>") was applied to all eight account files:
  `cluster/expanse/README.md`, `cluster/expanse/profile.json`, `cluster/expanse/test_expanse.py`,
  `cluster/sitekit/README.md`, `cluster/sitekit/submit.py`, `cluster/sitekit/test_sitekit.py`,
  `code/continuum/aux_job.sbatch` and `provenance/REVISION_NOTES.md`.

  None of the eight is hash-bound: no task or job `SHA256SUMS`, record, receipt or record-bound list carries their
  sha256. After the substitution no account name is left in the tree.
- Also changed:
  - the three result JSONs of the generation;
  - `README.md`, `cluster/symmetry/{README.md, profile.json, setup_env.sh}`;
  - the not-exported paths in `MANIFEST.sha256` (<NODE>).

  16 files changed in all, 15 of them manifest-listed.

Result of 575648:
- test PASS in 176 s. The selftest gave 8 PASS; the verifier reported 113 match, 15 scrubbed, 0 bad and 0 unlisted.
  The suites gave 5 PASS with the 5 stated skips, among them test_expanse 4 and test_sitekit 84, which see
  `<ACCOUNT>` in both the profile and the tests.
- replay PASS in 4 s (28 PASS).
- replay-full PASS in 12 s (10 PASS).

The replays matched `<NODE>` and the deviation-record key by pattern.

Job 575621 (the previous tree; the user-name and node-name substitutions only, without the account rule) also passed
all targets.

## Earlier iterations

| Job | Result | Fix |
|---|---|---|
| 575601 (Intel) | test PASS, replay PASS; replay-full FAIL | The first comparison applied one 1e-9 relative tolerance to every float. Cross-platform last-digit differences of ill-conditioned fit diagnostics and differences of nearly equal numbers fell outside it. Replaced by the tiered rule. |
| 575611 (Intel) | replay-full FAIL on 2 tier-A leaves at 1.1e-8, with tier A at 1e-8 | Tier A set to 1e-7, after these measurements (margin about 10). |

On the authors' personal desktop, two more FAILs were found and fixed. Each run took seconds of CPU.
- The selftest needed `expanse_job.json` (the receipt name of the first Expanse pilot) as a not-exported receipt.
- Tier B needed an absolute floor of 1e-6, for the prefix shift of the mixed limits (about 1e-8 absolute noise on
  limits of about 1e4).

Logs and result tables: `<SCRATCH>/sri_test/c2_cylinder_d2/slurm_<job>.out` and `res_<job>/`.
