#!/bin/bash
#SBATCH -N 1 -n 1 --exclusive --mem=4G -t 00:05:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# C8(2) PRODUCTION preparation on symmetry (2026-10-06): runtime-fingerprint survey of ONE AMD node for the PRODUCTION
# worker bin/c8d2_gmp_dd+mp256 (the gated build a46f3060..., built in the export by prbuild.slurm). Identical to the
# pilot's survey (pilot/scripts/ppsurvey.slurm, which fingerprinted bin/c8d2_gmp) apart from the executable, its
# expected sha256 and the output directory: the package's own runtime identity of a staged copy, exactly as a claim
# computes it before any pin (stage_runtime-like job-private c8d2_runtime_* copy under $TMPDIR, mode 0700;
# common.fingerprint -> runtime_identity / runtime_identity_key (X8), fingerprint_problems (Y6/Z6), loader_overrides
# (W7), preload_order / loader_env), in the lane worker's environment (~/c8d2/env.sh sourced), through the export's tools.
# One JSON per node: /mnt/beegfs/zzheng1/c8d2/evidence/<sha12>/prsurvey/<host>.<jobid>.json
# Exit 0 when the fingerprint is complete and the executable is the expected a46f3060...; 3 otherwise (record written).
# Usage: C8_PACKAGE=... sbatch --export=ALL -p amddebugq --exclude=cn112 --nodelist=cnNNN -J c8d2-prsv-cnNNN prsurvey.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
D=/mnt/beegfs/zzheng1/c8d2; TAG=$(basename "$C8_PACKAGE"); OUT=$D/evidence/$TAG/prsurvey; mkdir -p "$OUT"
F=$OUT/$(hostname -s).$SLURM_JOB_ID.json
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE ($(cat "$C8_PACKAGE.commit")); record $F"
python3 -B - "$C8_PACKAGE" "$F" <<'PY'
import json, os, shutil, socket, subprocess, sys, tempfile
from pathlib import Path
pkg, out = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(pkg / 'tools'))
import common
WANT = 'a46f3060a27f4d5e3af19023fc5bb67a7ca2dc6c4242e671ef4bdb9427254c8c'
src = pkg / 'bin' / 'c8d2_gmp_dd+mp256'
run = lambda *c: subprocess.run(list(c), capture_output=True, text=True, timeout=120)
rec = {'schema': 'c8-d2-production-node-survey-1', 'host': socket.gethostname(), 'slurm_job': os.environ.get('SLURM_JOB_ID'),
       'partition': os.environ.get('SLURM_JOB_PARTITION'), 'nodelist': os.environ.get('SLURM_JOB_NODELIST'), 'utc': common.utc(),
       'package': str(pkg), 'commit': Path(str(pkg) + '.commit').read_text().strip(), 'python': sys.executable,
       'tmpdir': tempfile.gettempdir(), 'kernel': os.uname().release}
sha = common.digest(src); rec['executable'] = {'path': str(src), 'sha256': sha, 'expected': WANT, 'is_expected': sha == WANT}
rec['loader_overrides'] = common.loader_overrides(); rec['loader_recorded'] = common.loader_recorded()
pre = Path('/etc/ld.so.preload'); rec['etc_ld_so_preload'] = pre.read_text() if pre.exists() else None
rec['ld_library_path'] = os.environ.get('LD_LIBRARY_PATH')
runtime = Path(tempfile.mkdtemp(prefix='c8d2_runtime_'))
try:
    exe = runtime / src.name; shutil.copyfile(src, exe); os.chmod(exe, 0o700)
    counter = {'bytes': 0}; cpu = {}
    fp = common.fingerprint(exe, counter, cpu)
    kind = common.elf_kind(exe)
    rec.update(staged_executable=str(exe), staged_sha256=common.digest(exe), elf_kind=kind, cpu_identity=cpu, fingerprint=fp,
               fingerprint_key=common.fingerprint_key(fp), fingerprint_bytes=counter['bytes'],
               fingerprint_problems=common.fingerprint_problems(fp, kind, cpu), fingerprint_malformed=common.fingerprint_malformed(fp),
               runtime_identity=common.runtime_identity(fp), runtime_identity_key=common.runtime_identity_key(fp))
    d = run(str(exe), '--describe'); rec['describe_rc'] = d.returncode
    try: rec['describe'] = json.loads(d.stdout)
    except ValueError: rec['describe'] = (d.stdout + d.stderr)[-500:]
finally:
    shutil.rmtree(runtime, ignore_errors=True)
rec['runtime_dir_removed'] = not runtime.exists()
fp2 = common.fingerprint(src); rec['runtime_identity_key_export_path'] = common.runtime_identity_key(fp2)
l = run('ldd', str(src)); rec['ldd_raw'] = {'rc': l.returncode, 'stdout': l.stdout, 'stderr': l.stderr}
ls = run('lscpu'); rec['lscpu_raw'] = ls.stdout
want = ('Architecture', 'CPU(s)', 'Thread(s) per core', 'Core(s) per socket', 'Socket(s)', 'NUMA node(s)', 'Vendor ID', 'Model name', 'CPU family', 'Model', 'Stepping',
        'CPU max MHz', 'L3 cache')
rec['lscpu'] = {k.strip(): v.strip() for k, _, v in (x.partition(':') for x in ls.stdout.splitlines()) if k.strip() in want}
rec['lscpu']['numa_cpus'] = {k.strip(): v.strip() for k, _, v in (x.partition(':') for x in ls.stdout.splitlines()) if k.strip().startswith('NUMA node') and 'CPU(s)' in k}
n = run('numactl', '--hardware'); rec['numactl_hardware'] = n.stdout if n.returncode == 0 else (n.stdout + n.stderr)[-500:]
rec['affinity_cpus'] = len(os.sched_getaffinity(0))
lib = lambda name: ((fp.get(name) or {}).get('sha256') or '')
rec['summary'] = {'host': rec['host'], 'cpu_vendor': cpu.get('vendor'), 'cpu_model': fp.get('cpu_model'), 'glibc': fp.get('glibc'),
                  'runtime_identity_key': rec['runtime_identity_key'], 'export_path_key_equal': rec['runtime_identity_key_export_path'] == rec['runtime_identity_key'],
                  'libgmp': lib('libgmp')[:12], 'libquadmath': lib('libquadmath')[:12], 'libgomp': lib('libgomp')[:12],
                  'complete': not rec['fingerprint_problems'] and rec['fingerprint_malformed'] is None, 'no_loader_override': not rec['loader_overrides'],
                  'preload_order': fp.get('preload_order'), 'loader_env': fp.get('loader_env'), 'numa_nodes': rec['lscpu'].get('NUMA node(s)'),
                  'cpus': rec['lscpu'].get('CPU(s)'), 'executable_ok': rec['executable']['is_expected'] and rec['staged_sha256'] == WANT,
                  'fingerprint_bytes': counter['bytes']}
rec['ok'] = rec['summary']['complete'] and rec['summary']['no_loader_override'] and rec['summary']['executable_ok']
out.write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n')
print(json.dumps(rec['summary'], sort_keys=True)); print('problems:', rec['fingerprint_problems'] or 'none', '; ok:', rec['ok'])
sys.exit(0 if rec['ok'] else 3)
PY
s=$?; echo "finished $(date -Is), status $s"; exit $s
