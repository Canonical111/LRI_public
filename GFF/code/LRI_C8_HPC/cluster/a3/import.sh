#!/bin/bash
# Amendment A3 (docs/EXTENSION_A3.md): copy merged A3 batches from Expanse back to symmetry's staging directory
# runs/ext1_a3_import (never into runs/ext1 directly). Run on the Mac. Usage: import.sh A3_COMMIT LABEL...
# (labels among b12 b13 b14; each must have its Expanse manifest, written by the merge job, and must not be staged yet).
# Admission protocol, shared with the close job (a3_close.py begin publishes the close lock FIRST and then refuses while
# any transfer is registered): per batch, (1) with the close lock absent, register the transfer by creating
# runs/ext1_a3_import/.incoming.<label> (mkdir: atomic, fails if another transfer of that batch is registered);
# (2) copy the manifest and the batch into it; (3) compare the manifest digests of both sites; (4) with the close lock
# still absent, publish by renames (batch, then manifest) and remove the registration last. A transfer that finds the
# close lock, or that is interrupted, leaves its registration, which stops the close until it is inspected and removed.
# On Expanse the transfer holds the A3 submit lock (runs/ext1/A3_SUBMIT.lock, as a3_expanse.py commands do) while it
# reads the batch, so no quarantine, resubmission or merge submission interleaves with it; an interrupted transfer
# leaves that lock too (inspect, then remove it).
# Then an optional c8x-a3check job validates the staged copies early (the close job validates them again itself).
set -euo pipefail
SHA=${1:?A3 commit};shift;[[ $# -ge 1 ]] || { echo "give labels" >&2; exit 64; }
W=/mnt/beegfs/zzheng1/c8_hpc;E=/expanse/lustre/scratch/zzheng8/temp_project/c8_hpc;I=$W/runs/ext1_a3_import;L=$W/runs/ext1/A3_CLOSE.lock
for b in "$@"; do
  [[ $b =~ ^b1[234]$ ]] || { echo "bad label $b" >&2; exit 64; }
  G=$I/.incoming.$b
  K="import $b $(hostname -s) $$ $(date +%s)"
  ssh -T expanse "set -o noclobber; echo '$K' > $E/runs/ext1/A3_SUBMIT.lock" || { echo "$b: Expanse submit lock held by another command" >&2; exit 64; }
  ssh -T expanse "test -f $E/runs/ext1/$b.expanse_manifest.txt" || { echo "$b: no Expanse manifest (not merged yet?); Expanse lock left: inspect, remove" >&2; exit 64; }
  ssh symmetry "test ! -e $L && mkdir -p $I && test ! -e $I/$b && test ! -e $I/$b.expanse_manifest.txt && mkdir $G" || { echo "$b: close lock present, already staged, or a transfer is registered; Expanse lock left: inspect, remove" >&2; exit 64; }
  ssh -T expanse "cat $E/runs/ext1/$b.expanse_manifest.txt" | ssh symmetry "set -o noclobber; cat > $G/manifest.txt"
  ssh -T expanse "cd $E/runs/ext1 && tar -cf - $b" | ssh symmetry "cd $G && tar -xf -"
  a=$(ssh -T expanse "sha256sum $E/runs/ext1/$b.expanse_manifest.txt" | cut -d' ' -f1);m=$(ssh symmetry "sha256sum $G/manifest.txt" | cut -d' ' -f1)
  [[ "$a" =~ ^[0-9a-f]{64}$ && "$a" == "$m" ]] || { echo "$b: manifest differs after the copy (registration $G left for inspection)" >&2; exit 1; }
  ssh -T expanse "test \"\$(cat $E/runs/ext1/A3_SUBMIT.lock)\" = '$K' && rm $E/runs/ext1/A3_SUBMIT.lock" || { echo "$b: Expanse lock is not ours any more: inspect" >&2; exit 1; }
  ssh symmetry "test ! -e $L && mv -T $G/$b $I/$b && mv -n $G/manifest.txt $I/$b.expanse_manifest.txt && test ! -e $G/manifest.txt && rmdir $G" || { echo "$b: not published (close lock appeared?): inspect $G" >&2; exit 1; }
  echo "$b staged in $I/$b"
done
ssh symmetry "bash $W/code/$SHA/cluster/a3/submit_sym.sh check $*"
