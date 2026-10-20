#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 2 --mem=4G -t 00:30:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# J-SMK-3, last step (PLAN "Design chain (J-SMK-3)"; A-DES-3, A-ASM-6/7 on real data): tools/combine.py on the two
# test-only batches of the frozen test bundle designs/test_smoke1 (distinct seeds): --partial with batch 1, final with
# batches 1 and 2; tools/verify_result.py on each output; tools/design.py report --bundle on the bundle for the record.
# Usage: C8_PACKAGE=... B1=... B2=... OUT=<evidence dir> sbatch --export=ALL -J c8d2-s5combine s5combine.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${B1:?}" "${B2:?}" "${OUT:?}"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); batches $B1 $B2; out $OUT"; lscpu | grep 'Model name'
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$OUT"; cd "$C8_PACKAGE" || exit 64; s=0
run() { local name=$1; shift; echo "== $name"; "$@" > "$OUT/$name.stdout" 2>&1; local c=$?; echo "== $name exit $c"; tail -12 "$OUT/$name.stdout" | cut -c1-250; [ $c -eq 0 ] || s=1; }
run combine_partial python3 -B tools/combine.py "$B1" --output "$OUT/C8_partial.json" --partial --test-only
run verify_partial python3 -B tools/verify_result.py "$OUT/C8_partial.json"
run combine_final python3 -B tools/combine.py "$B1" "$B2" --output "$OUT/C8_final.json" --test-only
run verify_final python3 -B tools/verify_result.py "$OUT/C8_final.json"
for b in "$B1" "$B2"; do run "verify_$(basename $b)" python3 -B tools/verify_result.py "$b/C8_test_result.json"; done
# F6: verify_result.py's rounding-level gates depend on the OpenBLAS kernels (this sharedq node: Xeon Gold 6148, AVX-512
# kernels; the results were assembled on AMD EPYC nodes, AVX2 kernels): the same verifications with the AVX2 kernels
for f in "$OUT/C8_partial.json" "$OUT/C8_final.json" "$B1/C8_test_result.json" "$B2/C8_test_result.json"; do
  [ -e "$f" ] && run "verify_haswell_$(basename $(dirname $f))_$(basename $f .json)" env OPENBLAS_CORETYPE=Haswell python3 -B tools/verify_result.py "$f"; done
echo "finished $(date -Is), status $s"; exit $s
