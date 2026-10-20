#!/bin/bash
# Mac driver of the pre-Stage-6b symmetry run (the fixed design tool of 77fab71 on J-DES-5's real data; evidence in
# benchmarks/symmetry_2026-10-c8/pre6b/). Run from the repository root of the main checkout, one step at a time:
#   p6b.sh export COMMIT          git archive COMMIT -> <SCRATCH>/c8d2/pkg/<sha12> (an existing export is
#                                 refused), checked file by file (pre6b/setup/export_check_<sha12>.json). The export is
#                                 exactly COMMIT: this folder's scripts are not in it (they are staged separately).
#   p6b.sh stage                  copy pre6b/scripts/{p6bdes.slurm,p6b_compare.py} to <SCRATCH>/c8d2/jobscripts/
#                                 pre6b/ (an existing file must be byte-identical; never overwritten); sha256 on both
#                                 sides in pre6b/setup/staged_scripts.sha256
#   p6b.sh sub NAME "ENVS" FILE   a fresh `squeue -u <USER>` snapshot (pre6b/admission/), then `sbatch --parsable
#                                 --export=ALL -J NAME <staged FILE>` from <SCRATCH>/c8d2 with ENVS set; one
#                                 line in pre6b/admission/submitted.txt; prints the job id. sharedq only (outside the H7
#                                 AMD-pool cap): the staged script must request sharedq with --no-requeue, --mem and -t.
# Rules: symmetry only; never longq; sharedq --no-requeue; other <USER> jobs are never counted or touched.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); R=$(cd "$S/.." && pwd); PKG=$(cd "$R/../../.." && pwd)
A=$R/admission; mkdir -p "$A" "$R/setup"
SL='export PATH=/cm/shared/apps/slurm/current/bin:$PATH'
D=<SCRATCH>/c8d2; J=$D/jobscripts/pre6b
step=${1:?step}; shift
case $step in
export)
  cd "$PKG"; h=$(git rev-parse "${1:?commit}^{commit}"); t=${h:0:12}; x=$D/pkg/$t
  if ssh -T symmetry "test -e $x"; then echo "$x exists; refusing" >&2; exit 64; fi
  git archive --format=tar "$h" | ssh -T symmetry "mkdir -p $x && tar -x -C $x && echo $h > $x.commit"
  T=$(mktemp -d "${TMPDIR:-/tmp}/c8d2_p6b.XXXXXX")
  ssh -T symmetry "python3 - $x" < benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/tree_manifest.py > "$T/tree.txt"
  <HOME>/anaconda3/bin/python3 benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/export_check.py "$h" "$T/tree.txt" symmetry "$x" "$R/setup/export_check_$t.json" >&2
  rm -rf "$T"; echo "$x";;
stage)
  ssh -T symmetry "mkdir -p $J"
  for f in p6bdes.slurm p6b_compare.py; do
    if ssh -T symmetry "test -e $J/$f"; then
      ssh -T symmetry "cat $J/$f" | cmp -s - "$S/$f" || { echo "$J/$f exists and differs; refusing" >&2; exit 64; }
    else
      ssh -T symmetry "cat > $J/$f.tmp && mv -n $J/$f.tmp $J/$f" < "$S/$f"
    fi
  done
  { (cd "$S" && shasum -a 256 p6bdes.slurm p6b_compare.py | sed 's/^/mac      /'); ssh -T symmetry "cd $J && sha256sum p6bdes.slurm p6b_compare.py" | sed 's/^/symmetry /'; } \
    | tee "$R/setup/staged_scripts.sha256"
  ssh -T symmetry "chmod a-w $J/p6bdes.slurm $J/p6b_compare.py";;
sub)
  name=$1 envs=$2 file=$3; shift 3
  hdr=$(ssh -T symmetry "grep '^#SBATCH' $J/$file")
  case $hdr in *"-p sharedq "*"--no-requeue"*) ;; *) echo "$J/$file is not a sharedq --no-requeue job: $hdr" >&2; exit 64;; esac
  case $hdr in *--mem=*) ;; *) echo "$J/$file has no --mem" >&2; exit 64;; esac
  case $hdr in *" -t "*) ;; *) echo "$J/$file has no -t" >&2; exit 64;; esac
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  ssh -T symmetry "$SL; squeue -u <USER> -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$A/squeue_before_${name}_$ts.txt" \
    || { echo "squeue failed; nothing submitted" >&2; exit 69; }
  id=$(ssh -T symmetry "$SL; cd $D && $envs sbatch --parsable --export=ALL -J $name $* $J/$file")
  echo "$ts $name $id sharedq $envs $* $J/$file" >> "$A/submitted.txt"
  echo "$id";;
*) sed -n '2,/^set -euo/p' "$0" | sed '$d' >&2; exit 64;;
esac
