#!/bin/bash
# Mac-side driver of the Stage-4b integration jobs on Expanse (branch c8; site deviation U1). Run from the repository
# root of the main checkout:
#   PHASE=steps bash benchmarks/expanse_2026-10-c8/stage4b/integration/scripts/submit_int.sh
#       exports S1 (+R5), S2 (+R3a), S3 (+R4a) and S4 (HEAD: +R4f and these scripts); builds (shared) S1, S2, S3, then
#       S4 with the zen2 variants and a speed smoke (afterok S2, S3); gate A (compute: S1, S2), gate B (compute: S3, the
#       zen2 builds B2f and B4, with the replay subset) and the speed job (compute), each afterok on the builds it uses.
#   PHASE=final [FINAL_ZEN2=1] bash .../submit_int.sh
#       exports HEAD (the final candidate after the A-PERF-2 decisions); build (shared; with FINAL_ZEN2=1 also the final
#       GMP_PREFIX=zen2 worker) and the full gate job (compute, afterok): G-L8SELF, thread identity, the quad
#       differential, and with FINAL_ZEN2=1 the zen2 worker's G-L8SELF, thread identity and replay subset.
# Rules: needs the existing ControlMaster (`ssh -O check expanse` must say "Master running"); never opens a login. Before
# EVERY sbatch: a fresh `squeue -A <ACCOUNT>`, the H7E-R admission (stage4a/scripts/h7_admit.py: c8d2 normal-QOS <= 11
# running and <= 27 submitted, account <= 32 running, c8d2 compute nodes <= 4, c8d2 shared <= 32) and this workflow's
# own limit (c8d2-int-* compute nodes <= 4 and shared jobs <= 8 live). Exports are git archive of the commit, checked
# equal to the archive (setup/export_check_<sha12>.json); an existing export is refused. L8 packs are hard-linked from
# C8_L8_PACKS (default the c17688158e2b export's), re-hashed by make. Planned cost (worst case at the time limits):
# PHASE=steps 4 x 16.4 SU/h x 0.75 h + 128 x (0.83 + 0.83 + 1.0) h = ~390 SU; expected ~110 SU.
# PHASE=final 16.4 x 0.75 + 128 x 0.83 = ~119 SU; expected ~25 SU.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../../.."
[ -f Makefile ] && [ -d .git ] && [ "$(git rev-parse --abbrev-ref HEAD)" = c8 ] || { echo "run from the main checkout on branch c8" >&2; exit 64; }
PHASE=${PHASE:?PHASE=steps or PHASE=final}
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "ssh -O check expanse: no ControlMaster running; nothing done" >&2; exit 69; }
D=<SCRATCH>/temp_project/c8d2; L8=${C8_L8_PACKS:-$D/pkg/c17688158e2b/inputs/packs}
R=benchmarks/expanse_2026-10-c8/stage4b/integration; P=benchmarks/expanse_2026-10-c8/stage4b/integration/scripts
dirty=$(git status --porcelain -- tools src tests Makefile inputs benchmarks/fixtures8 "$P")
[ -z "$dirty" ] || { echo "uncommitted changes in exported paths; commit first:"; echo "$dirty"; exit 64; } >&2
LT=$(mktemp -d "${C8_LOCAL_TMP:-${TMPDIR:-/tmp}}/c8d2_int.XXXXXX"); mkdir -p "$R/admission"
echo "phase $PHASE; HEAD $(git rev-parse HEAD); local tmp $LT"
admit() {  # admit <job name> <partition> <nodes>
  ssh -T expanse "squeue -A <ACCOUNT> -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$LT/squeue.txt" || { echo "squeue failed; nothing more submitted" >&2; exit 69; }
  cp "$LT/squeue.txt" "$R/admission/squeue_before_$1_$(date +%Y%m%dT%H%M%S).txt"
  python3 benchmarks/expanse_2026-10-c8/stage4a/scripts/h7_admit.py --site expanse --me <USER> --job "$1" --partition "$2" --nodes "$3" < "$LT/squeue.txt" | tee -a "$R/admission/h7e_r_admission.jsonl"
  python3 - "$2" "$3" "$LT/squeue.txt" <<'PY'
import sys
part, n, path = sys.argv[1], int(sys.argv[2]), sys.argv[3]
mine = [l.rstrip('\n').split('|', 6) for l in open(path) if l.strip()]
mine = [f for f in mine if f[5] == '<USER>' and f[6].startswith('c8d2-int-')]
nodes = sum(int(f[4]) if f[4].isdigit() else 1 for f in mine if set(f[2].split(',')) & {'compute', 'debug'})
shared = sum(1 for f in mine if 'shared' in f[2].split(','))
ok = (nodes + n <= 4) if part in ('compute', 'debug') else (shared + 1 <= 8)
print(f'workflow share: c8d2-int compute nodes {nodes}, shared jobs {shared}; new {part} job admitted: {ok}')
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
ssh -T expanse "lfs quota -u <USER> /expanse/lustre/scratch" | tail -2 | tee -a "$R/admission/lfs_quota.txt"
if [ "$PHASE" = steps ]; then
  X1=$(export_commit 138d486); X2=$(export_commit d46e736); X3=$(export_commit bc0bedc); X4=$(export_commit HEAD)
  Q=$X4/$P; W=$D/work/$(basename "$X4")
  b1=$(sub c8d2-int-build shared 1 "C8_PACKAGE=$X1 C8_L8_PACKS=$L8" "$Q/int_build.slurm")
  b2=$(sub c8d2-int-build shared 1 "C8_PACKAGE=$X2 C8_L8_PACKS=$L8" "$Q/int_build.slurm")
  b3=$(sub c8d2-int-build shared 1 "C8_PACKAGE=$X3 C8_L8_PACKS=$L8" "$Q/int_build.slurm")
  b4=$(sub c8d2-int-build shared 1 "C8_PACKAGE=$X4 C8_L8_PACKS=$L8 INT_VARIANTS=1 INT_S2=$X2 INT_S3=$X3 INT_SMOKE=1" --dependency=afterok:$b2:$b3 "$Q/int_build.slurm")
  ga=$(sub c8d2-int-gate compute 1 "INT_VARIANTS='S1|$X1|-|-;S2|$X2|-|-'" --dependency=afterok:$b1:$b2 -t 00:50:00 "$Q/int_gate.slurm")
  gb=$(sub c8d2-int-gate compute 1 "INT_VARIANTS='S3|$X3|-|-;B2f|$X2|$W/int-zen2-S2src/bin|replay;B4|$X4|$W/int-zen2-S3src/bin|replay'" --dependency=afterok:$b3:$b4 -t 00:50:00 "$Q/int_gate.slurm")
  sp=$(sub c8d2-int-speed compute 1 "INT_S1=$X1 INT_S2=$X2 INT_S3=$X3 INT_S4=$X4" --dependency=afterok:$b1:$b4 "$Q/int_speed.slurm")
  for x in "build S1 $b1 $X1" "build S2 $b2 $X2" "build S3 $b3 $X3" "build S4 $b4 $X4"; do set -- $x
    echo "$1 $2 job $3: log $D/logs/c8d2-int-build_$3.out; evidence $D/evidence/$(basename "$4")/intbuild.$3.0"; done
  echo "gate A job $ga: log $D/logs/c8d2-int-gate_$ga.out; evidence $D/evidence/$(basename "$X2")/intgate.$ga.0"
  echo "gate B job $gb: log $D/logs/c8d2-int-gate_$gb.out; evidence $D/evidence/$(basename "$X4")/intgate.$gb.0"
  echo "speed job $sp: log $D/logs/c8d2-int-speed_$sp.out; evidence $D/evidence/$(basename "$X4")/intspeed.$sp.0"
elif [ "$PHASE" = final ]; then
  XF=$(export_commit HEAD); Q=$XF/$P; W=$D/work/$(basename "$XF"); Z=""; V="FINAL|$XF|-|quaddiff"
  if [ "${FINAL_ZEN2:-0}" = 1 ]; then Z="INT_FINAL_ZEN2=1"; V="$V;FINALzen2|$XF|$W/int-zen2-final/bin|replay"; fi
  bf=$(sub c8d2-int-build shared 1 "C8_PACKAGE=$XF C8_L8_PACKS=$L8 $Z" "$Q/int_build.slurm")
  gf=$(sub c8d2-int-gate compute 1 "INT_VARIANTS='$V'" --dependency=afterok:$bf -t 00:50:00 "$Q/int_gate.slurm")
  echo "build final job $bf: log $D/logs/c8d2-int-build_$bf.out; evidence $D/evidence/$(basename "$XF")/intbuild.$bf.0"
  echo "gate final job $gf: log $D/logs/c8d2-int-gate_$gf.out; evidence $D/evidence/$(basename "$XF")/intgate.$gf.0"
else echo "PHASE must be steps or final" >&2; exit 64; fi
ssh -T expanse "squeue -u <USER> -h -o '%i %j %T %P %q %M %l %r'"
