#!/bin/bash
#SBATCH -A yun124 -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-s4c-precheck
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# Stage 4c development pre-check (never gate evidence): compile a working-tree copy (C8_PRECHECK: src/, Makefile,
# tests/numerics_f1.cpp, tools/build_record.py and tools/common.py, copied there by `submit_s4c.sh precheck`) before a
# commit: the default executables (their sha256 against the final default binary, A-RPL-8 in advance), the profile
# executables of C8_S4C_PROFILES and the F1 tool of bin/c8d2_gmp and of each profile (compile only); --describe of
# each. Exit 3 on a compile error. Writes $C8_PRECHECK/precheck.json.
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PRECHECK:?}"
PROFILES=${C8_S4C_PROFILES:-dd mp256 exp1 dd,mp256,exp1}
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); tree $C8_PRECHECK; profiles $PROFILES"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_PRECHECK" || exit 64
st=0
make -j2 bin/c8d2_decimal bin/c8d2_gmp > make_default.log 2>&1 || { echo "default build FAILED"; tail -60 make_default.log; st=3; }
pids=(); names=()
for p in $PROFILES; do
  c=$(python3 -c "import sys;sys.path.insert(0,'tools');from common import numerics_name;print(numerics_name(sys.argv[1]))" "$p")
  make "bin/c8d2_gmp_$c" NUMERICS="$p" > "make_$c.log" 2>&1 & pids+=($!); names+=("$c")
done
for i in "${!pids[@]}"; do wait "${pids[$i]}" || { echo "profile build ${names[$i]} FAILED"; tail -80 "make_${names[$i]}.log"; st=3; }; done
python3 - "$st" ${names[@]+"${names[@]}"} <<'PY' || st=3
import json, subprocess, sys, hashlib, os
from pathlib import Path
sys.path.insert(0, 'tools'); st = int(sys.argv[1]); names = sys.argv[2:]
final = {'bin/c8d2_decimal': '99a51c1d3f520f16a846eea90149e6cb9d42772db819dbdb2286cb12cb13bcbf', 'bin/c8d2_gmp': '1d2a218147ef52b5d0ac37dd8aaead55045ab4fe68e48ec963ea4b8e93024faa'}
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).exists() else None
rec = {'default': {k: {'sha256': h(k), 'final': v, 'identical': h(k) == v} for k, v in final.items()}, 'profiles': {}, 'f1_tools': {}}
exes = ['bin/c8d2_gmp'] + [f'bin/c8d2_gmp_{n}' for n in names]
for e in exes:
    if not Path(e).exists(): continue
    d = subprocess.run([e, '--describe'], capture_output=True, text=True)
    rec['profiles'][e] = {'sha256': h(e), 'describe': json.loads(d.stdout) if d.returncode == 0 else d.stderr[-500:]}
    cmd = json.loads(Path(e + '.build.json').read_text())['command']; cmd = [str(Path('tests/numerics_f1.cpp').resolve()) if w.endswith('src/c8d2_integrate.cpp') else w for w in cmd]
    cmd[cmd.index('-o') + 1] = f'/tmp/f1_{os.getpid()}_{Path(e).name}'
    cp = subprocess.run(cmd, capture_output=True, text=True); rec['f1_tools'][e] = {'compiled': cp.returncode == 0, 'stderr': cp.stderr[-3000:]}
    Path(cmd[cmd.index('-o') + 1]).unlink(missing_ok=True)
Path('precheck.json').write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps({'default_identical': {k: v['identical'] for k, v in rec['default'].items()}, 'numerics': {k: (v['describe'].get('numerics') if isinstance(v['describe'], dict) else v['describe']) for k, v in rec['profiles'].items()},
                  'f1_tools_compiled': {k: v['compiled'] for k, v in rec['f1_tools'].items()}}, indent=1))
for k, v in rec['f1_tools'].items():
    if not v['compiled']: print(f'F1 tool of {k} FAILED:\n{v["stderr"]}')
sys.exit(0 if all(v['compiled'] for v in rec['f1_tools'].values()) else 3)
PY
echo "finished $(date -Is), status $st"; exit $st
