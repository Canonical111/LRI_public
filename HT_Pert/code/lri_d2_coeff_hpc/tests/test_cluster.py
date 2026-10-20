"""Cluster layer: signal forwarding, job directory checks, checkpoint publication, submit.py (with fake
squeue/sbatch), stack receipts. No real Slurm."""
from pathlib import Path
import hashlib,importlib.util,json,os,shlex,signal,stat,subprocess,sys,tarfile,time
import pytest
ROOT=Path(__file__).resolve().parents[1]
PREFIX='lri_d2_coeff_hpc/'

def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/f'scripts/{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
submit=load('submit')

def clean_env(**extra):
    e={k:v for k,v in os.environ.items() if not k.startswith(('LRI_COEFF_','SBATCH_','SQUEUE_'))}
    e.update(PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMBA_NUM_THREADS='1',OMP_NUM_THREADS='1');e.update(extra);return e

STUB='''import signal,sys,time,pathlib
log=pathlib.Path(sys.argv[1]);mode=sys.argv[2]
def h(sig,frame):
    log.write_text(log.read_text()+f'got {signal.Signals(sig).name}\\n')
    if mode=='exit75':sys.exit(75)
    if mode=='term7' and sig==signal.SIGTERM:sys.exit(7)
if mode!='die':
    for s in (signal.SIGUSR1,signal.SIGTERM):signal.signal(s,h)
log.write_text('ready\\n')
for _ in range(600):time.sleep(0.05)
sys.exit(3)
'''

@pytest.mark.parametrize('mode,sig,want',[('exit75',signal.SIGUSR1,75),('term7',signal.SIGTERM,7),('die',signal.SIGUSR1,128+int(signal.SIGUSR1))])
def test_forwarding(tmp_path,mode,sig,want):
    stub=tmp_path/'stub.py';stub.write_text(STUB);log=tmp_path/'log'
    script=f'source {ROOT}/cluster/forward.sh; run_forwarding {sys.executable} {stub} {log} {mode} && rc=0 || rc=$?; echo rc=$rc'
    p=subprocess.Popen(['bash','-c',script],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    for _ in range(400):
        if log.exists() and 'ready' in log.read_text():break
        time.sleep(0.05)
    else:raise AssertionError('stub never became ready')
    time.sleep(0.2);p.send_signal(sig);out,err=p.communicate(timeout=60)
    assert f'rc={want}' in out,(out,err)
    if mode!='die':assert f'got {sig.name}' in log.read_text()

def test_times_selection_and_resources():
    assert submit.parse_time('01:30:00')==5400 and submit.parse_time('1-00:00:00')==86400
    assert submit.fmt_time(3*3600+61)=='03:01:01'
    assert submit.select('0-2,5',8)==[0,1,2,5] and submit.select(None,3)==[0,1,2]
    with pytest.raises(SystemExit):submit.select('7',3)
    r,_=submit.resources('expanse',30,None,16,3600);assert (r['partition'],r['cpus'],r['mem'])==('shared',16,30)
    r,_=submit.resources('expanse',140,None,16,3600);assert r['partition']=='shared' and r['cpus']==74 and r['charge']>=74
    r,_=submit.resources('expanse',324,None,16,3600);assert r['partition']=='large-shared' and r['cpus']>=21
    assert submit.resources('expanse',2100,None,16,3600)[0] is None
    assert submit.resources('expanse',30,None,16,49*3600)[0] is None
    r,_=submit.resources('expanse',30,None,16,None,10**6);assert r['time']=='48:00:00'
    r,_=submit.resources('symmetry',140,None,16,3600);assert (r['partition'],r['cpus'],r['charge'],r['mem'],r['need'])==('amdq','node',None,245,140)
    r,_=submit.resources('symmetry',324,None,16,3600);assert (r['partition'],r['mem'])==('largememq',370)
    assert submit.resources('symmetry',380,None,16,3600)[0] is None
    assert submit.resources('symmetry',200,'defq',16,3600)[0] is None
    assert submit.resources('symmetry',20,'debugq',16,7200)[0] is None             # explicit time over the limit
    r,_=submit.resources('symmetry',20,'debugq',16,None,7200);assert r['time']=='01:00:00'   # estimate capped by debugq
    r,_=submit.resources('symmetry',20,None,16,None,10**6);assert r['time']=='24:00:00'
    args=submit.sbatch_args('expanse','n',submit.resources('expanse',30,None,16,3600)[0],Path('/d'))
    assert '--account=yun124' in args and '--cpus-per-task=16' in args and '--signal=B:USR1@900' in args and '--no-requeue' in args
    args=submit.sbatch_args('symmetry','n',submit.resources('symmetry',30,None,16,3600)[0],Path('/d'))
    assert '--exclusive' in args and not any(a.startswith(('--account','--cpus-per-task')) for a in args)

def make_release(data):
    rel=data/'releases';rel.mkdir(parents=True);tar=rel/'lri2d_coeff-test.tar'
    names=['MANIFEST.sha256']+[l.split('  ',1)[1] for l in (ROOT/'MANIFEST.sha256').read_text().splitlines()]
    with tarfile.open(tar,'w') as t:
        for n in names:
            if (ROOT/n).is_file():t.add(ROOT/n,arcname=PREFIX+n,recursive=False)
    return tar

FAKE_SQUEUE='''#!/bin/bash
[[ -f "$FAKE/squeue_fail" ]] && { echo "slurm_load_jobs error" >&2; exit 1; }
cat "$FAKE/squeue_out" 2>/dev/null; exit 0
'''
FAKE_SBATCH='''#!/bin/bash
n=$(( $(cat "$FAKE/next" 2>/dev/null || echo 1000) + 1 )); echo $n > "$FAKE/next"
{ echo "ARGS $*"; env | grep -E '^(LRI_COEFF_|SBATCH_)' | sort; echo END; } >> "$FAKE/sbatch.log"
echo "$n"
'''

def fake_bin(tmp_path):
    b=tmp_path/'fakebin';b.mkdir()
    for name,body in (('squeue',FAKE_SQUEUE),('sbatch',FAKE_SBATCH)):
        f=b/name;f.write_text(body);f.chmod(f.stat().st_mode|stat.S_IXUSR)
    return b

def run_submit(data,fake,*args,**env):
    e=clean_env(PATH=f"{fake/'fakebin'}{os.pathsep}{os.environ['PATH']}",FAKE=str(fake),LRI_COEFF_DATA=str(data),**env)
    return subprocess.run([sys.executable,str(ROOT/'scripts/submit.py'),*args],env=e,capture_output=True,text=True,timeout=120)

def envelope(payload):
    return dict(schema='lri-coeff-v1',payload=payload,sha256=hashlib.sha256(submit.canonical(payload)).hexdigest())

STACK=dict(python='3.11.9',prefix='/v',numpy='2.3.5',scipy='1.17.0',numba='0.65.1',longdouble_nmant=63,machine='x86_64',cxx='g++',cxx_version='g++ 13.3.0')
def fake_result(t,source,stack=STACK,**over):
    ident,cfg=submit.expected_identity(t,source,stack);n=t['degree']+1;nv=1 if t['scheme']=='raw' else t['cutoff']//2+1
    p=dict(identity=ident,configuration=cfg,source_digest=source,runtime={},
           result=dict(scheme=t['scheme'],cutoff=t['cutoff'],degree=t['degree'],C=[0.0]*n,r=[0.0]*n,g=[0.0]*n,energies=[[0.0]*n]*4,vacuum_coefficients=[[0.0]*n]*nv),
           execution=dict(threads=1,seconds=1.0,peak_rss_KiB=1))
    p.update(over);return envelope(p)

def write_manifest(path,tasks,source):
    for t in tasks:t['task_digest']=hashlib.sha256(submit.canonical({k:v for k,v in t.items() if k!='task_digest'})).hexdigest()
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(envelope(dict(kind='lri-2d-coefficient-array-v1',source_digest=source,tasks=tasks))))

@pytest.mark.parametrize('site',['expanse','symmetry'])
def test_submit_end_to_end(tmp_path,site):
    data=tmp_path/'data';fake=tmp_path;fake_bin(tmp_path);tar=make_release(data);sbatch_log=fake/'sbatch.log'
    common=['--site',site,'--release',str(tar)]
    # validation: dry run submits nothing; --submit passes explicit resources and the job variables
    p=run_submit(data,fake,'validate',*common);assert p.returncode==0,p.stderr;assert 'dry run' in p.stdout and not sbatch_log.exists()
    p=run_submit(data,fake,'validate',*common,'--submit',SBATCH_PARTITION='wrong');assert p.returncode==0,p.stderr
    log=sbatch_log.read_text();assert 'SBATCH_' not in log and 'LRI_COEFF_JOB=validate' in log and '--signal=B:USR1@900' in log
    assert ('--exclusive' in log)==(site=='symmetry') and ('--account=yun124' in log)==(site=='expanse')
    sha=hashlib.sha256(tar.read_bytes()).hexdigest();assert f'LRI_COEFF_RELEASE_SHA256={sha}' in log
    (fake/'squeue_out').write_text(f'1001|lri2dc-val-{sha[:8]}-{site}|PENDING\n')
    p=run_submit(data,fake,'validate',*common,'--submit');assert p.returncode!=0 and 'already queued' in p.stderr
    # campaign: refused without a receipt
    man=data/'campaigns/t/campaign.json'
    p=subprocess.run([sys.executable,str(ROOT/'scripts/make_campaign.py'),'--cutoffs','2','4','--schemes','raw','consistent','--threads','1',
                      '--output-root',str(man.parent),'--manifest',str(man)],env=clean_env(),capture_output=True,text=True);assert p.returncode==0,p.stderr
    p=run_submit(data,fake,'campaign',*common,'--manifest',str(man));assert p.returncode!=0 and 'no passing validation receipt' in p.stderr
    rel=submit.release_info(str(tar),data)
    rdir=data/'validation'/f'{sha[:16]}_{site}_1001';rdir.mkdir(parents=True)
    (rdir/'receipt.json').write_text(json.dumps(dict(kind='lri-coeff-validation-receipt-v1',passed=True,site=site,release_sha256=sha,source_digest=rel['source_digest'],finished='x',stack=STACK)))
    # task states: 0 todo, 1 locked, 2 conflict, 3 live, and later a done output
    tasks=json.loads(man.read_text())['payload']['tasks'];cid=json.loads(man.read_text())['sha256'][:8]
    Path(tasks[1]['output']+'.lock').mkdir(parents=True);Path(tasks[1]['output']+'.lock/owner.json').write_text('{"slurm_job":"7"}')
    Path(tasks[2]['output']).write_text('{}')
    (fake/'squeue_out').write_text(f'1001|lri2dc-val-{sha[:8]}-{site}|COMPLETED\n2002|{submit.task_job_name(tasks[3])}|RUNNING\n')
    p=run_submit(data,fake,'campaign',*common,'--manifest',str(man));assert p.returncode==0,p.stderr
    out=p.stdout;assert 'todo' in out and 'locked' in out and 'conflict' in out and 'live' in out and 'would submit 1' in out
    before=sbatch_log.read_text()
    p=run_submit(data,fake,'campaign',*common,'--manifest',str(man),'--submit');assert p.returncode==0,p.stderr
    new=sbatch_log.read_text()[len(before):];assert new.count('ARGS')==1 and f'--job-name={submit.task_job_name(tasks[0])}' in new
    msha=hashlib.sha256(man.read_bytes()).hexdigest()
    mem='--mem=5G' if site=='expanse' else '--mem=245G'
    for want in ('LRI_COEFF_JOB=task','LRI_COEFF_INDEX=0',f'LRI_COEFF_MANIFEST_SHA256={msha}',f'LRI_COEFF_RECEIPT={rdir/"receipt.json"}',mem,'--no-requeue','--export=ALL'):
        assert want in new,want
    recs=[json.loads(l) for l in (data/'submissions.jsonl').read_text().splitlines()];assert (recs[-1]['index'],recs[-1]['job_id'])==(0,'1002')
    # the recorded job of task 0 is live by id even if renamed; a complete output with the validated
    # identity is done; one from another Python, or an incomplete one, is a conflict
    jid=recs[-1]['job_id'];(fake/'squeue_out').write_text(f'{jid}|renamed|PENDING\n')
    Path(tasks[3]['output']).write_text(json.dumps(fake_result(tasks[3],rel['source_digest'])))
    p=run_submit(data,fake,'campaign',*common,'--manifest',str(man));assert p.returncode==0,p.stderr
    lines={l.split()[0]:l for l in p.stdout.splitlines() if l.startswith('[')}
    assert 'live' in lines['[0]'] and 'done' in lines['[3]'] and 'would submit 0' in p.stdout
    good=fake_result(tasks[3],rel['source_digest']);res=good['payload']['result']
    for bad in (fake_result(tasks[3],rel['source_digest'],dict(STACK,python='3.13.5')),fake_result(tasks[3],rel['source_digest'],result={}),
                fake_result(tasks[3],rel['source_digest'],result={k:v for k,v in res.items() if k!='scheme'}),
                fake_result(tasks[3],rel['source_digest'],result=dict(res,vacuum_coefficients=[[]])),
                fake_result(tasks[3],rel['source_digest'],result=dict(res,energies=[[]]*4)),
                fake_result(tasks[3],rel['source_digest'],result=dict(res,C=['x']*len(res['C'])))):
        Path(tasks[3]['output']).write_text(json.dumps(bad))
        p=run_submit(data,fake,'campaign',*common,'--manifest',str(man),'--tasks','3');assert 'conflict' in p.stdout,p.stdout
    Path(tasks[3]['output']).unlink()
    # a second manifest writing the same outputs: task 0's output belongs to the live job (same output-derived
    # name, and its journal record); within one call, a duplicated output is submitted once
    man2=data/'campaigns/t2/campaign.json'
    write_manifest(man2,[dict(tasks[0]),dict(tasks[0],checkpoint_seconds=99),dict(tasks[3]),dict(tasks[3],checkpoint_seconds=99)],rel['source_digest'])
    p=run_submit(data,fake,'campaign',*common,'--manifest',str(man2));assert p.returncode==0,p.stderr
    lines={l.split()[0]:l for l in p.stdout.splitlines() if l.startswith('[')}
    assert 'live' in lines['[0]'] and 'job '+jid in lines['[0]'] and 'job '+jid in lines['[1]'] and 'todo' in lines['[2]']
    assert 'reserved' in lines['[3]'] and 'would submit 1' in p.stdout
    # the job name alone marks an output as taken, even without a journal entry
    (data/'submissions.jsonl').rename(data/'journal.bak');(fake/'squeue_out').write_text(f'{jid}|{submit.task_job_name(tasks[0])}|PENDING\n')
    p=run_submit(data,fake,'campaign',*common,'--manifest',str(man2),'--tasks','0-1');assert p.returncode==0,p.stderr
    assert 'would submit 0' in p.stdout and sum(' live ' in l for l in p.stdout.splitlines() if l.startswith('['))==2,p.stdout
    # ... also for a different configuration writing that same output (names depend on the output path only)
    man5=data/'campaigns/t5/campaign.json';write_manifest(man5,[dict(tasks[0],degree=7,scheme='raw')],rel['source_digest'])
    p=run_submit(data,fake,'campaign',*common,'--manifest',str(man5));assert p.returncode==0,p.stderr
    assert 'would submit 0' in p.stdout and ' live ' in p.stdout,p.stdout
    # relative task paths and shared graph caches are refused
    man3=data/'campaigns/t3/campaign.json';write_manifest(man3,[dict(tasks[3],output='rel/x.json')],rel['source_digest'])
    p=run_submit(data,fake,'campaign',*common,'--manifest',str(man3));assert p.returncode!=0 and 'not an absolute path' in p.stderr
    man4=data/'campaigns/t4/campaign.json';write_manifest(man4,[dict(tasks[3],cache=str(data/'campaigns/t4/graph_cache'))],rel['source_digest'])
    p=run_submit(data,fake,'campaign',*common,'--manifest',str(man4));assert p.returncode!=0 and 'graph cache' in p.stderr
    # squeue failure and a held mutex refuse to submit
    (fake/'squeue_fail').write_text('');p=run_submit(data,fake,'campaign',*common,'--manifest',str(man),'--submit')
    assert p.returncode!=0 and 'UNKNOWN' in p.stderr;(fake/'squeue_fail').unlink()
    (data/'.submit.lock').mkdir();p=run_submit(data,fake,'campaign',*common,'--manifest',str(man),'--submit')
    assert p.returncode!=0 and 'another submission' in p.stderr
    # a release tar outside DATA/releases or a modified tar is refused
    other=tmp_path/'elsewhere.tar';other.write_bytes(tar.read_bytes())
    assert run_submit(data,fake,'validate','--site',site,'--release',str(other)).returncode!=0
    side=tar.with_name(tar.name+'.sha256');side.write_text('0'*64+'  x\n')
    assert run_submit(data,fake,'validate',*common).returncode!=0

def test_release_source_digest_matches_storage(tmp_path):
    from lri_coeff.storage import source_digest
    tar=make_release(tmp_path/'data')
    assert submit.release_info(str(tar),tmp_path/'data')['source_digest']==source_digest()

def test_stack_receipt_match(tmp_path):
    st=load('stack');s=st.stack();f=tmp_path/'r.json'
    f.write_text(json.dumps(dict(kind='lri-coeff-validation-receipt-v1',passed=True,stack=s)));assert st.match_problems(s,f)==[]
    f.write_text(json.dumps(dict(kind='lri-coeff-validation-receipt-v1',passed=True,stack=dict(s,numba='0.0'))));assert st.match_problems(s,f)
    f.write_text(json.dumps(dict(kind='lri-coeff-validation-receipt-v1',passed=False,stack=s)));assert st.match_problems(s,f)


def trusted(path):
    src=(ROOT/'cluster/job.sbatch').read_text();fn=src[src.index('trusted_path() {'):src.index('\nJOBDIR=\n')]
    return subprocess.run(['bash','-c',fn+'\ntrusted_path '+shlex.quote(str(path))],capture_output=True).returncode==0

def test_trusted_job_parent(tmp_path):
    if subprocess.run(['stat','-c','%u','/'],capture_output=True).returncode:pytest.skip('needs GNU stat')
    if not trusted(tmp_path):pytest.skip('the test directory chain itself is not trusted here')
    good=tmp_path/'good';good.mkdir(mode=0o700);assert trusted(good)
    bad=tmp_path/'open';bad.mkdir();bad.chmod(0o777);(bad/'sub').mkdir(mode=0o700)
    assert not trusted(bad) and not trusted(bad/'sub')
    link=tmp_path/'link';link.symlink_to(good);assert not trusted(link)
    assert not trusted(tmp_path/'missing')

IDENT='a'*64
SOLVER_STUB='''import json,hashlib,pathlib,shutil,signal,sys,time
# Mimics src/lri_coeff/storage.save_checkpoint: envelopes with digests, the SHA-256 of every array recorded.
root=pathlib.Path(sys.argv[1])/{ident!r};mode=sys.argv[2];stop=[]
signal.signal(signal.SIGUSR1,lambda s,f:stop.append(s))
def env(p):return dict(schema='lri-coeff-v1',payload=p,sha256=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest())
def write(n):
    g=root/f'generation-{{n}}';g.mkdir(parents=True);a=b'A'*n*1000;b=b'B'*n
    (g/'a.npy').write_bytes(b'Z'+a[1:] if mode=='corrupt' and n==2 else a);(g/'b.npy').write_bytes(b)
    files={{'a':{{'sha256':hashlib.sha256(a).hexdigest()}},'b':{{'sha256':hashlib.sha256(b).hexdigest()}}}}
    (g/'metadata.json').write_text(json.dumps(env(dict(files=files))))
    (root/'latest.json').write_text(json.dumps(env(dict(identity={ident!r},generation=g.name))))
    for old in root.glob('generation-*'):
        if old.name not in (g.name,f'generation-{{n-1}}'):shutil.rmtree(old)
if (root/'latest.json').exists():
    print('restored',json.loads((root/'latest.json').read_text())['payload']['generation'],flush=True);write(3);sys.exit(0)
write(1);print('gen1',flush=True)
while not stop:time.sleep(0.05)
write(2);sys.exit(75)
'''.format(ident=IDENT)

# Code run before supervise() in the child interpreter: corrupt one payload byte of the temporary archive
# (same length) just before it is read back, or make it unreadable.
CORRUPT_READBACK="""
_open=tarfile.open
def _corrupt(*a,**k):
    if a and '.partial-' in str(a[0]):
        p=Path(a[0]);d=p.read_bytes();i=d.find(b'AAAA');p.write_bytes(d[:i]+b'AAAZ'+d[i+4:])
    return _open(*a,**k)
tarfile.open=_corrupt
"""
UNREADABLE_READBACK="""
_open=tarfile.open
def _unreadable(*a,**k):
    if a and '.partial-' in str(a[0]):raise tarfile.ReadError('simulated unreadable archive')
    return _open(*a,**k)
tarfile.open=_unreadable
"""

def supervise_cmd(stub,root,archive,mode='ok',setup=''):
    code=(f"import sys,tarfile\nfrom pathlib import Path\nsys.path.insert(0,{str(ROOT/'scripts')!r})\nimport ckpt_sync\nckpt_sync.RETRY_WAITS=(0,0.1)\n{setup}\n"
          f"sys.exit(ckpt_sync.supervise([sys.executable,{str(stub)!r},{str(root)!r},{mode!r}],None,Path({str(root)!r}),Path({str(archive)!r}),'t',poll=0.2))")
    return [sys.executable,'-c',code]

def wait_for(path):
    for _ in range(400):
        if path.exists():return
        time.sleep(0.05)
    raise AssertionError(f'{path} never appeared')

def test_checkpoint_publication(tmp_path):
    stub=tmp_path/'stub.py';stub.write_text(SOLVER_STUB);archive=tmp_path/'shared/task-x.tar'
    p=subprocess.Popen(supervise_cmd(stub,tmp_path/'local1',archive),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    for _ in range(400):
        if archive.exists():break
        time.sleep(0.05)
    else:raise AssertionError('generation 1 was never published')
    p.send_signal(signal.SIGUSR1);out,err=p.communicate(timeout=60);assert p.returncode==75,(out,err)
    with tarfile.open(archive) as t:
        names=set(t.getnames());latest=json.loads(t.extractfile(f'{IDENT}/latest.json').read())['payload']['generation']
        assert latest=='generation-2' and f'{IDENT}/generation-2/a.npy' in names and not any('generation-1' in n for n in names)
        assert t.extractfile(f'{IDENT}/generation-2/a.npy').read()==b'A'*2000
    assert not list(archive.parent.glob('.*partial*'))
    # a new job on another node restores generation 2; success removes the archive
    p=subprocess.run(supervise_cmd(stub,tmp_path/'local2',archive),capture_output=True,text=True,timeout=60)
    assert p.returncode==0 and 'restored generation-2' in p.stdout,(p.stdout,p.stderr);assert not archive.exists()

def test_checkpoint_restore_refuses_unsafe(tmp_path):
    ckpt=load('ckpt_sync');bad=tmp_path/'bad.tar';(tmp_path/'x').write_text('x')
    with tarfile.open(bad,'w') as t:t.add(tmp_path/'x',arcname='../x')
    with pytest.raises(ValueError):ckpt.restore(bad,tmp_path/'root')


def test_checkpoint_not_published(tmp_path):
    """Exit 75 becomes 76 and the node-local checkpoint is marked when the final archive cannot be written."""
    if os.geteuid()==0:pytest.skip('permissions are not enforced for root')
    stub=tmp_path/'stub.py';stub.write_text(SOLVER_STUB);shared=tmp_path/'shared';archive=shared/'task-x.tar';root=tmp_path/'node/checkpoints'
    p=subprocess.Popen(supervise_cmd(stub,root,archive),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    wait_for(archive);before=archive.read_bytes();shared.chmod(0o555)
    try:
        p.send_signal(signal.SIGUSR1);out,err=p.communicate(timeout=60)
    finally:shared.chmod(0o755)
    assert p.returncode==76,(out,err);assert (root.parent/'UNPUBLISHED').exists() and archive.read_bytes()==before

def test_stale_partials_removed_only_for_ended_jobs(tmp_path):
    shared=tmp_path/'shared';shared.mkdir();archive=shared/'task-x.tar'
    for jid in ('999','1000','abc'):(shared/f'.task-x.tar.partial-{jid}').write_bytes(b'junk')
    (shared/'.task-y.tar.partial-999').write_bytes(b'other task')
    b=tmp_path/'bin';b.mkdir();q=b/'squeue'
    q.write_text('#!/bin/bash\ncase "$3" in 999) echo "slurm_load_jobs error: Invalid job id specified" >&2; exit 1;; 1000) echo RUNNING;; esac\n')
    q.chmod(0o755);stub=tmp_path/'stub.py';stub.write_text(SOLVER_STUB)
    env=dict(os.environ,PATH=f"{b}{os.pathsep}{os.environ['PATH']}")
    p=subprocess.Popen(supervise_cmd(stub,tmp_path/'node/checkpoints',archive),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    wait_for(archive);p.send_signal(signal.SIGUSR1);out,err=p.communicate(timeout=60);assert p.returncode==75,(out,err)
    left=sorted(f.name for f in shared.iterdir())
    assert left==['.task-x.tar.partial-1000','.task-x.tar.partial-abc','.task-y.tar.partial-999','task-x.tar'],left


@pytest.mark.parametrize('case',['local_corrupt','readback_corrupt','readback_unreadable'])
def test_bad_generation_never_replaces_archive(tmp_path,case):
    """Generation 2 fails verification (corrupt local array; corrupt or unreadable read-back of every archive):
    exit 76, UNPUBLISHED marker, the solver waited for, and the archive untouched (generation 1, or none)."""
    stub=tmp_path/'stub.py';stub.write_text(SOLVER_STUB);archive=tmp_path/'shared/task-x.tar';root=tmp_path/'node/checkpoints'
    if case=='local_corrupt':
        p=subprocess.Popen(supervise_cmd(stub,root,archive,'corrupt'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        wait_for(archive);before=archive.read_bytes()
    else:
        setup=CORRUPT_READBACK if case=='readback_corrupt' else UNREADABLE_READBACK
        p=subprocess.Popen(supervise_cmd(stub,root,archive,'ok',setup),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        wait_for(root/IDENT/'latest.json');time.sleep(0.8);before=None   # several failed periodic publications
    p.send_signal(signal.SIGUSR1);out,err=p.communicate(timeout=60)
    assert p.returncode==76,(out,err);assert (root.parent/'UNPUBLISHED').exists()
    if before is None:assert not archive.exists() and 'failed' in err
    else:assert archive.read_bytes()==before
    assert not list(archive.parent.glob('.*partial*'))
