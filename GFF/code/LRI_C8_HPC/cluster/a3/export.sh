#!/bin/bash
# Amendment A3 (docs/EXTENSION_A3.md): copy the planned batches b12-b14 from symmetry to Expanse. Run on the Mac (both
# sites reachable by ssh; the copy streams through it). Usage: export.sh A3_COMMIT [--early] (deployed as code/A3_COMMIT
# on both). --early: before the A1 close, with the early gate (a3_tree.py gate --early); the close job then requires
# the A1-close snapshot to record b12-b14 untouched.
# 1. symmetry gate (a3_tree.py gate): the A1-close snapshot records b12-b14 untouched, queue_a2 holds only b10 and b11,
#    and b12-b14 still have no output and no claim; 2. the Expanse targets do not exist; 3. tar stream; 4. per batch, the
#    manifest digests on both sites must agree; 5. the gate again; 6. the export record runs/ext1/A3_export.json
#    (atomic, no-clobber) on Expanse, which submit_expanse.sh checks before submitting anything.
# Steps 2-6 hold the Expanse submit lock runs/ext1/A3_SUBMIT.lock (the lock of the a3_expanse.py commands, including
# stop), taken before the admission checks; the stop barrier is checked under it before the copy and again before the
# record. An interrupted export leaves the lock (inspect, then remove it); on success only this export's lock is removed.
set -euo pipefail
SHA=${1:?A3 commit};EARLY=${2:-};[[ -z "$EARLY" || "$EARLY" == --early ]] || { echo "usage: export.sh A3_COMMIT [--early]" >&2; exit 64; }
W=/mnt/beegfs/zzheng1/c8_hpc;E=/expanse/lustre/scratch/zzheng8/temp_project/c8_hpc
SA=$W/code/$SHA/cluster/a3;EA=$E/code/$SHA/cluster/a3
# remote shells: pipefail, and an environment-setup failure stops the command
sy(){ ssh symmetry "set -o pipefail; source $W/code/symmetry/env_symmetry.sh >/dev/null 2>&1 || exit 70; $1"; }
ex(){ ssh -T expanse "set -o pipefail; source $E/env.sh >/dev/null 2>&1 || exit 70; $1"; }
hex(){ [[ "$1" =~ ^[0-9a-f]{64}$ ]]; }
g=$(sy "\$C8_PYTHON $SA/a3_tree.py gate $EARLY") || { echo "gate refused" >&2; exit 64; };echo "$g"
K="export $(hostname -s) $$ $(date +%s)";L=$E/runs/ext1/A3_SUBMIT.lock
ex "mkdir -p $E/runs/ext1 && set -o noclobber && echo '$K' > $L" || { echo "Expanse submit lock held by another command" >&2; exit 64; }
mine(){ ex "test \"\$(cat $L)\" = '$K'"; }
ex "test -f $EA/a3_tree.py && test ! -e $E/runs/ext1/A3_STOP && test ! -e $E/runs/ext1/b12 && test ! -e $E/runs/ext1/b13 && test ! -e $E/runs/ext1/b14 && test ! -e $E/runs/ext1/A3_export.json" || { echo "export not admitted (stop barrier, existing targets or record); lock left: inspect, remove" >&2; exit 64; }
ssh symmetry "cd $W/runs/ext1 && tar -cf - b12 b13 b14" | ssh -T expanse "cd $E/runs/ext1 && tar -xf -"
M=() # manifest digests of b12 b13 b14, in that order (bash 3.2 on the Mac: no associative arrays)
for b in b12 b13 b14; do
  s=$(sy "\$C8_PYTHON $SA/a3_tree.py manifest $W/runs/ext1/$b --digest") || { echo "$b: symmetry manifest failed" >&2; exit 1; }
  e=$(ex "\$C8_PYTHON $EA/a3_tree.py manifest $E/runs/ext1/$b --digest") || { echo "$b: Expanse manifest failed (lock left: inspect)" >&2; exit 1; }
  hex "$s" && hex "$e" && [[ "$s" == "$e" ]] || { echo "$b: manifests differ or malformed (symmetry '$s', Expanse '$e'; lock left: inspect)" >&2; exit 1; }
  M+=("$s");echo "$b: identical on both sites (manifest sha256 $s)"
done
g2=$(sy "\$C8_PYTHON $SA/a3_tree.py gate $EARLY") || { echo "gate refused after the copy (lock left: inspect)" >&2; exit 1; };[[ "$g2" == "$g" ]] || { echo "gate changed during the copy: $g2" >&2; exit 1; }
rec=$(python3 -c "import json,sys,time;print(json.dumps({'schema':'c8-a3-export-1','time':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'a3_commit':sys.argv[1],'gate':json.loads(sys.argv[2]),'manifest_sha256':{'b12':sys.argv[3],'b13':sys.argv[4],'b14':sys.argv[5]}},indent=1))" "$SHA" "$g" "${M[0]}" "${M[1]}" "${M[2]}")
mine || { echo "Expanse lock is not ours any more: inspect" >&2; exit 1; }
printf '%s\n' "$rec" | ssh -T expanse "test ! -e $E/runs/ext1/A3_STOP && cat > $E/runs/ext1/.A3_export.json.tmp && sync && mv -n $E/runs/ext1/.A3_export.json.tmp $E/runs/ext1/A3_export.json && test ! -e $E/runs/ext1/.A3_export.json.tmp" || { echo "export record not written (stop barrier?); lock left: inspect" >&2; exit 1; }
mine && ex "rm $L" || { echo "Expanse lock is not ours any more: inspect" >&2; exit 1; }
echo "$rec"
