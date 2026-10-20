# Stage-6 fix round 4, group G1: the native harness (2026-10-06)

Branch `fx4-g1` from 945e526 (the tree inspected in round 4), on the Mac (arm64, anaconda Python 3.10.11),
`C8_ALLOW_NO_L8=1`. Items W1, W2, W3 and W22 of `LRI_C8_D2_HPC_loop/artifacts/s6_fix4_dispositions.md` (findings
S6A4-01, S6A4-02, S6A4-03 and the host residual on `tests/thread_identity.py`). This is the last fix round.

**No `src/` change and no cluster job.** No native argument, input or numerics changed, so the default and profile
binaries stay byte-identical (decimal a18ce425, gmp 7741f733, dd+mp256 a46f3060). Every stored record of these
tools in `benchmarks/` is still accepted where it was acceptance evidence.

## The fixes

### W1 (S6A4-01): the quad differential's acceptance threshold is fixed

- `tests/quad_differential.py` no longer has `--min-pairs`. `MIN_PAIRS = 10**9` (PLAN R3a) is a constant.
- The gates are now the correctness gates only: mismatches, edges, first mismatches, injection and sanitizer.
- The size and scope of the run are `coverage(record)`'s. It recomputes from the record, never from the arguments or
  the record's own gates:
  - the ranges, measured on the six default blocks (at least 16 graphs and 256 points each, block order);
  - the add/sub and mul windows, recomputed from those ranges with `window()`, which must equal both the recorded
    windows and the kernel windows the differential run used;
  - per operation, at least `MIN_PAIRS` random pairs over the four streams (each non-empty, summing to the total) and
    every edge category non-empty;
  - no mismatch and no first mismatch;
  - the injection run of 2^22 pairs, detected for every operation;
  - the sanitizer run, on at least 2^22 random pairs and on every edge pair.
- Status and exit code:

  | Status | Meaning | Exit |
  |---|---|---|
  | `passed` | every gate passes and the coverage is complete | 0 |
  | `failed` | a gate failed | 1 |
  | `development run (...)` | the gates pass but the coverage is incomplete; the status names what is missing | 3 |

- Consumers check a record with `--check RECORD` (exit 0 only for acceptance evidence) or with `coverage()`.
- All five stored records pass `--check`.

### W2 (S6A4-02): G-BK8 compares every row field

- `tests/validate.py compare(ref, new, backend, tails=False)` now covers every field:
  - **Rows with mp > 0:** `max_abs` must be within 1e-30 normalized, as the values already were.
  - **Tail fields, with `tails=True` (G-BK8):**
    - mp = 0: exact.
    - mp > 0: every `tail_top` entry and `tail_sum` within 1e-30 normalized, and equal widths.
    - `tail_argmax` must be equal, or differ only at a documented near tie (`TIE_POLICY`: in both rows the two
      largest |t| agree within the tolerance). Near ties are counted in `tail_argmax_ties`.
    - Every row's tails must be well formed (`tail_shape`): min(16, points) descending finite values and an argmax
      inside [begin, end).
  - **Field coverage:** a field no rule covers fails the batch, as does a missing field.
  - A G-REF reference (the research worker) must carry no tail fields.
  - The common header fields must be equal.
- G-BK8 records now carry `row_rule: c8-d2-bk8-row-rule-2`, the new difference fields and `tie_policy`.
- Same class, fixed in the same round:
  - `compare_exact` (G-C7) and `compare_jet` (G-JET) refuse an uncovered field.
  - A-RPL-6's chunk merge (`chunk_merge`, used by `invariance`) now also requires that the chunks tile the task, that
    quad and mp add up, and that the largest chunk `max_abs` equals the whole task's.

### Acceptance for every validate.py record (the W1/W22 class)

- `validate.coverage(record, gate)` judges a record per gate: J-VAL-1, J-VAL-2, G-BK8, G-L8SELF and A-IN-6b. It checks
  the scope, the sizes and the parts. A skipped part, such as diagnostics, is no evidence.
- `validate.py --check RECORD --gate NAME` runs the same check from the command line.
- Every record lists its gates in `acceptance`.
- On the stored records:
  - every symmetry J-VAL-1 record and every J-VAL-2, G-L8SELF and A-IN-6b record passes;
  - every stored G-BK8 record passes only with `row_rule=False`, because each predates W2;
  - seven Expanse development J-VAL-1 records with a skipped diagnostic part are refused, although their status says
    "passed".

### W22 (host residual): restricted thread-identity runs

- `tests/thread_identity.py` reports `passed` only when `coverage()` is complete. That requires:
  - both default workers (no `--executable`), each with both sectors;
  - for each block, 64 tasks × 256 points on 32 graphs, identical;
  - runs at exactly 1, 8, 16 and 64 threads plus the 8 × 8 lane split;
  - every observed team of the requested size, and `team_sizes_verified`.
- A restricted run (`--backends`, `--threads`, `--lanes` or `--lane-threads`) says `development run (...)` and exits
  3.
- A `--executable` run is a profile's F5 run (A-FLAG-3; `docs/NUMERICS.md` documents it). It is judged by
  `coverage(record, gate='F5')`: both sectors of that one executable, which must not be a default worker, with the same
  sizes, threads, lanes and teams. Its status is `passed (F5 of an opt-in profile executable; not A-RPL-6 evidence)`,
  never plain `passed`, so a consumer that checks for `passed` cannot take it for A-RPL-6 evidence. It is checked with
  `--check RECORD --gate F5`.
- `--check RECORD [--gate F5]` and `main(argv)` are new.
- `coverage(record, teams=False)` skips only the team conditions. It is for records made before X3.
- Stored records:
  - The post-X3 symmetry records pass.
  - The pre-X3 ones pass only with `teams=False`.
  - The stored s6fix1 `thread_identity_omp_env.json` (gmp only, status `passed`) is refused. It is the residual on a
    real record.

### Consumers

- `benchmarks/expanse_2026-10-c8/stage4b/final/scripts/summarize_final.py` now judges each record by its status
  **and** the recomputed coverage, using these verdict functions:
  - `quad_differential_verdict`
  - `thread_identity_verdict` (`teams=False`: pre-X3 records)
  - `validate_verdict`, for J-VAL-2, G-BK8 (`row_rule=False`: pre-W2 records), G-L8SELF and A-IN-6b
  - `forced_tiers_verdict` (Z2)
- Its stored records still give `passed: true`, and edited ones are FAILED.

### W3 (S6A4-03): relative paths in the reproduced build

- Every build record now names its `build_directory`: the working directory make compiled in.
- `reproduce_worker` keeps the meaning of the relative words of the record's command and of the include environment:
  - The words covered are a relative compiler, `-I`, `-isystem`, `-L`, a link input, `CPATH`, `LIBRARY_PATH` and so
    on, and `PATH` when the compiler is named without `/`.
  - The words are **not** rewritten. A real compiler embeds the include path it found, for example in a header's
    `__FILE__`, so rewriting would change the bytes. The test shows this with the host compiler: `-I../inc` gives
    `../inc/h.hpp`, and the absolute `-I` gives the absolute path.
  - Instead, the snapshot is nested below private parent directories, as deep as the words climb (`snapshot_root`).
  - Each name a relative word reaches outside the snapshot's own `src/` and tool sources becomes a symlink to the same
    name under the build directory (`mirror`).
  - The byte-identity requirement is unchanged.
- A record without `build_directory` (written before this round) is reproduced only when it holds no relative word.
- The precision tool is compiled in the caller's working directory. So when the make flags or the include environment
  hold relative words, the binding is refused unless the caller runs in the worker's build directory. Nothing is
  compiled before the refusal.
- Same class, not in G1's files: `tests/numerics_flags.py` (`compile_in`/`bind`, X2) runs the record's command in its
  own snapshot. This is listed as a cross-group issue.

## Evidence

- **Before the fix:** `demo_before_945e526.json`. `fx4g1_demo.py` was run on a git archive of 945e526 with the fx4-g1
  `tests/test_native_guards.py` and `tests/test_gmp_binding.py` overlaid. It shows all four defects:

  | Item | On 945e526 |
  |---|---|
  | W1 | the finding's `--pairs 4 --min-pairs 4 --ubsan-pairs 4 --no-ranges` run says `passed`, exit 0 |
  | W2 | G-BK8 accepts a tampered `max_abs`, `tail_top` entry and `tail_argmax` on an mp>0 row |
  | W22 | `--backends gmp` says `passed` |
  | W3 | a worker built with `CPPFLAGS=-I../boost_rel` is refused as stale from its own build directory |

  `demo_after.json` is the same driver on this tree: no defect.
- The new tests on 945e526 (same overlay) all fail:
  - `test_native_guards --only quad_coverage,thread_coverage,bk8_compare,summaries`;
  - `test_gmp_binding --only relative_paths`.
- **Suites on this tree:** see `suite_exits.txt` and each JSON record. Every suite exits 0 except `test_omp_launch`
  without the cross-group patch below.

  | Suite | What it covers |
  |---|---|
  | `test_native_guards` | hooks, loader, syntax, and the new quad_coverage, thread_coverage, bk8_compare, summaries |
  | `test_gmp_binding` | 15 tests, `relative_paths` new |
  | `test_numerics_flags` | |
  | `test_gmp_prefix` | |
  | `test_profiling` | |
  | `sanitize --capture-check` | |
  | `ast_scan` | tools, gen and tests |
  | `unit_orchestration` | |
  | `test_pipeline` | |

- **`test_omp_launch` needs a cross-group patch.** Its stand-in worker writes rows without `max_abs`, a field every
  real worker row has, and the strict `chunk_merge` refuses them.
  - Without the patch: `test_omp_launch_without_patch.json` (invariance fails with KeyError `max_abs`).
  - With `LRI_C8_D2_HPC_loop/artifacts/s6_fix4_g1_test_omp_launch.patch` applied: `test_omp_launch_with_g1_patch.json`
    (5/5).
