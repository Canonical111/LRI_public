#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:20:00 --no-requeue
#SBATCH -J c8d2-r3a-dev
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# R3a development probe (not a gate, not a build change): which of GCC's unit-wide IPA limits moves code outside
# calculate_shared<Q>? The baseline source (4a export) and R3A_DEV's are compiled to assembly with the worker's flags
# plus one experimental --param set each, and compared with asm_compare.py. Only the plain flags are ever shipped.
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"; : "${R3A_DEV:?}"
cd "$R3A_DEV"; mkdir -p out/ipa; BP=$C8_DATA/pkg/c17688158e2b
F="-O3 -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math"
declare -A V=([plain]="" [unit]="--param inline-unit-growth=100000 --param large-unit-insns=100000000"
  [ipacp]="--param ipa-cp-unit-growth=100000" [both]="--param inline-unit-growth=100000 --param large-unit-insns=100000000 --param ipa-cp-unit-growth=100000"
  [noipacp]="-fno-ipa-cp" [nopartial]="-fno-partial-inlining")
for v in "${!V[@]}"; do for b in gmp decimal; do D=""; [ $b = gmp ] && D=-DC8_USE_GMP
  g++ $F ${V[$v]} $D -S "$BP/src/c8d2_integrate.cpp" -o out/ipa/base_${b}_$v.s &
  g++ $F ${V[$v]} $D -S src/c8d2_integrate.cpp -o out/ipa/new_${b}_$v.s & done; done; wait
for v in plain unit ipacp both noipacp nopartial; do for b in gmp decimal; do
  python3 scripts/asm_compare.py out/ipa/base_${b}_$v.s out/ipa/new_${b}_$v.s --output out/ipa/asm_${b}_$v.json > /dev/null
  python3 -c "
import json,sys;d=json.load(open('out/ipa/asm_${b}_$v.json'))
print('$v $b',d['functions_baseline'],d['functions_candidate'],'identical',d['identical'],'different',[v['demangled'][:70] for v in d['different'].values()],'only_base',[x[:60] for x in d['only_baseline']],'only_new',[x[:60] for x in d['only_candidate']])"
done; done
