# Stage-6 fix round 1, group G4: the static scan and the delivery test (2026-10-05)

Branch `fx1-g4` from e88bf4f (the inspected tree), on the Mac (arm64, anaconda Python 3.10.11),
`C8_ALLOW_NO_L8=1 OPENBLAS_NUM_THREADS=1`. Items X17-X20 of `LRI_C8_D2_HPC_loop/artifacts/s6_fix1_dispositions.md`
(findings S6E-01..04). Only `tests/ast_scan.py` and `tests/test_delivery_verifier.py` changed, plus this folder. No
`src/` or `tools/` change and no cluster job: the default path, every plan and every number are unchanged.

## The fixes

- **X17 (S6E-01), `tests/ast_scan.py`.** `LocalNames` now collects match-pattern captures (`MatchAs.name`,
  `MatchStar.name`, `MatchMapping.rest`) as bindings of the function, so a read after an unmatched case, or before
  the match, is reported. A capture stays bound only in its own guard and body.
- **X18 (S6E-02).** `ast.Compare` is handled explicitly: the left operand and the first comparator always run; a
  later comparator's walrus target is not definite after the comparison (it is visible to the later links).
- **X19 (S6E-03).** A handler's except-as name is removed from every state that leaves the handler: its end, and each
  break and continue it appends to the enclosing loop, before an enclosing finally block is applied.
- **Same class, found while fixing (no finding id):** a dict display evaluates key, value, key, value (it was all keys
  first); an augmented assignment loads its target before its value; decorators run before defaults; class keywords
  (`metaclass=`) are checked; a walrus in a nested def's or lambda's defaults or decorators, or in class bases, makes
  the name local; an assert's test binds nothing (`python -O` skips it); and an unreachable statement in an except
  handler is reported once (it was counted twice).
- **X20 (S6E-04), `tests/test_delivery_verifier.py`.** The package root is now `tmp/pkg`, with a real file
  `tmp/escape.txt` outside it. Six unsafe or noncanonical manifest paths (`../escape.txt`, its absolute path,
  `tools/../payload.txt`, `payload\alias.txt`, `./payload.txt`, `tools//verify_delivery.py`) are each listed in an
  otherwise consistent package: the file exists with its true size and digest, the totals and SHA256SUMS are
  refreshed, and `local_build` is gone. Both modes must fail with exactly `Unsafe or noncanonical path: <name>`. A
  control runs the same fixtures through the verifier with `safe_file` reduced to "an existing regular file" and
  requires a pass. Every other negative case now asserts its exact error list as well.

## Before and after

`fx1g4_evidence.py` writes `evidence.json`; it needs the git checkout, because it reads e88bf4f's files with
`git show`.
- **ast_scan self-test.** 55 probes. The current analyser passes all of them. The e88bf4f analyser miscounts 17,
  which are the tests that fail before the fix:
  - X17: the five `match_*_after_unmatched*` probes and `match_capture_read_before_match`;
  - X18: `compare_chain_later_walrus`;
  - X19: `handler_target_after_break`, `handler_target_after_continue` and `handler_target_break_through_finally`;
  - the same-class items: `dict_value_before_later_key`, `aug_subscript_target_first`, `aug_name_target_first`,
    `decorator_before_default`, `lambda_default_walrus_is_local`, `class_keyword_load`, `assert_walrus_not_definite`
    and `unreachable_in_handler_once`.

  The clean probes, such as `match_capture_every_path` and `compare_chain_first_link_walrus`, pass with both
  analysers.
- **Delivery test against verifier mutants.** The e88bf4f test passes when `safe_file` loses its path-syntax guard,
  and it passes when any one of its sub-checks is dropped: absolute, `..`, backslash or noncanonical. That is
  S6E-04. The current test fails each of those mutants at the matching unsafe-path case. Both tests pass the
  unmodified verifier.
- **Differential fuzz (`ast_scan_fuzz.py`).** Random small functions run on all 16 input combinations, and every
  name that raises `UnboundLocalError` must be reported. Results, at 1,500 functions × 3 seeds:

  | Analyser | False negatives per seed | Record |
  |---|---|---|
  | current | 0, 0, 0 | `ast_scan_fuzz.json` |
  | e88bf4f | 91, 86, 84 | `ast_scan_fuzz_e88bf4f.json` |

  Python 3.14.7 and seeds 4-5 also gave 0 false negatives (not recorded). Reports caused by correlated conditions
  are counted, not failed.

## Suites run (Mac)

| Command | Result |
|---|---|
| `tests/ast_scan.py` (default: `tools/*.py`) | 27 files, 0 findings, self-test passed (`ast_scan.json`) |
| `tests/ast_scan.py` over every git-tracked `.py` file plus the two new scripts here | 173 files, 2 findings, both pre-existing (see below); self-test passed (`ast_scan_whole_package.json`) |
| `tests/test_delivery_verifier.py` | 30 cases passed (`test_delivery_verifier.json`) |
| `fx1g4_evidence.py`, `ast_scan_fuzz.py` | passed (`evidence.json`, `ast_scan_fuzz.json`) |

The whole-package scan finds only `tests/validate.py:297`: `free8` and `g8` in `bad_inputs()`. Both are assigned
under `if have8:` and read under the same condition. That is a correlated-condition false positive, and the e88bf4f
analyser reports it too. The file is outside the default scan (`tools/*.py`). The fixed analyser adds no finding
anywhere in the package.

`tools/verify_delivery.py --write` and then `--strict` ran before the commit.

## Owed

Nothing on the clusters for these items. J-VAL-1 runs `make test-python`, which runs both changed tests.
