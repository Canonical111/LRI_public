#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 03:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Stage-6 fix round 4 on symmetry sharedq: re-freeze the route-(b) bundles with the NEW dd+mp256 gate record (s4flag;
# W18: the gate entry must carry the inputs manifest the gate ran on, which 570536's lacks, so the 570539 bundles no
# longer plan), in the export built by s4build.slurm (nothing is built here). The profile build (a46f3060...) and its cost
# model (cost_models/gmp_symmetry_amd_c8_dd+mp256.json, 18e50440..., job 570538) are unchanged, so the model is NOT
# re-measured. Template: s6fix3/scripts/s3des.slurm (job 570539), without the sweep accounting and model install.
#  0. The executables are s4build's, the cost model's executable is the profile build, and the gate record passes this
#     export's design.check_gate with this export's inputs manifest (W18).
#  1. For T = 1e-3, 5e-4, 2.5e-4, 1.35e-4: design.py freeze --pilot <J-SWEEP-2 sweep2-5d7586e9f1ab> --test-only
#     --target-rel T --numerics dd+mp256 --approved-numerics-change "<approval>" --cost-model <the model> --numerics-gate
#     <GATE> (W18: check_gate against the pilot's inputs manifest); p6b_compare.py against 570539's bundle of the same
#     target (work/s3des-997639178c1f/bundles/b_<T>): the same design expected (only the gate entry changed).
#  2. production.py plan --design <bundle> --test-graphs all --numerics dd+mp256 ... (J-DES-5's sizing), a fresh seed,
#     NOT submitted: route (b) re-checks the gate entry (W18: inputs_manifest_sha256 equal to the bundle's) and binds the
#     gated executable to the gate's libgmp (W8: numerics_route.gate_gmp_library); des5_measure.py records the plan, with
#     each index's est_peak_bytes (W9: one block of task rows and the plan metadata added); the seed is added to
#     $C8_SEEDS with a label.
#  3. W7/W8/W9 on a real claim (the 5e-4 plan only): `production.py run PLAN --index I --threads 8 --max-blocks 1`, the
#     claim a lane runs, on the index with the most tasks whose one block is cheap (estimated <= 60 core-s): the claim
#     must check that no dynamic-loader override is set (W7), bind the worker to the gate's libgmp 4dc20a90... (W8: exit
#     64 otherwise) and stream its task rows one block at a time (W9); its own peak RSS (getrusage RUSAGE_SELF, via a
#     runpy wrapper) and its children's are recorded against that index's est_peak_bytes; the runtime pin is recorded.
#     Then the plan directory is DELETED.
# Usage (from <SCRATCH>/c8d2): C8_PACKAGE=... BUILD_EVIDENCE=<s4build> GATE=<s4flag numerics_flags.json> \
#   SEEDS="b1 b2 b3 b4" sbatch --export=ALL --dependency=afterok:<s4flag> -J c8d2-s4des s4des.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${BUILD_EVIDENCE:?}" "${GATE:?}" "${SEEDS:?}" "${C8_SEEDS:?}"
REF='user check-in 2026-10-05: dd+mp256 approved for production after the pilot (C62d PLAN-REVIEW-LOG)'
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s4des.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
W=$D/work/s4des-$TAG; mkdir -p "$W/plans"; mkdir "$W/bundles" || { echo "$W/bundles exists; refusing" >&2; exit 64; }
SW=<SCRATCH>/c8-d2/sweep2-5d7586e9f1ab
CMP_DD=$C8_PACKAGE/cost_models/gmp_symmetry_amd_c8_dd+mp256.json   # 18e50440..., job 570538, build a46f3060... (unchanged)
REF3=$D/work/s3des-997639178c1f/bundles
CMP=$C8_PACKAGE/benchmarks/symmetry_2026-10-c8/pre6b/scripts/p6b_compare.py
M=$C8_PACKAGE/benchmarks/symmetry_2026-10-c8/stage5/des5/scripts/des5_measure.py
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE ($(cat "$C8_PACKAGE.commit")); pilot $SW; gate $GATE; work $W; evidence $E"
{ hostname; lscpu; free -g; } > "$E/node.txt" 2>&1; grep -E 'Model name' "$E/node.txt"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS C8_INPUTS C8_ALLOW_NO_L8
env | grep -E '^(LD_PRELOAD|LD_AUDIT|LD_DYNAMIC_WEAK|GLIBC_TUNABLES|DYLD_)' | sort > "$E/loader_env_inherited.txt"; echo "inherited loader overrides (W7): $(wc -l < "$E/loader_env_inherited.txt")"
cd "$C8_PACKAGE" || exit 64
status=0
sha256sum bin/c8d2_gmp bin/c8d2_gmp_dd+mp256 "$CMP_DD" | tee "$E/binaries.sha256"
python3 -B - "$E/binaries.sha256" "$GATE" "$E/check_gate.json" "$BUILD_EVIDENCE" "$CMP_DD" <<'PY' || { echo "executables, cost model or gate refused"; exit 3; }
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, 'tools'); import design
got = {l.split()[1]: l.split()[0] for l in open(sys.argv[1]).read().splitlines()}
B = Path(sys.argv[4]); want = {l.split()[1]: l.split()[0] for l in (B / 'binaries_after_profile.sha256').read_text().splitlines()}
want = {'bin/c8d2_gmp': want['bin/c8d2_gmp'], 'bin/c8d2_gmp_dd+mp256': (B / 'profile.sha256').read_text().split()[0]}
ok = all(got.get(k) == v for k, v in want.items())
cm = json.loads(Path(sys.argv[5]).read_text()); cm_ok = cm.get('executable_sha256') == want['bin/c8d2_gmp_dd+mp256'] and cm.get('numerics') == 'dd+mp256'
im = hashlib.sha256(Path('inputs/manifest.json').read_bytes()).hexdigest()
g = design.check_gate(Path(sys.argv[2]), 'dd+mp256', json.loads(Path('inputs/inventory.json').read_text()), im)
Path(sys.argv[3]).write_text(json.dumps({'executables_identical': ok, 'cost_model_of_the_profile_build': cm_ok, 'cost_model_sha256': got.get(sys.argv[5]), 'gate': g}, indent=1) + '\n')
print('executables = s4build\'s:', ok, '; cost model of the profile build:', cm_ok, '; check_gate passed:', g['sha256'][:12], 'profile', g['profile_executable_sha256'][:12],
      'inputs', g.get('inputs_manifest_sha256', '')[:12], 'gmp_library', g.get('gmp_library'))
sys.exit(0 if ok and cm_ok and g['profile_executable_sha256'] == want['bin/c8d2_gmp_dd+mp256'] and g['exact_executable_sha256'] == want['bin/c8d2_gmp']
         and g.get('inputs_manifest_sha256') == im else 3)
PY
sha256sum "$HOME/c8d2/env.sh" "$CMP_DD" "$GATE" tools/{design,production,accounting,ledger,seeds}.py "$M" "$CMP" | tee "$E/inputs.sha256"
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
set -- $SEEDS; i=0
for T in 1e-3 5e-4 2.5e-4 1.35e-4; do
  i=$((i+1)); SEED=${!i}; N=b_$T; B=$W/bundles/$N; P=$W/plans/$N
  t=$(date +%s)
  /usr/bin/time -v -o "$E/time_freeze_$N.txt" python3 -B tools/design.py freeze --pilot "$SW" --test-only --target-rel "$T" --seeds-log "$C8_SEEDS" \
    --out "$B" --numerics dd+mp256 --approved-numerics-change "$REF" --cost-model "$CMP_DD" --numerics-gate "$GATE" > "$E/freeze_$N.stdout" 2>&1; s=$?
  echo "freeze $N exit $s after $(( $(date +%s) - t )) s"; [ $s -eq 0 ] || { status=$s; tail -5 "$E/freeze_$N.stdout"; continue; }
  cp -p "$B/design.json" "$E/design_$N.json"; cp -p "$B/design_meta.json" "$E/design_meta_$N.json"; sha256sum "$B"/design.json "$B"/design_meta.json >> "$E/bundles.sha256"
  python3 -B "$CMP" "$B" --ref "s3des_570539=$REF3/$N" --out "$E/compare_$N.json"; s=$?; [ $s -eq 0 ] || { echo "compare $N exit $s (target or caps not met)"; status=$s; }
  python3 -B - "$E/compare_$N.json" "$B/design.json" "$REF3/$N/design.json" "$B/design_meta.json" "$REF3/$N/design_meta.json" <<'PY' || true
import json, sys
c = json.load(open(sys.argv[1])); r = c['refs']['s3des_570539']; n = c['new']
same_design = open(sys.argv[2], 'rb').read() == open(sys.argv[3], 'rb').read()
a, b = json.load(open(sys.argv[4])), json.load(open(sys.argv[5]))
def flat(d, p=''):
    if isinstance(d, dict): return {k2: v2 for k, v in d.items() for k2, v2 in flat(v, f'{p}/{k}').items()}
    if isinstance(d, list) and d and all(isinstance(x, dict) for x in d): return {k2: v2 for i, v in enumerate(d) for k2, v2 in flat(v, f'{p}[{i}]').items()}
    return {p: d}
fa, fb = flat(a), flat(b); meta_diff = sorted(k for k in set(fa) | set(fb) if fa.get(k) != fb.get(k))
print('against 570539:', {k: r.get(k) for k in ('counts_equal', 'replicates_equal', 's_equal', 'batches_equal', 'eta_node_equal')}, '; design.json byte-identical', same_design,
      '; cost ratio', r.get('cost_ratio_new_over_ref'), '; SE ratio', r.get('se_ratio_new_over_ref'), '; meets target', n.get('meets_target'), '; caps ok', n.get('caps_ok'),
      '; design_meta fields that differ', meta_diff[:20])
json.dump({'design_json_identical': same_design, 'design_meta_differing_fields': meta_diff}, open(sys.argv[1].replace('compare_', 'meta_diff_'), 'w'), indent=1)
PY
  python3 -B tools/seeds.py check "$SEED" > "$E/seed_check_$N.txt" 2>&1 || { echo "seed $SEED refused"; status=65; continue; }
  t=$(date +%s)
  /usr/bin/time -v -o "$E/time_plan_$N.txt" python3 -B tools/production.py plan "$P" --design "$B" --test-graphs all --numerics dd+mp256 \
    --approved-numerics-change "$REF" --cost-model "$CMP_DD" --backend gmp --threads 8 --checkpoint-tasks 256 --index-hours 1.5 \
    --forbid-seeds-from "$C8_SEEDS" --seed "$SEED" > "$E/plan_$N.stdout" 2> "$E/plan_$N.stderr"; s=$?
  wall=$(( $(date +%s) - t )); echo "plan $N exit $s after $wall s"; tail -3 "$E/plan_$N.stderr" | cut -c1-300
  if [ $s -ne 0 ]; then status=$s; rm -rf "$P" "$P".tmp.*; continue; fi
  python3 -B tools/seeds.py add --seed "$SEED" --label "Stage-6 fix round 4: plan of the route (b) dd+mp256 re-freeze (W18 gate re-run) at target-rel $T ($P; test-only, never submitted, deleted after measurement)" >> "$E/seeds_add.txt" 2>&1 \
    || { echo "seed add $SEED FAILED"; status=66; }
  python3 -B "$M" "$P" "$B" --time "$E/time_plan_$N.txt" --wall "$wall" --out "$E/measure_$N.json"; s=$?; [ $s -eq 0 ] || status=$s
  python3 -B -c "import json,sys; m=json.load(open(sys.argv[1])); json.dump({k: m.get(k) for k in ('numerics', 'approved_numerics_change', 'numerics_route', 'executable_sha256', 'cost_model_sha256', 'cost_model_numerics', 'design')}, open(sys.argv[2], 'w'), indent=1)" \
    "$P/manifest.json" "$E/route_$N.json"
  python3 -B - "$P/manifest.json" "$E/peaks_$N.json" <<'PY' || true
import json, sys
m = json.load(open(sys.argv[1])); jobs = m['jobs']
pk = sorted(jobs, key=lambda j: -j['est_peak_bytes'])[:5]; big = sorted(jobs, key=lambda j: -j.get('tasks', 0))[:5]
rec = {'jobs': len(jobs), 'tasks': sum(j.get('tasks', 0) for j in jobs), 'max_est_peak_bytes': pk[0]['est_peak_bytes'], 'mem_suggestion_mb': (m.get('estimates') or {}).get('mem_suggestion_mb'),
       'largest_peaks': [{k: j.get(k) for k in ('id', 'group', 'tasks', 'blocks', 'est_peak_bytes', 'est_core_seconds')} for j in pk],
       'most_tasks': [{k: j.get(k) for k in ('id', 'group', 'tasks', 'blocks', 'est_peak_bytes', 'est_core_seconds')} for j in big]}
json.dump(rec, open(sys.argv[2], 'w'), indent=1); print('W9 peaks', json.dumps({k: rec[k] for k in ('jobs', 'tasks', 'max_est_peak_bytes')}), 'most tasks', json.dumps(rec['most_tasks'][:2]))
PY
  if [ "$T" = 5e-4 ]; then  # 3. W7/W8/W9: one real claim (one block) of the index with the most tasks among those whose one block is cheap
    IDX=$(python3 -B -c "
import json,sys; m=json.load(open(sys.argv[1])); ok=[j for j in m['jobs'] if j.get('blocks') and (j.get('est_core_seconds') or 0)/j['blocks'] <= 60]
print(max(ok, key=lambda j: (j.get('tasks',0), -j['id']))['id'] if ok else '')" "$P/manifest.json")
    if [ -n "$IDX" ]; then
      mkdir -p "$TMPDIR/claim"; t=$(date +%s)
      python3 -B "$E/rss_wrapper.py" "$E/claim_rss_$N.json" tools/production.py run "$P" --index "$IDX" --threads 8 --max-blocks 1 --scratch "$TMPDIR/claim" \
        > "$E/claim_$N.stdout" 2> "$E/claim_$N.stderr"; c=$?
      echo "claim of index $IDX (one block) exit $c after $(( $(date +%s) - t )) s"; tail -5 "$E/claim_$N.stderr" | cut -c1-300; [ $c -eq 0 ] || status=7
      cp -p "$P/runtime_identity.json" "$E/runtime_identity_$N.json" 2>/dev/null; cp -p "$P/cpu_vendor.json" "$E/cpu_vendor_$N.json" 2>/dev/null
      python3 -B - "$P" "$IDX" "$E/claim_rss_$N.json" "$E/claim_$N.json" "$E/route_$N.json" <<'PY' || status=7
import json, sys
from pathlib import Path
P, idx = Path(sys.argv[1]), int(sys.argv[2]); m = json.loads((P / 'manifest.json').read_text()); j = m['jobs'][idx]
rss = json.loads(Path(sys.argv[3]).read_text()) if Path(sys.argv[3]).exists() else {}
ck = sorted((P / 'groups' / j['group'] / 'checkpoints').glob('*.json')); doc = json.loads(ck[0].read_text()) if ck else {}
fp = (doc.get('runtime') or {}).get('fingerprint') or {}; libs = fp.get('libraries') or {}
gmp = {k: (v.get('sha256') if isinstance(v, dict) else v) for k, v in libs.items() if 'libgmp.so' in k and 'gmpxx' not in k}
nr = json.loads(Path(sys.argv[5]).read_text()).get('numerics_route') or {}
rec = {'index': idx, 'group': j['group'], 'tasks': j.get('tasks'), 'blocks': j.get('blocks'), 'est_peak_bytes': j['est_peak_bytes'], 'est_core_seconds': j.get('est_core_seconds'),
       'checkpoints_written': len(ck), 'rss': rss, 'self_peak_bytes': (rss.get('self_maxrss_kib') or 0) * 1024,
       'self_peak_within_est_peak_bytes': bool(rss) and rss['self_maxrss_kib'] * 1024 <= j['est_peak_bytes'],
       'w8_gate_gmp_library': nr.get('gate_gmp_library'), 'w8_worker_libgmp': gmp, 'w8_bound': bool(gmp) and set(gmp.values()) <= set(nr.get('gate_gmp_library') or []),
       'w7_preload_order': fp.get('preload_order'), 'w7_loader_env': fp.get('loader_env'), 'host': fp.get('host'), 'cpu_model': fp.get('cpu_model'),
       'omp_team': (doc.get('runtime') or {}).get('omp_team')}
Path(sys.argv[4]).write_text(json.dumps(rec, indent=1, default=str) + '\n'); print(json.dumps(rec, indent=1, default=str)[:2500])
sys.exit(0 if rec['checkpoints_written'] == 1 and rec['self_peak_within_est_peak_bytes'] and rec['w8_bound'] and not rec['w7_preload_order'] else 1)
PY
    else echo "no cheap index for the claim"; status=7; fi
  fi
  ls -la "$P/design_bundle" > "$E/design_bundle_$N.txt" 2>&1; (cd "$P/design_bundle" 2>/dev/null && find . -type f | sort | xargs sha256sum) >> "$E/design_bundle_$N.txt" 2>&1
  gzip -c "$P/manifest.json" > "$E/plan_manifest_$N.json.gz"
  du -sb "$P" > "$E/du_plan_$N.txt"; find "$P" -type f | wc -l >> "$E/du_plan_$N.txt"
  rm -rf "$P"; if [ -e "$P" ]; then echo "plan directory $P NOT deleted"; status=70; else echo "deleted $P" | tee -a "$E/deleted.txt"; fi
done
ls -la "$W/plans" > "$E/plans_after.txt" 2>&1
tar -C "$W" -czf "$E/bundles.tgz" bundles
cp -p "$C8_SEEDS" "$E/forbidden_seeds_after.json"; sha256sum "$C8_SEEDS" > "$E/seeds_after.sha256"
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
