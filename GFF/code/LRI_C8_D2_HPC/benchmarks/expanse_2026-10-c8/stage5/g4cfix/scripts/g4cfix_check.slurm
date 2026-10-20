#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:45:00 --no-requeue
#SBATCH -J c8d2-s5-g4cfix
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 5, the G4c verifier fixes on Expanse (one shared job; site deviation U1). C8_WORK is `git archive` of the fix
# commit (the Mac driver extracts it and checks it file by file). Evidence: $C8_DATA/evidence/g4cfix-<sha12>/g4cfix.<job>.0/
# with g4cfix.json (every check and its verdict). Exit 3 when a check fails.
#   D3  numerics_flags.register_f2_seeds($C8_SEEDS, 820262401): the J-FLAG F2 base seed and its 48 derived native and
#       net seeds into the Expanse seed log (tools/seeds.py add under the log's lock; entries already there stay).
#   D2  (a) bin/c8d2_decimal and bin/c8d2_gmp built here against the final default binary 99a51c1d... and 1d2a2181...;
#       (b) the profile executables dd, mp256, exp1 and dd+mp256+exp1 without overrides: no "development" in
#       --describe, and their sha256 against the gate export's (C8_GATE_PKG, default pkg/5569c535dcfd);
#       (c) override builds, each in its own copy of the tree: mp256 CPPFLAGS=-DC8_MP256_RATIO=1e-60, exp1
#       CPPFLAGS=-DC8_EXP1_RANGE=4000, dd CPPFLAGS="-DC8_DD_DEVELOPMENT -DC8_DD_RATIO=1e-21": --describe says
#       "development":true (mp256 and exp1 also name the override), the build record lists the overrides with
#       "development": true, and production.py plan's executable checks (describe, read_build_record) refuse each.
#   D1  design.py rates --rule one-step on J-SWEEP-1 (C8_SWEEP1) with the Stage-4c source bundle (C8_R7/src_bundle):
#       its rate tables equal the Stage-4c provisional map's (C8_R7/prov/rates.json, from dev_r7's r7_spec.py), and
#       its per-stratum record equals r7_spec.py's (dev_r7/expanse/r7prep.54673789.0/spec_derivation.json).
#   D6  the survey for the export pruning: every pkg/<sha12> path in $C8_DATA/evidence and $C8_DATA/logs (file:match),
#       every c8d2/pkg path in C63d's c8d3 evidence, logs, intents and ledger, and per export its baseline
#       directories, F1 stores and L8 packs (with hard-link counts).
# Usage: C8_WORK=<archive dir> sbatch --export=ALL g4cfix_check.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_WORK:?}" "${C8_SEEDS:?}"
GATE=${C8_GATE_PKG:-$C8_DATA/pkg/5569c535dcfd}; SW1=${C8_SWEEP1:-$C8_DATA/sweep1-81aa9770e6fe}; R7=${C8_R7:-$C8_DATA/r7-ebf01f62e833}
TAG=$(basename "$C8_WORK"); RUN=g4cfix.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); work $C8_WORK; gate export $GATE; J-SWEEP-1 $SW1; r7 $R7; seeds $C8_SEEDS; evidence $E"
lscpu | grep -E 'Model name'; g++ --version | head -1
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_WORK" || exit 64
test ! -e bin || { echo "bin/ exists in $C8_WORK; refusing" >&2; exit 64; }
step() { echo "== $(date -Is) $*"; }

step "D3: register the J-FLAG F2 seeds in $C8_SEEDS"
cp "$C8_SEEDS" "$E/seeds_before.json"
python3 -B - "$C8_SEEDS" > "$E/d3_register.json" 2> "$E/d3_register.stderr" <<'PY'
import json, sys
from pathlib import Path
sys.path[:0] = ['tools', 'tests']
import numerics_flags as NF
print(json.dumps(NF.register_f2_seeds(Path(sys.argv[1]), 820262401), indent=1))
PY
echo "exit $?"; cat "$E/d3_register.json" "$E/d3_register.stderr"; cp "$C8_SEEDS" "$E/seeds_after.json"

step "D2: default and profile builds (no override) in $C8_WORK"
make -j2 bin/c8d2_decimal bin/c8d2_gmp > "$E/make_default.log" 2>&1 || { echo "default build FAILED"; tail -40 "$E/make_default.log"; }
pids=()
for p in dd mp256 exp1 dd,mp256,exp1; do
  c=${p//,/+}; make "bin/c8d2_gmp_$c" NUMERICS="$p" > "$E/make_$c.log" 2>&1 & pids+=($!)
done
step "D2: override builds, each in its own copy of the tree"
for spec in "mp256|-DC8_MP256_RATIO=1e-60" "exp1|-DC8_EXP1_RANGE=4000" "dd|-DC8_DD_DEVELOPMENT -DC8_DD_RATIO=1e-21"; do
  p=${spec%%|*}; f=${spec#*|}; t=ov_$p; mkdir "$t" && cp -r src Makefile tools "$t/" || exit 64
  (cd "$t" && make "bin/c8d2_gmp_$p" NUMERICS="$p" CPPFLAGS="$f") > "$E/make_ov_$p.log" 2>&1 & pids+=($!)
done
for pid in "${pids[@]}"; do wait "$pid" || echo "a build exited $?"; done
step "D2: checks"
python3 -B - "$E" "$GATE" > "$E/d2.json" 2> "$E/d2.stderr" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path
E, gate = Path(sys.argv[1]), Path(sys.argv[2]); sys.path[:0] = ['tools']
import production as prod
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).exists() else None
desc = lambda e: json.loads(subprocess.run([str(e), '--describe'], capture_output=True, text=True, check=True).stdout)
final = {'bin/c8d2_decimal': '99a51c1d3f520f16a846eea90149e6cb9d42772db819dbdb2286cb12cb13bcbf', 'bin/c8d2_gmp': '1d2a218147ef52b5d0ac37dd8aaead55045ab4fe68e48ec963ea4b8e93024faa'}
rec = {'default': {k: {'sha256': h(k), 'final': v, 'identical': h(k) == v} for k, v in final.items()}, 'profiles': {}, 'overrides': {}}
for name in ('dd', 'mp256', 'exp1', 'dd+mp256+exp1'):
    e = Path(f'bin/c8d2_gmp_{name}'); g = gate / 'bin' / e.name
    if not e.exists(): rec['profiles'][name] = {'built': False}; continue
    d = desc(e); br = json.loads(Path(str(e) + '.build.json').read_text())
    dev = sorted(k for k, v in d['numerics_params'].items() if v.get('development'))
    try: prod.describe(e, name); prod.read_build_record(e); refused = None
    except ValueError as x: refused = str(x)
    rec['profiles'][name] = {'built': True, 'sha256': h(e), 'gate_sha256': h(g), 'identical_to_gate': h(e) == h(g), 'numerics_params': d['numerics_params'],
                             'development_profiles': dev, 'build_record_parameter_overrides': br.get('parameter_overrides'), 'build_record_development': br.get('development'),
                             'plan_refusal': refused, 'ok': not dev and br.get('parameter_overrides') == [] and br.get('development') is False and refused is None}
for p, ov in (('mp256', ['-DC8_MP256_RATIO=1e-60']), ('exp1', ['-DC8_EXP1_RANGE=4000']), ('dd', ['-DC8_DD_DEVELOPMENT', '-DC8_DD_RATIO=1e-21'])):
    e = Path(f'ov_{p}/bin/c8d2_gmp_{p}')
    if not e.exists(): rec['overrides'][p] = {'built': False, 'ok': False}; continue
    d = desc(e); br = json.loads(Path(str(e) + '.build.json').read_text()); np_ = d['numerics_params'][p]
    r1 = r2 = None
    try: prod.describe(e, p)
    except ValueError as x: r1 = str(x)
    try: prod.read_build_record(e)
    except ValueError as x: r2 = str(x)
    want_ov = {'mp256': ['C8_MP256_RATIO'], 'exp1': ['C8_EXP1_RANGE'], 'dd': None}[p]
    ok = np_.get('development') is True and np_.get('overrides') == want_ov and br.get('parameter_overrides') == ov and br.get('development') is True \
         and r1 is not None and 'development build' in r1 and r2 is not None and 'profile-parameter overrides' in r2
    rec['overrides'][p] = {'built': True, 'sha256': h(e), 'numerics_params': np_, 'build_record_parameter_overrides': br.get('parameter_overrides'),
                           'build_record_development': br.get('development'), 'CPPFLAGS': br.get('CPPFLAGS'), 'plan_describe_refusal': r1, 'plan_build_record_refusal': r2, 'ok': ok}
rec['ok'] = all(v['identical'] for v in rec['default'].values()) and all(v.get('ok') for v in rec['profiles'].values()) and all(v['ok'] for v in rec['overrides'].values())
print(json.dumps(rec, indent=1)); sys.exit(0 if rec['ok'] else 3)
PY
d2=$?; echo "D2 exit $d2"; cat "$E/d2.stderr"
python3 -c "import json,sys;r=json.load(open(sys.argv[1]));print(json.dumps({'default':{k:v['identical'] for k,v in r['default'].items()},'profiles_identical_to_gate':{k:v.get('identical_to_gate') for k,v in r['profiles'].items()},'profiles_ok':{k:v.get('ok') for k,v in r['profiles'].items()},'overrides_ok':{k:v['ok'] for k,v in r['overrides'].items()}},indent=1))" "$E/d2.json"
mkdir -p "$E/build_records" "$E/describe"
for x in bin/*.build.json ov_*/bin/*.build.json; do cp "$x" "$E/build_records/$(echo "$x" | tr / _)"; done
sha256sum bin/c8d2_* ov_*/bin/c8d2_* 2>/dev/null | grep -v build.json | tee "$E/binaries.sha256"

step "D1: design.py rates --rule one-step on J-SWEEP-1"
python3 -B tools/design.py rates --pilot "$SW1" --source-bundle "$R7/src_bundle" --rule one-step --out "$C8_WORK/rule_prov" > "$E/d1_rates_out.json" 2> "$E/d1_rates.stderr"
echo "exit $?"; cat "$E/d1_rates_out.json"; tail -5 "$E/d1_rates.stderr"
cp "$C8_WORK/rule_prov/design_meta.json" "$E/d1_rule_prov_design_meta.json" 2>/dev/null
python3 -B - "$C8_WORK/rule_prov" "$R7/prov/rates.json" benchmarks/expanse_2026-10-c8/stage4c/dev_r7/expanse/r7prep.54673789.0/spec_derivation.json > "$E/d1.json" <<'PY'
import json, math, sys
from pathlib import Path
new, old, rec = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text()), json.loads(Path(sys.argv[3]).read_text())
r = {'built': (new / 'rates.json').exists()}
if r['built']:
    nr = json.loads((new / 'rates.json').read_text()); meta = json.loads((new / 'design_meta.json').read_text()); rule = meta['rate_rule']
    r['rates_tables_equal_stage4c_map'] = nr['rates'] == old['rates']; r['spec_equal'] = rule['spec'] == rec['spec']
    rows = []
    for a, b in zip(rule['strata'], rec['strata']):
        eq = all(a[k] == b[k] for k in ('sector', 'L', 'graphs', 'replicates', 'points', 'rate_a', 'rate_b'))
        num = all(math.isclose(a[k][c], b[k][c], rel_tol=1e-12, abs_tol=0) for k in ('W', 'V', 'C_seconds_per_point_sum') for c in 'ab')
        rat = math.isclose(a['ratio_W2_b_over_a'], b['ratio_W2_b_over_a'], rel_tol=1e-12, abs_tol=0)
        bq = (a['bootstrap_ratio_W2'] is None) == (b['bootstrap_ratio_W2'] is None) and (a['bootstrap_ratio_W2'] is None or all(
            math.isclose(a['bootstrap_ratio_W2'][q], b['bootstrap_ratio_W2'][q], rel_tol=1e-12, abs_tol=0) for q in b['bootstrap_ratio_W2']))
        rows.append({'sector': a['sector'], 'L': a['L'], 'graphs': a['graphs'], 'ratio': a['ratio_W2_b_over_a'], 'decision': a['decision'], 'rates': [a['rate_a'], a['rate_b']],
                     'fields_equal': eq, 'W_V_C_equal_1e-12': num, 'ratio_equal_1e-12': rat, 'bootstrap_equal_1e-12': bq})
    r['strata'] = rows; r['rule'] = {k: rule[k] for k in ('name', 'step', 'band', 'min_graphs', 'bootstrap')}; r['provisional'] = meta['provisional']
    r['ok'] = r['rates_tables_equal_stage4c_map'] and r['spec_equal'] and len(rows) == len(rec['strata']) == 12 and all(x['fields_equal'] and x['W_V_C_equal_1e-12'] and x['ratio_equal_1e-12'] and x['bootstrap_equal_1e-12'] for x in rows)
else: r['ok'] = False
print(json.dumps(r, indent=1)); sys.exit(0 if r['ok'] else 3)
PY
d1=$?; echo "D1 exit $d1"; python3 -c "import json,sys;r=json.load(open(sys.argv[1]));print({k:r.get(k) for k in ('rates_tables_equal_stage4c_map','spec_equal','ok')})" "$E/d1.json"

step "D6: export survey"
grep -rIHoE 'pkg/[0-9a-f]{12}(/[^ "'"'"',;)]*)?' "$C8_DATA/evidence" "$C8_DATA/logs" 2>/dev/null | sed "s#^$C8_DATA/##" | sort -u > "$E/d6_pkg_refs.txt"
echo "$(wc -l < "$E/d6_pkg_refs.txt") distinct file:path references"
# C63d's tree (c8d3): any use of a c8d2 export there
X3=$(dirname "$C8_DATA")/c8d3; grep -rIHoE 'c8d2/pkg/[0-9a-f]{12}(/[^ "'"'"',;)]*)?' "$X3/evidence" "$X3/logs" "$X3/intents" "$X3/ledger.jsonl" 2>/dev/null | sort -u > "$E/d6_c8d3_refs.txt"
echo "$(wc -l < "$E/d6_c8d3_refs.txt") references to c8d2 exports in $X3"
for x in "$C8_DATA"/pkg/*/; do
  find "$x" -maxdepth 3 \( -name baseline -o -name 'f1_baseline*' -o -name '*_L8.pack' -o -name 'refs*' -o -name 'ref' \) -printf '%n %s %p\n' 2>/dev/null
done | sed "s#$C8_DATA/##" > "$E/d6_export_content.txt"; cat "$E/d6_export_content.txt"
st=0; [ "$d2" = 0 ] || st=3; [ "$d1" = 0 ] || st=3; grep -q '"added"' "$E/d3_register.json" || st=3
echo "finished $(date -Is), status $st"; exit $st
