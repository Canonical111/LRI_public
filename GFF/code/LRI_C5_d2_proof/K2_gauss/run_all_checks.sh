#!/bin/zsh
# Runs every machine check of proof_K2.md sequentially (one Mathematica kernel at a time) and logs the output.
cd <PROJECT>/LRI_C5_d2_proof/K2_gauss
for f in check_residue_series check_expansion check_singles check_dLambda check_bilateral check_gamma_constants check_extraction check_Kdefinition check_K2_cauchy check_position check_endtoend; do
  echo "=== ${f}.wl  $(date)" > logs/${f}.log
  timeout 1500 wolframscript -file ${f}.wl >> logs/${f}.log 2>&1
  echo "=== exit $? $(date)" >> logs/${f}.log
done
echo ALLDONE > logs/ALLDONE
