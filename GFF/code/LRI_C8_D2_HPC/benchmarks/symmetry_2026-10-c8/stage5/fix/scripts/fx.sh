#!/bin/bash
# Mac driver of the post-merge re-validation on symmetry (Stage-5 G5 fixes F1-F9 merged into c8; evidence in
# benchmarks/symmetry_2026-10-c8/stage5/fix/). Run from the repository root of the main checkout, one step at a time:
#   fx.sh export                      git archive HEAD -> <SCRATCH>/c8d2/pkg/<sha12> (an existing export is
#                                     refused), checked file by file (fix/setup/export_check_<sha12>.json)
#   fx.sh sub NAME PART "ENVS" ARGS   a fresh `squeue -u <USER>` snapshot (fix/admission/), for an AMD partition
#                                     (amdq, amddebugq, amdpreq) the H7 check (at most 4 live c8d2-* jobs on the AMD pool,
#                                     the new one included; other <USER> jobs never counted or touched), then
#                                     `sbatch --parsable --export=ALL -J NAME ARGS` from <SCRATCH>/c8d2 with
#                                     ENVS set; one line in fix/admission/submitted.txt; prints the job id. PART 'none':
#                                     sharedq jobs (outside the H7 cap) get the snapshot but no cap check.
#   fx.sh upload FILE PKG             a script written after the export, copied to <SCRATCH>/c8d2/work/fx-<sha12>/
#                                     with both sha256 recorded in submitted.txt; prints the remote path
# Rules: symmetry only; amdq/amddebugq always --exclude=cn112; never longq; sharedq --no-requeue (in the scripts).
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); R=$(cd "$S/.." && pwd); PKG=$(cd "$R/../../../.." && pwd)
A=$R/admission; mkdir -p "$A" "$R/setup"
SL='export PATH=/cm/shared/apps/slurm/current/bin:$PATH'
D=<SCRATCH>/c8d2
step=${1:?step}; shift
case $step in
export)
  cd "$PKG"
  dirty=$(git status --porcelain -- tools src tests Makefile inputs gen slurm vendor cost_models benchmarks/fixtures8 benchmarks/symmetry_2026-10-c8/stage5/fix/scripts)
  [ -z "$dirty" ] || { echo "uncommitted changes in exported paths; commit first:"; echo "$dirty"; exit 64; } >&2
  h=$(git rev-parse HEAD); t=${h:0:12}; x=$D/pkg/$t
  if ssh -T symmetry "test -e $x"; then echo "$x exists; refusing" >&2; exit 64; fi
  git archive --format=tar "$h" | ssh -T symmetry "mkdir -p $x && tar -x -C $x && echo $h > $x.commit"
  T=$(mktemp -d "${TMPDIR:-/tmp}/c8d2_fx.XXXXXX")
  ssh -T symmetry "python3 - $x" < benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/tree_manifest.py > "$T/tree.txt"
  <HOME>/anaconda3/bin/python3 benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/export_check.py "$h" "$T/tree.txt" symmetry "$x" "$R/setup/export_check_$t.json" >&2
  rm -rf "$T"; echo "$x";;
sub)
  name=$1 part=$2 envs=$3; shift 3
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  ssh -T symmetry "$SL; squeue -u <USER> -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$A/squeue_before_${name}_$ts.txt" \
    || { echo "squeue failed; nothing submitted" >&2; exit 69; }
  if [ "$part" != none ]; then
    <HOME>/anaconda3/bin/python3 "$PKG/benchmarks/expanse_2026-10-c8/stage4a/scripts/h7_admit.py" --site symmetry --me <USER> --job "$name" --partition "$part" \
      < "$A/squeue_before_${name}_$ts.txt" | tee -a "$A/h7_admission.jsonl" >&2
  fi
  id=$(ssh -T symmetry "$SL; cd $D && $envs sbatch --parsable --export=ALL -J $name $*")
  echo "$ts $name $id $part $envs $*" >> "$A/submitted.txt"
  echo "$id";;
upload)
  f=$1 x=$2; W=$D/work/fx-$(basename "$x"); ssh -T symmetry "mkdir -p $W"
  ssh -T symmetry "cat > $W/$(basename "$f")" < "$f"
  echo "$(date -u +%FT%TZ) uploaded $f sha256 $(shasum -a 256 "$f" | cut -c1-64) remote $(ssh -T symmetry "sha256sum $W/$(basename "$f")" | cut -c1-64)" >> "$A/submitted.txt"
  echo "$W/$(basename "$f")";;
*) sed -n '2,/^set -euo/p' "$0" | sed '$d' >&2; exit 64;;
esac
