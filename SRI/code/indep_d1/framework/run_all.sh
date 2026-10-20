#!/usr/bin/env bash
# Regenerate every framework output and run every test (local; about 10 min in total).
set -euo pipefail
cd "$(dirname "$0")"
python3 derive_rg.py            > out/derive_rg.stdout             # symbolic Part 1 (does not import the module)
python3 derive_invariants.py    > out/derive_invariants.stdout     # symbolic Part 2
python3 validate_low_order.py   > out/validate_low_order.stdout    # Part 3
python3 derive_C8.py            > out/derive_C8.stdout             # symbolic C8 = 8 T4 (phase 3)
python3 make_requirements.py    > out/make_requirements.stdout     # required lists + sensitivities (D3; C8)
python3 c8_production.py        > out/c8_production.stdout         # B_old on the production replicates (phase 3)
# (the sealed comparison compare_c8_production.py is run by hand, after c8_production.py)
python3 run_framework.py --required --order D4 --out out/required_inputs_D4_short.json > out/required_inputs_D4_short.txt
python3 run_framework.py --raw examples/raw_b3_sector.json --allow-missing \
        --out examples/result_b3_sector.json > examples/result_b3_sector.txt   # partial input: MISSING demo
./run_tests.sh
grep -E "AGREEMENT|DISCREPANCY|AGREE|PASSED|FAILED|verified|ALL OK|FAILURES|REGENERATED" out/*.stdout out/tests.log
