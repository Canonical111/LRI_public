#!/usr/bin/env bash
# Run every framework test (local; each test under 1.5 min, about 4 min in total). Log: out/tests.log
set -uo pipefail
cd "$(dirname "$0")"
fail=0
: > out/tests.log
for t in test_strict_missing test_error_model test_replicates test_pmax \
         test_module_vs_sympy test_normalization test_archive_pipeline test_vs_spec test_c8; do
  echo "=== tests/$t.py" >> out/tests.log
  start=$SECONDS
  if python3 "tests/$t.py" >> out/tests.log 2>&1; then r=PASS; else r=FAIL; fail=1; fi
  echo "--- $t: $r ($((SECONDS - start)) s)" | tee -a out/tests.log
done
# the phase-1 critic's independent transcription of the note's recurrence/dictionary/assemblies (read-only)
echo "=== review/check_note_recurrence_direct.py" >> out/tests.log
if python3 review/check_note_recurrence_direct.py >> out/tests.log 2>&1; then :; fi
grep -q "NOTE-DIRECT CHECK PASSED" out/tests.log && echo "--- check_note_recurrence_direct (critic): PASS" | tee -a out/tests.log \
  || { echo "--- check_note_recurrence_direct (critic): FAIL" | tee -a out/tests.log; fail=1; }
grep -E "^  FAIL" out/tests.log && fail=1
[ $fail -eq 0 ] && echo "ALL TESTS PASSED" | tee -a out/tests.log || echo "SOME TESTS FAILED" | tee -a out/tests.log
exit $fail
