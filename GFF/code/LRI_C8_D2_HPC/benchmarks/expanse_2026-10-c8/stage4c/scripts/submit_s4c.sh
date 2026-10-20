#!/bin/bash
# Mac-side driver of the Stage-4c jobs on Expanse (PLAN Stage 4c, A-FLAG; site deviation U1). Run from the repository
# root of a checkout (branch c8 or a profile branch), with everything that is exported committed:
#   bash benchmarks/expanse_2026-10-c8/stage4c/scripts/submit_s4c.sh precheck
#       DEVELOPMENT ONLY, no commit needed: copies the working tree's src/, Makefile, tests/numerics_f1.cpp,
#       tools/build_record.py and tools/common.py to $C8_DATA/work/s4c-<tag>-precheck-<time>/ and runs
#       s4c_precheck.slurm (shared, 16 CPUs, 0:30): default and profile builds, the default executables' sha256
#       against the final default binary, the F1 tools compiled, --describe. Never gate evidence.
#   ... build
#       export HEAD (git archive, checked equal to the archive: setup/export_check_<sha12>.json; an existing export
#       is refused), then s4c_build.slurm (shared, 16 CPUs, 32 GB, 0:45): default + profile builds, A-RPL-8, the
#       preprocessed-program identity and the stub identity. Prints the export path and the job id.
#   ... selftest PKG [--after JOB]
#       s4c_flags_shared.slurm (shared, 32 CPUs, 64 GB, 1:00): numerics_flags.py --self-test at development scales,
#       then the dd stub (--profile dd, reusing the self-test's F1 baseline), which must equal the exact path.
#   ... dev PROFILE PKG [--after JOB] [-- ARGS...]
#       a development F-gate run of PROFILE on shared (32 CPUs, 1:00), ARGS default to $DEV_ARGS below.
#   ... baseline PKG [--after JOB]
#       the full-scale F1 exact baseline on ONE exclusive compute node (s4c_flags_node.slurm, 1:30):
#       numerics_flags.py --f1-baseline-only; the directory to pass to `gate` is printed.
#   ... gate PROFILE PKG BASELINE [--after JOB]
#       the full-scale J-FLAG run of PROFILE on ONE exclusive compute node (1:30); BASELINE is a full-scale F1 baseline
#       directory of the same bin/c8d2_gmp, or - to compute it in the run. With C8_S4C_ARGS2 (and C8_S4C_NAME2) set,
#       a second numerics_flags.py run with those arguments follows in the same job (s4c_flags_node.slurm's
#       FLAGS_ARGS2/FLAGS_NAME2; e.g. the F4 layout control of the framework's all-stub dd executable).
# PKG is an export built by `build` ($C8_DATA/pkg/<sha12>); --after JOB adds --dependency=afterok:JOB.
# Rules: the existing ControlMaster only (`ssh -O check expanse` must say "Master running"; never opens a login), and
# before EVERY sbatch a fresh `squeue -A yun124` with the H7E-R admission (stage4a/scripts/h7_admit.py: c8d2 normal-QOS
# <= 11 running and <= 27 submitted, account <= 32 running, c8d2 compute nodes <= 4, c8d2 shared <= 32) and this
# agent's share: its own live jobs, named c8d2-s4c-$C8_S4C_TAG-*, use at most C8_S4C_MAX_NODES (1) compute nodes and
# C8_S4C_MAX_SHARED (8) shared jobs. Set C8_S4C_TAG per agent (fw, dd, mp256, exp1, gate, ...; default fw).
# Worst cases at the time limits: build 16 x 0.75 = 12 SU; shared run 32 x 1 = 32 SU; node run 128 x 1.5 = 192 SU.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../.."
[ -f Makefile ] && [ -e .git ] || { echo "run from a checkout of the package" >&2; exit 64; }
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "ssh -O check expanse: no ControlMaster running; nothing done" >&2; exit 69; }
D=/expanse/lustre/scratch/zzheng8/temp_project/c8d2; L8=${C8_L8_PACKS:-$D/pkg/c17688158e2b/inputs/packs}
TAGN=${C8_S4C_TAG:-fw}; [[ $TAGN =~ ^[a-z0-9]+$ ]] || { echo "C8_S4C_TAG must be lower-case letters and digits" >&2; exit 64; }
MAXN=${C8_S4C_MAX_NODES:-1}; MAXS=${C8_S4C_MAX_SHARED:-8}; PFX=c8d2-s4c-$TAGN-
DEV_ARGS=${DEV_ARGS:---f1-scale 0.05 --f2-graphs 16 --f4-sample 25 --f4-repeats 2 --f5-threads 1 8 16 --f5-lanes 4 --f5-lane-threads 4}
R=benchmarks/expanse_2026-10-c8/stage4c; A=$R/admission/$TAGN; mkdir -p "$A"
LT=$(mktemp -d "${C8_LOCAL_TMP:-${TMPDIR:-/tmp}}/c8d2_s4c.XXXXXX")
admit() {  # admit <job name> <partition> <nodes>
  ssh -T expanse "squeue -A yun124 -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$LT/squeue.txt" || { echo "squeue failed; nothing submitted" >&2; exit 69; }
  cp "$LT/squeue.txt" "$A/squeue_before_$1_$(date +%Y%m%dT%H%M%S).txt"
  python3 benchmarks/expanse_2026-10-c8/stage4a/scripts/h7_admit.py --site expanse --me zzheng8 --job "$1" --partition "$2" --nodes "$3" < "$LT/squeue.txt" | tee -a "$A/h7e_r_admission.jsonl"
  python3 - "$2" "$3" "$LT/squeue.txt" "$PFX" "$MAXN" "$MAXS" <<'PY'
import sys
part, n, path, pfx, maxn, maxs = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
mine = [l.rstrip('\n').split('|', 6) for l in open(path) if l.strip()]
mine = [f for f in mine if f[5] == 'zzheng8' and f[6].startswith(pfx)]
nodes = sum(int(f[4]) if f[4].isdigit() else 1 for f in mine if set(f[2].split(',')) & {'compute', 'debug'})
shared = sum(1 for f in mine if 'shared' in f[2].split(','))
ok = (nodes + n <= maxn) if part in ('compute', 'debug') else (shared + 1 <= maxs)
print(f'agent share {pfx}*: compute nodes {nodes}/{maxn}, shared jobs {shared}/{maxs}; new {part} job admitted: {ok}')
sys.exit(0 if ok else 65)
PY
}
sub() {  # sub <name> <partition> <nodes> <env assignments> <sbatch args...>: admission, then sbatch; prints the job id
  local name=$1 part=$2 n=$3 envs=$4; shift 4
  admit "$name" "$part" "$n" >&2
  local id; id=$(ssh -T expanse "cd $D && $envs sbatch --parsable --export=ALL -J $name $*")
  echo "$(date -u +%FT%TZ) $name $id $part $envs $*" >> "$A/submitted.txt"; echo "$id"
}
pkg_ok() { ssh -T expanse "test -x $1/bin/c8d2_gmp" || { echo "$1 has no bin/c8d2_gmp: run build first (or pass --after its job)" >&2; [ -n "${AFTER:-}" ] || exit 64; }; }
q() { printf '%q' "$1"; }
cmd=${1:-}; shift || true
AFTER=
case $cmd in
precheck)
  w=$D/work/s4c-$TAGN-precheck-$(date +%Y%m%dT%H%M%S)
  ssh -T expanse "test ! -e $w && mkdir -p $w"
  COPYFILE_DISABLE=1 tar --no-mac-metadata --no-xattrs -cf - src Makefile tests/numerics_f1.cpp tools/build_record.py tools/common.py "$R/scripts/s4c_precheck.slurm" | ssh -T expanse "tar -x -C $w"
  id=$(sub "${PFX}precheck" shared 1 "C8_PRECHECK=$w${C8_S4C_PROFILES:+ C8_S4C_PROFILES=$(q "$C8_S4C_PROFILES")}" "$w/$R/scripts/s4c_precheck.slurm")
  echo "precheck $id tree $w"
  echo "log $D/logs/${PFX}precheck_$id.out; record $w/precheck.json" >&2;;
build)
  dirty=$(git status --porcelain -- tools src tests Makefile inputs benchmarks/fixtures8 "$R/scripts")
  [ -z "$dirty" ] || { echo "uncommitted changes in exported paths; commit first:"; echo "$dirty"; exit 64; } >&2
  ssh -T expanse "lfs quota -u zzheng8 /expanse/lustre/scratch" | tail -2 | tee -a "$A/lfs_quota.txt"
  h=$(git rev-parse HEAD); t=${h:0:12}; x=$D/pkg/$t
  if ssh -T expanse "test -e $x"; then echo "$x exists; refusing (use it with the other steps, or commit anew)" >&2; exit 64; fi
  git archive --format=tar "$h" | ssh -T expanse "mkdir -p $x && tar -x -C $x"
  ssh -T expanse "python3 - $x" < benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/tree_manifest.py > "$LT/c8d2_tree_$t.txt"
  python3 benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/export_check.py "$h" "$LT/c8d2_tree_$t.txt" expanse "$x" "benchmarks/expanse_2026-10-c8/setup/export_check_$t.json" >&2
  id=$(sub "${PFX}build" shared 1 "C8_PACKAGE=$x C8_L8_PACKS=$L8${C8_S4C_PROFILES:+ C8_S4C_PROFILES=$(q "$C8_S4C_PROFILES")}" "$x/$R/scripts/s4c_build.slurm")
  echo "export $x build $id"
  echo "log $D/logs/${PFX}build_$id.out; evidence $D/evidence/$t/s4cbuild.$id.0" >&2;;
selftest|dev|baseline|gate)
  if [ "$cmd" = dev ] || [ "$cmd" = gate ]; then P=${1:?profile}; shift; fi
  X=${1:?export path}; shift
  if [ "$cmd" = gate ]; then BASE=${1:?baseline directory or -}; shift; fi
  if [ "${1:-}" = --after ]; then AFTER=${2:?job id}; shift 2; fi
  [ "${1:-}" = -- ] && shift
  pkg_ok "$X"; dep=${AFTER:+--dependency=afterok:$AFTER}
  case $cmd in
  selftest)
    id=$(sub "${PFX}selftest" shared 1 "C8_PACKAGE=$X FLAGS_NAME=selftest FLAGS_ARGS=$(q "--self-test $DEV_ARGS") FLAGS_NAME2=stub_dd FLAGS_ARGS2=$(q "--profile dd --f1-baseline @OUT1/f1_baseline $DEV_ARGS")" $dep "$X/$R/scripts/s4c_flags_shared.slurm");;
  dev)
    args=${*:-$DEV_ARGS}
    id=$(sub "${PFX}dev" shared 1 "C8_PACKAGE=$X FLAGS_NAME=dev_${P//+/_} FLAGS_ARGS=$(q "--profile $P $args")" $dep "$X/$R/scripts/s4c_flags_shared.slurm");;
  baseline)
    id=$(sub "${PFX}baseline" compute 1 "C8_PACKAGE=$X FLAGS_NAME=f1_baseline_full FLAGS_ARGS=--f1-baseline-only" $dep "$X/$R/scripts/s4c_flags_node.slurm")
    echo "baseline directory (after the job): $D/evidence/$(basename "$X")/s4cgate.$id.0/f1_baseline_full/f1_baseline" >&2;;
  gate)
    b=; [ "$BASE" = - ] || b="--f1-baseline $BASE"
    e2=; if [ -n "${C8_S4C_ARGS2:-}" ]; then e2=" FLAGS_NAME2=${C8_S4C_NAME2:?C8_S4C_NAME2 names the second run} FLAGS_ARGS2=$(q "$C8_S4C_ARGS2")"; fi
    id=$(sub "${PFX}gate" compute 1 "C8_PACKAGE=$X FLAGS_NAME=jflag_${P//+/_} FLAGS_ARGS=$(q "--profile $P $b")$e2" $dep "$X/$R/scripts/s4c_flags_node.slurm");;
  esac
  ev=s4cflags; [ "$cmd" = baseline ] || [ "$cmd" = gate ] && ev=s4cgate
  echo "$cmd $id"
  echo "log $D/logs/${PFX}${cmd}_$id.out; evidence $D/evidence/$(basename "$X")/$ev.$id.0" >&2;;
*) sed -n '2,/^set -euo/p' "$0" | sed '$d' >&2; exit 64;;
esac
ssh -T expanse "squeue -u zzheng8 -h -o '%i %j %T %P %q %M %l %r'" >&2
rm -rf "$LT"
