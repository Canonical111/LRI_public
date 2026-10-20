# Stage-6 fix round 3, group G2: orchestration (2026-10-06)

Branch `fx3-g2` from a42cfb7 (the tree inspected in round 3), on the Mac (arm64, anaconda Python 3.10, numpy, scipy),
`C8_ALLOW_NO_L8=1`. Items Z3 (the `production.py` side), Z5, Z6, Z7, Z11, Z13 and Z15 of
`LRI_C8_D2_HPC_loop/artifacts/s6_fix3_dispositions.md` (findings S6A3-03, S6R3-B-01, S6-C-R3-01, S6-C-R3-02,
S6D-R3-04, S6E-R3-01, S6R3-F-02). No `src/` change and no cluster job. No native argument, input or numerics changed:
valid-input outputs are bit-identical by construction.

## The fixes

- **Z3 (S6A3-03): a non-test plan needs a valid, matching build record.** `production.read_build_record(exe, backend,
  numerics, required)`. For a NON-test plan, a missing or unreadable record refuses the plan. So does a record that is
  not a `c8-d2-build-record-1` record of this build: its executable name, sha256, backend and NUMERICS must be the
  plan's, its diagnostic kind none and `required_flags_present` true. Every plan, as before, refuses a development build
  (parameter overrides or a C8_NX_* hook in the recorded compiler options, or `development`). A test-only plan keeps a
  missing record with the warning. The compile-time refusal of injected C8_NX_* hooks is G1's half of Z3.
- **Z5 (S6R3-B-01): `gen/gates.py` check_gfile parses G-file integers as the native loader does.** Every mask must be a
  plain ASCII decimal in [0, 2^E) of L edges, ascending. Before, a negated mask passed, because `bin(-m)` has the
  popcount of m. Every term entry must be a plain decimal (an optional '-') within the loader's int. Python's `int()`
  also takes '0_7', '+7' and non-ASCII digits.
- **Z6 (S6-C-R3-01): `common.fingerprint` accounts for every ldd line.** The loader prints an object requested by an
  absolute path (an `LD_PRELOAD` library, which `omp_child_env` keeps; a dependency named by path) as
  `/path (0x...)`, without `=>`. Such an entry is now hashed and keyed by its path, so it is part of the runtime
  identity. The same form naming the ELF interpreter (PT_INTERP, by path or realpath) is the interpreter, hashed once.
  The vDSO (`linux-vdso.so.1 (0x...)`, also `linux-gate`) is left out, as are a static executable's `statically linked`
  and `not a dynamic executable`. Any other line of a successful probe becomes an unexplained entry without a sha256,
  which `fingerprint_problems` refuses for a dynamic ELF worker (claim exit 64). The identity of an ordinary node
  (vDSO, `=>` libraries, the interpreter line) is unchanged.
- **Z7 (S6-C-R3-02): sbatch's memory precedence, and a preflight of every job.** `slurm_submit.effective_options`
  follows Slurm's `_validate_memory_options`. A memory option of the job's command line or script directives replaces
  an inherited `SBATCH_MEM_PER_CPU` / `SBATCH_MEM_PER_NODE`, and `sbatch_env` removes those variables for such a job.
  Two memory kinds among the directives and the command line are refused (64), as sbatch refuses them. An example is a
  user `--mem-per-cpu` against the array script's `#SBATCH --mem`. So are two inherited ones when neither sets memory.
  `Context.preflight` builds and checks every job of a submission before the first sbatch: the arrays and merge of
  `submit` and `resubmit`, the lane workers and merge of `lanes N`, and a window's arrays. A contract that only the
  merge breaks now refuses with nothing submitted. The job arguments are built by `work_args`, `lane_args` and
  `merge_args`, shared by the preflight and the submission.
- **Z11 (S6D-R3-04): `seeds.py init` under the lock, never overwriting.** `seeds.init` holds `<log>.lock` (the lock of
  add and merge) and re-checks under it. It publishes with a hard link (`common.publish`), which never replaces a file,
  so a log that appears meanwhile refuses (64). `seeds.log_lock` is the one lock constructor.
- **Z13 (S6E-R3-01): unconditional cleanup in `tests/unit_orchestration.py`.** `Owned` registers a case's direct
  children (started with `start_new_session=True`), the strings unique to it (its campaign or scratch path, which find
  the production runs that `lanes.py` starts in sessions of their own and their native workers) and its FIFOs. On every
  exit path it first appends the owned processes to the failure message (evidence), then kills every owned process
  group and process until none is left, reaps the children, closes their pipes, and releases (non-blocking) and removes
  each FIFO. `fifo_go` releases the fake sbatch without an `open()` that could block forever. It is used in the
  campaign-lock and site-lock cases, the lane SIGTERM case, and the signal cases, where the evidence is taken inside the
  scope. The harness check `z13_cleanup` fails on purpose before a FIFO release and during lane startup. It also shows
  the two old patterns leaking:
  - a Popen without a scope leaves the submission blocked in the fake sbatch;
  - killing only the worker's process group leaves the production runs and their natives running.
- **Z15 (S6R3-F-02): a non-test plan registers its own seed.** The registration log is the first
  `--forbid-seeds-from`, which must be a `tools/seeds.py` log ($C8_SEEDS in every documented command). This is checked
  before anything is created. After the staging directory is built, `production.register_seed` (via `seeds.register`)
  does four things under the log's lock:
  1. re-reads the log;
  2. re-checks the seed against it and the plan's other forbidden sources, so a seed registered meanwhile is refused
     and nothing is published;
  3. appends (seed, source = the campaign directory, as `seeds.py add RUN` writes it);
  4. publishes the campaign, still holding the lock.

  A failed publication leaves the seed registered. The manifest and the plan's JSON name `seed_log`. `slurm/plan.sh`'s
  later `seeds.py add RUN` finds the seed present. Test-only plans register nothing, unchanged.

## Tests (each fails on a42cfb7's tools and passes here)

| Item | Test | On a42cfb7 (`before_a42cfb7/`) |
|---|---|---|
| Z3 | unit_orchestration `z3_build_record`: 13 refused records, valid accepted, test-only warning kept | FAIL: the plan without a record was published |
| Z5 | gen/test_regress.py `gfile_gate_checks` (7 checks) | 5 FAIL: negated mask, '0_m', '+m', 2^31, '1_0' accepted |
| Z6 | unit_orchestration `z6_ldd_absolute` (stubbed ldd; end-to-end claim refused 64) | FAIL: the preload entry was dropped |
| Z7 | unit_orchestration `z7_mem_env` (3 env combinations x submit and lanes; mutually exclusive; preflight x 3) | FAIL: arrays submitted, then the merge refused (64) |
| Z11 | unit_orchestration `z11_seeds_init` (lock held; post-check race; plain init) | FAIL: init wrote the log while the lock was held |
| Z13 | unit_orchestration `z13_cleanup`, plus the converted cases | (harness code; the test shows the old patterns leaking) |
| Z15 | unit_orchestration `z15_plan_seed` (registration, present, refusals, two lock interleavings, test-only) | FAIL: no entry in the log |

A real Z13 instance was on this Mac during the round. A `slurm_submit.py resubmit` and its fake sbatch, under
`c8d2_orch_8_hcv5p2/slurm_arrays`, had been blocked on a FIFO for about 2 days 7 hours, reparented to launchd, with
their temporary directory gone. They were left untouched.

## Mac suites (`make test-python` lines, records in this folder)

`make -k test-python OUTPUT=...` (`make_test_python.log`) ran check_venv, unit_orchestration and test_pipeline, then
stopped the recipe at test_pipeline's failure. The remaining lines of the recipe ran one by one
(`make_test_python_rest.log`).

| Suite | Result |
|---|---|
| `tests/check_venv.py` | passed |
| `tests/unit_orchestration.py` | 66 groups, 78 tests passed (6 new groups) |
| `tests/test_pipeline.py` | parts 1 and 2 passed (24 PASS lines); part 3 stopped at its first non-test plan (below) |
| `tests/ast_scan.py` (tools; gen and tests) | 0 findings over 27 and 46 files |
| `gen/test_regress.py` | 97/97 (7 new Z5 checks) |
| `gen/test_handoff_inventory.py` | 17/17 |
| `tests/merge_scale.py --rows 20000` | passed |
| `tests/check_vendored.py` | 36/36 |
| `tests/vendored_isolated.py` | 10/10 |
| `tests/test_delivery_verifier.py` | passed |
| `tests/check_inputs.py` | 23/23 |
| `tests/test_profiling.py` | passed |
| `tests/test_gmp_prefix.py` | passed |
| `tests/test_gmp_binding.py` | 10/10 |
| `tests/test_omp_launch.py` | 5/5 |
| `tests/test_numerics_flags.py` | 11/11 |
| `tests/test_dd_profile.py` | 8/8 |
| `tests/sanitize.py --capture-check` | passed |

`tests/test_pipeline.py` part 3 is a cross-group file, not G2's. Its non-test plans run the scratch package's fake
worker, which has no build record (Z3). Two refusal cases also reuse the seed of an accepted plan, which that plan now
registers (Z15). The patch
`LRI_C8_D2_HPC_loop/artifacts/s6_fix3_g2_test_pipeline.patch` (59 lines) fixes both:
- fake build records for the package's fake workers and the profile copies;
- the record rewritten in the "another build" case;
- fresh seeds for the refusals after an accepted plan.

With it, part 3 passes on these tools (`test_pipeline_part3_with_cross_group_patch.json`).

`tests/ast_scan.py` (tools, and gen + tests): 0 findings. `tools/verify_delivery.py --write` and then `--strict` ran
before the commit.

## Owed on symmetry (Verify phase)

- The real worker's fingerprint on the amdq nodes must show no unexplained ldd line (the J-VAL-1 A-ORC-13 real claim
  covers one node; the ldd survey owed before the pilot covers the rest).
- A submission with `SBATCH_MEM_PER_CPU` inherited: one drill-mode `submit.sh --lanes 1` (the merge is accepted).
