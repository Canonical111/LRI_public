#!/bin/bash
# Local analysis after rsync of results/ (about 2 minutes on the Mac): table, internal and archive checks,
# GLS engine comparison on every existing engine file, injected-error calibration, README summary tables.
# Usage: bash run_analysis.sh [ENGINE_FILE ...]   (default: the engine's validation and pilot5 series)
set -euo pipefail
cd "$(dirname "$0")"
E=../../engine
python3 build_table.py
python3 compare_checks.py > /dev/null
python3 compare_archive.py > /dev/null
python3 ../tests/test_compare_engine.py
run() {   # name, files...
  local name=$1; shift
  python3 compare_engine.py "$@" --offset-fit --out ../results/engine_comparison_$name.json \
      > ../results/engine_comparison_$name.txt 2>&1
  tail -2 ../results/engine_comparison_$name.txt | head -1
}
if [ $# -gt 0 ]; then
  run user "$@" --merge
else
  run validation_c $E/results/validation_c.json
  run validation_d $E/results/validation_d_inputs.json
  run pilot5 $E/runs/pilot5/results.json
  run merged $E/runs/pilot5/results.json $E/results/validation_d_inputs.json $E/results/validation_c.json --merge
  python3 calibrate_injections.py > /dev/null
  python3 summarize_engine_comparison.py > ../results/engine_comparison_summary.md
fi
