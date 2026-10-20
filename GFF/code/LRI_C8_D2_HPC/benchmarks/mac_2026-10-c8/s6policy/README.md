# The Stage-6 policy fix: the Mac suite (2026-10-05)

The last fix before the Stage-6 Codex inspection, on `c8` (parent c46b102). It closes the pre-Stage-6 verifier's
MEDIUM-LOW policy gap and its LOW items (`LRI_C8_D2_HPC_loop/PLAN-REVIEW-LOG.md`, "Design-tool fixes before Stage 6"),
following the user's decisions of 2026-10-05: `dd+mp256` for production after the pilot; the smoke and the pilot exact;
`exp1` and R7 off.
- **`tools/production.py` `plan`:**
  - a non-test `--pilot` under a profile or a rate map is refused unless `APPROVED_PROFILE_PILOTS` (new, empty) holds it;
  - every non-test plan whose numerics are not exact runs only a build covered by a passed, full-scale J-FLAG gate
    record: route (b) through the bundle's records, any other plan through the new `--numerics-gate`.
- **`tools/design.py`:** `freeze --numerics` refuses a profile cost model measured with an ungated build. The prune
  pass's stop on a cap and the comparison at a fixed batch count K are now documented.

No `src/` change and no cluster job: the default path, every exact plan and every design number are unchanged.

The suite ran on the Mac: arm64, anaconda Python 3.10.11, numpy 1.23.5, scipy 1.10.0, pytest 7.1.2. The command was:

```
C8_ALLOW_NO_L8=1 make test-python PYTHON=<HOME>/anaconda3/bin/python3 OUTPUT=<dir>
```

It took 18:18 wall (20:20-20:38 EDT) and exited 0. The records are in this folder; `make_test_python.log` is the
console output, with the output directory shown as `$OUTPUT`.

## Results

| Suite | Result |
|---|---|
| `tests/check_venv.py` | passed. It warns that numpy, mpmath and sympy are below their minimums on the Mac; that counts as a failure only with `--strict`. |
| `tests/unit_orchestration.py` | 42 groups, 54 tests, all passed. New: `route_b_records`, which covers every refusal branch of `production.route_b`'s record and final checks, of `design.check_gate`'s 18 cases, and of `production.gated_route`. |
| `tests/test_pipeline.py` | 24/24 passed. New: `Stage6_non_test_pilot_exact_…`, with 10 refusals and 3 acceptances, and the R7 measurement pilot's `APPROVED_PROFILE_PILOTS` refusal. Changed: route (b) in process now has 22 refusals, including the ungated profile cost model. |
| `tests/ast_scan.py` | 27 files, 0 findings. A first run found a possibly unbound `rid` in `plan()`; it was fixed, and the whole suite was run again from the start. |
| `gen/test_regress.py` | 42/42 |
| `tests/merge_scale.py --rows 20000` | passed |
| `tests/check_vendored.py` | 17/17 |
| `tests/vendored_isolated.py` | 10/10 |
| `tests/test_delivery_verifier.py` | passed |
| `tests/check_inputs.py` | 11/11; 2 skipped because the L8 packs are not on the Mac |
| `tests/test_profiling.py` | 15 passed |
| `tests/test_gmp_prefix.py` | 7 passed |
| `tests/test_numerics_flags.py` | 8 passed |
| `tests/test_dd_profile.py` | 8 passed |
| `tests/sanitize.py --capture-check` | passed. The probe's report is lost on a pipe and read on the pty, as designed. |

`tools/verify_delivery.py --write` and then `--strict` ran before the commit. Two docs-only edits landed after the
run, with no code change: `docs/DESIGN.md` (the R7 measurement step names both allow-lists) and `docs/HPC.md` (the
count of pinned-tool changes since the pilots were planned).

## Owed on the clusters

Nothing new for the default path. The Stage-6 inspection covers this change. After it:
- J-VAL-1 on the approved commit;
- A-EXP-3 on Expanse;
- both pilots re-planned with fresh seeds, because `production.py` is a pinned tool;
- the H6 hand-off re-issued, because `design.py` changed;
- pre6b repeated if Stage 6 changes `design.py` again.
