#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 02:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# pre-Stage-6b on symmetry sharedq: the fixed design tool of 77fab71 (F13 and the F11 follow-up: optimize() searches from
# both split rules with a prune pass and a bounded lattice search; a route-(b) freeze keeps the cheaper feasible of the
# re-optimized design and the exact design re-costed under the profile) on J-DES-5's real data, in the git-archive
# export C8_PACKAGE = pkg/<sha12> (tools/design.py and tools/production.py plan only; nothing is submitted).
#  0. production.py plan --describes its executable and verifies all twelve packs, so: the two L8 packs of C8_L8_PACKS
#     (pkg/7a8aad783c31/inputs/packs) are re-hashed against the export's inputs/manifest.json and hard-linked into
#     inputs/packs/; make -j8 gmp, then make -j8 gmp NUMERICS=dd,mp256 (exact default path otherwise: no GMP_PREFIX, no
#     flag overrides). The executables are recorded against 570239's (gmp 2cc5e88e..., the gated dd+mp256 d5df32ac...);
#     a different hash is recorded, not fatal (test-only plans record executable_gated, they do not enforce it).
#  1. design.py report --test-only on the merged J-SWEEP-2 sweep (sweep2-5d7586e9f1ab, exact, all 24,173 graphs;
#     eta_node from its ledger), exact and --numerics dd+mp256 --cost-model <the package's profile model>.
#  2. For T = 1e-3, 5e-4, 2.5e-4, 1.35e-4:
#     (x) design.py freeze --pilot <J-SWEEP-2> --test-only --target-rel T (J-DES-5's arguments);
#     (b) the route-(b) freeze: the same plus --numerics dd+mp256 --approved-numerics-change "<approval>" --cost-model
#         cost_models/gmp_symmetry_amd_c8_dd+mp256.json --numerics-gate <the 570210 gate record in this export>;
#     each bundle compared (p6b_compare.py) with pre6's 570241 bundle of the same route and target and (x) J-DES-5's;
#     then production.py plan --design <bundle> --test-graphs all with J-DES-5's sizing (gmp, --threads 8,
#     --checkpoint-tasks 256, --index-hours 1.5), (x) with the exact symmetry cost model, (b) with --numerics dd+mp256
#     --approved-numerics-change "<approval>" and the profile model; a fresh seed checked against $C8_SEEDS, under GNU
#     time -v; NOT submitted. des5_measure.py records the plan (caps); the seed is added to $C8_SEEDS with a label; the
#     plan directory is DELETED.
# Usage (from <SCRATCH>/c8d2): C8_PACKAGE=... C8_L8_PACKS=... SEEDS="x1 x2 x3 x4 b1 b2 b3 b4" \
#   sbatch --export=ALL -J c8d2-p6bdes <staged copy of this file>   (pre6b/scripts/p6b.sh sub)
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}" "${SEEDS:?}" "${C8_SEEDS:?}"
REF='user check-in 2026-10-05: dd+mp256 approved for production after the pilot (C62d PLAN-REVIEW-LOG)'
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=p6bdes.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
W=$D/work/p6bdes-$TAG; mkdir -p "$W/plans"; mkdir "$W/bundles" || { echo "$W/bundles exists; refusing" >&2; exit 64; }
SH=$D/jobscripts/pre6b; CMP=$SH/p6b_compare.py
SW=<SCRATCH>/c8-d2/sweep2-5d7586e9f1ab
CM=$C8_PACKAGE/cost_models/gmp_symmetry_amd_c8.json; CMP_DD=$C8_PACKAGE/cost_models/gmp_symmetry_amd_c8_dd+mp256.json
GATE=$C8_PACKAGE/benchmarks/symmetry_2026-10-c8/stage5/close/clflag.570210.0/jflag_dd+mp256/numerics_flags.json
DES5=$D/work/des5-5d7586e9f1ab/bundles; P6=$D/work/p6des-3a250eaa5918/bundles
M=$C8_PACKAGE/benchmarks/symmetry_2026-10-c8/stage5/des5/scripts/des5_measure.py
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE ($(cat "$C8_PACKAGE.commit")); pilot $SW; work $W; evidence $E"
{ hostname; lscpu; free -g; } > "$E/node.txt" 2>&1; grep -E 'Model name' "$E/node.txt"
g++ --version | head -1 | tee "$E/gcc.txt"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS C8_INPUTS C8_ALLOW_NO_L8
cd "$C8_PACKAGE" || exit 64
status=0
# 0. packs and executables
test ! -e bin && test ! -e build || { echo "bin/ or build/ exists in the export; refusing" >&2; exit 64; }
python3 -B - "$C8_L8_PACKS" "$E/l8_packs.json" <<'PY' || { echo "L8 packs do not match inputs/manifest.json; nothing linked" >&2; exit 3; }
import hashlib, json, sys
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2]); man = json.loads(Path('inputs/manifest.json').read_text())['sha256']; rec = {}
for s in ('free', 'power'):
    p = src / f'{s}_L8.pack'; h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''): h.update(b)
    rec[s] = {'source': str(p), 'bytes': p.stat().st_size, 'inode': p.stat().st_ino, 'sha256': h.hexdigest(),
              'manifest': man[f'packs/{s}_L8.pack'], 'equal': h.hexdigest() == man[f'packs/{s}_L8.pack']}
out.write_text(json.dumps(rec, indent=1) + '\n'); print(json.dumps({s: v['equal'] for s, v in rec.items()})); sys.exit(0 if all(v['equal'] for v in rec.values()) else 3)
PY
for s in free power; do ln "$C8_L8_PACKS/${s}_L8.pack" "inputs/packs/${s}_L8.pack" || exit 64; done
t0=$(date +%s)
make -j8 gmp > "$E/make_gmp.log" 2>&1 || { echo "gmp build FAILED"; tail -40 "$E/make_gmp.log"; exit 3; }
echo "make gmp (and inputs) in $(( $(date +%s) - t0 )) s"; sha256sum bin/c8d2_gmp | tee "$E/binaries.sha256"
t0=$(date +%s)
make -j8 gmp NUMERICS=dd,mp256 > "$E/make_dd+mp256.log" 2>&1 || { echo "profile build FAILED"; tail -60 "$E/make_dd+mp256.log"; exit 3; }
echo "make gmp NUMERICS=dd,mp256 in $(( $(date +%s) - t0 )) s"
sha256sum bin/c8d2_gmp > "$E/binaries_after_profile.sha256"; sha256sum bin/c8d2_gmp_dd+mp256 | tee "$E/profile.sha256"
mkdir "$E/describe" "$E/build_records"
for x in c8d2_gmp c8d2_gmp_dd+mp256; do bin/$x --describe > "$E/describe/$x.json"; cp bin/$x.build.json "$E/build_records/"; done
python3 -B - "$E" <<'PY'; [ $? -eq 0 ] || echo "WARNING: executables differ from 570239's (recorded in identity.json; test-only plans continue)"
import json, sys
from pathlib import Path
E = Path(sys.argv[1])
want = {'bin/c8d2_gmp': '2cc5e88e76386c0d5c062eaf347cad95c0731a12d62a1af529660797ed715c17',
        'bin/c8d2_gmp_dd+mp256': 'd5df32ac87d612b2e94cee8dee770160d04f98ce48a421418ce750835f2fc33d'}
rd = lambda f: {l.split()[1]: l.split()[0] for l in (E / f).read_text().splitlines()}
got = {**rd('binaries.sha256'), **rd('profile.sha256')}
rec = {'rule': "570239's builds of 3a250ea (pre6/p6build.570239.0): gmp = the Stage-5 symmetry build of 5d7586e; dd+mp256 = the build the J-FLAG gate 570208/570210 passed",
       'executables': {k: {'sha256': got.get(k), 'p6build_570239': v, 'identical': got.get(k) == v} for k, v in want.items()},
       'gmp_unchanged_by_profile_build': rd('binaries.sha256') == rd('binaries_after_profile.sha256')}
d = json.loads((E / 'describe' / 'c8d2_gmp_dd+mp256.json').read_text()); br = json.loads((E / 'build_records' / 'c8d2_gmp_dd+mp256.build.json').read_text())
np_ = d.get('numerics_params') or {}
rec['profile'] = {'numerics': d.get('numerics'), 'diagnostic': d.get('diagnostic'),
                  'development_overrides': sorted(k for k, v in np_.items() if isinstance(v, dict) and v.get('development')),
                  'stubs': sorted(k for k, v in np_.items() if isinstance(v, dict) and v.get('stub')),
                  'build_record_numerics': br.get('NUMERICS'), 'build_record_parameter_overrides': br.get('parameter_overrides')}
rec['BOOST_LIB_VERSION'] = {p.name: json.loads(p.read_text()).get('BOOST_LIB_VERSION') for p in sorted((E / 'build_records').glob('*.build.json'))}
rec['ok'] = all(v['identical'] for v in rec['executables'].values()) and rec['gmp_unchanged_by_profile_build']
(E / 'identity.json').write_text(json.dumps(rec, indent=1) + '\n')
print('executables identical to 570239:', {k: v['identical'] for k, v in rec['executables'].items()}, '; gmp unchanged by the profile build:',
      rec['gmp_unchanged_by_profile_build'], '; profile numerics:', d.get('numerics'), '; BOOST:', rec['BOOST_LIB_VERSION'])
sys.exit(0 if rec['ok'] else 3)
PY
sha256sum "$HOME/c8d2/env.sh" "$CM" "$CMP_DD" "$GATE" tools/{design,production,accounting,ledger,seeds}.py bin/c8d2_gmp bin/c8d2_gmp_dd+mp256 "$M" \
  "$SH"/p6bdes.slurm "$CMP" | tee "$E/inputs.sha256"
# 1. reports
t=$(date +%s); python3 -B tools/design.py report --pilot "$SW" --test-only --json "$E/report_exact.json" > "$E/report_exact.stdout" 2>&1; s=$?
echo "report exact exit $s after $(( $(date +%s) - t )) s"; head -8 "$E/report_exact.stdout" | cut -c1-200; [ $s -eq 0 ] || status=$s
t=$(date +%s); python3 -B tools/design.py report --pilot "$SW" --test-only --numerics dd+mp256 --cost-model "$CMP_DD" --json "$E/report_dd+mp256.json" \
  > "$E/report_dd+mp256.stdout" 2>&1; s=$?
echo "report dd+mp256 exit $s after $(( $(date +%s) - t )) s"; head -9 "$E/report_dd+mp256.stdout" | cut -c1-200; [ $s -eq 0 ] || status=$s
# 2. freezes and plans
set -- $SEEDS; i=0
for R in x b; do
 for T in 1e-3 5e-4 2.5e-4 1.35e-4; do
  i=$((i+1)); SEED=${!i}; N=${R}_$T; B=$W/bundles/$N; P=$W/plans/$N
  if [ $R = x ]; then FX=(); PX=(--cost-model "$CM"); LBL="exact"; REFS=(--ref "pre6_570241=$P6/p6x_$T" --ref "jdes5_570114=$DES5/des5_$T")
  else FX=(--numerics dd+mp256 --approved-numerics-change "$REF" --cost-model "$CMP_DD" --numerics-gate "$GATE")
       PX=(--numerics dd+mp256 --approved-numerics-change "$REF" --cost-model "$CMP_DD"); LBL="route (b) dd+mp256"; REFS=(--ref "pre6_570241=$P6/p6b_$T"); fi
  t=$(date +%s)
  /usr/bin/time -v -o "$E/time_freeze_$N.txt" python3 -B tools/design.py freeze --pilot "$SW" --test-only --target-rel "$T" --seeds-log "$C8_SEEDS" \
    --out "$B" "${FX[@]}" > "$E/freeze_$N.stdout" 2>&1; s=$?
  echo "freeze $N exit $s after $(( $(date +%s) - t )) s"; [ $s -eq 0 ] || { status=$s; tail -5 "$E/freeze_$N.stdout"; continue; }
  cp -p "$B/design.json" "$E/design_$N.json"; cp -p "$B/design_meta.json" "$E/design_meta_$N.json"; sha256sum "$B"/design.json "$B"/design_meta.json >> "$E/bundles.sha256"
  python3 -B "$CMP" "$B" "${REFS[@]}" --out "$E/compare_$N.json"; s=$?; [ $s -eq 0 ] || { echo "compare $N exit $s (target or caps not met)"; status=$s; }
  python3 -B tools/seeds.py check "$SEED" > "$E/seed_check_$N.txt" 2>&1 || { echo "seed $SEED refused"; status=65; continue; }
  t=$(date +%s)
  /usr/bin/time -v -o "$E/time_plan_$N.txt" python3 -B tools/production.py plan "$P" --design "$B" --test-graphs all "${PX[@]}" --backend gmp \
    --threads 8 --checkpoint-tasks 256 --index-hours 1.5 --forbid-seeds-from "$C8_SEEDS" --seed "$SEED" > "$E/plan_$N.stdout" 2> "$E/plan_$N.stderr"; s=$?
  wall=$(( $(date +%s) - t )); echo "plan $N exit $s after $wall s"; tail -3 "$E/plan_$N.stderr" | cut -c1-300
  if [ $s -ne 0 ]; then status=$s; rm -rf "$P" "$P".tmp.*; continue; fi
  python3 -B tools/seeds.py add --seed "$SEED" --label "pre-Stage-6b check of the fixed design tool (77fab71), plan of the $LBL freeze at target-rel $T ($P; test-only, never submitted, deleted after measurement)" >> "$E/seeds_add.txt" 2>&1 \
    || { echo "seed add $SEED FAILED"; status=66; }
  python3 -B "$M" "$P" "$B" --time "$E/time_plan_$N.txt" --wall "$wall" --out "$E/measure_$N.json"; s=$?; [ $s -eq 0 ] || status=$s
  python3 -B -c "import json,sys; m=json.load(open(sys.argv[1])); json.dump({k: m.get(k) for k in ('numerics', 'approved_numerics_change', 'numerics_route', 'executable_sha256', 'cost_model_sha256', 'design')}, open(sys.argv[2], 'w'), indent=1)" \
    "$P/manifest.json" "$E/route_$N.json"
  gzip -c "$P/manifest.json" > "$E/plan_manifest_$N.json.gz"
  du -sb "$P" > "$E/du_plan_$N.txt"; find "$P" -type f | wc -l >> "$E/du_plan_$N.txt"
  rm -rf "$P"; if [ -e "$P" ]; then echo "plan directory $P NOT deleted"; status=70; else echo "deleted $P" | tee -a "$E/deleted.txt"; fi
 done
done
ls -la "$W/plans" > "$E/plans_after.txt" 2>&1
tar -C "$W" -czf "$E/bundles.tgz" bundles
python3 -B tools/seeds.py list > "$E/seeds_after.txt" 2>&1
cp -p "$C8_SEEDS" "$E/forbidden_seeds_after.json"; sha256sum "$C8_SEEDS" >> "$E/seeds_after.txt"
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
