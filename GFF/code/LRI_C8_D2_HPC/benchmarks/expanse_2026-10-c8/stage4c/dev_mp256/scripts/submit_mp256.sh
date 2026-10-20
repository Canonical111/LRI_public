#!/bin/bash
# Mac-side driver of the R4b (mp256) development speed job on Expanse (Stage 4c; site deviation U1). Run from the
# repository root of a checkout of the flag-mp256 branch:
#   bash benchmarks/expanse_2026-10-c8/stage4c/dev_mp256/scripts/submit_mp256.sh speed PKG [--after JOB]
#       mp256_speed.slurm on ONE exclusive compute node (0:30): exact against mp256 on heavy_free_L8 and heavy_power_L8.
#   bash benchmarks/expanse_2026-10-c8/stage4c/dev_mp256/scripts/submit_mp256.sh prof PKG
#       mp256_prof.slurm on 16 shared cores (0:30): perf symbol profiles of exact and mp256 (informative).
# PKG is an export built by stage4c/scripts/submit_s4c.sh build (it has bin/c8d2_gmp and bin/c8d2_gmp_mp256);
# --after JOB adds --dependency=afterok:JOB. The other steps (precheck, build, dev) are submit_s4c.sh's.
# Rules as submit_s4c.sh: the existing ControlMaster only, and before the sbatch a fresh `squeue -A <ACCOUNT>` with the
# H7E-R admission (stage4a/scripts/h7_admit.py) and this agent's share (job names c8d2-s4c-mp256-*: at most
# C8_S4C_MAX_NODES = 1 compute node and C8_S4C_MAX_SHARED = 8 shared jobs live). Admission records go to
# stage4c/admission/mp256/, as submit_s4c.sh's with C8_S4C_TAG=mp256.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../../.."
[ -f Makefile ] && [ -e .git ] || { echo "run from a checkout of the package" >&2; exit 64; }
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "ssh -O check expanse: no ControlMaster running; nothing done" >&2; exit 69; }
D=<SCRATCH>/temp_project/c8d2
TAGN=mp256; MAXN=${C8_S4C_MAX_NODES:-1}; MAXS=${C8_S4C_MAX_SHARED:-8}; PFX=c8d2-s4c-$TAGN-
R=benchmarks/expanse_2026-10-c8/stage4c; A=$R/admission/$TAGN; mkdir -p "$A"
LT=$(mktemp -d "${C8_LOCAL_TMP:-${TMPDIR:-/tmp}}/c8d2_mp256.XXXXXX")
admit() {  # admit <job name> <partition> <nodes>
  ssh -T expanse "squeue -A <ACCOUNT> -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$LT/squeue.txt" || { echo "squeue failed; nothing submitted" >&2; exit 69; }
  cp "$LT/squeue.txt" "$A/squeue_before_$1_$(date +%Y%m%dT%H%M%S).txt"
  python3 benchmarks/expanse_2026-10-c8/stage4a/scripts/h7_admit.py --site expanse --me <USER> --job "$1" --partition "$2" --nodes "$3" < "$LT/squeue.txt" | tee -a "$A/h7e_r_admission.jsonl"
  python3 - "$2" "$3" "$LT/squeue.txt" "$PFX" "$MAXN" "$MAXS" <<'PY'
import sys
part, n, path, pfx, maxn, maxs = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
mine = [l.rstrip('\n').split('|', 6) for l in open(path) if l.strip()]
mine = [f for f in mine if f[5] == '<USER>' and f[6].startswith(pfx)]
nodes = sum(int(f[4]) if f[4].isdigit() else 1 for f in mine if set(f[2].split(',')) & {'compute', 'debug'})
shared = sum(1 for f in mine if 'shared' in f[2].split(','))
ok = (nodes + n <= maxn) if part in ('compute', 'debug') else (shared + 1 <= maxs)
print(f'agent share {pfx}*: compute nodes {nodes}/{maxn}, shared jobs {shared}/{maxs}; new {part} job admitted: {ok}')
sys.exit(0 if ok else 65)
PY
}
cmd=${1:-}; shift || true
case $cmd in
speed)
  X=${1:?export path}; shift; AFTER=
  if [ "${1:-}" = --after ]; then AFTER=${2:?job id}; shift 2; fi
  ssh -T expanse "test -x $X/bin/c8d2_gmp_mp256" || [ -n "$AFTER" ] || { echo "$X has no bin/c8d2_gmp_mp256: build it first (or pass --after its job)" >&2; exit 64; }
  name=${PFX}speed; admit "$name" compute 1 >&2
  id=$(ssh -T expanse "cd $D && C8_PACKAGE=$X sbatch --parsable --export=ALL -J $name ${AFTER:+--dependency=afterok:$AFTER} $X/$R/dev_mp256/scripts/mp256_speed.slurm")
  echo "$(date -u +%FT%TZ) $name $id compute C8_PACKAGE=$X ${AFTER:+--dependency=afterok:$AFTER} $X/$R/dev_mp256/scripts/mp256_speed.slurm" >> "$A/submitted.txt"
  echo "speed $id"
  echo "log $D/logs/${name}_$id.out; evidence $D/evidence/$(basename "$X")/mp256speed.$id.0" >&2;;
prof)
  # informative perf profile on 16 shared cores; the job script is this checkout's mp256_prof.slurm, copied to
  # $D/work/ (an export older than the script lacks it); the job records its sha256
  X=${1:?export path}; shift
  ssh -T expanse "test -x $X/bin/c8d2_gmp_mp256" || { echo "$X has no bin/c8d2_gmp_mp256" >&2; exit 64; }
  w=$D/work/s4c-mp256-prof-$(date +%Y%m%dT%H%M%S); ssh -T expanse "test ! -e $w && mkdir -p $w"
  ssh -T expanse "cat > $w/mp256_prof.slurm" < "$R/dev_mp256/scripts/mp256_prof.slurm"
  shasum -a 256 "$R/dev_mp256/scripts/mp256_prof.slurm" >&2
  name=${PFX}prof; admit "$name" shared 1 >&2
  id=$(ssh -T expanse "cd $D && C8_PACKAGE=$X sbatch --parsable --export=ALL -J $name $w/mp256_prof.slurm")
  echo "$(date -u +%FT%TZ) $name $id shared C8_PACKAGE=$X $w/mp256_prof.slurm" >> "$A/submitted.txt"
  echo "prof $id"
  echo "log $D/logs/${name}_$id.out; evidence $D/evidence/$(basename "$X")/mp256prof.$id.0" >&2;;
*) sed -n '2,/^set -euo/p' "$0" | sed '$d' >&2; exit 64;;
esac
ssh -T expanse "squeue -u <USER> -h -o '%i %j %T %P %q %M %l %r'" >&2
rm -rf "$LT"
