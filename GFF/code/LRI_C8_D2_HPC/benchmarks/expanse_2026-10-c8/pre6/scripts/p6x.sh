#!/bin/bash
# Mac driver of the Expanse items owed before Stage 6 (user rule 2026-10-05: "symmetry is back, so for the moment only
# use expanse if symmetry is not enough"; Expanse runs only its own checks). Evidence in
# benchmarks/expanse_2026-10-c8/pre6/. Run from the repository root of the main checkout, one step at a time:
#   p6x.sh export          git archive HEAD -> $C8_DATA/pkg/<sha12> (this workflow's ONE new export; an existing one is
#                          refused), checked file by file (benchmarks/expanse_2026-10-c8/setup/export_check_<sha12>.json)
#   p6x.sh seeds X         the two-log seed sync, Expanse side only: symmetry's log is READ (ssh cat, never written) and
#                          merged into Expanse's $C8_DATA/forbidden_seeds.json with export X's tools/seeds.py merge
#                          (under the log's lock; nothing removed or reordered); then the three sets (symmetry, Expanse,
#                          designs/forbidden_seeds.json) are compared and every seed of PENDING_EXPANSE_SYNC.txt is
#                          checked to be in Expanse's log. Copies and sha256 in pre6/seeds/.
#   p6x.sh exp1 X          the J-EXP-1 rerun (A-EXP-3): stage5/fix/scripts/fxe_exp1.slurm of export X on `debug`
#                          (-N 1 --exclusive --mem=240G -t 00:30:00, the debug partition's MaxTime), after the H7E-R
#                          admission on a fresh squeue
#   p6x.sh harvest X ID    the job's Slurm log, its evidence directory (without bulky test trees) and sacct, into pre6/
# Rules: the existing ControlMaster only (`ssh -O check expanse` must say "Master running"; every session uses
# -o BatchMode=yes, so nothing can prompt for a login); before the sbatch a fresh `squeue -A <ACCOUNT>` and the H7E-R
# admission (stage4a/scripts/h7_admit.py: c8d2 normal-QOS <= 11 running / 27 submitted, account <= 32 running, c8d2
# compute+debug nodes <= 4). Records go to pre6/admission/.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../.."
[ -f Makefile ] && [ -e .git ] || { echo "run from a checkout of the package" >&2; exit 64; }
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "no ControlMaster for expanse; nothing done" >&2; exit 69; }
XS() { ssh -o BatchMode=yes -T expanse "$@"; }
D=<SCRATCH>/temp_project/c8d2; R=benchmarks/expanse_2026-10-c8/pre6; A=$R/admission
SYM=<SCRATCH>/c8-d2/forbidden_seeds.json; XL=$D/forbidden_seeds.json
PEND=benchmarks/symmetry_2026-10-c8/stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt
PY=<HOME>/anaconda3/bin/python3; mkdir -p "$A" "$R/seeds" "$R/logs"
LT=$(mktemp -d "${TMPDIR:-/tmp}/c8d2_p6x.XXXXXX"); trap 'rm -rf "$LT"' EXIT
stamp() { date +%Y%m%dT%H%M%S; }
step=${1:?step}; shift
case $step in
export)
  dirty=$(git status --porcelain -- tools src tests Makefile inputs gen slurm vendor cost_models benchmarks/fixtures8 benchmarks/expanse_2026-10-c8/stage5/fix/scripts)
  [ -z "$dirty" ] || { echo "uncommitted changes in exported paths; commit first:"; echo "$dirty"; exit 64; } >&2
  h=$(git rev-parse HEAD); t=${h:0:12}; x=$D/pkg/$t
  { echo "# $(date -u +%FT%TZ) before the export of $t"; XS "timeout 120 lfs quota -u <USER> /expanse/lustre/scratch 2>&1" | tail -3; } | tee -a "$A/lfs_quota.txt"
  if XS "test -e $x"; then echo "$x exists; refusing" >&2; exit 64; fi
  git archive --format=tar "$h" | XS "mkdir -p $x && tar -x -C $x"
  XS "python3 - $x" < benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/tree_manifest.py > "$LT/tree.txt"
  $PY benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/export_check.py "$h" "$LT/tree.txt" expanse "$x" "benchmarks/expanse_2026-10-c8/setup/export_check_$t.json" >&2
  { echo "# $(date -u +%FT%TZ) after the export of $t"; XS "timeout 120 lfs quota -u <USER> /expanse/lustre/scratch 2>&1" | tail -3; } | tee -a "$A/lfs_quota.txt"
  echo "$x";;
seeds)
  X=$1; ts=$(date -u +%Y%m%dT%H%M%SZ); W=$D/work/p6x-seeds
  ssh -o BatchMode=yes -T symmetry "cat $SYM" > "$R/seeds/symmetry_$ts.json"
  XS "cat $XL" > "$R/seeds/expanse_before_$ts.json"
  XS "mkdir -p $W" && XS "cat > $W/from_symmetry_$ts.json" < "$R/seeds/symmetry_$ts.json"
  [ "$(XS "sha256sum < $W/from_symmetry_$ts.json" | cut -c1-64)" = "$(shasum -a 256 < "$R/seeds/symmetry_$ts.json" | cut -c1-64)" ] || { echo "copy to Expanse differs; nothing merged" >&2; exit 3; }
  XS "source ~/c8d2/env_expanse.sh >/dev/null 2>&1; cd $X && python3 -B tools/seeds.py merge $W/from_symmetry_$ts.json --log $XL" | tee "$R/seeds/merge_$ts.json"
  XS "cat $XL" > "$R/seeds/expanse_after_$ts.json"
  (cd "$R/seeds" && shasum -a 256 "symmetry_$ts.json" "expanse_before_$ts.json" "expanse_after_$ts.json" ../../../../designs/forbidden_seeds.json | tee -a sha256.txt)
  $PY - "$R/seeds/symmetry_$ts.json" "$R/seeds/expanse_after_$ts.json" designs/forbidden_seeds.json "$R/seeds/expanse_before_$ts.json" "$PEND" "$R/seeds/check_$ts.json" <<'PY'
import hashlib, json, sys
from pathlib import Path
sym, exp, mir, before, pend, out = map(Path, sys.argv[1:7])
def seeds(p):
    d = json.loads(p.read_bytes()); return d, {int(e['seed']) for e in d['seeds']}
rec = {'utc_checked': __import__('time').strftime('%Y-%m-%dT%H:%M:%SZ', __import__('time').gmtime())}
sets = {}
for k, p in (('symmetry', sym), ('expanse', exp), ('mirror', mir), ('expanse_before', before)):
    d, s = seeds(p); sets[k] = s
    rec[k] = {'file': str(p), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
              'entries': len(d['seeds']), 'distinct_seeds': len(s)}
pending = [int(l.split()[0]) for l in pend.read_text().splitlines() if l.strip() and not l.startswith('#') and l.split()[0].isdigit()]
rec['pending'] = {str(s): {'in_expanse_before': s in sets['expanse_before'], 'in_expanse': s in sets['expanse'],
                           'in_symmetry': s in sets['symmetry'], 'in_mirror': s in sets['mirror']} for s in pending}
rec['added_to_expanse'] = sorted(sets['expanse'] - sets['expanse_before'])
rec['expanse_lost'] = sorted(sets['expanse_before'] - sets['expanse'])
rec['symmetry_minus_expanse'] = sorted(sets['symmetry'] - sets['expanse']); rec['expanse_minus_symmetry'] = sorted(sets['expanse'] - sets['symmetry'])
rec['mirror_minus_expanse'] = sorted(sets['mirror'] - sets['expanse']); rec['expanse_minus_mirror'] = sorted(sets['expanse'] - sets['mirror'])
rec['equal_sets'] = sets['symmetry'] == sets['expanse'] == sets['mirror']
rec['all_pending_in_expanse'] = all(v['in_expanse'] for v in rec['pending'].values())
rec['passed'] = rec['equal_sets'] and rec['all_pending_in_expanse'] and not rec['expanse_lost']
out.write_text(json.dumps(rec, indent=1) + '\n'); print(json.dumps(rec, indent=1)); sys.exit(0 if rec['passed'] else 1)
PY
  ;;
exp1)
  X=$1; name=c8d2-p6x-exp1
  XS "squeue -A <ACCOUNT> -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$LT/squeue.txt" || { echo "squeue failed; nothing submitted" >&2; exit 69; }
  cp "$LT/squeue.txt" "$A/squeue_before_${name}_$(stamp).txt"
  $PY benchmarks/expanse_2026-10-c8/stage4a/scripts/h7_admit.py --site expanse --me <USER> --job "$name" --partition debug --nodes 1 < "$LT/squeue.txt" | tee -a "$A/h7e_r_admission.jsonl"
  sb="-A <ACCOUNT> -p debug -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:30:00 --no-requeue --exclude=<NODE> -J $name"
  id=$(XS "cd $D && C8_PACKAGE=$X sbatch --parsable --export=ALL $sb $X/benchmarks/expanse_2026-10-c8/stage5/fix/scripts/fxe_exp1.slurm")
  echo "$(date -u +%FT%TZ) $name $id debug C8_PACKAGE=$X $sb $X/benchmarks/expanse_2026-10-c8/stage5/fix/scripts/fxe_exp1.slurm" >> "$A/submitted.txt"
  echo "J-EXP-1 job $id; log $D/logs/${name}_$id.out; evidence $D/evidence/$(basename "$X")/fxeexp1.$id.0";;
harvest)
  X=$1; id=$2; name=c8d2-p6x-exp1; t=$(basename "$X"); E=$D/evidence/$t/fxeexp1.$id.0
  XS "cat $D/logs/${name}_$id.out" > "$R/logs/${name}_$id.out"
  XS "cd $(dirname "$E") && tar -cf - $(basename "$E")" | tar -xf - -C "$R"
  XS "sacct -j $id --duplicates -o JobID,JobName%20,Partition,NodeList,AllocCPUS,State,ExitCode,Submit,Start,End,Elapsed,ElapsedRaw,ReqMem,MaxRSS -P" > "$R/sacct.txt"
  cat "$R/sacct.txt";;
*) sed -n '2,/^set -euo/p' "$0" | sed '$d' >&2; exit 64;;
esac
