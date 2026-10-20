#!/usr/bin/env python3
"""Expanse validation receipt for one staged release (run by validate.sbatch on a compute node).

Pristine checks on the verified node-local extraction (ROOT = this file's release):
  verify_manifest  tests/verify_manifest.py (the 615 original distribution files)
  release          RELEASE.sha256 (every tracked file) -> release fingerprint
Then a writable node-local copy (validators rewrite validation/*) runs:
  pytest, validate_physics, validate_numerics, validate_large, validate_benchmarks
Any failed or skipped stage gives passed=false. The receipt also records the source
hash, release fingerprint, runtime identity, CPU/node and whether sacct reports a
billing TRES for this job (used for measured SU accounting).
"""
import argparse,json,os,platform,re,shutil,socket,subprocess,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(HERE))
from ht3d.hpc import atomic_json,source_hash  # noqa: E402
import lanes  # noqa: E402

PY=[sys.executable,'-E']      # -E: ignore PYTHON* variables (PYTHONOPTIMIZE would strip the validators' asserts)
# Validators assert, then write a report with passed=true; the report must be fresh (IR01).
VALIDATORS=[('validate_physics','tests/validate_physics.py','validation/physics_checks.json'),
            ('validate_numerics','tests/validate_numerics.py','validation/numerical_checks.json'),
            ('validate_large','tests/validate_large.py','validation/large_independent_checks.json'),
            ('validate_benchmarks','tests/validate_benchmarks.py','validation/benchmark_audit.json'),
            ('validate_l18_fix','tests/validate_l18_fix.py','validation/l18_fix/current_checks.json')]


def clean_env():
    """No pytest overrides/plugins from the submission environment, no Python optimization."""
    return {k:v for k,v in os.environ.items() if not k.startswith(('PYTEST_','PYTHONOPTIMIZE','PYTHONWARNINGS','PYTHONSTARTUP','PYTHONPATH','PYTHONHOME'))}


def stage(name,cmd,cwd,logs):
    log=logs/f'{name}.log';t=time.perf_counter();start=time.time()
    with open(log,'w') as f:rc=subprocess.run(cmd,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,env=clean_env()).returncode
    tail=log.read_text().splitlines()[-5:]
    return {'stage':name,'rc':rc,'seconds':time.perf_counter()-t,'started':start,'log':str(log),'tail':tail}


def pytest_stage(work,logs):
    """Collect, then run with JUnit XML; pass only if executed == collected and nothing failed/erred/skipped."""
    import xml.etree.ElementTree as ET
    col=stage('pytest_collect',[*PY,'-m','pytest','--collect-only','-q','-p','no:cacheprovider','-o','addopts='],work,logs)
    m=[re.search(r'(\d+) tests? collected',l) for l in Path(col['log']).read_text().splitlines()]
    collected=next((int(x.group(1)) for x in m if x),0)
    xml=logs/'pytest.junit.xml'
    run=stage('pytest',[*PY,'-m','pytest','-q','-p','no:cacheprovider','-o','addopts=','--junitxml',str(xml)],work,logs)
    counts={'tests':0,'failures':0,'errors':0,'skipped':0}
    try:
        root=ET.parse(xml).getroot();suites=[root] if root.tag=='testsuite' else list(root.iter('testsuite'))
        for s in suites:
            for k in counts:counts[k]+=int(s.get(k,0))
    except (OSError,ET.ParseError) as exc:run['junit_error']=str(exc)
    ok=(run['rc']==0 and col['rc']==0 and collected>0 and counts['tests']==collected
        and counts['failures']==counts['errors']==counts['skipped']==0)
    run.update(collected=collected,junit=counts,rc=run['rc'] if ok else (run['rc'] or 1))
    return [col,run]


def validator_stage(name,script,report,work,logs):
    s=stage(name,[*PY,script],work,logs);p=Path(work)/report
    try:
        fresh=p.stat().st_mtime>=s['started']-1;passed=json.loads(p.read_text()).get('passed') is True
    except (OSError,ValueError,AttributeError):fresh=passed=False
    s.update(report=str(p),report_fresh=fresh,report_passed=passed)
    if not (fresh and passed) and s['rc']==0:s['rc']=1
    return s


def billing_reported():
    jid=os.environ.get('SLURM_JOB_ID')
    if not jid:return None
    try:out=subprocess.run(['sacct','-X','-n','-P','-j',jid,'-o','AllocTRES'],capture_output=True,text=True,timeout=120).stdout
    except (OSError,subprocess.TimeoutExpired):return None
    return {'alloc_tres':out.strip(),'has_billing':'billing=' in out}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();out=Path(a.out);logs=out/'logs';logs.mkdir(parents=True,exist_ok=True)
    stages=[stage('verify_manifest',[*PY,'tests/verify_manifest.py'],ROOT,logs)]
    t=time.perf_counter()
    try:fingerprint=lanes.release_fingerprint(ROOT);rel={'stage':'release','rc':0,'seconds':time.perf_counter()-t}
    except lanes.Refused as exc:fingerprint=None;rel={'stage':'release','rc':1,'seconds':time.perf_counter()-t,'error':str(exc)}
    stages.append(rel)
    work=Path(a.work)
    if work.exists():raise SystemExit(f'{work} exists')
    shutil.copytree(ROOT,work,symlinks=True)
    stages+=pytest_stage(work,logs)
    for name,script,report in VALIDATORS:stages.append(validator_stage(name,script,report,work,logs))
    required=['verify_manifest','release','pytest_collect','pytest']+[n for n,_,_ in VALIDATORS]
    done={s['stage']:s for s in stages}
    passed=all(n in done and done[n]['rc']==0 for n in required)
    cpu=next((ln.split(':',1)[1].strip() for ln in Path('/proc/cpuinfo').read_text().splitlines() if ln.startswith('model name')),None) if Path('/proc/cpuinfo').exists() else platform.processor()
    receipt={'schema':'ht3d-expanse-receipt-v2','passed':passed,'required_stages':required,'stages':stages,
             'source_sha256':source_hash(),'release_sha256':fingerprint,'git_sha':(ROOT/'GIT_SHA').read_text().strip() if (ROOT/'GIT_SHA').exists() else None,
             'runtime':lanes.runtime_identity(),'node':socket.gethostname(),'cpu_model':cpu,
             'slurm':{k:os.environ.get(k) for k in ('SLURM_JOB_ID','SLURM_CPUS_PER_TASK','SLURM_MEM_PER_NODE','SLURM_JOB_PARTITION')},
             'numba_num_threads':os.environ.get('NUMBA_NUM_THREADS'),'billing':billing_reported(),'time':time.time()}
    atomic_json(out/'receipt.json',receipt)
    print(json.dumps({'passed':passed,'stages':{s['stage']:s['rc'] for s in stages},'receipt':str(out/'receipt.json')}))
    return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
