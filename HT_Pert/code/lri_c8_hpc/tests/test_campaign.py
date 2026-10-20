import os,sys,subprocess,json
from pathlib import Path
from lri_c8 import io
ROOT=Path(__file__).resolve().parents[1]
def test_campaign_lane(tmp_path):
    receipt=tmp_path/'test_receipt.json'
    io.atomic_save(receipt,{'status':'pass','source_sha256':io.source_digest(),'scope':'unit-test fixture, not production receipt'})
    env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'OPENBLAS_NUM_THREADS':'1','NUMBA_NUM_THREADS':'2'}
    manifest=tmp_path/'campaign.json'
    # 8 and 10 cross a digit boundary: plan keys must survive the JSON round trip.
    cmd=[sys.executable,str(ROOT/'scripts/make_campaign.py'),'--cutoffs','8','10','--schemes','raw','vacuum_only',
         '--threads','2','--memory-limit-gib','2','--receipt',str(receipt),'--output',str(manifest)]
    r=subprocess.run(cmd,env=env,capture_output=True,text=True)
    assert r.returncode!=0 and 'compute-node' in r.stderr  # a local receipt is refused by default
    subprocess.run(cmd+['--allow-local-receipt'],env=env,check=True,capture_output=True)
    m=io.read(manifest);cid=json.loads(manifest.read_text())['sha256'][:16]
    assert len(m['lanes'])==4 and set(m['plans'])=={'8','10'}
    assert [x['cutoff'] for lane in m['lanes'] for x in lane][:2]==[10,10]  # largest first
    info=lambda:subprocess.run([sys.executable,str(ROOT/'scripts/campaign_info.py'),'todo',str(manifest),str(tmp_path/'lane')],
                               env=env,check=True,capture_output=True,text=True).stdout.split()
    assert info()==['0,1,2,3',cid]
    for k in range(4):
        subprocess.run([sys.executable,str(ROOT/'scripts/run_lane.py'),'--manifest',str(manifest),'--lane',str(k),
                        '--output-dir',str(tmp_path/'lane')],env=env,check=True,capture_output=True)
    assert io.read(tmp_path/'lane/accepted/raw_L10_d8.json')['C'][8]>0
    assert io.read(tmp_path/'lane/accepted/vacuum_only_L8_d8.json')['C'][8]>0
    j=io.read(tmp_path/f'lane/journals/{cid}/lane_0.json')
    assert j['attempts'][-1]['exit']==0 and j['attempts'][-1]['items'][0]['status']=='accepted'
    assert not list((tmp_path/'lane/owners').rglob('*.owner'))  # released
    assert info()==['-',cid]
    # A rerun reuses the accepted output and appends a second attempt.
    subprocess.run([sys.executable,str(ROOT/'scripts/run_lane.py'),'--manifest',str(manifest),'--lane','0',
                    '--output-dir',str(tmp_path/'lane')],env=env,check=True,capture_output=True)
    assert len(io.read(tmp_path/f'lane/journals/{cid}/lane_0.json')['attempts'])==2

def test_lane_refuses_foreign_owner_and_too_few_cores(tmp_path):
    receipt=tmp_path/'r.json';io.atomic_save(receipt,{'status':'pass','source_sha256':io.source_digest()})
    env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'OPENBLAS_NUM_THREADS':'1','NUMBA_NUM_THREADS':'2'}
    env.pop('SLURM_JOB_ID',None)
    for name,threads in (('ok.json','1'),('big.json','100000')):
        subprocess.run([sys.executable,str(ROOT/'scripts/make_campaign.py'),'--cutoffs','4','--threads',threads,
                        '--memory-limit-gib','2','--receipt',str(receipt),'--output',str(tmp_path/name),
                        '--allow-local-receipt'],env=env,check=True,capture_output=True)
    lane=lambda name:subprocess.run([sys.executable,str(ROOT/'scripts/run_lane.py'),'--manifest',str(tmp_path/name),
                                     '--lane','0','--output-dir',str(tmp_path/'out')],env=env,capture_output=True,text=True)
    assert lane('big.json').returncode==64
    # Another writer (on any node) holds the solver's item owner: the solver exits 73.
    token=io.acquire_owner(tmp_path/'out/accepted/claims/raw_L4_d8.owner')
    r=lane('ok.json');assert r.returncode==73,r.stdout+r.stderr
    assert not (tmp_path/'out/accepted/raw_L4_d8.json').exists()
    io.release_owner(tmp_path/'out/accepted/claims/raw_L4_d8.owner',token)
    assert lane('ok.json').returncode==0

def _env():
    env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'OPENBLAS_NUM_THREADS':'1','NUMBA_NUM_THREADS':'2'}
    env.pop('SLURM_JOB_ID',None);return env

def _campaign(tmp_path,name='c.json',cutoffs=('4',)):
    receipt=tmp_path/'r.json'
    if not receipt.exists():io.atomic_save(receipt,{'status':'pass','source_sha256':io.source_digest()})
    subprocess.run([sys.executable,str(ROOT/'scripts/make_campaign.py'),'--cutoffs',*cutoffs,'--threads','1',
                    '--memory-limit-gib','2','--receipt',str(receipt),'--output',str(tmp_path/name),
                    '--allow-local-receipt'],env=_env(),check=True,capture_output=True)
    return tmp_path/name,json.loads((tmp_path/name).read_text())['sha256'][:16]

def _lane(manifest,out,lane=0,env=None):
    return subprocess.run([sys.executable,str(ROOT/'scripts/run_lane.py'),'--manifest',str(manifest),'--lane',str(lane),
                           '--output-dir',str(out)],env=env or _env(),capture_output=True,text=True)

def _info(manifest,out,*extra,env=None):
    r=subprocess.run([sys.executable,str(ROOT/'scripts/campaign_info.py'),'todo',str(manifest),str(out),*extra],
                     env=env or _env(),capture_output=True,text=True,check=True)
    return r.stdout.split()[0],r.stderr

def test_rejected_launcher_leaves_journal_alone(tmp_path):
    m,cid=_campaign(tmp_path);out=tmp_path/'out'
    journal=out/'journals'/cid/'lane_0.json'
    io.atomic_save(journal,{'campaign':cid,'lane':0,'attempts':[{'exit':137,'reason':'earlier OOM'}]})
    before=journal.read_bytes()
    token=io.acquire_owner(out/'owners'/'lanes'/f'{cid}_lane_0.owner')
    assert _lane(m,out).returncode==73
    assert journal.read_bytes()==before  # a launcher that does not own the lane never writes its journal
    io.release_owner(out/'owners'/'lanes'/f'{cid}_lane_0.owner',token)
    assert _info(m,out)[0]=='-'  # the earlier real failure still holds the lane
    assert _info(m,out,'--retry-failed')[0]=='0'

def test_failure_and_unusable_output_are_held(tmp_path):
    m,cid=_campaign(tmp_path);out=tmp_path/'out'
    bad=out/'accepted'/'raw_L4_d8.json';bad.parent.mkdir(parents=True);bad.write_text('not json')
    r=_lane(m,out);assert r.returncode==1,r.stdout+r.stderr
    att=io.read(out/'journals'/cid/'lane_0.json')['attempts'][-1]
    assert att['exit']==1 and att['items'][0]['status']=='failed'
    todo,err=_info(m,out,'--retry-failed');assert todo=='-' and 'unreadable output' in err
    bad.unlink();assert _info(m,out,'--retry-failed')[0]=='0'

def test_mismatched_output_is_not_done(tmp_path):
    m,cid=_campaign(tmp_path);out=tmp_path/'out'
    env={**_env(),'NUMBA_NUM_THREADS':'2'}
    subprocess.run([sys.executable,'-m','lri_c8','run','--cutoff','4','--threads','2','--memory-limit-gib','2',
                    '--output-dir',str(out/'accepted')],env=env,check=True,capture_output=True)
    todo,err=_info(m,out);assert todo=='-' and "does not match the frozen item in ['threads']" in err

def test_unfinished_attempt_classified_by_sacct(tmp_path):
    m,cid=_campaign(tmp_path);out=tmp_path/'out';bindir=tmp_path/'bin';bindir.mkdir()
    io.atomic_save(out/'journals'/cid/'lane_0.json',{'campaign':cid,'lane':0,'attempts':[
        {'slurm_job_id':'555','slurm_array_job_id':'555','slurm_array_task_id':'3','items':[]}]})
    sacct=bindir/'sacct'
    def with_state(state):
        # The bare id 555 would also match sibling tasks: only the 555_3 row may count.
        sacct.write_text(f'#!/bin/sh\n[ "$2" = "555_3" ] && printf "555_3|{state}\\n" && exit 0\n'
                         'printf "555_0|TIMEOUT\\n555_3|OUT_OF_MEMORY\\n"\n');sacct.chmod(0o755)
        return _info(m,out,env={**_env(),'PATH':f"{bindir}{os.pathsep}{os.environ['PATH']}"})
    assert with_state('TIMEOUT')[0]=='0'
    todo,err=with_state('OUT_OF_MEMORY');assert todo=='-' and 'without an exit record' in err
    todo,err=with_state('RUNNING');assert todo=='-' and 'still RUNNING' in err
    sacct.write_text('#!/bin/sh\nexit 1\n')
    todo,err=_info(m,out,env={**_env(),'PATH':f"{bindir}{os.pathsep}{os.environ['PATH']}"})
    assert todo=='-' and 'UNKNOWN' in err

def test_lane_rejects_other_stack_and_records_it(tmp_path):
    m,cid=_campaign(tmp_path);payload=io.read(m);payload['stack']={**payload['stack'],'numba':'0.0.0'}
    m2=tmp_path/'other_stack.json';io.atomic_save(m2,payload);cid2=json.loads(m2.read_text())['sha256'][:16]
    r=_lane(m2,tmp_path/'out');assert r.returncode==64,r.stdout+r.stderr
    att=io.read(tmp_path/'out'/'journals'/cid2/'lane_0.json')['attempts'][-1]
    assert att['exit']==64 and 'stack' in att['reason'] and att['items']==[]
    assert not list((tmp_path/'out'/'owners').rglob('*.owner'))

def test_production_receipt_coverage(tmp_path):
    import platform,numpy,numba,scipy
    stack={'python':platform.python_version(),'numpy':numpy.__version__,'numba':numba.__version__,'scipy':scipy.__version__}
    env=_env();layer=env.get('NUMBA_THREADING_LAYER','default')
    steps={k:{'returncode':0} for k in ('manifest','pytest','grid_replay','original_comparison','fs_probe')}
    steps['pytest']={'returncode':0,'collected':63,'counts':{'passed':63}}
    def make(name,**over):
        rec={'status':'pass','source_sha256':io.source_digest(),'kind':'compute-node','full':True,'stack':stack,
             'numba_threading_layer_setting':layer,'compare_cutoff':60,'steps':steps,**over}
        io.atomic_save(tmp_path/(name+'.receipt'),rec)
        return subprocess.run([sys.executable,str(ROOT/'scripts/make_campaign.py'),'--cutoffs','4','--threads','1',
                               '--memory-limit-gib','2','--receipt',str(tmp_path/(name+'.receipt')),
                               '--output',str(tmp_path/(name+'.json'))],env=env,capture_output=True,text=True)
    assert make('ok').returncode==0
    assert 'production coverage' in make('small',compare_cutoff=4).stderr
    assert 'production coverage' in make('nofs',steps={k:v for k,v in steps.items() if k!='fs_probe'}).stderr
    assert 'threading layer' in make('layer',numba_threading_layer_setting='other').stderr
    assert 'complete suite' in make('partial',steps={**steps,'pytest':{'returncode':0,'collected':63,'counts':{'passed':1}}}).stderr
    assert io.read(tmp_path/'ok.json')['threading_layer']==layer

def test_submitted_task_without_journal_is_classified(tmp_path):
    m,cid=_campaign(tmp_path);out=tmp_path/'out';out.mkdir();bindir=tmp_path/'bin';bindir.mkdir()
    (out/'submissions.txt').write_text(f'900 c8-abcdef12-{cid} 2026-10-03T00:00:00+0000 lanes=0\n'
                                       f'901 c8-abcdef12-0000000000000000 2026-10-03T00:00:00+0000 lanes=0\n')
    sacct=bindir/'sacct';env={**_env(),'PATH':f"{bindir}{os.pathsep}{os.environ['PATH']}"}
    def with_state(state):
        sacct.write_text(f'#!/bin/sh\n[ "$2" = "900_0" ] && printf "900_0|{state}\\n"\n');sacct.chmod(0o755)
        return _info(m,out,env=env)
    todo,err=with_state('FAILED');assert todo=='-' and '900_0 ended FAILED without a journal attempt' in err
    assert _info(m,out,'--retry-failed',env=env)[0]=='0'
    assert with_state('CANCELLED')[0]=='0'  # cancelled while pending, or an interruption: resubmit
    todo,err=with_state('PENDING');assert todo=='-' and 'still PENDING' in err

def test_todo_refuses_campaign_for_other_stack(tmp_path):
    m,cid=_campaign(tmp_path);payload=io.read(m);payload['stack']={**payload['stack'],'numpy':'0.0'}
    io.atomic_save(tmp_path/'other.json',payload)
    r=subprocess.run([sys.executable,str(ROOT/'scripts/campaign_info.py'),'todo',str(tmp_path/'other.json'),str(tmp_path/'out')],
                     env=_env(),capture_output=True,text=True)
    assert r.returncode!=0 and 'differs' in r.stderr

def test_clean_owners_only_moves_provably_stale(tmp_path):
    out=tmp_path/'out';bindir=tmp_path/'bin';bindir.mkdir()
    lane=out/'owners'/'lanes'/'x_lane_0.owner';item=out/'accepted'/'checkpoints'/'claims'/'raw_L4_d8.owner'
    env={**_env(),'PATH':f"{bindir}{os.pathsep}{os.environ['PATH']}",'USER':'me'}
    def owners(lane_job,item_job):
        for p,j in ((lane,lane_job),(item,item_job)):
            p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'slurm_job_id':j,'host':'h','pid':1} if j else {'host':'h','pid':1}))
    squeue=bindir/'squeue'
    def run(queue):
        squeue.write_text('#!/bin/sh\n'+(f'printf "{queue}"\n' if queue is not None else 'exit 1\n'));squeue.chmod(0o755)
        return subprocess.run([sys.executable,str(ROOT/'scripts/clean_owners.py'),str(out)],env=env,capture_output=True,text=True)
    owners('11','12')
    r=run('12 RUNNING\\n11 TIMEOUT\\n');assert r.returncode==3 and 'job 12 is RUNNING' in r.stderr and lane.exists() and item.exists()
    assert run(None).returncode==3 and lane.exists()  # squeue failure: nothing moved
    owners('11',None)
    r=run('');assert r.returncode==3 and 'no Slurm job recorded' in r.stderr and lane.exists()
    owners('11','12')
    r=run('12 COMPLETED\\n');assert r.returncode==0,r.stderr
    assert not lane.exists() and not item.exists() and len(list((out/'owners_stale').rglob('*.owner')))==2
    assert run('').stdout.strip()=='no owner files'

def test_solver_owner_and_exclusive_publication(tmp_path):
    env={**_env(),'NUMBA_NUM_THREADS':'2'}
    call=lambda *a:subprocess.run([sys.executable,'-m','lri_c8',*map(str,a)],env=env,capture_output=True,text=True)
    # A direct solver respects an owner held on another node (only the O_EXCL file is shared).
    token=io.acquire_owner(tmp_path/'claims'/'raw_L4_d8.owner')
    assert call('run','--cutoff',4,'--memory-limit-gib',2,'--output-dir',tmp_path).returncode==73
    io.release_owner(tmp_path/'claims'/'raw_L4_d8.owner',token)
    # Its checkpoint is owned too: a writer whose destination is that checkpoint (e.g. a run
    # with --output-dir <dir>/checkpoints) blocks the solver.
    ck=tmp_path/'checkpoints'/'raw_L4_d8.json';token=io.acquire_owner(io.owner_path(ck))
    assert call('run','--cutoff',4,'--memory-limit-gib',2,'--output-dir',tmp_path).returncode==73
    io.release_owner(io.owner_path(ck),token)
    assert call('run','--cutoff',4,'--memory-limit-gib',2,'--output-dir',tmp_path).returncode==0
    assert not (tmp_path/'claims'/'raw_L4_d8.owner').exists()
    # Export: a concurrent publisher (owner present) is refused, then a normal export works
    # and a second export is refused without touching the first one's files.
    exp=tmp_path/'e.json';t=io.acquire_owner(io.owner_path(exp))
    r=call('export','--inputs',tmp_path/'raw_L4_d8.json','--output',exp);assert r.returncode==73 and not exp.exists()
    io.release_owner(io.owner_path(exp),t)
    # The sidecar is owned too: a publisher of e.provenance.json blocks the export.
    t=io.acquire_owner(io.owner_path(tmp_path/'e.provenance.json'))
    assert call('export','--inputs',tmp_path/'raw_L4_d8.json','--output',exp).returncode==73 and not exp.exists()
    io.release_owner(io.owner_path(tmp_path/'e.provenance.json'),t)
    assert call('export','--inputs',tmp_path/'raw_L4_d8.json','--output',exp).returncode==0
    before=(exp.read_bytes(),exp.with_suffix('.provenance.json').read_bytes())
    assert call('export','--inputs',tmp_path/'raw_L4_d8.json','--output',exp).returncode!=0
    assert (exp.read_bytes(),exp.with_suffix('.provenance.json').read_bytes())==before
    assert not list(tmp_path.rglob('*.owner')) and not list(tmp_path.glob('*.tmp.*'))
    # assemble into the solver's destination uses the solver's owner (one owner per file).
    assert io.owner_path(tmp_path/'raw_L4_d8.json')==tmp_path/'claims'/'raw_L4_d8.owner'
