# Stage-6 fix round 2, group G4: lambda and comprehension scopes, and the atomic-plan test (2026-10-06)

Branch `fx2-g4` from 2ae3db7 (the tree inspected in round 2), on the Mac (arm64, anaconda Python 3.10.11),
`C8_ALLOW_NO_L8=1 OPENBLAS_NUM_THREADS=1`. Items Y14 and Y15 of `LRI_C8_D2_HPC_loop/artifacts/s6_fix2_dispositions.md`
(findings S6E-R2-02 and S6E-R2-03). Only `tests/ast_scan.py` and `test_atomic_plan` in `tests/unit_orchestration.py`
changed, plus this folder. No `src/` or `tools/` change and no cluster job, so the default path, every plan and every
number are unchanged.

## The fixes

- **Y14 (S6E-R2-02), `tests/ast_scan.py`.** `unbound()` used to skip every `ast.Lambda`, and `Flow.expr` skipped lambda
  bodies, so `def f(): return (lambda: (x, (x := 1)))()` was not reported. Each lambda is now analysed as its own
  scope. Its locals are its parameters plus the walrus targets of its body, including those in a comprehension there
  and in the defaults of a nested lambda. The body is one expression and is checked in evaluation order. This covers
  lambdas at every level: in functions, in comprehensions, at module level and in class bodies.
- **The same class, found while fixing (no finding id).** These are the other scopes the analysis skipped or merged
  into the enclosing scope:
  - **A comprehension is its own scope.** Its first iterable runs in the enclosing scope, and its targets are its own
    locals. A target read before the clause that binds it raises `UnboundLocalError`; that read can be in an earlier
    condition (`[x for _ in s if x for x in t]`) or a later iterable (`for y in y`). This holds even when the
    enclosing function has bound the same name. The old analyser checked targets against the enclosing function and
    missed all of these.
  - **Attribute and subscript targets.** A comprehension target like `a[0]` now loads its base (`a`) and its index.
  - **Comprehensions no function flow reaches.** A comprehension at module level, in a class body (also one nested in
    a function), or in the decorators, defaults or bases evaluated there is now checked for its own targets.
  - **Walrus bindings inside lambdas.** `LocalNames` used to treat a walrus inside a lambda body inside a
    comprehension as a binding of the enclosing function. That produced false reports (a global read in that function
    was flagged). Such a walrus binds the lambda. A walrus in a lambda's defaults there still binds the function.
- **Y15 (S6E-R2-03), `test_atomic_plan`.** The old test had three gaps. It never required that its polling had seen
  the write phase. It never checked that the child was alive or that SIGKILL killed it. It then certified recovery
  with `E.small`, a different and smaller plan. The new test works as follows:
  - **The child.** It runs in its own session, with its output in a log file rather than a pipe.
  - **Looking at it.** The test looks at the child only while it is frozen. It sends SIGSTOP, waits with
    `waitpid(WUNTRACED)` until the child has stopped, and sends SIGCONT with 20 ms between looks. So a look cannot race
    the publishing rename.
  - **The kill.** SIGKILL goes only to a live, stopped child whose staging directory holds a group while the target
    does not exist. The child must die by SIGKILL and leave its staging directory.
  - **Immediate failures.** The test fails at once in three cases: the child exits before the write phase is seen,
    the target exists while the plan runs, or no write phase appears within 120 s.
  - **Cleanup.** On every failure path the child and its session are killed and reaped. macOS refuses `killpg` once
    only the exited, unreaped child is left (EPERM), so the test then signals the child itself.
  - **The rerun.** It uses the identical argv and must publish the whole campaign: `test_only`, `test_graphs` `all`,
    jobs, and the group directories equal to the manifest's groups.

## Before and after

`fx2g4_evidence.py` writes `evidence.json`. It needs the git checkout, because it reads 2ae3db7's files with
`git show`.

- **ast_scan self-test.** There are now 83 probes, 23 of them new. The current analyser passes all 83. The 2ae3db7
  analyser miscounts 16 of the new probes; these are the tests that fail before the fix:
  - Y14: `lambda_body_read_before_walrus`, `lambda_body_conditional_walrus`, `lambda_body_shadows_bound_outer`,
    `lambda_module_level`, `lambda_class_level` and `lambda_in_comprehension`;
  - same class: `lambda_body_walrus_in_comprehension_not_function_local` (a false report before),
    `comprehension_target_read_in_earlier_condition`, `comprehension_target_shadows_bound_outer`,
    `comprehension_target_read_in_later_iterable`, `generator_target_read_first`,
    `comprehension_subscript_target_loads_base`, `comprehension_module_level`, `comprehension_in_class_body_in_function`,
    `comprehension_in_class_bases_in_function` and `comprehension_in_default_at_module_level`.

  The 7 clean or already-found new probes pass with both analysers. Every new positive probe was run under Python
  3.10 and 3.14 and raises `UnboundLocalError` there.
- **test_atomic_plan against plan mutants.** Each test version is run in an isolated package copy (`pkgcopy`, as the
  suite does). The mutants change only the `--test-graphs all` plan, which is the one the test interrupts:

  | Mutant of `tools/production.py` | 2ae3db7 test | current test |
  |---|---|---|
  | unmodified | passes | passes |
  | dies_before_staging (raises before its staging directory) | **passes** (polls 120 s, signals a dead process, reruns a smaller plan) | fails in under 1 s: exited before the write phase |
  | fails_in_write_phase (staging and a group, 1 s, then raises) | **passes** (kills it, then reruns a different plan) | fails: the rerun of the same plan fails |
  | hangs_before_staging (sleeps an hour) | **passes** after 120 s | fails after 120 s: no write phase; the stopped child is killed |
  | publishes_in_place (control: builds in the target) | fails after 120 s | fails in under 1 s: target exists while the plan runs |

  After every run, `ps` shows no process of that run's plan.
- **Differential fuzz (`ast_scan_fuzz.py`).** This is the round-1 generator extended with the new scopes:
  - lambda bodies called in place, with the lambda-only names `p` and `r`;
  - comprehensions in the function, in lambda bodies and in a class body inside the function, whose targets `q` and
    `w` may be read before they are bound.

  Names are disjoint per scope kind, so a runtime `UnboundLocalError` names its scope. Every such name must be
  reported. Results at 1,500 functions per seed:

  | Analyser, Python | False negatives per seed | Record |
  |---|---|---|
  | current, 3.10.11 | 0, 0, 0 | `ast_scan_fuzz.json` |
  | 2ae3db7, 3.10.11 | 298, 273, 294 (all in lambda or comprehension names) | `ast_scan_fuzz_2ae3db7.json` |
  | current, 3.12.14, seeds 1-5 | 0 each | `ast_scan_fuzz_py312.json` |
  | current, 3.14.7, seeds 1-5 | 0 each | `ast_scan_fuzz_py314.json` |
  | current, round-1 generator (`fx1g4/ast_scan_fuzz.py`) | 0, 0, 0 | `ast_scan_fuzz_round1_generator.json` |

  The last row also shows the same false-positive counts as the fix-round-1 record (623, 643 and 667). So on
  function-scope code without lambdas the analyser behaves exactly as before. Reports caused by correlated conditions,
  or by a statement that an earlier exception skips, are counted, not failed.

## Suites run (Mac)

| Command | Result |
|---|---|
| `tests/ast_scan.py` (default: `tools/*.py`) | 27 files, 0 findings, self-test passed (`ast_scan.json`) |
| `tests/ast_scan.py gen/*.py tests/*.py` (the Makefile's second scan) | 44 files, 0 findings (`ast_scan_gen_tests.json`) |
| `tests/ast_scan.py` over every git-tracked `.py` file plus the two scripts here | 175 files, 0 findings (`ast_scan_whole_package.json`) |
| `tests/unit_orchestration.py --only atomic`, three times | passed (`unit_orchestration_atomic.json`, the last run) |
| `tests/unit_orchestration.py` (all tests) | 49 tests, 61 sub-tests passed, 0 failed (`unit_orchestration.json`) |
| `fx2g4_evidence.py`, `ast_scan_fuzz.py` | passed (`evidence.json` and the fuzz records) |

The whole-package scan with the fixed analyser finds nothing, in this tree or in the other fix-round-2 worktrees
(fx2-g1, fx2-g2 and fx2-g3 as of this commit, including their uncommitted files). The package has 563 lambdas, none
with a walrus in its body, and 3,683 comprehensions.

`tools/verify_delivery.py --write` and then `--strict` ran before the commit.

## Owed

Nothing on the clusters for these items. J-VAL-1 runs `make test-python`, which runs both changed tests; the
atomic-plan test there exercises the Linux `killpg`/`waitpid` path.
