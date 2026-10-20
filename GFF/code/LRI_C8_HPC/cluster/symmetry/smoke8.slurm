#!/bin/bash
#SBATCH --job-name=c8x-smoke
#SBATCH --partition=debugq
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=180G
#SBATCH --time=01:00:00
#SBATCH --output=/mnt/beegfs/zzheng1/c8_hpc/logs/%x_%j.out
# Replays short elements of Expanse batch b1 on symmetry with the Expanse binary, in two variants at once:
# phys (NUMA node 0, one thread per core) and ht (NUMA node 1, both hardware threads), then compares every replayed
# checkpoint with the Expanse checkpoint of the same identity (smoke_compare.py). Not production: nothing here enters a
# result. Rerun only the comparison of an earlier replay: C8X_SMOKE_COMPARE_ONLY=<job id>.
set -eo pipefail
source /mnt/beegfs/zzheng1/c8_hpc/code/symmetry/env_symmetry.sh
set -u
ELEMENTS="5 84 9 10 11 12" # the qualifying set of amendment A1 (fixed; reduced replays are not run through this script)
[[ -n "${ELEMENTS// /}" ]] || { echo "C8X smoke: empty element list" >&2; exit 64; }
if [[ -n "${C8X_SMOKE_COMPARE_ONLY:-}" ]]; then
  exec "$C8_PYTHON" $C8W/code/symmetry/smoke_compare.py "$C8W/smoke/$C8X_SMOKE_COMPARE_ONLY" "$C8W/runs/prod4/b1" 1e-10 1e-6 "$C8W/analysis/v1/full_affine8.json" "$C8W/results/C8_final/C8_final.json" phys,ht $ELEMENTS
fi
B1=$C8W/runs/prod4/b1;SM=$C8W/smoke/$SLURM_JOB_ID;S=/local1/zzheng1_c8x_smoke_$SLURM_JOB_ID
mkdir -p "$SM" "$S";trap 'rm -rf "$S"' EXIT
echo "C8X smoke on $(hostname) $(date -Is)";lscpu | grep -E 'Model name|NUMA node[0-9]'
python3 -c 'import sys,numpy,scipy;print("python",sys.version.split()[0],"numpy",numpy.__version__,"scipy",scipy.__version__)'
sha256sum "$C8_EXE";ldd "$C8_EXE"
[[ "$(sha256sum "$C8_EXE" | cut -d' ' -f1)" == "$C8_EXE_SHA256" ]] || { echo "C8X: executable digest mismatch" >&2; exit 64; }
declare -A SET
for mode in phys ht; do
  mapfile -t L < <("$C8_PYTHON" $C8W/code/symmetry/cpusets.py $mode)
  if [[ $mode == phys ]]; then SET[$mode]="${L[0]}"; else SET[$mode]="${L[1]}"; fi
done
pids=();modes=()
for mode in phys ht; do
  mkdir -p "$SM/$mode/b1" "$S/$mode"
  rsync -a --exclude checkpoints --exclude merged --exclude inputs "$B1/" "$SM/$mode/b1/"
  ln -s "$B1/inputs" "$SM/$mode/b1/inputs"
  read -r node n cpus <<<"${SET[$mode]}"
  ( for i in $ELEMENTS; do
      t0=$(date +%s)
      numactl --physcpubind="$cpus" --membind="$node" "$C8_PYTHON" "$C8_ROOT/tools/production8.py" run "$SM/$mode/b1" --index "$i" --threads "$n" --executable "$C8_EXE" --scratch "$S/$mode" > "$SM/$mode/element_$i.log" 2>&1 \
        || { echo "$mode element $i FAILED (see $SM/$mode/element_$i.log)"; exit 1; }
      echo "$mode element $i threads $n seconds $(( $(date +%s) - t0 ))"
    done ) > "$SM/$mode/timing.txt" 2>&1 &
  pids+=($!);modes+=($mode)
done
fail=0
for k in "${!pids[@]}"; do wait "${pids[$k]}" || { echo "C8X smoke: replay ${modes[$k]} FAILED"; fail=1; }; done
cat "$SM"/*/timing.txt
"$C8_PYTHON" $C8W/code/symmetry/smoke_compare.py "$SM" "$B1" 1e-10 1e-6 "$C8W/analysis/v1/full_affine8.json" "$C8W/results/C8_final/C8_final.json" phys,ht $ELEMENTS || fail=1
echo "C8X smoke done $(date -Is): $([[ $fail == 0 ]] && echo PASS || echo FAIL)"
exit $fail
