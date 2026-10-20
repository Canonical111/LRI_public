#!/bin/bash
# Mac driver of the C8(2) L8 pilot PREPARATION on symmetry (2026-10-06; evidence in benchmarks/symmetry_2026-10-c8/pilot/).
# Template: s6fix4/scripts/s4.sh. Run from the repository root of the main checkout, one step at a time:
#   pp.sh export COMMIT               git archive COMMIT -> /mnt/beegfs/zzheng1/c8d2/pkg/<sha12> (an existing export is
#                                     refused), checked file by file (pilot/setup/export_check_<sha12>.json). The job
#                                     scripts of this folder are NOT in that export (they postdate the commit): `upload`
#                                     copies each to /mnt/beegfs/zzheng1/c8d2/work/pilot-<sha12>/ (never overwritten;
#                                     read-only), recording both sha256.
#   pp.sh sub NAME PART "ENVS" ARGS   a fresh `squeue -u zzheng1` snapshot (pilot/admission/), for an AMD partition
#                                     (amdq, amddebugq, amdpreq) the H7 check (at most 4 live c8d2-* jobs on the AMD pool,
#                                     the new one included; C63d's c8d3-* jobs and other zzheng1 jobs never counted or
#                                     touched), then `sbatch --parsable --export=ALL -J NAME ARGS` from
#                                     /mnt/beegfs/zzheng1/c8d2 with ENVS set; one line in pilot/admission/submitted.txt;
#                                     prints the job id. PART 'none': sharedq jobs (outside the H7 cap) get the snapshot
#                                     but no cap check.
#   pp.sh upload FILE PKG             a script of this folder copied to /mnt/beegfs/zzheng1/c8d2/work/pilot-<sha12>/
# Rules: symmetry only; amdq/amddebugq always --exclude=cn112; never longq; sharedq --no-requeue; every job --mem, --time
# and a c8d2- name. This driver never submits the pilot's lane workers or merge (the host does, after C63d agrees).
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); R=$(cd "$S/.." && pwd); PKG=$(cd "$R/../../.." && pwd)
A=$R/admission; mkdir -p "$A" "$R/setup"
SL='export PATH=/cm/shared/apps/slurm/current/bin:$PATH'
D=/mnt/beegfs/zzheng1/c8d2
step=${1:?step}; shift
case $step in
export)
  cd "$PKG"
  h=$(git rev-parse "${1:?commit}^{commit}"); t=${h:0:12}; x=$D/pkg/$t
  if ssh -T symmetry "test -e $x"; then echo "$x exists; refusing" >&2; exit 64; fi
  git archive --format=tar "$h" | ssh -T symmetry "mkdir -p $x && tar -x -C $x && echo $h > $x.commit"
  T=$(mktemp -d "${TMPDIR:-/tmp}/c8d2_pp.XXXXXX")
  ssh -T symmetry "python3 - $x" < benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/tree_manifest.py > "$T/tree.txt"
  /Users/zheng/anaconda3/bin/python3 benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/export_check.py "$h" "$T/tree.txt" symmetry "$x" "$R/setup/export_check_$t.json" >&2
  rm -rf "$T"; echo "$x";;
sub)
  name=$1 part=$2 envs=$3; shift 3
  case $name in c8d2-*) ;; *) echo "job names start with c8d2-" >&2; exit 64;; esac
  case " $* " in *longq*) echo "never longq" >&2; exit 64;; esac
  case $part in amdq|amddebugq|amdpreq) case " $* " in *cn112*) ;; *) echo "AMD jobs carry --exclude=cn112" >&2; exit 64;; esac;; esac
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  ssh -T symmetry "$SL; squeue -u zzheng1 -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$A/squeue_before_${name}_$ts.txt" \
    || { echo "squeue failed; nothing submitted" >&2; exit 69; }
  if [ "$part" != none ]; then
    /Users/zheng/anaconda3/bin/python3 "$PKG/benchmarks/expanse_2026-10-c8/stage4a/scripts/h7_admit.py" --site symmetry --me zzheng1 --job "$name" --partition "$part" \
      < "$A/squeue_before_${name}_$ts.txt" | tee -a "$A/h7_admission.jsonl" >&2
  fi
  id=$(ssh -T symmetry "$SL; cd $D && $envs sbatch --parsable --export=ALL -J $name $*")
  echo "$ts $name $id $part $envs $*" >> "$A/submitted.txt"
  echo "$id";;
upload)
  f=$1 x=$2; W=$D/work/pilot-$(basename "$x"); ssh -T symmetry "mkdir -p $W"
  if ssh -T symmetry "test -e $W/$(basename "$f")"; then echo "$W/$(basename "$f") exists; refusing (never overwritten)" >&2; exit 64; fi
  ssh -T symmetry "cat > $W/$(basename "$f").tmp && mv -n $W/$(basename "$f").tmp $W/$(basename "$f") && chmod a-w $W/$(basename "$f")" < "$f"
  echo "$(date -u +%FT%TZ) uploaded $f sha256 $(shasum -a 256 "$f" | cut -c1-64) remote $(ssh -T symmetry "sha256sum $W/$(basename "$f")" | cut -c1-64)" >> "$A/submitted.txt"
  echo "$W/$(basename "$f")";;
*) sed -n '2,/^set -euo/p' "$0" | sed '$d' >&2; exit 64;;
esac
