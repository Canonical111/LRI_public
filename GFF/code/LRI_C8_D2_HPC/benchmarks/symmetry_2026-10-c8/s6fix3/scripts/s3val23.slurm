#!/bin/bash
#SBATCH -p amdq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 06:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Stage-6 fix round 3 on symmetry: the FULL exact validation of the new executables (Z4 changed src/kernel.hpp), on one
# whole amdq node, in the export built by s3build.slurm (afterok; nothing is built here). J-VAL-2 and the exact parts of
# J-VAL-3 run in one job so that the AMD-pool cap of 4 live c8d2-* jobs holds (templates: stage5/scripts/s5val2.slurm,
# job 570028, and s5val3.slurm, job 570029). Every step runs and writes its own record; the job fails if any fails.
#   0. The executables are s3build's (its binaries.sha256 and baseline_prev.sha256), the c7ref workers the plan's
#      e696d7f3.../7e3c8c92...; recorded before and after (nothing may rebuild them).
#   1. J-VAL-2: `make test-full OUTPUT=<evidence>/val2`: tests/validate.py --full (A-RPL-1 G-REF, A-RPL-2 G-C7, A-RPL-3
#      G-JET exact on the L=2 graph and all 3,773 L3-L7 kernels, both backends, against make c7ref), tests/check_points.py
#      (450-digit point checks L3-L8 < 1e-280; since Z1 each tool is compiled from a source snapshot in which its worker is
#      first rebuilt byte for byte), check_inputs, workflow, staging.
#   2. J-VAL-3, exact parts: tests/thread_identity.py (A-RPL-6, the observed OpenMP teams), tests/validate.py --bk8
#      (A-RPL-4 G-BK8), tests/forced_tiers.py (A-RPL-5 through the Z1 source binding; then forced_tiers.py --check
#      RECORD, Z2's acceptance check, must exit 0). The L=2 control (statistical, A-IN-6(b)) and merge_scale are not
#      rerun (no kernel arithmetic changed; the task's scope).
#   3. A-RPL-7 G-L8SELF: tests/validate.py --l8self bin/baseline (the symmetry Stage-3 baseline of tag c8-stage3): the L8
#      sweep sample (1,600 free + 400 power kernels, 2 x 512 points), both backends, every scientific field exact.
#   4. Extra: the same L8 comparison against the previous default build (bin/prev = a42cfb7's 619ddf7d.../2cc5e88e...),
#      exact: Z4 leaves every valid input's output unchanged bit for bit.
# Usage: C8_PACKAGE=... BUILD_EVIDENCE=<s3build evidence dir> sbatch --export=ALL --dependency=afterok:<s3build> -J c8d2-s3val23 s3val23.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${BUILD_EVIDENCE:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s3val23.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE ($(cat "$C8_PACKAGE.commit")); build evidence $BUILD_EVIDENCE; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset C8_INPUTS CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS C8_ALLOW_NO_L8
env | grep -E '^(OMP_|GOMP_|KMP_)' | sort > "$E/omp_env_inherited.txt"; echo "inherited OpenMP controls: $(wc -l < "$E/omp_env_inherited.txt")"
cd "$C8_PACKAGE" || exit 64
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp bin/baseline/c8d2_decimal bin/baseline/c8d2_gmp bin/prev/c8d2_decimal bin/prev/c8d2_gmp"
sha256sum $X | tee "$E/binaries_before.sha256"
python3 - "$E/binaries_before.sha256" "$BUILD_EVIDENCE" <<'PY' || { echo "executables are not s3build's; refusing" >&2; exit 3; }
import sys
from pathlib import Path
got = {l.split()[1]: l.split()[0] for l in open(sys.argv[1]).read().splitlines()}
B = Path(sys.argv[2]); want = {}
for f in ('binaries_after_profile.sha256', 'baseline_prev.sha256'):
    want.update({l.split()[1]: l.split()[0] for l in (B / f).read_text().splitlines()})
plan = {'bin/ref/c7d2_decimal': 'e696d7f30cf2374e6b7051b659af334c0b2c9b385edaed2b0b55d36923124df5',
        'bin/ref/c7d2_gmp': '7e3c8c922bbbc70f0a15752ca23147acc360305ff4a947004484cce3024fe8c3'}
bad = {k: (v, want.get(k)) for k, v in got.items() if want.get(k) != v} | {k: (got.get(k), v) for k, v in plan.items() if got.get(k) != v}
print('executables = s3build\'s, c7ref = the plan\'s:', not bad, bad or ''); sys.exit(1 if bad else 0)
PY
status=0
run() { local name=$1; shift; local t=$(date +%s); echo "== $name $(date -Is)"; "$@" > "$E/$name.stdout" 2>&1; local c=$?
        echo "== $name exit $c after $(( $(date +%s) - t )) s"; echo "$name $c $(( $(date +%s) - t ))" >> "$E/exits.txt"; tail -3 "$E/$name.stdout" | cut -c1-300
        [ $c -eq 0 ] || status=1; return 0; }
# 1. J-VAL-2
run make_test_full make test-full OUTPUT="$E/val2"
grep -E 'passed in|"status"|FAILED|Error' "$E/make_test_full.stdout" | cut -c1-300 | head -40
# 2. J-VAL-3, exact parts
run thread_identity python3 -B tests/thread_identity.py --output "$E/thread_identity.json"
run bk8 python3 -B tests/validate.py --only none --bk8 --jobs 16 --threads 4 --output "$E/bk8.json"
run forced_tiers python3 -B tests/forced_tiers.py --worker bin/c8d2_gmp --threads 64 --output "$E/forced_tiers.json"
run forced_tiers_check python3 -B tests/forced_tiers.py --check "$E/forced_tiers.json"
# 3. A-RPL-7 against the Stage-3 baseline; 4. against the previous default build
run l8self python3 -B tests/validate.py --only none --l8self bin/baseline --jobs 16 --threads 4 --output "$E/l8self.json"
run l8prev python3 -B tests/validate.py --only none --l8self bin/prev --jobs 16 --threads 4 --output "$E/l8prev.json"
sha256sum $X > "$E/binaries_after.sha256"
if cmp -s "$E/binaries_before.sha256" "$E/binaries_after.sha256"; then echo "executables unchanged"; else echo "executables CHANGED" >&2; status=3; fi
python3 - "$E" <<'PY' || status=1
import json, sys
from pathlib import Path
E = Path(sys.argv[1]); out = {}
def load(p):
    try: return json.loads(Path(p).read_text())
    except Exception as e: return {'unreadable': str(e)}
vf = load(E / 'val2/validate_full.json'); out['validate_full'] = vf.get('status')
summ = [t for t in vf.get('tests', []) if t.get('test') == 'replay_summary']
out['replay_summary'] = {k: v for k, v in (summ[0] if summ else {}).items() if not isinstance(v, (list,)) and k != 'reference_worker_command'}
pc = load(E / 'val2/point_checks.json'); out['point_checks'] = pc.get('status')
out['point_checks_max'] = {x.get('backend'): x.get('max_error_scaled_by_absolute_terms') for x in pc.get('results', [])}
out['point_checks_source_binding'] = {x.get('backend'): ((x.get('binding') or {}).get('source_binding') or {}).get('reproduction', {}).get('reproduced') for x in pc.get('results', [])}
for k in ('workflow', 'staging'):
    j = load(E / f'val2/{k}.json'); out[k] = j.get('status') or ('passed' if j.get('passed') else j.get('verdict'))
for k in ('thread_identity', 'bk8', 'l8self', 'l8prev', 'forced_tiers'):
    j = load(E / f'{k}.json'); out[k] = j.get('status') or ('passed' if j.get('passed') is True else 'FAILED')
ti = load(E / 'thread_identity.json'); out['thread_identity_team_sizes_verified'] = ti.get('team_sizes_verified')
ft = load(E / 'forced_tiers.json'); out['forced_tiers_coverage'] = ft.get('coverage')
out['forced_tiers_source_binding'] = ((ft.get('gmp_binding') or {}).get('source_binding') or {}).get('reproduction')
for k in ('l8self', 'l8prev'):
    j = load(E / f'{k}.json'); out[f'{k}_tests'] = [{x: t.get(x) for x in ('sector', 'backend', 'graphs', 'rows', 'quad_points', 'mp_points', 'rule')} for t in j.get('tests', [])]
ok = (out['validate_full'] == 'passed' and out['point_checks'] == 'passed' and all(v is not None and float(v) < 1e-280 for v in out['point_checks_max'].values())
      and all(out[k] == 'passed' for k in ('workflow', 'staging', 'thread_identity', 'bk8', 'l8self', 'l8prev', 'forced_tiers'))
      and (out['forced_tiers_coverage'] or {}).get('complete') is True)
out['ok'] = ok
(E / 'summary.json').write_text(json.dumps(out, indent=1, default=str) + '\n'); print(json.dumps(out, indent=1, default=str)[:4000])
sys.exit(0 if ok else 1)
PY
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
