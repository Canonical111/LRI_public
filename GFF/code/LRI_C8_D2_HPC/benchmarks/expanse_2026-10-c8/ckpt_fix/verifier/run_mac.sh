#!/bin/bash
# Mac pure-logic suites at HEAD (independent verifier run). Usage: OUT=<new directory> bash run_mac.sh
P=<HOME>/anaconda3/bin/python3
O=${OUT:?set OUT to a new directory}; mkdir -p "$O"
cd <PROJECT>/LRI_C8_D2_HPC
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
run(){ n=$1; shift; t=$(date +%s); "$@" > "$O/$n.log" 2>&1; c=$?; echo "$n exit $c $(( $(date +%s)-t ))s" >> "$O/summary.txt"; }
: > "$O/summary.txt"
$P --version >> "$O/summary.txt"
run unit_orchestration $P -B tests/unit_orchestration.py --output "$O/unit_orchestration.json"
run test_pipeline $P -B tests/test_pipeline.py --output "$O/test_pipeline.json"
run ast_scan $P -B tests/ast_scan.py --output "$O/ast_scan.json"
run test_regress $P -B gen/test_regress.py --output "$O/test_regress.json"
run merge_scale $P -B tests/merge_scale.py --rows 20000 --output "$O/merge_scale.json"
run verify_result_tamper $P -B tests/verify_result_tamper.py --output "$O/verify_result_tamper.json"
run combine_core $P -B tests/combine_core.py --output "$O/combine_core.json"
run assembly_checks $P -B tests/assembly_checks.py --exact --output "$O/assembly_checks.json"
run check_vendored $P -B tests/check_vendored.py --output "$O/check_vendored.json"
run vendored_isolated $P -B tests/vendored_isolated.py --output "$O/vendored_isolated.json"
run check_inputs env C8_ALLOW_NO_L8=1 $P -B tests/check_inputs.py --output "$O/check_inputs.json"
run delivery_verifier $P -B tests/test_delivery_verifier.py
echo done >> "$O/summary.txt"
