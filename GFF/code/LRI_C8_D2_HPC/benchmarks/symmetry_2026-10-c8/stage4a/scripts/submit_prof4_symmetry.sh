#!/bin/bash
# Mac-side driver for the symmetry P4 job (symmetry_prof4.slurm; PLAN "Performance plan", J-PROF-4 on symmetry).
#   C8_L8_PACKS=<dir on symmetry> bash benchmarks/symmetry_2026-10-c8/stage4a/scripts/submit_prof4_symmetry.sh
#   (or C8_INVENTORY=<inventory8_d2 on symmetry>; one of the two is required unless the export already holds the packs)
# 1. Exports HEAD with git archive into /mnt/beegfs/zzheng1/c8d2/pkg/<sha12> (never rsync) and checks it against the
#    archive (export_check.py -> benchmarks/symmetry_2026-10-c8/setup/export_check_<sha12>.json); an existing export is
#    reused as it is (it may hold a build or packs from an earlier job).
# 2. H7 before the sbatch (h7_admit.py on `squeue -u zzheng1`): at most 4 live c8d2-* jobs in amdq, amddebugq and
#    amdpreq together, the new one included. Other zzheng1 jobs (lri-prod*, another project) are never counted or touched.
# 3. sbatch -p amddebugq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 01:00:00 (directives in the script).
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../.."
EXP=benchmarks/expanse_2026-10-c8
ssh -T -o BatchMode=yes symmetry true || { echo "ssh symmetry failed; nothing done" >&2; exit 69; }
H=$(git rev-parse HEAD); T=${H:0:12}; D=/mnt/beegfs/zzheng1/c8d2; X=$D/pkg/$T
dirty=$(git status --porcelain -- tools src Makefile benchmarks/fixtures8 benchmarks/probes benchmarks/symmetry_2026-10-c8/stage4a)
[ -z "$dirty" ] || { echo "uncommitted changes in exported paths; commit first:"; echo "$dirty"; exit 64; } >&2
LT=$(mktemp -d "${C8_LOCAL_TMP:-${TMPDIR:-/tmp}}/c8d2_prof4s.XXXXXX")
if ssh -T symmetry "test -e $X"; then echo "reusing the existing export $X"
else
  git archive --format=tar "$H" | ssh -T symmetry "mkdir -p $X && tar -x -C $X"
  ssh -T symmetry "python3 - $X" < $EXP/ckpt_fix/scripts/tree_manifest.py > "$LT/c8d2_tree_$T.txt"
  mkdir -p benchmarks/symmetry_2026-10-c8/setup
  python3 $EXP/ckpt_fix/scripts/export_check.py "$H" "$LT/c8d2_tree_$T.txt" symmetry "$X" "benchmarks/symmetry_2026-10-c8/setup/export_check_$T.json"
fi
ssh -T symmetry "export PATH=/cm/shared/apps/slurm/current/bin:\$PATH; squeue -u zzheng1 -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$LT/squeue.txt" \
  || { echo "squeue failed; nothing submitted" >&2; exit 69; }
python3 $EXP/stage4a/scripts/h7_admit.py --site symmetry --me zzheng1 --job c8d2-prof4 --partition amddebugq < "$LT/squeue.txt"
envs="C8_PACKAGE=$X"
[ -n "${C8_L8_PACKS:-}" ] && envs="$envs C8_L8_PACKS=$C8_L8_PACKS"
[ -n "${C8_INVENTORY:-}" ] && envs="$envs C8_INVENTORY=$C8_INVENTORY"
id=$(ssh -T symmetry "export PATH=/cm/shared/apps/slurm/current/bin:\$PATH; mkdir -p $D/logs && cd $D && $envs sbatch --parsable --export=ALL $X/benchmarks/symmetry_2026-10-c8/stage4a/scripts/symmetry_prof4.slurm")
echo "prof4 (symmetry) $id: log $D/logs/c8d2-prof4_$id.out; evidence $D/evidence/$T/prof4.$id.0"
ssh -T symmetry "export PATH=/cm/shared/apps/slurm/current/bin:\$PATH; squeue -u zzheng1 -h -o '%i %j %T %P %M %l %R'"
