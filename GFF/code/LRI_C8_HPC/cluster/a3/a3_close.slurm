#!/bin/bash
#SBATCH --job-name=c8x-finalize
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=180G
#SBATCH --time=06:00:00
#SBATCH --output=/mnt/beegfs/zzheng1/c8_hpc/logs/%x_%j.out
# Amendment A3 (docs/EXTENSION_A3.md), symmetry: the closing job of the C8(1) extension (complete close only; a user
# stop gets its own reviewed procedure). Named c8x-finalize so that lane8.py finalize accepts it as its own job.
#  0. a3_close.py begin: close lock (no-clobber, held to the end), then no other unfinished c8x- job, no registered
#     transfer, queue_a2 complete, b12-b14 staged (on every invocation);
#  1. lane8.py finalize on queue_a2, then on queue (merge-only; b12-b14 still have no checkpoint on symmetry here, so the
#     A1 queue leaves them unmerged); recorded in runs/ext1/A3_finalized.json and not repeated once recorded;
#  2. per A3 batch: a3_close.py verify (full validation of the staged copy before anything is moved; receipt), a3_tree.py
#     install, production8.py merge of the installed batch (re-validation; writes nothing);
#  3. a3_close.py batches: all of b5-b14 complete and merged; combine8.py --closed into the private directory
#     results/C8_final_A3.pending; a3_close.py end: the result must be the closed K=14 combination; A3_close.json;
#     publication by rename to results/C8_final_A3 only if no stop was acknowledged (A3_PUBLISH / A3_STOP markers).
# Submit (login node): <W>/code/<A3 commit>/cluster/a3/submit_sym.sh close (sanitized environment, pinned revision).
set -eo pipefail
source /mnt/beegfs/zzheng1/c8_hpc/code/symmetry/env_symmetry.sh
set -u
W=/mnt/beegfs/zzheng1/c8_hpc;R=$W/runs/ext1;I=$W/runs/ext1_a3_import;T=$W/code/15a110e
[[ "${C8X_A3:?}" == $W/code/*/cluster/a3 && -f $C8X_A3/a3_close.py ]] || { echo "C8X_A3 not a deployed cluster/a3" >&2; exit 64; }
cmp -s "$0" "$C8X_A3/a3_close.slurm" || { echo "this job script differs from $C8X_A3/a3_close.slurm: submit with submit_sym.sh of that revision" >&2; exit 64; }
[[ "$(env | grep '^C8X_' | sort | tr '\n' '|')" == "C8X_A3=$C8X_A3|" ]] || { echo "unexpected C8X_* variables" >&2; exit 64; }
[[ "$SLURM_JOB_NAME" == c8x-finalize ]] || { echo "job must be named c8x-finalize" >&2; exit 64; }
S=/local1/zzheng1_c8x_a3close_$SLURM_JOB_ID;mkdir -p "$S";trap 'rm -rf "$S"' EXIT
cd $W
"$C8_PYTHON" $C8X_A3/a3_close.py begin
if [[ ! -e $R/A3_finalized.json ]]; then
  for q in queue_a2 queue; do "$C8_PYTHON" $T/tools/lane8.py finalize --queue $R/$q --c8-root "$C8_ROOT" --scratch "$S"; done
  ( set -o noclobber; echo "{\"finalized\": [\"queue_a2\", \"queue\"], \"job\": \"$SLURM_JOB_ID\", \"time\": \"$(date -Is)\"}" > $R/A3_finalized.json )
else echo "queues already finalized: $(cat $R/A3_finalized.json)"; fi
for b in b12 b13 b14; do
  "$C8_PYTHON" $C8X_A3/a3_close.py verify $b "$C8_ROOT" "$S"
  "$C8_PYTHON" $C8X_A3/a3_tree.py install $R/$b $I/$b $I/$b.expanse_manifest.txt
  "$C8_PYTHON" $C8_ROOT/tools/production8.py merge $R/$b --scratch "$S"
done
B=$("$C8_PYTHON" $C8X_A3/a3_close.py batches)
echo "combining b1-b4 and: $B"
"$C8_PYTHON" $T/tools/combine8.py runs/prod4/b1 runs/prod4/b2 runs/prod4/b3 runs/prod4/b4 $B \
  --extension $R/extension.json --closed --output results/C8_final_A3.pending --affine analysis/v1/full_affine8.json \
  --exact5 runs/exact8_L5/exact_L5/merged/N14.json runs/exact8_L5/exact_L5/merged/N12.json \
  --design-meta designs_frozen/prod4_34000/design_meta.json --jobs 32
"$C8_PYTHON" $C8X_A3/a3_close.py end $B
