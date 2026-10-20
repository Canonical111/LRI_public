#!/bin/zsh
# verify every stored result of the tree $1 with that tree's verifier
root=$1; fail=0; n=0
cd $root
for f in $(grep -rl '"c8-d2-hpc-result-1"' benchmarks tests/fixtures | sort); do
  n=$((n+1))
  if C8_ALLOW_NO_L8=1 OPENBLAS_NUM_THREADS=1 <HOME>/anaconda3/bin/python3 -B tools/verify_result.py $f > /dev/null 2>&1; then echo "ok   $f"; else echo "FAIL $f"; fail=$((fail+1)); fi
done
echo "code $root results $n failing $fail"
