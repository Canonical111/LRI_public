#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 03:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# W9 (Stage-6 fix round 4, S6-C-R4-03) on symmetry, before and after the fix: a claim's peak RSS on a LARGE index against
# that index's est_peak_bytes. Before the fix (the tools of b58e9b6, export pkg/b58e9b6f4afd, job 570540's build: the same
# executables) production.py run materialized every task row of its index (job_rows, blocks_of_rows) while est_peak_bytes
# counted one block's kernels, threads x 4 MB and 0.5 GiB; since the fix a claim streams its verified task file one block
# at a time and est_peak_bytes adds one block of rows (16 KiB each) and the plan metadata (2 KiB per job entry and per
# inventory row). The finding's shape with 8-point tasks: a test-only pilot `--pilot --points 512 --replicates 2
# --test-graphs all --bootstrap-chunk 8 --shards 1` (one index per group; the a_free_L8 index holds 16,064 graphs x 2
# replicates x 64 tasks = 2,056,192 tasks, about 6.2 million in the plan), planned once by each package's own tools in a
# Slurm job (above 10^6 tasks), each with a fresh seed checked against $C8_SEEDS and added there with a label (test-only
# plans do not register themselves). Then, in each package, one claim of ONE block of the a_free_L8 index
# (`production.py run PLAN --index I --threads 8 --max-blocks 1`: the command a lane runs, bounded to one block; the
# 256 heaviest 8-point tasks, a few CPU-seconds), its own peak RSS taken by getrusage(RUSAGE_SELF) at exit through a
# runpy wrapper (the native worker's in RUSAGE_CHILDREN), its wall time recorded; the index's est_peak_bytes from each
# plan's manifest. Both plan directories are DELETED afterwards. sharedq (Intel; one claim per campaign, so one CPU
# vendor each), outside the H7 cap.
# Usage (from <SCRATCH>/c8d2): C8_PACKAGE=... SEED_OLD=... SEED_NEW=... sbatch --export=ALL -J c8d2-s4mem s4mem.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${SEED_OLD:?}" "${SEED_NEW:?}" "${C8_SEEDS:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s4mem.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
OLD=$D/pkg/b58e9b6f4afd
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
W=$D/work/s4mem-$TAG; mkdir -p "$W"; PL=$W/plans.$SLURM_JOB_ID; mkdir "$PL" || { echo "$PL exists; refusing" >&2; exit 64; }
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); new $C8_PACKAGE ($(cat "$C8_PACKAGE.commit")); old $OLD ($(cat "$OLD.commit")); work $W; evidence $E"
{ hostname; lscpu; free -g; } > "$E/node.txt" 2>&1; grep -E 'Model name' "$E/node.txt"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS C8_INPUTS C8_ALLOW_NO_L8
sha256sum "$C8_PACKAGE/bin/c8d2_gmp" "$OLD/bin/c8d2_gmp" "$C8_PACKAGE/tools/production.py" "$OLD/tools/production.py" | tee "$E/inputs.sha256"
cat > "$E/rss_wrapper.py" <<'PY'
# runs a Python tool as __main__ and records, at exit, the peak RSS of this process (RUSAGE_SELF: the claim's Python
# process only) and of its reaped children (RUSAGE_CHILDREN: the native worker), in KiB as Linux reports them
import atexit, json, os, resource, runpy, sys, time
out = sys.argv[1]; sys.argv = sys.argv[2:]; t0 = time.time()
sys.path[0] = os.path.dirname(os.path.abspath(sys.argv[0]))  # as `python3 TOOL` would set it (the tool imports its siblings)
atexit.register(lambda: open(out, 'w').write(json.dumps({'self_maxrss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                                         'children_maxrss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                                                         'wall_seconds': round(time.time() - t0, 2), 'argv': sys.argv}) + '\n'))
runpy.run_path(sys.argv[0], run_name='__main__')
PY
status=0
for tag in old new; do
  if [ $tag = old ]; then PKG=$OLD; SEED=$SEED_OLD; else PKG=$C8_PACKAGE; SEED=$SEED_NEW; fi
  P=$PL/w9_$tag
  ( cd "$PKG" && python3 -B tools/seeds.py check "$SEED" ) > "$E/seed_check_$tag.txt" 2>&1 || { echo "seed $SEED refused"; status=65; continue; }
  t=$(date +%s)
  ( cd "$PKG" && /usr/bin/time -v -o "$E/time_plan_$tag.txt" python3 -B tools/production.py plan "$P" --pilot --points 512 --replicates 2 --test-graphs all \
      --bootstrap-chunk 8 --shards 1 --threads 8 --checkpoint-tasks 256 --backend gmp --forbid-seeds-from "$C8_SEEDS" --seed "$SEED" ) \
    > "$E/plan_$tag.stdout" 2> "$E/plan_$tag.stderr"; s=$?
  echo "plan ($tag tools) exit $s after $(( $(date +%s) - t )) s"; tail -3 "$E/plan_$tag.stderr" | cut -c1-300
  if [ $s -ne 0 ]; then status=$s; rm -rf "$P" "$P".tmp.*; continue; fi
  ( cd "$C8_PACKAGE" && python3 -B tools/seeds.py add --seed "$SEED" --label "Stage-6 fix round 4: W9 memory check, test-only pilot-shaped plan ($tag tools; $P; one block of one index run, deleted after measurement)" ) >> "$E/seeds_add.txt" 2>&1 \
    || { echo "seed add $SEED FAILED"; status=66; }
  IDX=$(python3 -B -c "import json,sys; m=json.load(open(sys.argv[1])); print([j['id'] for j in m['jobs'] if j['group']=='a_free_L8'][0])" "$P/manifest.json")
  mkdir -p "$TMPDIR/claim_$tag"; t=$(date +%s)
  ( cd "$PKG" && python3 -B "$E/rss_wrapper.py" "$E/claim_rss_$tag.json" tools/production.py run "$P" --index "$IDX" --threads 8 --max-blocks 1 --scratch "$TMPDIR/claim_$tag" ) \
    > "$E/claim_$tag.stdout" 2> "$E/claim_$tag.stderr"; c=$?
  echo "claim ($tag tools) of index $IDX, one block: exit $c after $(( $(date +%s) - t )) s"; tail -3 "$E/claim_$tag.stderr" | cut -c1-300; [ $c -eq 0 ] || status=7
  python3 -B - "$P" "$IDX" "$E/claim_rss_$tag.json" "$E/claim_$tag.json" "$tag" <<'PY' || true
import json, sys
from pathlib import Path
P, idx, tag = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[5]; m = json.loads((P / 'manifest.json').read_text()); j = m['jobs'][idx]
rss = json.loads(Path(sys.argv[3]).read_text()) if Path(sys.argv[3]).exists() else {}
ck = sorted((P / 'groups' / j['group'] / 'checkpoints').glob('*.json'))
rec = {'tools': tag, 'index': idx, 'group': j['group'], 'tasks': j['tasks'], 'blocks': j['blocks'], 'tasks_bytes': j.get('tasks_bytes'), 'est_peak_bytes': j['est_peak_bytes'],
       'plan_tasks': (m.get('scale') or {}).get('tasks'), 'plan_checkpoints': (m.get('scale') or {}).get('checkpoints'), 'plan_jobs': len(m['jobs']),
       'mem_suggestion_mb': (m.get('estimates') or {}).get('mem_suggestion_mb'), 'checkpoints_written': len(ck), 'rss': rss,
       'self_peak_bytes': (rss.get('self_maxrss_kib') or 0) * 1024}
rec['self_peak_over_est_peak_bytes'] = round(rec['self_peak_bytes'] / j['est_peak_bytes'], 4) if rss else None
Path(sys.argv[4]).write_text(json.dumps(rec, indent=1) + '\n'); print(json.dumps(rec, indent=1))
PY
  gzip -c "$P/manifest.json" > "$E/plan_manifest_$tag.json.gz"; du -sb "$P" > "$E/du_plan_$tag.txt"
  rm -rf "$P"; if [ -e "$P" ]; then echo "plan directory $P NOT deleted"; status=70; else echo "deleted $P" | tee -a "$E/deleted.txt"; fi
done
python3 -B - "$E" <<'PY' || status=1
import json, sys
from pathlib import Path
E = Path(sys.argv[1]); r = {t: json.loads((E / f'claim_{t}.json').read_text()) for t in ('old', 'new') if (E / f'claim_{t}.json').exists()}
out = {t: {k: v.get(k) for k in ('tasks', 'est_peak_bytes', 'self_peak_bytes', 'self_peak_over_est_peak_bytes', 'checkpoints_written')} for t, v in r.items()}
new = r.get('new') or {}
out['new_within_estimate'] = bool(new) and new['checkpoints_written'] == 1 and new['self_peak_bytes'] <= new['est_peak_bytes']
out['old_over_its_estimate'] = bool(r.get('old')) and r['old']['self_peak_bytes'] > r['old']['est_peak_bytes']
(E / 'w9_summary.json').write_text(json.dumps(out, indent=1) + '\n'); print(json.dumps(out, indent=1))
sys.exit(0 if out['new_within_estimate'] else 1)
PY
cp -p "$C8_SEEDS" "$E/forbidden_seeds_after.json"; sha256sum "$C8_SEEDS" > "$E/seeds_after.sha256"
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
