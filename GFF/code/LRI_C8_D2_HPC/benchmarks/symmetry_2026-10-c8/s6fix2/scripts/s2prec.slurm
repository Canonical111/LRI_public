#!/bin/bash
#SBATCH -p amdq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 01:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Stage-6 fix round 2 on symmetry, one whole amdq node, in the export built by s2build.slurm:
#   Y6  every worker's runtime fingerprint on this node is complete: common.fingerprint + fingerprint_problems = [] for
#       bin/c8d2_gmp, bin/c8d2_decimal and bin/c8d2_gmp_dd+mp256 (the ldd survey of this node), with ldd's raw output;
#   Y7  lanes.cgroup_memory_limit() and lanes.memory_limit() under this exclusive allocation, with /proc/self/cgroup and
#       the limit file of every cgroup level;
#   Y1  tests/forced_tiers.py --worker bin/c8d2_gmp --threads 64 (A-RPL-5) and tests/check_points.py (450 digits, L3-L8,
#       both backends) through the Y1 binding with the default GMP: every record carries its binding (GMP_PREFIX none;
#       the tool and the worker resolve the libgmp the build record names). Y1's class at the integration:
#       tests/sanitize.py pc_tool + verify_pc_tool against bin/c8d2_{decimal,gmp}_san (compile and the libgmp check
#       only, not the sanitizer runs), and tools/perf_profile.py build_twin(exe=bin/c8d2_gmp) with same_code() against
#       the worker (the twin = the worker's recorded command plus -g);
#   Y2  tools/benchmark.py --lane-shapes 8x8,1x64 --workload p4_L8 --fraction 0.1 with OMP_THREAD_LIMIT=1 and
#       OMP_DYNAMIC=true inherited: every block's OpenMP team verified (team_sizes_verified), rows equal across shapes.
#   The executables are unchanged by all of it (sha256 before and after).
# Usage: C8_PACKAGE=... sbatch --export=ALL --dependency=afterok:<s2build> -J c8d2-s2prec s2prec.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s2prec.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)|^CPU\(s\)' "$E/node.txt"
sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"; g++ --version | head -1 | tee "$E/gcc.txt"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset C8_SEEDS C8_SITE C8_INPUTS CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS
env | grep -E '^(OMP|GOMP|KMP)_' > "$E/omp_env_at_start.txt" || true
cd "$C8_PACKAGE" || exit 64
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_dd+mp256 bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_decimal_san bin/c8d2_gmp_san"
sha256sum $X | tee "$E/binaries_before.sha256"
status=0
run() {
  local name=$1; shift; local t=$(date +%s); echo "== $name $(date -Is)"
  "$@" > "$E/$name.log" 2>&1; local c=$?
  echo "== $name exit $c after $(( $(date +%s) - t )) s"; echo "$name $c $(( $(date +%s) - t ))" >> "$E/exits.txt"; tail -3 "$E/$name.log" | cut -c1-300
  if [ $c -ne 0 ]; then status=1; grep -E '^FAIL|Error|Traceback|failed|refused' "$E/$name.log" | head -20 | cut -c1-300; fi
}
ldd bin/c8d2_gmp > "$E/ldd_c8d2_gmp.txt" 2>&1
# ---- Y6 and Y7
run y6_y7 python3 -B - "$E" <<'PY'
import json, os, sys
from pathlib import Path
sys.path.insert(0, 'tools')
import common, lanes
E = Path(sys.argv[1]); rec = {'host': os.uname().nodename}
fps = {}
for x in ('bin/c8d2_gmp', 'bin/c8d2_decimal', 'bin/c8d2_gmp_dd+mp256'):
    cpu = {}; fp = common.fingerprint(Path(x), None, cpu); kind = common.elf_kind(Path(x))
    fps[x] = {'elf_kind': kind, 'cpu_identity': cpu, 'problems': common.fingerprint_problems(fp, kind, cpu),
              'malformed': common.fingerprint_malformed(fp), 'runtime_identity_key': common.runtime_identity_key(fp),
              'ldd_error': fp.get('ldd_error'), 'libraries': {k: (v or {}).get('sha256') for k, v in fp['libraries'].items()},
              'interpreter_sha256': (fp.get('interpreter') or {}).get('sha256')}
rec['Y6'] = {'fingerprints': fps, 'complete': all(not v['problems'] and v['malformed'] is None for v in fps.values())}
lines = Path('/proc/self/cgroup').read_text().splitlines(); levels = []
for line in lines:
    parts = line.split(':', 2)
    if len(parts) != 3: continue
    ctrl, path = parts[1], parts[2]
    if ctrl == '': base, name = Path('/sys/fs/cgroup'), 'memory.max'
    elif 'memory' in ctrl.split(','): base, name = Path('/sys/fs/cgroup/memory'), 'memory.limit_in_bytes'
    else: continue
    p = base / path.lstrip('/')
    while True:
        f = p / name
        try: levels.append({'dir': str(p), 'file': name, 'value': f.read_text().strip()})
        except OSError as e: levels.append({'dir': str(p), 'file': name, 'error': type(e).__name__})
        if p == base: break
        p = p.parent
finite = [int(l['value']) for l in levels if l.get('value') not in (None, '', 'max') and int(l['value']) < 2**60]
lim, src = lanes.memory_limit({k: v for k, v in os.environ.items()})
rec['Y7'] = {'proc_self_cgroup': lines, 'levels': levels, 'cgroup_memory_limit': lanes.cgroup_memory_limit(), 'memory_limit': [lim, src],
             'min_finite_over_levels': min(finite) if finite else None, 'SLURM_MEM_PER_NODE': os.environ.get('SLURM_MEM_PER_NODE')}
rec['Y7']['equals_min'] = rec['Y7']['cgroup_memory_limit'] == rec['Y7']['min_finite_over_levels']
(E / 'y6_y7.json').write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps({'Y6_complete': rec['Y6']['complete'], 'problems': {k: v['problems'] for k, v in fps.items()},
                  'Y7': {k: rec['Y7'][k] for k in ('cgroup_memory_limit', 'memory_limit', 'min_finite_over_levels', 'equals_min', 'SLURM_MEM_PER_NODE')}}, indent=1))
sys.exit(0 if rec['Y6']['complete'] and rec['Y7']['equals_min'] else 3)
PY
# ---- Y1: the precision tools bound to the default worker's GMP
run forced_tiers python3 -B tests/forced_tiers.py --worker bin/c8d2_gmp --threads 64 --output "$E/forced_tiers.json"
run check_points python3 -B tests/check_points.py --output "$E/point_checks.json"
run y1_class python3 -B - "$E" "$TMPDIR" <<'PY'
import json, sys
from pathlib import Path
sys.path[:0] = ['tools', 'tests']
import sanitize as S, perf_profile as PP
E, T = Path(sys.argv[1]), Path(sys.argv[2]); rec = {'sanitize_pc_tool': {}}
for b in ('decimal', 'gmp'):
    import subprocess
    exe = T / f'pc_san_{b}'; cmd, binding = S.pc_tool(b, exe, Path(f'bin/c8d2_{b}_san')); subprocess.run(cmd, check=True)
    rec['sanitize_pc_tool'][b] = {'command': cmd, 'binding': S.verify_pc_tool(exe, binding)}
tw = PP.build_twin(T / 'c8d2_gmp_dbginfo', exe=Path('bin/c8d2_gmp'))
rec['perf_twin'] = {k: tw[k] for k in ('command', 'GMP_PREFIX', 'gmp_prefix_note', 'returncode', 'seconds')}
want = json.loads(Path('bin/c8d2_gmp.build.json').read_text())['command']
want = [str(T / 'c8d2_gmp_dbginfo') if x == 'bin/c8d2_gmp' else x for x in want]; want.insert(want.index('-std=c++17'), '-g')
rec['perf_twin']['command_is_record_plus_g'] = tw['command'] == want
rec['perf_twin']['same_code'] = PP.same_code(Path('bin/c8d2_gmp'), T / 'c8d2_gmp_dbginfo', T) if tw['returncode'] == 0 else None
ok = (rec['sanitize_pc_tool']['gmp']['binding']['linked']['match'] and rec['perf_twin']['returncode'] == 0 and rec['perf_twin']['command_is_record_plus_g'])
rec['ok'] = bool(ok); (E / 'y1_class.json').write_text(json.dumps(rec, indent=1, default=str) + '\n')
print(json.dumps({'pc_tool_gmp_linked': rec['sanitize_pc_tool']['gmp']['binding']['linked']['match'], 'twin_returncode': tw['returncode'],
                  'twin_command_is_record_plus_g': rec['perf_twin']['command_is_record_plus_g'], 'twin_same_code': rec['perf_twin']['same_code']}, indent=1, default=str))
sys.exit(0 if ok else 3)
PY
python3 -B - "$E" <<'PY' | tee "$E/y1_summary.json"
import json, sys
from pathlib import Path
E = Path(sys.argv[1]); out = {}
ft = E / 'forced_tiers.json'
if ft.exists():
    d = json.loads(ft.read_text()); b = d.get('gmp_binding') or {}
    out['forced_tiers'] = {'status': d.get('status'), 'wall_seconds': d.get('wall_seconds'), 'GMP_PREFIX': b.get('GMP_PREFIX'),
                           'linked_match': (b.get('linked') or {}).get('match'), 'libgmp_sha256': (b.get('gmp_library') or {}).get('sha256'),
                           'tool_command': d.get('tool_command')}
pc = E / 'point_checks.json'
if pc.exists():
    d = json.loads(pc.read_text())
    out['point_checks'] = {'status': d.get('status'), 'results': [{'backend': (r.get('binding') or {}).get('backend'), 'GMP_PREFIX': (r.get('binding') or {}).get('GMP_PREFIX'),
                           'linked_match': ((r.get('binding') or {}).get('linked') or {}).get('match')} for r in d.get('results', [])]}
print(json.dumps(out, indent=1))
PY
# ---- Y2: the P4 lane shapes under inherited OpenMP controls
python3 -B tools/prepare_benchmarks.py --order 8 > "$E/fixtures_verify.json" 2>&1 || { echo "fixtures do not verify"; status=1; }
S=$TMPDIR/p4; mkdir -p "$S"
run p4_omp_inherited env OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true python3 -B tools/benchmark.py --lane-shapes 8x8,1x64 --workload p4_L8 --fraction 0.1 \
  --exe bin/c8d2_gmp --output "$E/p4" --scratch "$S"
python3 -B - "$E" <<'PY' | tee "$E/p4_teams.json"
import json, sys
from pathlib import Path
E = Path(sys.argv[1]); f = next(iter(sorted((E / 'p4').glob('*.json'))), None) if (E / 'p4').exists() else None
recs = {p.name: json.loads(p.read_text()) for p in sorted((E / 'p4').glob('*.json'))} if (E / 'p4').exists() else {}
top = next((v for v in recs.values() if v.get('profile') == 'P4'), {})
out = {'team_sizes_verified': top.get('team_sizes_verified'), 'team_check': (top.get('settings') or {}).get('team_check'),
       'shapes': [{k: s.get(k) for k in ('shape', 'team_sizes_verified', 'teams', 'errors', 'rows_digest', 'blocks', 'wall_seconds')} for s in top.get('shapes', [])]}
out['rows_equal_across_shapes'] = len({s['rows_digest'] for s in out['shapes']}) == 1 if out['shapes'] else None
print(json.dumps(out, indent=1))
sys.exit(0 if out['team_sizes_verified'] is True and out['rows_equal_across_shapes'] else 3)
PY
[ ${PIPESTATUS[0]} -eq 0 ] || status=1
sha256sum $X > "$E/binaries_after.sha256"
if cmp -s "$E/binaries_before.sha256" "$E/binaries_after.sha256"; then echo "executables unchanged"; else echo "executables CHANGED" >&2; status=1; fi
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
