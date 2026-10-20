#!/bin/bash
# Mac-side driver of the Stage-4b G4b jobs on Expanse (branch c8; site deviation U1): the final J-VAL-2 and J-VAL-3
# (with A-RPL-7 G-L8SELF) on the final default binary. Run from the repository root of the main checkout:
#   bash benchmarks/expanse_2026-10-c8/stage4b/final/scripts/submit_final.sh
# It exports HEAD (git archive, checked equal to the archive: setup/export_check_<sha12>.json; an existing export is
# refused), then submits
#   final_build.slurm  (shared, 16 CPUs, 32 GB, 0:45)   the build, identity against e7ef98d's build;
#   g4b_val2.slurm     (compute, 1 node, 0:45)          J-VAL-2 = make test-full, afterok on the build;
#   g4b_val3.slurm     (compute, 1 node, 1:00)          J-VAL-3 + G-L8SELF + quad differential, afterok on the build.
# Rules: needs the existing ControlMaster (`ssh -O check expanse` must say "Master running"); never opens a login. Before
# EVERY sbatch: a fresh `squeue -A yun124`, the H7E-R admission (stage4a/scripts/h7_admit.py: c8d2 normal-QOS <= 11
# running and <= 27 submitted, account <= 32 running, c8d2 compute nodes <= 4, c8d2 shared <= 32) and this workflow's
# own limit (c8d2-g4b-* compute nodes <= 4, shared jobs <= 8 live). L8 packs are hard-linked from C8_L8_PACKS (default
# the c17688158e2b export's) after the build job re-hashes them against the export's inputs/manifest.json.
# Planned cost (worst case at the time limits): 16.4 SU/h x 0.75 h + 128 x (0.75 + 1.0) h = ~236 SU; expected ~45 SU.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../../.."
[ -f Makefile ] && [ -d .git ] && [ "$(git rev-parse --abbrev-ref HEAD)" = c8 ] || { echo "run from the main checkout on branch c8" >&2; exit 64; }
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "ssh -O check expanse: no ControlMaster running; nothing done" >&2; exit 69; }
D=/expanse/lustre/scratch/zzheng8/temp_project/c8d2; L8=${C8_L8_PACKS:-$D/pkg/c17688158e2b/inputs/packs}
L2SEED=7082694491065029298   # Stage 3's L=2 control seed (job 54637264), registered in $C8_SEEDS
R=benchmarks/expanse_2026-10-c8/stage4b/final; P=$R/scripts
dirty=$(git status --porcelain -- tools src tests Makefile inputs benchmarks/fixtures8 "$P")
[ -z "$dirty" ] || { echo "uncommitted changes in exported paths; commit first:"; echo "$dirty"; exit 64; } >&2
LT=$(mktemp -d "${C8_LOCAL_TMP:-${TMPDIR:-/tmp}}/c8d2_g4b.XXXXXX"); mkdir -p "$R/admission"
echo "HEAD $(git rev-parse HEAD); local tmp $LT"
admit() {  # admit <job name> <partition> <nodes>
  ssh -T expanse "squeue -A yun124 -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$LT/squeue.txt" || { echo "squeue failed; nothing more submitted" >&2; exit 69; }
  cp "$LT/squeue.txt" "$R/admission/squeue_before_$1_$(date +%Y%m%dT%H%M%S).txt"
  python3 benchmarks/expanse_2026-10-c8/stage4a/scripts/h7_admit.py --site expanse --me zzheng8 --job "$1" --partition "$2" --nodes "$3" < "$LT/squeue.txt" | tee -a "$R/admission/h7e_r_admission.jsonl"
  python3 - "$2" "$3" "$LT/squeue.txt" <<'PY'
import sys
part, n, path = sys.argv[1], int(sys.argv[2]), sys.argv[3]
mine = [l.rstrip('\n').split('|', 6) for l in open(path) if l.strip()]
mine = [f for f in mine if f[5] == 'zzheng8' and f[6].startswith('c8d2-g4b-')]
nodes = sum(int(f[4]) if f[4].isdigit() else 1 for f in mine if set(f[2].split(',')) & {'compute', 'debug'})
shared = sum(1 for f in mine if 'shared' in f[2].split(','))
ok = (nodes + n <= 4) if part in ('compute', 'debug') else (shared + 1 <= 8)
print(f'workflow share: c8d2-g4b compute nodes {nodes}, shared jobs {shared}; new {part} job admitted: {ok}')
sys.exit(0 if ok else 65)
PY
}
export_commit() {  # export_commit <commit>: prints the export path; refuses an existing export
  local h t x; h=$(git rev-parse "$1"); t=${h:0:12}; x=$D/pkg/$t
  if ssh -T expanse "test -e $x"; then echo "$x exists; refusing (remove it or use another commit)" >&2; exit 64; fi
  git archive --format=tar "$h" | ssh -T expanse "mkdir -p $x && tar -x -C $x"
  ssh -T expanse "python3 - $x" < benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/tree_manifest.py > "$LT/c8d2_tree_$t.txt"
  python3 benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/export_check.py "$h" "$LT/c8d2_tree_$t.txt" expanse "$x" "benchmarks/expanse_2026-10-c8/setup/export_check_$t.json" >&2
  echo "$x"
}
sub() {  # sub <name> <partition> <nodes> <env assignments> <sbatch args...>: admission, then sbatch; prints the job id
  local name=$1 part=$2 n=$3 envs=$4; shift 4
  admit "$name" "$part" "$n" >&2
  local id; id=$(ssh -T expanse "cd $D && $envs sbatch --parsable --export=ALL -J $name $*")
  echo "$(date -u +%FT%TZ) $name $id $part $envs $*" >> "$R/admission/submitted.txt"; echo "$id"
}
ssh -T expanse "lfs quota -u zzheng8 /expanse/lustre/scratch" | tail -2 | tee -a "$R/admission/lfs_quota.txt"
XF=$(export_commit HEAD); Q=$XF/$P
bf=$(sub c8d2-g4b-build shared 1 "C8_PACKAGE=$XF C8_L8_PACKS=$L8" "$Q/final_build.slurm")
v2=$(sub c8d2-g4b-val2 compute 1 "C8_PACKAGE=$XF" --dependency=afterok:$bf "$Q/g4b_val2.slurm")
v3=$(sub c8d2-g4b-val3 compute 1 "C8_PACKAGE=$XF C8_L2_SEED=$L2SEED" --dependency=afterok:$bf "$Q/g4b_val3.slurm")
echo "build job $bf: log $D/logs/c8d2-g4b-build_$bf.out; evidence $D/evidence/$(basename "$XF")/g4bbuild.$bf.0"
echo "J-VAL-2 job $v2: log $D/logs/c8d2-g4b-val2_$v2.out; evidence $D/evidence/$(basename "$XF")/g4bval2.$v2.0"
echo "J-VAL-3 job $v3: log $D/logs/c8d2-g4b-val3_$v3.out; evidence $D/evidence/$(basename "$XF")/g4bval3.$v3.0"
ssh -T expanse "squeue -u zzheng8 -h -o '%i %j %T %P %q %M %l %r'"
