#!/bin/bash
#SBATCH -p amdq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 03:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# The dd+mp256 J-FLAG gate re-run for W18 (Stage-6 fix round 4): the gate record must now carry an authenticated
# input-set identity (tests/numerics_flags.py input_identity: the inputs manifest sha256, every input, pack and vendored
# pin verified against it before anything is built and again at the end, complete), and design.check_gate requires it and
# its equality with the plan's or pilot's inputs manifest. Fix round 3's record (job 570536) predates the field and is
# refused for exactly that, so the gate runs again on the SAME profile build a46f3060... (no src/ change; s4build checks
# the bytes) with a FRESH F1 baseline (a reused baseline has no input identity and is refused). Template:
# s6fix3/scripts/s3flag.slurm (job 570536). One whole amdq node, in the export built by s4build.slurm (afterok).
#   1. Identity: bin/c8d2_decimal, bin/c8d2_gmp and bin/c8d2_gmp_dd+mp256 are s4build's, before and after the gate.
#   2. tests/numerics_flags.py --profile dd+mp256 at FULL scale (A-FLAG-3; no development option): fresh F1 baseline, X2
#      binding (since fix round 4 with the build commands' relative words mirrored, none here), F1 coverage (X1), libgmp
#      provenance (Y1/Z19), F2 (base seed 820262401: its 49 seeds already in symmetry's log; reserved in one locked
#      transaction since W20), F3, F4, F5 with the observed teams (X3), the inputs block (W18).
#   3. design.check_gate(record, 'dd+mp256', inventory, inputs_manifest_sha256 = this export's inputs/manifest.json):
#      must pass and return inputs_manifest_sha256; the same check of 570536's record must refuse it for exactly the
#      missing input-set identity (W18 on real data); 570536 with an inputs manifest of another sha256 asserted is refused too.
#   4. For the record: F1/F2/F3 compared with 570536's (identical streams and executables, so equal), F4 timing only.
# Evidence: <SCRATCH>/c8d2/evidence/<sha12>/s4flag.<job>.0/. Scratch on the node-local /tmp (TMPDIR).
# Usage: C8_PACKAGE=... BUILD_EVIDENCE=<s4build evidence dir> sbatch --export=ALL --dependency=afterok:<s4build> -J c8d2-s4flag s4flag.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${BUILD_EVIDENCE:?}" "${C8_SEEDS:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s4flag.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
OLD=$C8_PACKAGE/benchmarks/symmetry_2026-10-c8/s6fix3/s3flag.570536.0/jflag_dd+mp256/numerics_flags.json
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; seeds log $C8_SEEDS; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)|^CPU\(s\)' "$E/node.txt"
g++ --version | head -1 | tee "$E/gcc.txt"; sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS C8_ALLOW_NO_L8
cd "$C8_PACKAGE" || exit 64
sha256sum "$C8_SEEDS" | tee "$E/seeds_log_before.sha256"
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_dd+mp256"
sha256sum $X | tee "$E/before.sha256"
check() {  # $1 = the sha256 listing to check, against s4build's
  python3 - "$1" "$BUILD_EVIDENCE" <<'PY'
import sys
from pathlib import Path
got = {l.split()[1]: l.split()[0] for l in open(sys.argv[1]).read().splitlines()}
B = Path(sys.argv[2]); want = {l.split()[1]: l.split()[0] for l in (B / 'binaries_after_profile.sha256').read_text().splitlines()}
want = {k: want[k] for k in ('bin/c8d2_decimal', 'bin/c8d2_gmp')}; want['bin/c8d2_gmp_dd+mp256'] = (B / 'profile.sha256').read_text().split()[0]
bad = {k: (got.get(k), v) for k, v in want.items() if got.get(k) != v}
print('identity', 'ok' if not bad else f'DIFFERS {bad}', {k: v[:12] for k, v in want.items()}); sys.exit(1 if bad else 0)
PY
}
check "$E/before.sha256" || exit 3
status=0; t=$(date +%s)
echo "== numerics_flags.py --profile dd+mp256 (full scale, fresh F1 baseline) $(date -Is)"
python3 -B tests/numerics_flags.py --profile dd+mp256 --seeds-log "$C8_SEEDS" --output "$E/jflag_dd+mp256" --scratch "$TMPDIR" || status=$?
echo "numerics_flags.py exit $status after $(( $(date +%s) - t )) s"
sha256sum $X > "$E/after.sha256"; check "$E/after.sha256" || status=3
sha256sum "$C8_SEEDS" | tee "$E/seeds_log_after.sha256"
python3 - "$E/jflag_dd+mp256/numerics_flags.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print(json.dumps({k: d.get(k) for k in ('mode', 'profile_name', 'status', 'verdicts', 'development', 'error', 'wall_seconds', 'f2_seeds', 'inputs')}, indent=1))
print('f1_baseline', json.dumps({k: (d.get('f1_baseline') or {}).get(k) for k in ('reused', 'inputs_manifest_sha256', 'sha256')}))
F2 = d.get('F2') or {}; F4 = d.get('F4') or {}
print('F2 total', json.dumps(F2.get('total')), 'per_task', json.dumps(F2.get('per_task'))[:600])
print('F4 speedup', json.dumps(F4.get('speedup_exact_over_profile')), 'medians', json.dumps(F4.get('medians'))[:600])
PY
python3 -B - "$E/jflag_dd+mp256/numerics_flags.json" "$E/check_gate.json" "$OLD" <<'PY' || status=4
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, 'tools'); import design
inv = json.loads(Path('inputs/inventory.json').read_text()); im = hashlib.sha256(Path('inputs/manifest.json').read_bytes()).hexdigest()
rec = {'inputs_manifest_sha256': im}
try:
    g = design.check_gate(Path(sys.argv[1]), 'dd+mp256', inv, im); rec.update(passed=True, gate=g)
except Exception as e:
    rec.update(passed=False, error=str(e))
try:  # W18 on real data: fix round 3's record is refused for exactly the missing input-set identity
    design.check_gate(Path(sys.argv[3]), 'dd+mp256', inv, im); rec['old_570536'] = {'refused': False}
except ValueError as e:
    why = str(e).split('production build of dd+mp256: ', 1)[-1]
    rec['old_570536'] = {'refused': True, 'error': str(e), 'only_the_input_identity': why.startswith('no authenticated input-set identity') and ';' not in why}
try:  # the new record for an inputs manifest it did not run on
    design.check_gate(Path(sys.argv[1]), 'dd+mp256', inv, '7' * 64); rec['other_inputs'] = {'refused': False}
except ValueError as e:
    rec['other_inputs'] = {'refused': True, 'error': str(e)[-300:]}
Path(sys.argv[2]).write_text(json.dumps(rec, indent=1) + '\n')
print('design.check_gate:', 'PASSED' if rec['passed'] else 'REFUSED: ' + rec['error'][:600], '; inputs', (rec.get('gate') or {}).get('inputs_manifest_sha256', '')[:12],
      '; 570536 refused for the input identity only:', rec['old_570536'], '; other inputs refused:', rec['other_inputs']['refused'])
ok = rec['passed'] and rec['gate'].get('inputs_manifest_sha256') == im and rec['old_570536'].get('only_the_input_identity') and rec['other_inputs']['refused']
sys.exit(0 if ok else 4)
PY
# 4. against fix round 3's gate 570536 (the same executables and streams)
python3 - "$E/jflag_dd+mp256/numerics_flags.json" "$OLD" "$E/vs_570536.json" <<'PY' || true
import json, sys
n, o = (json.load(open(f)) for f in sys.argv[1:3])
def g(d, *ks):
    for k in ks: d = d.get(k) if isinstance(d, dict) else None
    return d
cmp = {'F2_total_equal': g(n, 'F2', 'total') == g(o, 'F2', 'total'), 'F2_per_task_equal': g(n, 'F2', 'per_task') == g(o, 'F2', 'per_task'),
       'F3_counters_equal': n.get('F3_counters') == o.get('F3_counters'), 'F3_tiers_equal': n.get('F3_tiers') == o.get('F3_tiers'),
       'F1_verdict_equal': g(n, 'F1', 'verdict') == g(o, 'F1', 'verdict'), 'F1_coverage_sectors_equal': g(n, 'F1', 'coverage', 'sectors') == g(o, 'F1', 'coverage', 'sectors'),
       'gmp_library_equal': (g(n, 'exact', 'build_record', 'gmp_library', 'sha256'), g(n, 'profile', 'build_record', 'gmp_library', 'sha256')) ==
                            (g(o, 'exact', 'build_record', 'gmp_library', 'sha256'), g(o, 'profile', 'build_record', 'gmp_library', 'sha256')),
       'F4_speedup_new': g(n, 'F4', 'speedup_exact_over_profile'), 'F4_speedup_570536': g(o, 'F4', 'speedup_exact_over_profile'),
       'F4_medians_new': g(n, 'F4', 'medians'), 'F4_medians_570536': g(o, 'F4', 'medians')}
open(sys.argv[3], 'w').write(json.dumps(cmp, indent=1, default=str) + '\n'); print(json.dumps(cmp, indent=1, default=str)[:3000])
PY
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"; exit $status
