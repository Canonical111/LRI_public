"""Lane mode and the campaign entry points (PLAN D.9, D.10, D.11; A-ORC-4, A-ORC-10, the auto lane time, held jobs,
drill mode), array recovery and the re-merge after a recovered index (F8-d3): the lane part of
tests/unit_orchestration.py (imported by it; not run alone). Also the Stage-6 group-A cases run with the scratch
package: the CPU vendor pin and the mixed-vendor merge (S2-001), seed reservations through slurm/plan.sh and
tools/sweep.py, required wherever seeds are checked (S2-002), plan staging and publication (S2-005) and stop signals
in lane mode (F7).
Every lane-mode campaign here plans with role campaign on a model that make_cost_model.py measured from a fake
cost_sweep of the same fake worker (HC7)."""
from __future__ import annotations
import hashlib,json,math,os,re,shutil,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import c8pkg
from c8pkg import tool,manifest,config
from unit_orchestration import ok,must,spy,opened,SEED

def wait_for(cond,seconds:float)->bool:
    end=time.time()+seconds
    while time.time()<end:
        if cond():return True
        time.sleep(0.05)
    return cond()

def alive(pid:int)->bool:
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False
    except PermissionError:return True

def fake_sysfs(root:Path,nodes:int,per:int,sockets:int=2)->Path:
    """A /sys tree: `nodes` NUMA nodes of `per` cores, no SMT, the nodes split over `sockets` packages."""
    for n in range(nodes):
        d=root/f'devices/system/node/node{n}';d.mkdir(parents=True,exist_ok=True);(d/'cpulist').write_text(f'{n*per}-{n*per+per-1}\n')
        for c in range(n*per,n*per+per):
            t=root/f'devices/system/cpu/cpu{c}/topology';t.mkdir(parents=True,exist_ok=True)
            (t/'physical_package_id').write_text(str(n*sockets//nodes));(t/'core_id').write_text(str(c))
    return root

def campaign(E,site,name,seed,**kw):
    d=site.run_dir(name);E.plan(d,'--pilot','--test-only','--replicates',kw.pop('reps',2),'--threads',kw.pop('threads',2),'--cost-model',E.model(),'--index-hours',kw.pop('ih',0.001),
                                *kw.pop('extra',[]),seed=seed,**kw)
    return d

def worker(E,site,d,jid,**x):
    return E.t('lanes.py','worker',d,check=False,**site.env(C8_RUN=d,SLURM_JOB_ID=jid,SLURM_TMPDIR=E.scr,**x))

def merge_job(E,site,d,jid,**x):
    """The real slurm/merge.sh as the body of the fake merge job jid (status, merge, assemble; as test_pipeline's job_body)."""
    j=next(j for j in site.jobs()if j['id']==jid);tmp=E.scr/f'job_{jid}';tmp.mkdir(exist_ok=True)
    return subprocess.run(['bash',str(E.pkg/'slurm/merge.sh')],capture_output=True,text=True,
                          env=c8pkg.env(**site.env(C8_RUN=d,C8_PACKAGE=E.pkg,C8_PYTHON=sys.executable,SLURM_JOB_ID=jid,SLURM_JOB_NAME=j['name'],SLURM_TMPDIR=tmp,
                                                   SLURM_CPUS_PER_TASK=2,C8_BOOTSTRAP=16,**x)))

def test_lanes(E,td:Path):
    import lanes
    from common import Refuse
    # NUMA shapes from fake sysfs: the Expanse compute tree 8 x 16, numa:2 -> 4 x 32, numa:4 -> 2 x 64; the login tree 16 x 4; symmetry 8 x 8
    old=os.environ.get('C8_SYSFS')
    try:
        for name,(nodes,per),cases in (('expanse',(8,16),{'numa':[16]*8,'numa:2':[32]*4,'numa:4':[64]*2,None:[16]*8,'4':[32]*4}),
                                       ('login',(16,4),{'numa':[4]*16}),('symmetry',(8,8),{'numa':[8]*8})):
            os.environ['C8_SYSFS']=str(fake_sysfs(td/f'sys_{name}',nodes,per))
            cpus=list(range(nodes*per))
            for spec,want in cases.items():
                got=[len(x)for x in lanes.cpu_lanes(cpus,spec,vendor='AuthenticAMD')];assert got==want,(name,spec,got)
            if name=='expanse':
                lanes_=lanes.cpu_lanes(cpus,'numa',vendor='AuthenticAMD');assert lanes_[1]==list(range(16,32))
                part=lanes.cpu_lanes(list(range(16,48)),'numa',vendor='AuthenticAMD');assert [len(x)for x in part]==[16,16]   # affinity intersected
                assert [len(x)for x in lanes.cpu_lanes(list(range(10)),'2',drill=True)]==[5,5]
                try:lanes.cpu_lanes(cpus,'numa',drill=True);raise AssertionError
                except Refuse as r:assert r.code==64
                try:lanes.cpu_lanes(cpus,'numa:x');raise AssertionError
                except Refuse as r:assert r.code==64
    finally:
        if old is None:os.environ.pop('C8_SYSFS',None)
        else:os.environ['C8_SYSFS']=old
    # the memory guard, the class factor, time left
    G=2**30;assert lanes.memory_guard(8,30*G,240*G)==6 and lanes.memory_guard(8,G,240*G)==8
    try:lanes.memory_guard(8,230*G,240*G);raise AssertionError
    except Refuse as r:assert r.code==64
    cm={'cpu_model':'AMD EPYC 7742 64-Core Processor','cpu_class_factors':{'Intel Xeon Gold 6248':{'a':{'free':{'8':1.3,'6':1.1}}}}}
    assert lanes.class_factor(cm,'AMD  EPYC 7742 64-Core Processor','a','free',8)==1.0 and lanes.class_factor(cm,'Intel Xeon Gold 6248','a','free',8)==1.3
    assert lanes.class_factor(cm,'Intel Xeon Gold 6248','a','free',4)==1.1 and lanes.class_factor(cm,'other','a','free',8)==1.5 and lanes.class_factor(None,'x','a','free',8)==1.5
    stub=td/'sqbin';stub.mkdir();(stub/'squeue').write_text('#!/bin/sh\nprintf "%s\\n" "$FAKE_L"\n');(stub/'squeue').chmod(0o755)
    code='import sys,os,json;sys.path.insert(0,sys.argv[1]);import lanes\ntry:print(json.dumps(lanes.remaining_seconds("42",dict(os.environ))))\nexcept Exception as e:print("ERR",getattr(e,"code",None),e)'
    def left(**x):
        return subprocess.run([sys.executable,'-B','-c',code,str(E.pkg/'tools')],capture_output=True,text=True,
                              env=c8pkg.env(PATH=f'{stub}:{os.environ["PATH"]}',**x)).stdout.strip()
    assert json.loads(left(FAKE_L='1-02:03:04'))[0]==93784 and json.loads(left(FAKE_L='45:00'))[0]==2700
    assert left(FAKE_L='UNLIMITED').startswith('ERR 69')
    u=json.loads(left(FAKE_L='UNLIMITED',C8_TIME_POLICY='unlimited').replace('Infinity','1e999'))[0];assert u==math.inf
    assert json.loads(left(FAKE_L='UNLIMITED',C8_LANE_SECONDS='600'))[0]==600 and left(FAKE_L='INVALID').startswith('ERR 69')
    assert left(FAKE_L='1:00:00',C8_TIME_POLICY='bogus').startswith('ERR 64')
    # queue generations and the bounded scan (10^5 indices, 64 lanes)
    run=td/'genrun';(run/'lanes/done').mkdir(parents=True);(run/'lanes/claims').mkdir();lanes.write_queue(run,[(1,10.),(2,5.)],generation=1)
    v=lanes.LaneView(run);v.refresh();assert [i for i,_ in v.candidates(2)]==[1,2]
    (run/'lanes/done/1').write_text('x');v.refresh();assert [i for i,_ in v.candidates(2)]==[1,2]   # done/ re-listed only after 60 s or a new generation
    lanes.write_queue(run,[(1,10.),(2,5.),(3,1.)],generation=2);v.refresh();assert [i for i,_ in v.candidates(2)]==[2,3]
    big=td/'bigq';(big/'lanes/done').mkdir(parents=True);(big/'lanes/claims').mkdir();(big/'lanes/failures').mkdir()
    lanes.write_queue(big,[(i,float(10**5-i))for i in range(10**5)],generation=7)
    for i in range(0,10**5,2):(big/f'lanes/done/{i}').write_text('')
    calls={'n':0};real_l,real_s=os.listdir,os.stat
    def cl(*a,**k):calls['n']+=1;return real_l(*a,**k)
    def cs(*a,**k):calls['n']+=1;return real_s(*a,**k)
    views=[lanes.LaneView(big)for _ in range(64)];t0=time.time();views[0].refresh();first=time.time()-t0
    os.listdir,os.stat=cl,cs
    try:
        for v in views[1:]:v.refresh()
        per_scan=calls['n']/63;calls['n']=0;views[0].refresh();again=calls['n']
    finally:os.listdir,os.stat=real_l,real_s
    assert per_scan<=6 and again<=4 and first<1.0,(per_scan,again,first)
    assert next(views[0].candidates(2))[0]==1
    ok('A-ORC-4: NUMA shapes from fake sysfs (Expanse compute 8 x 16, numa:2 -> 4 x 32, numa:4 -> 2 x 64, the default on AMD = numa, n equal '
       'parts; login 16 x 4; symmetry 8 x 8; the job affinity intersected; drill mode splits the affinity set); the memory guard reduces or '
       'refuses (64); the CPU-class factor (1 on the model CPU, the measured class, 1.5 unknown); squeue %L time left (UNLIMITED: no deadline only '
       'under C8_TIME_POLICY=unlimited, else C8_LANE_SECONDS or 69); queue generations re-list '
       'done/ at once; a queue of 10^5 indices scanned by 64 lanes costs a constant number of filesystem calls per scan and < 1 s',
       fs_calls_per_scan=per_scan,first_scan_seconds=round(first,3))

def test_lanes_submission(E,td:Path):
    import lanes,slurm_submit as ss,production as prod
    site=c8pkg.SlurmSite(td,'subm')
    d=campaign(E,site,'L1',SEED+31)
    # --dry-run: the snapshot, the derived lane time (hand value), the reservation, the merge path, the line admission; nothing submitted
    m=manifest(d);entries=lanes.queue_entries(d,m,prod.job_progress(d,m))
    W=sum(e for _,e in entries)/(2*128*0.9);need=max(e/(m['threads']*0.9)*1.5+300 for _,e in entries);T=math.ceil(max(1.5*W+900,need+900)/900)*900
    cp=must(site.submit(E.pkg,'lanes','2','--dry-run',C8_RUN=d),0,f'lane time {ss.hms(T)}','reservation mode=reservation;id=H7E-R','the merge will take the path: assemble',
            'dry run: the line admits','projected','counts')
    assert not site.history()and ss.auto_lane_time(m,entries,2)['seconds']==T
    # lanes 2 then lanes 1: one pending merge on all three workers, the superseded one cancelled after the re-snapshot passes
    must(site.submit(E.pkg,'lanes','2',C8_RUN=d),0);must(site.submit(E.pkg,'lanes','1',C8_RUN=d),0)
    jobs=site.jobs();merges=[j for j in jobs if j['name'].startswith('c8d3-merge-')];lan=[j for j in jobs if j['name'].startswith('c8d3-lane-')]
    pend=[j for j in merges if j['state']=='PENDING'];assert len(lan)==3 and len(pend)==1 and sorted(pend[0]['dep']['ids'])==sorted(j['id']for j in lan)
    lsb=[h['argv']for h in site.history()if any(x.startswith('--job-name=c8d3-lane-')or x=='c8d3-lane'for x in h['argv'])or any('c8d3-lane-'in x for x in h['argv'])]
    assert len(lsb)>=3 and all('--mem=240G'in a and ('compute'in a or '--partition=compute'in a)for a in lsb),lsb[:1]   # A-ORC-5
    assert [j['state']for j in merges if j['id']!=pend[0]['id']]==['CANCELLED']
    # a running merge is never cancelled; lanes 0 submits a merge on the live workers only
    site.fake.set(pend[0]['id'],state='RUNNING',start=site.fake.now())
    must(site.submit(E.pkg,'lanes','0',C8_RUN=d),0);jobs=site.jobs()
    assert next(j for j in jobs if j['id']==pend[0]['id'])['state']=='RUNNING'
    newm=[j for j in jobs if j['name'].startswith('c8d3-merge-')and j['state']=='PENDING'];assert len(newm)==1 and sorted(newm[0]['dep']['ids'])==sorted(j['id']for j in lan)
    ids={j['id']for j in lan};assert not [j for j in jobs if j['name'].startswith('c8d3-lane-')and j['id']not in ids]
    # mixed mode: array mode refuses while lane workers are live, lane mode while array elements are live
    must(site.submit(E.pkg,'submit',C8_RUN=d),65,'lane mode and array mode are not mixed')
    d2=campaign(E,site,'L2',SEED+32,ih=1);must(site.submit(E.pkg,'submit',C8_RUN=d2),0)
    must(site.submit(E.pkg,'lanes','1',C8_RUN=d2),65,'not mixed')
    # the workers: one lane worker runs every index (requeue safety: its own stale claims released first)
    for j in lan:site.fake.finish(j['id'],'COMPLETED',elapsed=10)
    jw=lan[0]['id'];(d/'lanes/claims').mkdir(parents=True,exist_ok=True)
    (d/'lanes/claims/0.json').write_text(json.dumps({'job':jw,'lane':0,'start_epoch':0}))
    cp=worker(E,site,d,jw,C8_LANES='2',C8_LANE_SECONDS='36000');assert cp.returncode==0 and 'released own stale claim 0'in cp.stdout,cp.stdout[-800:]+cp.stderr[-800:]
    must(E.t('production.py','status',d,'--fast',check=False),0,'every checkpoint block is committed')
    # held jobs (D.9): a lane worker pending with `launch failed requeued held` is released once (annotation), cancelled at its second hold;
    # another held job is reported and left alone; admission counts the held job
    d3=campaign(E,site,'L3',SEED+33);must(site.submit(E.pkg,'lanes','1',C8_RUN=d3),0)
    h=[j for j in site.jobs()if j['name'].startswith('c8d3-lane-')and j['state']=='RUNNING'][-1]['id']
    site.fake.set(h,state='PENDING',reason='launch failed requeued held',start=None,hold_start=True)
    must(site.submit(E.pkg,'release',h),0,'released held job');assert len(site.history('scontrol'))>=1
    site.fake.set(h,state='PENDING',reason='launch failed requeued held',start=None,hold_start=True)   # held a second time
    must(site.submit(E.pkg,'release',h),0,'cancelled');assert next(j for j in site.jobs()if j['id']==h)['state']=='CANCELLED'
    o=site.fake.add_job('c8d3-lane-cccccccccccc-dddddddddddd',state='PENDING',partition='compute',nodes=1,cpus=128,comment='c8d3:cccccccccccc:000000000000:dddddddddddd')[0]
    site.fake.set(o,reason='JobHeldUser');n0=len(site.history('scancel'))
    must(site.submit(E.pkg,'release',o),69,'reported, nothing done');assert len(site.history('scancel'))==n0
    ann=[json.loads(l)['rec']for l in (site.root/'ledger.jsonl').read_text().splitlines()];acts=[r['action']for r in ann if r['kind']=='annotation'and r.get('about')=='held_release']
    assert acts==['release_attempt','released','cancelled'],acts   # the attempt is recorded before scontrol (S2-006)
    # drill mode (shared or debug; no --exclusive; -c C8_LANE_CPUS 2..16; --mem <= 2G x CPUs; test-only plans)
    d4=campaign(E,site,'L4',SEED+34);n0=len(site.history())
    for part,lim in (('shared','01:00:00'),('debug','00:25:00')):
        must(site.submit(E.pkg,'lanes','1',C8_RUN=d4,C8_LANE_DRILL='1',C8_LANE_CPUS='16',C8_LANE_MEM='32G',C8_LANE_TIME=lim,C8_SBATCH_ARGS=f'-A yun124 -p {part}',
                         C8_MERGE_SBATCH_ARGS='-A yun124 -p shared -c 4 --mem=8G -t 00:30:00'),0)
        sb=site.history()[-2]['argv'];assert '--exclusive'not in sb and '--cpus-per-task=16'in sb and f'-p'in sb and part in sb,sb
    must(site.submit(E.pkg,'lanes','1',C8_RUN=d4,C8_LANE_DRILL='1',C8_LANE_CPUS='32',C8_LANE_MEM='32G',C8_SBATCH_ARGS='-A yun124 -p shared'),64,'C8_LANE_CPUS')
    must(site.submit(E.pkg,'lanes','1',C8_RUN=d4,C8_LANE_DRILL='1',C8_LANE_CPUS='4',C8_LANE_MEM='32G',C8_SBATCH_ARGS='-A yun124 -p shared'),64,'exceeds 2G')
    must(site.submit(E.pkg,'lanes','1',C8_RUN=d4,C8_LANE_DRILL='1',C8_LANE_CPUS='4',C8_LANE_MEM='8G',C8_SBATCH_ARGS='-A yun124 -p compute'),64,'shared or debug')
    nt=site.run_dir('L5');E.plan(nt,'--pilot','--replicates',2,'--threads',2,'--cost-model',E.model(),'--forbid-seeds-from',E.seeds,'--index-hours',0.001,seed=SEED+35)
    must(site.submit(E.pkg,'lanes','1',C8_RUN=nt,C8_LANE_DRILL='1',C8_LANE_CPUS='4',C8_LANE_MEM='8G',C8_SBATCH_ARGS='-A yun124 -p shared'),64,'test-only plans')
    dw=[j for j in site.jobs()if j['name'].startswith('c8d3-lane-')and j['partition']=='debug'][-1]['id']
    cp=worker(E,site,d4,dw,C8_LANE_DRILL='1',C8_LANES='2',C8_LANE_SECONDS='36000');assert cp.returncode==0 and '2 lane(s)'in cp.stdout,cp.stdout[-600:]+cp.stderr[-600:]
    ok('A-ORC-10/D.9/D.10: lanes --dry-run prints the snapshot, the auto lane time (= the hand value), the reservation, the merge path and what the '
       'line admits, and submits nothing; lanes 2 then lanes 1 leave one pending merge on all three workers (the superseded one cancelled); a '
       'running merge is never cancelled and lanes 0 adds a merge on the live workers only; lane and array mode are not mixed (65 both ways); '
       'a worker releases its own stale claims and runs the campaign; a `launch failed requeued held` worker is released once and cancelled at '
       'its second hold (annotations), another held job is left alone; drill mode on shared and debug (no --exclusive, -c 2..16, mem <= 2G x '
       'CPUs, test-only plans) is admitted and its worker splits the affinity set')

def test_done_markers(E,td:Path):
    import lanes,production as prod
    site=c8pkg.SlurmSite(td,'done');d=campaign(E,site,'D1',SEED+41)
    must(site.submit(E.pkg,'lanes','1',C8_RUN=d),0);jw=[j for j in site.jobs()if j['name'].startswith('c8d3-lane-')][-1]['id']
    assert worker(E,site,d,jw,C8_LANES='1',C8_LANE_SECONDS='36000').returncode==0
    m=manifest(d);j=m['jobs'][3];ck=d/'groups'/j['group']/'checkpoints'/f'{prod.block_name(j["shard"],0)}.json';saved=json.loads(ck.read_text())
    assert (d/f'lanes/done/{j["id"]}').exists()
    # (iv) a marker without its blocks still makes merge refuse with "incomplete campaign"; (v) status and merge never open lanes/done/
    ck.unlink();must(E.t('production.py','merge',d,'--scratch',E.scr,check=False),1,'Incomplete campaign')
    for args in (['status',d,'--fast'],['merge',d,'--scratch',E.scr]):
        cp,ev=spy(E.pkg,td,'production.py',*args);assert not [p for p in opened(ev,False)if '/lanes/done/'in p],args
    # (ii) a lane that saw the old generation picks the index up after the rebuild's new generation
    v=lanes.LaneView(d);v.refresh();assert j['id']not in [i for i,_ in v.candidates(2)]
    # (i) the next lanes 1 rebuilds the queue: the marker is removed and logged, the index queued again; a lane recomputes it
    for x in site.jobs():
        if x['state']in('RUNNING','PENDING'):site.fake.finish(x['id'],'COMPLETED',elapsed=5)
    must(site.submit(E.pkg,'lanes','1',C8_RUN=d),0,'done markers of incomplete indices removed')
    inv=[json.loads(l)for l in (d/'lanes/done_invalidated.jsonl').read_text().splitlines()];assert [x['index']for x in inv]==[j['id']]
    assert not (d/f'lanes/done/{j["id"]}').exists();v.refresh();assert j['id']in [i for i,_ in v.candidates(2)]
    jw2=[x for x in site.jobs()if x['name'].startswith('c8d3-lane-')and x['state']=='RUNNING'][-1]['id']
    assert worker(E,site,d,jw2,C8_LANES='1',C8_LANE_SECONDS='36000').returncode==0
    new=json.loads(ck.read_text());keys=prod.SCIENTIFIC
    assert all(a.get(k)==b.get(k)for a,b in zip(saved['native']['rows'],new['native']['rows'])for k in keys)
    must(E.t('production.py','status',d,'--fast',check=False),0)
    # (iii) a claim holder that finds a marker on its claimed, incomplete index removes it and runs the index
    j2=m['jobs'][5];ck2=d/'groups'/j2['group']/'checkpoints'/f'{prod.block_name(j2["shard"],0)}.json';ck2.unlink()
    # the scratch package's own lanes.attempt in a process of its own (its ROOT is the package's), the view's done set stale
    code=('import sys,json,os;sys.path.insert(0,sys.argv[1]);import lanes\nfrom pathlib import Path\nd=Path(sys.argv[2]);m=json.loads((d/"manifest.json").read_text())\n'
          'v=lanes.LaneView(d);v.done=set()\nprint(lanes.attempt(d,m,int(sys.argv[3]),1.,{"job":"999","lane":0},v,2,Path(sys.argv[4]),dict(os.environ),d/"lanes/logs","999","0",0))')
    cp=subprocess.run([sys.executable,'-B','-c',code,str(E.pkg/'tools'),str(d),str(j2['id']),str(E.scr)],capture_output=True,text=True,env=c8pkg.env())
    assert cp.stdout.strip()=='done'and ck2.exists()and (d/f'lanes/done/{j2["id"]}').exists(),cp.stdout+cp.stderr[-600:]
    inv=[json.loads(l)for l in (d/'lanes/done_invalidated.jsonl').read_text().splitlines()];assert inv[-1]['index']==j2['id']and 'claim holder'in inv[-1]['reason']
    ok('A-ORC-4 done markers: (i) a completed index that lost a checkpoint loses its marker at the next lanes 1 (logged in done_invalidated.jsonl), '
       'is queued again and recomputed with scientific fields equal to the saved checkpoint, status exits 0; (ii) a lane that saw the old '
       'generation picks it up after the new one; (iii) a claim holder that finds a marker on its incomplete index removes it and runs it; (iv) a '
       'marker without its blocks still makes merge refuse "Incomplete campaign"; (v) status and merge never open lanes/done/ (spy)')

def test_recovery_merge(E,td:Path):
    """F8-d3 (C62d's F8, LRI_C8_D2_HPC 86e15f4; A-ORC-4 (i)): J-DRL-8 run unattended on the fake Slurm, the Stage-5
    failure of symmetry jobs 570487 and 570490 reproduced. A lane-mode campaign is completed and its merge job
    (slurm/merge.sh: status, merge, assemble) publishes the result. One checkpoint of a completed index and its group's
    merged.json are deleted; `lanes 1` rebuilds the queue (the marker dropped and logged) and a lane recomputes the index
    with other timings (C8_FAKE_SPP), so the group's graph_costs.csv and merged.json differ in timing only. The next
    merge job then succeeds: merged.json is the commit point, so the uncommitted graph_costs.csv is replaced (reported,
    timing only) while the scientific tables stay byte-identical, the new batches equal the saved ones, and assemble
    supersedes the result whose only change is that group's merged_sha256 (the old bytes kept as
    C8_test_result.superseded.<sha12>.json; the new one verifies). A rerun of the merge job changes nothing. Real
    conflicts are still refused: a changed table of a committed group stops the merge; a stale uncommitted scientific
    table is replaced and reported as such; a committed table never changes (_publish_copy); a result whose science
    differs is not overwritten. S3-R2-007, on a copy of the campaign: a recovered checkpoint whose row has another positive
    tail_sum (jets and top 16 unchanged; checkpoint validation admits it) re-merges into another graph_tails.csv
    ("SCIENTIFIC TABLE CHANGED") while every assembled value stays the same (an in-process evaluate equals the published
    result apart from merged_sha256 and science_sha256), and assemble refuses it naming the group and graph_tails.csv;
    before S3-R2-007 it superseded the result as "scientific content unchanged". Function level: combine's results
    (combined_from[i].merged_sha256, superseded only with equal recorded scientific identities, combined_from[i].
    science_sha256; a changed or missing one is refused) and the pilot_subset summary (only its timing digests may
    change). Before F8-d3 the merge job stops at "Checksum mismatch" on graph_costs.csv, and with that fixed alone, at the
    result's "exists and differs"."""
    import production as prod,assemble as asm,pilot_report as pr
    site=c8pkg.SlurmSite(td,'recm');d=campaign(E,site,'R1',SEED+61)
    def lanes1():
        before={j['id']for j in site.jobs()};must(site.submit(E.pkg,'lanes','1',C8_RUN=d),0);new=[j for j in site.jobs()if j['id']not in before]
        return next(j['id']for j in new if j['name'].startswith('c8d3-lane-')),next(j['id']for j in new if j['name'].startswith('c8d3-merge-'))
    def run_lane(jw,**x):
        cp=worker(E,site,d,jw,C8_LANES='1',C8_LANE_SECONDS='36000',**x);assert cp.returncode==0,cp.stdout[-800:]+cp.stderr[-800:];site.fake.finish(jw,'COMPLETED',elapsed=60)
    def run_merge(jm):
        cp=merge_job(E,site,d,jm);site.fake.finish(jm,'COMPLETED'if cp.returncode==0 else'FAILED',elapsed=20);return cp
    jw,jm=lanes1();run_lane(jw);cp=run_merge(jm);assert cp.returncode==0,(cp.stdout[-800:],cp.stderr[-800:])
    res=d/'C8_test_result.json';saved_res=res.read_bytes()
    m=manifest(d);j=max(m['jobs'],key=lambda j:(j['blocks'],-j['id']));idx=j['id'];g=d/'groups'/j['group'];ck=g/'checkpoints'/f'{prod.block_name(j["shard"],0)}.json'
    names=('merged.json','graph_replicates.csv','graph_tails.csv','graph_promotions.csv','graph_costs.csv')
    saved={f:(g/f).read_bytes()for f in names};saved_ck=json.loads(ck.read_text())
    ck.unlink();(g/'merged.json').unlink()
    jw,jm=lanes1()   # the queue rebuild drops the done marker of the incomplete index and logs it
    inv=[json.loads(l)for l in (d/'lanes/done_invalidated.jsonl').read_text().splitlines()];assert [x['index']for x in inv]==[idx],inv
    run_lane(jw,C8_FAKE_SPP='0.0015');must(E.t('production.py','status',d,'--fast',check=False),0)
    new_ck=json.loads(ck.read_text());sci=lambda c:[{k:r.get(k)for k in prod.SCIENTIFIC}for r in c['native']['rows']]
    assert sci(new_ck)==sci(saved_ck)and [r['seconds']for r in new_ck['native']['rows']]!=[r['seconds']for r in saved_ck['native']['rows']]   # other timings
    # the merge job of J-DRL-8: before F8-d3 it stopped at the stale graph_costs.csv, then at the result's no-clobber rule
    cp=run_merge(jm);assert cp.returncode==0,(cp.stdout[-1500:],cp.stderr[-1500:])
    assert f'{j["group"]}: replaced the uncommitted graph_costs.csv'in cp.stdout and 'timing only'in cp.stdout and 'SCIENTIFIC'not in cp.stdout,cp.stdout[-1200:]
    new_m=json.loads((g/'merged.json').read_text());old_m=json.loads(saved['merged.json'])
    assert new_m['batches']==old_m['batches']and new_m['graph_costs_sha256']!=old_m['graph_costs_sha256']and new_m['graph_costs_sha256']==hashlib.sha256((g/'graph_costs.csv').read_bytes()).hexdigest()
    assert all((g/f).read_bytes()==saved[f]for f in names[1:4])and (g/'graph_costs.csv').read_bytes()!=saved['graph_costs.csv']
    sha=hashlib.sha256(saved_res).hexdigest();keep=d/f'C8_test_result.superseded.{sha[:12]}.json'
    assert 'superseded: scientific content unchanged'in cp.stdout and keep.read_bytes()==saved_res,(cp.stdout[-800:],sorted(x.name for x in d.iterdir()))
    new_r=json.loads(res.read_text());old_r=json.loads(saved_res)
    assert {k for k in new_r if new_r[k]!=old_r[k]}=={'merged_sha256'}and {x for x in new_r['merged_sha256']if new_r['merged_sha256'][x]!=old_r['merged_sha256'][x]}=={j['group']}
    must(E.t('verify_result.py',res,check=False),0)
    snap=c8pkg.tree(d);cp=run_merge(jm);assert cp.returncode==0 and 'identical result already present; kept'in cp.stdout and c8pkg.tree(d)==snap,cp.stdout[-600:]
    # S3-R2-007 (a copy of the campaign): a recovered checkpoint with another positive tail_sum in one row (jets and top 16
    # unchanged) re-merges into another graph_tails.csv while every assembled value stays the same; assemble refuses it
    from common import canon,object_hash
    d7=td/'R1_sci';shutil.copytree(d,d7);g7=d7/'groups'/j['group'];ck7=g7/'checkpoints'/ck.name;doc=json.loads(ck7.read_text())
    row=next(r for r in doc['native']['rows']if float(r['tail_sum'])>0);ts=row['tail_sum'];row['tail_sum']=str(prod.D(str(ts))*2)if isinstance(ts,str)else 2*ts
    doc['payload_sha256']=object_hash(doc['native']);ck7.unlink();ck7.write_text(json.dumps(doc));res7=d7/'C8_test_result.json';pub7=res7.read_bytes()
    tails0=(g7/'graph_tails.csv').read_bytes();m7=json.loads((g7/'merged.json').read_text());(g7/'merged.json').unlink()
    r=E.merge(d7,'--group',j['group'])
    assert f'{j["group"]}: replaced the uncommitted graph_tails.csv'in r.stdout and 'SCIENTIFIC TABLE CHANGED'in r.stdout and (g7/'graph_tails.csv').read_bytes()!=tails0,r.stdout[-800:]
    assert json.loads((g7/'merged.json').read_text())['batches']==m7['batches']
    sup7=sorted(d7.glob('C8_test_result.superseded.*'));cp7=E.t('assemble.py',d7,'--bootstrap',16,check=False)
    assert cp7.returncode==1 and 'exists and differs from the recomputed result'in cp7.stderr and 'scientific identity changed'in cp7.stderr and j['group']in cp7.stderr \
        and 'graph_tails.csv'in cp7.stderr and res7.read_bytes()==pub7 and sorted(d7.glob('C8_test_result.superseded.*'))==sup7,(cp7.returncode,cp7.stderr[-600:],cp7.stdout[-300:])
    strip=lambda x:{k:v for k,v in x.items()if k not in('merged_sha256','science_sha256')}  # noqa: E731
    E.t('assemble.py',d7,'--bootstrap',16,'--output',td/'r7.json');r7=json.loads((td/'r7.json').read_text())   # the recomputed result, written apart
    assert canon(strip(r7))==canon(strip(json.loads(pub7)))   # every assembled value unchanged: equal fields alone would have superseded
    assert {g for g in r7['science_sha256']if r7['science_sha256'][g]!=json.loads(pub7)['science_sha256'][g]}=={j['group']}
    assert new_r['science_sha256']==old_r['science_sha256']and set(new_r['science_sha256'])==set(new_r['merged_sha256'])   # the timing-only recovery above kept them
    must(E.t('verify_result.py',d7,check=False),1,'does not belong to this campaign')   # the published result no longer binds to the re-merged campaign
    # real conflicts: a committed group's table changed; a stale uncommitted scientific table; a committed table at publish time; a result whose science differs
    other=next(x['name']for x in m['groups']if x['name']!=j['group']and config(d,x['name'])['tasks']);og=d/'groups'/other;c0=(og/'graph_costs.csv').read_bytes()
    (og/'graph_costs.csv').unlink();(og/'graph_costs.csv').write_bytes(c0+b'0,0,0.0,0\n')
    must(E.t('production.py','merge',d,'--scratch',E.scr,check=False),1,'Checksum mismatch','graph_costs.csv')
    (og/'graph_costs.csv').unlink();(og/'graph_costs.csv').write_bytes(c0);rep0=(og/'graph_replicates.csv').read_bytes();m0=(og/'merged.json').read_bytes()
    (og/'merged.json').unlink();(og/'graph_replicates.csv').unlink();(og/'graph_replicates.csv').write_bytes(rep0.replace(b',',b', ',1))
    r=E.merge(d,'--group',other)
    assert f'{other}: replaced the uncommitted graph_replicates.csv'in r.stdout and 'SCIENTIFIC TABLE CHANGED'in r.stdout,r.stdout[-600:]
    assert (og/'graph_replicates.csv').read_bytes()==rep0 and (og/'merged.json').read_bytes()==m0
    pc=td/'pc';pc.mkdir();src=td/'src.csv';src.write_bytes(b'x\n');(pc/'t.csv').write_bytes(b'y\n');(pc/'merged.json').write_text('{}')
    try:prod._publish_copy(src,pc/'t.csv','grp',True);raise AssertionError('a committed table was replaced')
    except ValueError as e:assert 'Checksum mismatch'in str(e)and (pc/'t.csv').read_bytes()==b'y\n',str(e)
    assert prod._publish_copy(src,pc/'u.csv')=='published'and prod._publish_copy(src,pc/'u.csv')=='identical'
    (pc/'merged.json').unlink();assert prod._publish_copy(src,pc/'t.csv','grp',True)=='replaced'and (pc/'t.csv').read_bytes()==b'x\n'
    assert sorted(x.name for x in pc.iterdir())==['t.csv','u.csv']   # no temporary file left
    bad=json.loads(res.read_text());bad['test_partial']['C8_full']+=1.;res.unlink();res.write_text(json.dumps(bad,indent=2)+'\n')
    must(E.t('assemble.py',d,'--bootstrap',16,check=False),1,'exists and differs from the recomputed result')
    # function level: a combine.py result (combined_from[i].merged_sha256, under partial_values) and a pilot_subset summary
    sc=lambda h:{'graph_replicates.csv':h*64,'graph_tails.csv':'b'*64,'graph_promotions.csv':'c'*64,'graph_prefixes.csv':None,'merged_science':'e'*64}  # noqa: E731
    f=td/'C8_partial.json';r0={'label':'partial','final':False,'partial_values':{'C8_full':1.5,'combined_from':[
        {'run':'/r/b1','merged_sha256':{'a_free_L3':'1'*64},'science_sha256':{'a_free_L3':sc('1')}},{'run':'/r/b2','merged_sha256':{'a_free_L3':'2'*64},'science_sha256':{'a_free_L3':sc('2')}}]}}
    assert asm.publish_result(f,r0)=='written'and asm.publish_result(f,r0)=='identical result already present; kept'
    old=f.read_bytes();r1=json.loads(json.dumps(r0));r1['partial_values']['combined_from'][1]['merged_sha256']['a_free_L3']='3'*64
    s=asm.publish_result(f,r1);assert s.startswith('superseded')and 'combined_from[1]:a_free_L3'in s and json.loads(f.read_text())==r1,s
    assert (td/f'C8_partial.superseded.{hashlib.sha256(old).hexdigest()[:12]}.json').read_bytes()==old
    for change in (lambda x:x['partial_values'].update(C8_full=1.6),lambda x:x['partial_values']['combined_from'][0].update(run='/r/b3'),
                   # S3-R2-007: a batch's scientific identity changed (graph_tails.csv) with or without its merged_sha256, or missing
                   lambda x:x['partial_values']['combined_from'][1]['science_sha256']['a_free_L3'].update({'graph_tails.csv':'f'*64}),
                   lambda x:(x['partial_values']['combined_from'][1]['merged_sha256'].update(a_free_L3='4'*64),
                             x['partial_values']['combined_from'][1]['science_sha256']['a_free_L3'].update(merged_science='0'*64))):
        r2=json.loads(json.dumps(r1));change(r2)
        try:asm.publish_result(f,r2);raise AssertionError('a result whose science changed was superseded')
        except ValueError as e:assert 'exists and differs'in str(e)and json.loads(f.read_text())==r1,str(e)
    f0=td/'C8_partial_noscience.json';n0=json.loads(json.dumps(r0));[x.pop('science_sha256')for x in n0['partial_values']['combined_from']];asm.publish_result(f0,n0)
    n1=json.loads(json.dumps(n0));n1['partial_values']['combined_from'][1]['merged_sha256']['a_free_L3']='3'*64
    try:asm.publish_result(f0,n1);raise AssertionError('a merged_sha256 change without a recorded scientific identity was superseded')
    except ValueError as e:assert 'no scientific identity is recorded'in str(e)and json.loads(f0.read_text())==n0,str(e)
    sd=td/'subset_summary.json';doc={'schema':'c8-d3-subset-1','graphs':3,'merged_sha256':{'a_free_L8':{'merged.json':'a','graph_costs.csv':'b','graph_replicates.csv':'c'}}}
    assert pr.publish_summary(sd,doc)=='written'and pr.publish_summary(sd,doc)=='identical summary kept'
    old=sd.read_bytes();d1=json.loads(json.dumps(doc));d1['merged_sha256']['a_free_L8'].update({'merged.json':'A','graph_costs.csv':'B'})
    assert pr.publish_summary(sd,d1).startswith('superseded')and (td/f'subset_summary.superseded.{hashlib.sha256(old).hexdigest()[:12]}.json').read_bytes()==old
    for change in (lambda x:x['merged_sha256']['a_free_L8'].update({'graph_replicates.csv':'C'}),lambda x:x.update(graphs=4)):
        d2=json.loads(json.dumps(d1));change(d2)
        try:pr.publish_summary(sd,d2);raise AssertionError('a summary whose science changed was superseded')
        except ValueError as e:assert 'exists and differs'in str(e)and json.loads(sd.read_text())==d1,str(e)
    ok('F8-d3 (A-ORC-4 (i), J-DRL-8 unattended on the fake Slurm): after a recovered completed index (one checkpoint and its group\'s merged.json '
       'deleted, the index recomputed with other timings by the lane of the next `lanes 1`), the merge job replaces the uncommitted graph_costs.csv '
       '(timing only, reported), keeps the scientific tables byte for byte and the batches, and supersedes the result whose only change is that '
       'group\'s merged_sha256 (old bytes kept as C8_test_result.superseded.<sha12>.json; verify_result passes); a rerun changes nothing; a '
       'committed table that changed stops the merge (Checksum mismatch), a stale uncommitted scientific table is replaced and reported '
       '(SCIENTIFIC TABLE CHANGED), a committed table is never replaced at publish time, a result whose science differs is refused; S3-R2-007: a '
       'recovered checkpoint with another tail_sum re-merges into another graph_tails.csv with every assembled value unchanged, and assemble '
       'refuses it naming the group and the table (science_sha256); combine\'s per-batch merged_sha256 supersedes only with equal recorded '
       'scientific identities, and the pilot_subset summary\'s timing digests likewise, every other change is refused',
       index=idx,group=j['group'],superseded=keep.name)

def test_arrays_and_recovery(E,td:Path):
    import production as prod
    # a small campaign (12 indices): an array's planned tasks count in the shared share until every task is terminal (HD17 "Slots")
    import hashlib
    from unit_orchestration import selection
    inv=json.loads((E.pkg/'inputs/inventory.json').read_text());im=hashlib.sha256((E.pkg/'inputs/manifest.json').read_bytes()).hexdigest()
    f=td/'sel_arr.json';f.write_text(json.dumps(selection(inv,im,{'free:3':[{'id':0,'points':4096}],'power:8':[{'id':g,'points':4096}for g in range(4)]},role='other')))
    site=c8pkg.SlurmSite(td,'arr');d=site.run_dir('A1')
    E.plan(d,'--pilot','--graphs',f,'--test-only','--replicates',2,'--threads',2,'--cost-model',E.model(),'--shards',4,seed=SEED+51)
    m=manifest(d);sug=m['estimates']['mem_suggestion_mb']
    must(site.submit(E.pkg,'submit',C8_RUN=d,C8_SBATCH_ARGS='-A yun124 -p shared --mem=1G'),64,'below the plan')
    must(site.submit(E.pkg,'submit',C8_RUN=d,C8_SBATCH_ARGS=f'-A yun124 -p shared --mem={sug+1024}M'),0);sb=[h['argv']for h in site.history()if '--test-only'not in h['argv']]
    arr=[a for a in sb if any(x.startswith('--array=')for x in a)];assert len(arr)==1 and f'--array=0-{len(m["jobs"])-1}%8'in arr[0]and f'--mem={sug+1024}M'in arr[0],arr   # a larger value accepted (A-ORC-5)
    assert any(x.startswith('--time=')for x in arr[0])and any(x.startswith('--dependency=afterok:')for x in sb[-1])
    # resubmit: complete some indices, keep one element live, the rest missing
    jobs=site.jobs();el=[j for j in jobs if j['task']is not None]
    for j in m['jobs'][:5]:E.t('production.py','run',d,'--index',j['id'],'--threads',2,'--scratch',E.scr)
    for x in el:
        if x['task']!=7:site.fake.finish(x['id'],'FAILED' if x['task']>=5 else 'COMPLETED',elapsed=5)
    for x in site.jobs():
        if x['name'].startswith('c8d3-merge-')and x['state']=='PENDING':site.fake.finish(x['id'],'CANCELLED')
    cp=must(site.submit(E.pkg,'resubmit',C8_RUN=d),0,'missing indices 7 are still live')
    last=[h['argv']for h in site.history()if '--test-only'not in h['argv']];rs=[a for a in last if any(x.startswith('--array=')for x in a)][-1]
    want=prod.ranges([i for i in range(5,len(m['jobs']))if i!=7]);assert f'--array={want}%8'in rs,rs
    mg=last[-1];dep=next(x for x in mg if x.startswith('--dependency=afterok:'));assert next(x['id']for x in site.jobs()if x['task']==7)in dep
    # window OFF:RANGE: one array, no merge; status prints the window lines
    creating=lambda:[h for h in site.history()if '--test-only'not in h['argv']]
    n0=len(creating());must(site.submit(E.pkg,'window','0:2-3',C8_RUN=d),0);new=creating()[n0:]
    assert len(new)==1 and '--array=2-3%8'in new[0]['argv']and not any(x.startswith('--dependency')for x in new[0]['argv'])
    st=E.t('production.py','status',d,'--fast',check=False);assert st.returncode==1 and 'slurm_submit.py'in st.stdout and 'window 0:'in st.stdout
    # recovery_plan: uncertain states (69), live merges (65) and live lanes (65)
    c=prod.campaign_c(d);p_=prod.campaign_p(d)
    q=lambda role,state,t='N/A':f'123|{t}|{state}|c8d3-{role}-{c}-aaaaaaaaaaaa|c8d3:{c}:{p_}:aaaaaaaaaaaa\n'
    assert prod.recovery_plan(d,q('merge','COMPLETING'))['refuse']['code']==69
    assert prod.recovery_plan(d,q('merge','PENDING'))['refuse']['code']==65 and prod.recovery_plan(d,q('lane','RUNNING'))['refuse']['code']==65
    bad=f'123|N/A|RUNNING|c8d3-lane-{c}-aaaaaaaaaaaa|c8d3:{c}:{"f"*12}:aaaaaaaaaaaa\n';assert prod.recovery_plan(d,bad)['refuse']['code']==69
    # symmetry (A1 repair round 2): array mode puts its windows or its merge on Intel defq/debugq (AVX-512, like cn112)
    # only for a plan of role campaign; a validation plan under `c8_profile intel` is refused (64) before the session
    # lock and any query, nothing submitted. On the Mac the session lock then stops every admissible call (69: no
    # BeeGFS mount here), which shows the vendor rule let it through.
    v=site.run_dir('V1')
    E.plan(v,'--pilot','--test-only','--points',512,'--replicates',2,'--threads',2,'--plan-role','validation','--bootstrap-chunk',512,'--shards',2,seed=SEED+52)
    assert manifest(v)['plan_role']=='validation'
    SYM=dict(C8_SITE='symmetry',USER='zzheng1',C8_RESERVATION='mode=reservation;id=H7;amd_nodes=4;amd_total=8',
             C8_OTHER_SITE_SU=f'dev=0;pilot=0;asof={time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())};ref=lanes_tests (fake)')
    AMD_MERGE='-p amdq -c 64 --mem=240G -t 02:00:00';INTEL_MERGE='-p defq -c 40 --mem=180G -t 02:00:00'
    n0=len(site.history());sq0=len(site.history('squeue'))
    for mode,extra in (('submit',()),('window',('0:0-1',)),('resubmit',())):
        must(site.submit(E.pkg,mode,*extra,C8_RUN=v,C8_SBATCH_ARGS='-p defq --mem=64G -t 01:00:00',C8_MERGE_SBATCH_ARGS=INTEL_MERGE,**SYM),64,
             'refused for a plan of role \'validation\'','AVX-512','C8_SBATCH_ARGS')
    must(site.submit(E.pkg,'submit',C8_RUN=v,C8_SBATCH_ARGS='-p debugq --mem=64G -t 00:59:00',C8_MERGE_SBATCH_ARGS=AMD_MERGE,**SYM),64,'debugq (C8_SBATCH_ARGS)')
    must(site.submit(E.pkg,'submit',C8_RUN=v,C8_SBATCH_ARGS='-p amdq --mem=64G -t 01:00:00',C8_MERGE_SBATCH_ARGS=INTEL_MERGE,**SYM),64,'defq (C8_MERGE_SBATCH_ARGS)')
    assert len(site.history())==n0 and len(site.history('squeue'))==sq0   # refused before the lock: no query, no sbatch
    for run,args in ((v,'-p amdq --mem=64G -t 01:00:00'),(d,f'-p defq --mem={sug+1024}M -t 01:00:00')):   # admissible: the vendor rule passes
        cp=site.submit(E.pkg,'submit',C8_RUN=run,C8_SBATCH_ARGS=args,C8_MERGE_SBATCH_ARGS=AMD_MERGE if run==v else INTEL_MERGE,**SYM)
        assert cp.returncode==69 and 'AVX-512'not in cp.stderr and 'mount'in cp.stderr,(run,cp.returncode,cp.stderr[-600:])
    ok('array mode: submit uses windows throttled %8 with the plan\'s memory suggestion (a smaller --mem refused, 64; a larger one accepted) and time, and an afterok '
       'merge; resubmit sends the missing indices that are not live and a merge afterok on them and on the live element; window submits one '
       'array; status prints the slurm_submit.py window lines; recovery refuses uncertain states (69), live merges and lanes (65) and a job of '
       'another plan (69); on symmetry a validation plan\'s windows or merge on Intel defq/debugq are refused (64) before the lock in submit, '
       'window and resubmit, while amdq and a campaign plan on defq pass the rule')

# =====================================================================================================================
# Stage 6, group A (S2-001, S2-002, S2-005, F7)
def test_vendor_pin(E,td:Path):
    """S2-001: a campaign's first work admission pins its CPU vendor in RUN/cpu_vendor.json (exclusively, under the
    session lock, before its first sbatch; a dry run pins nothing); every later admission of the campaign is checked
    against it and refused (64, nothing submitted) on another vendor: lanes N, lanes 0 (a dry run included), submit,
    window and a resubmit that brings no new window (its merge alone). The merge refuses checkpoints of mixed CPU vendors
    (the runtime fingerprint's cpu_model every checkpoint records), parallel and serial, before anything is published."""
    import hashlib,slurm_submit as ss
    site=c8pkg.SlurmSite(td,'vend');d=campaign(E,site,'V1',SEED+61);pin=d/'cpu_vendor.json'
    must(site.submit(E.pkg,'lanes','1','--dry-run',C8_RUN=d),0,'dry run');assert not pin.exists()
    must(site.submit(E.pkg,'lanes','1',C8_RUN=d),0,'campaign CPU vendor pinned: amd');doc=json.loads(pin.read_text())
    assert (doc['schema'],doc['vendor'],doc['site'],doc['first_admission']['command'])==('c8-d3-cpu-vendor-1','amd','expanse','lanes 1'),doc
    assert doc['manifest_sha256']==hashlib.sha256((d/'manifest.json').read_bytes()).hexdigest()and doc['campaign_c']==ss.ledger.dir_sha12(d)
    must(site.submit(E.pkg,'lanes','0',C8_RUN=d),0);assert json.loads(pin.read_text())==doc   # a later admission of the same vendor reads it
    pin.write_text(json.dumps({**doc,'vendor':'intel'},indent=1)+'\n')                       # the pin of another vendor
    for args in (('lanes','1'),('lanes','0'),('lanes','1','--dry-run')):
        n0=len(site.history());must(site.submit(E.pkg,*args,C8_RUN=d),64,'pinned to CPU vendor intel','S2-001','nothing submitted');assert len(site.history())==n0,args
    # array mode: `submit` pins; with every index complete a `resubmit` brings only its merge, which is checked too
    d2=campaign(E,site,'V2',SEED+62,ih=1);pin2=d2/'cpu_vendor.json'
    must(site.submit(E.pkg,'submit',C8_RUN=d2),0,'campaign CPU vendor pinned: amd');assert json.loads(pin2.read_text())['first_admission']['command']=='submit'
    for j in site.jobs():
        if j['state']in('RUNNING','PENDING'):site.fake.finish(j['id'],'COMPLETED',elapsed=5)
    E.run_all(d2)
    must(site.submit(E.pkg,'resubmit',C8_RUN=d2),0,'no work to resubmit')
    for j in site.jobs():
        if j['state']in('RUNNING','PENDING'):site.fake.finish(j['id'],'COMPLETED',elapsed=5)
    pin2.write_text(json.dumps({**json.loads(pin2.read_text()),'vendor':'intel'},indent=1)+'\n')
    for args in (('resubmit',),('window','0:0-0'),('submit',)):
        n0=len(site.history());must(site.submit(E.pkg,*args,C8_RUN=d2),64,'pinned to CPU vendor intel');assert len(site.history())==n0,args
    pin2.write_text('{"schema": "c8-d3-cpu-vendor-1", "vendor": "arm"}\n');must(site.submit(E.pkg,'resubmit',C8_RUN=d2),69,'cpu_vendor.json')
    # the merge: every checkpoint records the CPU it ran on; one of another vendor refuses the merge, parallel and serial
    m=manifest(d2);cks=sorted((d2/'groups').glob('*/checkpoints/*.json'));assert cks and all(json.loads(c.read_text())['runtime']['fingerprint']['cpu_model']for c in cks)
    def set_cpu(f,model):doc=json.loads(f.read_text());doc['runtime']['fingerprint']['cpu_model']=model;f.write_text(json.dumps(doc,indent=2)+'\n')
    for f in cks:set_cpu(f,'AMD EPYC 7543 32-Core Processor')
    odd=cks[len(cks)//2];set_cpu(odd,'Intel(R) Xeon(R) Gold 6148 CPU @ 2.40GHz');grp=odd.parent.parent.name
    cp=E.merge(d2,'--jobs',2,check=False);assert cp.returncode==1 and 'several vendors (amd, intel)'in cp.stderr and 'S2-001'in cp.stderr,(cp.returncode,cp.stderr[-600:])
    assert not list((d2/'groups').glob('*/merged.json'))   # the parallel merge publishes nothing
    cp=E.merge(d2,'--serial',check=False);assert cp.returncode==1 and 'several vendors (amd, intel)'in cp.stderr,(cp.returncode,cp.stderr[-600:])
    assert not list((d2/'groups').glob('*/merged.json'))   # nor the serial one (all groups checked first)
    set_cpu(odd,'AMD EPYC 7532 32-Core Processor');E.merge(d2,'--jobs',2);assert len(list((d2/'groups').glob('*/merged.json')))==len(m['groups'])   # one vendor, two models: merged
    ok('S2-001: the first work admission pins the CPU vendor (cpu_vendor.json; a dry run pins nothing); lanes N, lanes 0 and their dry run, submit, window '
       'and a resubmit that brings only its merge are refused (64, nothing submitted) against a pin of another vendor, an unreadable pin 69; the merge '
       'refuses checkpoints of mixed vendors (parallel and serial, nothing published) and merges one vendor\'s')

def plan_sh(E,site,run,seed,args,jid,log,popen=False,**x):
    """slurm/plan.sh of the scratch package as a plan job runs it: SLURM_JOB_ID, a c8d3-plan- name, SLURM_TMPDIR, C8_SEEDS."""
    import hashlib,secrets
    tmp=E.td/f'planjob_{jid}';tmp.mkdir(exist_ok=True)
    name=f'c8d3-plan-{hashlib.sha256(str(Path(os.path.realpath(run))).encode()).hexdigest()[:12]}-{secrets.token_hex(6)}'
    env=c8pkg.env(**site.env(C8_SEEDS=log,C8_PACKAGE=E.pkg,C8_PYTHON=sys.executable,SLURM_JOB_ID=jid,SLURM_JOB_NAME=name,SLURM_TMPDIR=tmp,**x))
    argv=['bash',str(E.pkg/'slurm/plan.sh'),str(run),'--seed',str(seed),*map(str,args)]
    return subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)if popen else subprocess.run(argv,capture_output=True,text=True,env=env)

def test_seed_reservations(E,td:Path):
    """S2-002 (HD6): a plan reserves its seed itself, rechecked under the seed log's lock and keyed by the campaign
    directory, before anything is built or published (slurm/plan.sh passes $C8_SEEDS; tools/sweep.py --reserve-seed).
    Two concurrent plans of one seed (both past their first check) publish one campaign: the other is refused (65); an
    interrupted plan keeps its reservation, its retry is idempotent (one entry) and another directory is refused; a
    sweep's seed is in the log before anything runs; test-only twins that check no seed share theirs (registered)."""
    site=c8pkg.SlurmSite(td,'seeds');log=td/'seeds.json';E.t('seeds.py','init','--log',log,'--from',E.pkg/'designs/forbidden_seeds.json')
    M=E.model();nt=['--pilot','--replicates',2,'--threads',2,'--cost-model',M,'--forbid-seeds-from',log]
    def entries(seed):return [e['source']for e in json.loads(log.read_text())['seeds']if e['seed']==seed]
    R=lambda p:str(Path(p).resolve())   # the campaign's identity: its resolved directory
    # the race: both plans pass their first seed check and sit in their self-test before either reserves
    S=SEED+71;flog=td/'race_selftest.log';ra,rb=site.run_dir('race_a'),site.run_dir('race_b')
    ps=[plan_sh(E,site,r,S,nt,jid,log,popen=True,C8_FAKE_LOG=flog,C8_FAKE_SLEEP='4')for r,jid in ((ra,'7101'),(rb,'7102'))]
    try:reached=wait_for(lambda:flog.exists()and len(flog.read_text().splitlines())>=2,120)
    finally:outs=[p.communicate(timeout=600)for p in ps]
    # the plans' own stderr in the message: a refusal before the self-test (on a real site, "this host is ... but
    # C8_SITE is 'fake'", which val1 classes SITE_REFUSED) must not hide behind the timeout
    assert reached,('both plans never reached their self-test',[p.returncode for p in ps],[o[1][-1500:]for o in outs])
    rcs=[p.returncode for p in ps];won=[r for r,c in zip((ra,rb),rcs)if c==0]
    assert sorted(rcs)==[0,65]and len(won)==1 and entries(S)==[R(won[0])],(rcs,entries(S),[o[1][-600:]for o in outs])
    lost=(rb if won[0]==ra else ra);err=outs[(ra,rb).index(lost)][1]
    assert 'is held in'in err and not lost.exists()and (won[0]/'manifest.json').exists(),err[-600:]
    # an interrupted plan keeps its reservation; its retry is idempotent; another directory with the seed is refused
    S2=SEED+72;ri=site.run_dir('interrupted')
    cp=plan_sh(E,site,ri,S2,nt,'7103',log,C8_TEST_IO_FAULT='plan_rename');assert cp.returncode==74 and not ri.exists(),(cp.returncode,cp.stderr[-600:])
    assert entries(S2)==[R(ri)],entries(S2)
    cp=plan_sh(E,site,ri,S2,nt,'7104',log);assert cp.returncode==0 and 'present for'in cp.stderr and entries(S2)==[R(ri)],(cp.returncode,cp.stderr[-600:])
    cp=plan_sh(E,site,site.run_dir('other'),S2,nt,'7105',log);assert cp.returncode in(1,65)and not site.run_dir('other').exists()and entries(S2)==[R(ri)],(cp.returncode,cp.stderr[-400:])
    # test-only twins that check no seed: both registered, both published (A-SMK-1's twins)
    S3=SEED+73;tw=['--pilot','--test-graphs',1,'--replicates',2,'--threads',2,'--cost-model',M]
    for name,jid in (('twin_a','7106'),('twin_b','7107')):cp=plan_sh(E,site,site.run_dir(name),S3,tw,jid,log);assert cp.returncode==0,(name,cp.stderr[-600:])
    assert entries(S3)==[R(site.run_dir('twin_a')),R(site.run_dir('twin_b'))],entries(S3)
    # a sweep: its plan reserves the seed before any index runs (--plan-only stops right after the plan)
    S4=SEED+74;rs=site.run_dir('sweep')
    cp=E.t('sweep.py',rs,'--seed',S4,'--plan-only','--threads',2,'--forbid-seeds-from',log,'--reserve-seed',log,'--scratch',E.scr,check=False,**site.env())
    assert cp.returncode==0 and entries(S4)==[R(rs)],(cp.returncode,cp.stderr[-600:],entries(S4))
    ok('S2-002: concurrent plans of one seed publish one campaign (the other refused 65 at the reservation); an interrupted plan keeps its '
       'reservation, its retry is idempotent and another directory is refused; test-only twins share theirs; a sweep reserves before it runs')

def test_reserve_required(E,td:Path):
    """S2-002, follow-up: a plan that checks its seed (--forbid-seeds-from) must reserve it in that same log. A non-test
    plan, or a sweep's test-only plan, without --reserve-seed, or with --reserve-seed naming another log, is refused (65)
    before anything is created, every log unchanged; with it the plan reserves and publishes; tools/sweep.py refuses the
    same (65). tests/argmax_run.py's plan carries --reserve-seed $C8_SEEDS (the log it checks) and no `seeds.py add`
    follows it. Test-only plans that check no seed (the J-SMK-1 twins, prefix_check.py --real) neither check nor reserve:
    two of one seed both publish and the log is untouched."""
    import argparse
    site=c8pkg.SlurmSite(td,'rr');log=td/'seeds.json';E.t('seeds.py','init','--log',log,'--from',E.pkg/'designs/forbidden_seeds.json')
    other=td/'other.json';shutil.copy2(log,other);before=log.read_bytes();M=E.model();nt=['--pilot','--replicates',2,'--threads',2,'--cost-model',M]
    plan=lambda d,seed,*x:E.t('production.py','plan',d,'--seed',seed,*nt,*x,'--scratch',E.scr,check=False,**site.env(SLURM_JOB_ID='9999'))
    for name,x in (('none',['--forbid-seeds-from',log]),('other_log',['--forbid-seeds-from',log,'--reserve-seed',other]),
                   ('test_only',['--test-graphs',1,'--forbid-seeds-from',log])):
        d=site.run_dir(f'rr_{name}');must(plan(d,SEED+101,*x),65,'S2-002','nothing was planned')
        assert not d.exists()and log.read_bytes()==before==other.read_bytes(),name
    d=site.run_dir('rr_ok');must(plan(d,SEED+101,'--forbid-seeds-from',log,'--reserve-seed',log),0,'reserved for');assert (d/'manifest.json').exists()
    assert [e['source']for e in json.loads(log.read_text())['seeds']if e['seed']==SEED+101]==[str(d.resolve())]
    rs=site.run_dir('rr_sweep')
    must(E.t('sweep.py',rs,'--seed',SEED+102,'--plan-only','--threads',2,'--forbid-seeds-from',log,'--scratch',E.scr,check=False,**site.env()),65,'S2-002');assert not rs.exists()
    # test-only twins that check no seed: one seed, both published, nothing reserved
    for name in ('tw_a','tw_b'):
        must(E.t('production.py','plan',site.run_dir(name),'--seed',SEED+103,'--pilot','--test-graphs',1,'--replicates',2,'--threads',2,'--cost-model',M,
                 '--scratch',E.scr,check=False,SLURM_JOB_ID='9999'),0)
    assert not [e for e in json.loads(log.read_text())['seeds']if e['seed']==SEED+103]
    # argmax_run: the plan names --reserve-seed $C8_SEEDS, the log it checks; the next tool is not a registration
    import argmax_run as ar
    calls=[]
    class Stop(Exception):pass
    def spy(script,*args,check=True,env=None):
        calls.append((script,[str(x)for x in args]))
        if script!='production.py':raise Stop()
        return subprocess.CompletedProcess([],0,'','')
    real=ar.tool;ar.tool=spy
    try:
        try:ar.campaign(argparse.Namespace(seed=SEED+104,replicates=2,cost_model=M,threads=2,scratch=str(E.scr),points=4096),td/'am',[228],'0'*64,td,str(log))
        except Stop:pass
    finally:ar.tool=real
    assert len(calls)==2 and calls[0][0]=='production.py'and calls[0][1][0]=='plan'and '--reserve-seed'in calls[0][1],calls
    a0=calls[0][1];assert a0[a0.index('--forbid-seeds-from')+1]==a0[a0.index('--reserve-seed')+1]==str(log),a0
    assert calls[1][0]!='seeds.py',calls[1]   # the plan's reservation is the registration (before anything is built)
    ok('S2-002 follow-up: a plan that checks its seed without reserving it in the same log is refused (65, nothing created, logs unchanged): '
       'non-test, a test-only sweep plan, another reserve log; sweep.py refuses the same; with the reservation it publishes; argmax_run\'s plan '
       'reserves in $C8_SEEDS and no seeds.py add follows; test-only twins that check no seed publish with one seed, nothing reserved')

def test_plan_staging(E,td:Path):
    """S2-005: a plan's staging copy beside the target is its own (host, pid, SLURM_JOB_ID); another attempt's is never
    removed, only listed; the publication is a rename that fails when the target exists, an empty directory included,
    removing only its own staging copy (common.rename_noreplace; its recheck_rename fallback refuses alike)."""
    import common
    M=E.model();args=['--pilot','--test-only','--replicates',2,'--threads',2,'--cost-model',M]
    out=td/'st1';foreign=td/'st1.tmp.otherhost.4242.99999';(foreign/'groups').mkdir(parents=True);(foreign/'groups/x').write_text('live\n')
    cp=E.plan(out,*args,seed=SEED+81);assert (out/'manifest.json').exists()and (foreign/'groups/x').read_text()=='live\n'
    assert foreign.name in cp.stderr and 'left in place'in cp.stderr and [p.name for p in td.iterdir()if p.name.startswith('st1.tmp.')]==[foreign.name],cp.stderr[-600:]
    # the target appears while the plan runs (another attempt; an empty directory, which a plain rename would replace)
    out2=td/'st2';flog=td/'st2_selftest.log'
    p=subprocess.Popen([sys.executable,'-B',str(E.pkg/'tools/production.py'),'plan',str(out2),'--seed',str(SEED+82),*map(str,args),'--scratch',str(E.scr)],
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=c8pkg.env(C8_FAKE_LOG=flog,C8_FAKE_SLEEP='3',SLURM_JOB_ID='9998'))
    try:assert wait_for(flog.exists,120),'the plan never reached its self-test'
    finally:
        out2.mkdir();so,se=p.communicate(timeout=600)
    assert p.returncode==1 and 'created by another attempt'in se and out2.is_dir()and not list(out2.iterdir()),(p.returncode,se[-600:])
    assert not [x.name for x in td.iterdir()if x.name.startswith('st2.tmp.')],list(td.iterdir())
    for fn in (common.rename_noreplace,common.recheck_rename):
        a,b=td/f'rn_a_{fn.__name__}',td/f'rn_b_{fn.__name__}';a.mkdir();(a/'f').write_text('1');b.mkdir()
        try:fn(a,b);raise AssertionError(f'{fn.__name__} replaced an existing empty directory')
        except FileExistsError:pass
        assert (a/'f').exists()and not list(b.iterdir());b.rmdir();fn(a,b);assert (b/'f').read_text()=='1'and not a.exists()
    ok('S2-005: another attempt\'s staging copy survives a plan (listed, not removed); a target created during the plan refuses the publication '
       '(nothing replaced, the own staging copy removed); rename_noreplace and its recheck_rename fallback never replace an existing directory')

def stop_deadline_unit()->dict:
    """S2-R2-005 at function level: StopGuard.drain on three real children that ignore SIGTERM and whose death after the
    kill is delayed 1.5 s (a lane held in I/O after SIGKILL; the kill is a timer). The drain starts 0.5 s after the
    signal with a 2 s deadline: it returns by 2 s after the SIGNAL (one absolute deadline across grace and reaping),
    every survivor is killed within 0.2 s of the others and before the deadline (all signalled before any is waited on),
    and none is reaped yet when it returns (the deadline is not extended for a slow reap)."""
    import lanes,threading
    kids=[subprocess.Popen(['/bin/sh','-c','trap "" TERM; echo ready; exec sleep 60'],stdout=subprocess.PIPE,text=True)for _ in range(3)];timers=[]
    try:
        assert all(k.stdout.readline().strip()=='ready'for k in kids)
        g=lanes.StopGuard();asked={}
        for k in kids:g.add(k)
        def late_kill(c):asked[c.pid]=time.monotonic();x=threading.Timer(1.5,c.kill);timers.append(x);x.start()
        g._handler(signal.SIGTERM,None);t_sig=time.monotonic()   # the stop signal: recorded and forwarded (ignored by the children)
        time.sleep(0.5);killed=g.drain(2.0,late_kill);took=time.monotonic()-t_sig
        assert took<=2.25,('drain waited past its deadline (2 s after the signal)',round(took,2),{p:round(a-t_sig,2)for p,a in asked.items()})
        spread=max(asked.values())-min(asked.values())
        assert len(killed)==3 and set(asked)=={k.pid for k in kids}and spread<0.2 and max(asked.values())-t_sig<2.0,('not every survivor signalled before reaping',spread)
        assert all(k.poll()is None for k in kids),'a child was reaped although its death was delayed past the deadline'
    finally:
        for x in timers:x.cancel()
        for k in kids:
            try:k.kill()
            except OSError:pass
            k.wait()
    return {'took':round(took,3),'kill_spread':round(spread,4)}

def test_lane_sigterm(E,td:Path):
    """F7 (A-ORC-8a cleanup, ported from C62d) and S2-R2-005 (one shutdown deadline): first stop_deadline_unit; then SIGTERM
    to the lane worker alone, as slurmstepd delivers a scancel to the batch process, while two lanes run native tasks,
    and every case must end within the configured C8_LANE_STOP_SECONDS (the worker's whole shutdown, cleanup included;
    no larger allowance). forwarded (the default 25 s): the worker forwards it to its lanes and each lane to its
    `production.py run`, which stops its native worker and removes its runtime; the lanes remove their scratch and the
    worker exits 143. stuck_native (C8_LANE_STOP_SECONDS=4, a native worker that ignores SIGTERM): each lane kills its
    run's session at 0.95 x 0.7 x 4 s and still removes its scratch. stuck_lanes (4 s; both lanes frozen with SIGSTOP, so
    neither acts on the forwarded SIGTERM): the worker kills both lanes at once at 0.95 x 0.88 x 4 s and removes their
    scratch itself (their runs, orphaned, are left to Slurm's end-of-job kill: here the test kills them). In every case
    nothing of the job is left in the scratch, no process of the worker's session survives, the claims stay (stale) with
    no failure record, and a rerun of the same job id releases its own stale claims and completes the campaign."""
    import lanes
    unit=stop_deadline_unit()
    site=c8pkg.SlurmSite(td,'sig');out={}
    for case,extra,S in (('forwarded',{},lanes.STOP_SECONDS),('stuck_native',{'C8_FAKE_IGNORE_TERM':'1','C8_LANE_STOP_SECONDS':'4'},4.),
                         ('stuck_lanes',{'C8_LANE_STOP_SECONDS':'4'},4.)):
        d=campaign(E,site,f'S_{case}',SEED+91+len(out),ih=1);E.t('lanes.py','queue',d,**site.env())
        scr=td/f'lanesig_tmp_{case}';scr.mkdir();flog=td/f'lanesig_{case}.log';natives=[]
        env=c8pkg.env(SLURM_JOB_ID='6500',C8_LANE_SECONDS='36000',C8_LANES='2',SLURM_TMPDIR=scr,C8_FAKE_SLEEP='120',C8_FAKE_LOG=flog,**extra)
        proc=subprocess.Popen([sys.executable,'-B',str(E.pkg/'tools/lanes.py'),'worker',str(d)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env,start_new_session=True)
        try:
            assert wait_for(lambda:flog.exists()and len(flog.read_text().splitlines())>=2,120),(case,'two native tasks never started')
            natives=[json.loads(l)['pid']for l in flog.read_text().splitlines()];assert all(alive(x)for x in natives)
            assert len(list(scr.glob('c8d3_lane_6500_*/c8d3_runtime_*')))==2 and len(list((d/'lanes/claims').glob('*.json')))==2,(case,[x.name for x in scr.rglob('*')][:10])
            if case=='stuck_lanes':
                ps=subprocess.run(['ps','-eo','pid=,ppid='],capture_output=True,text=True).stdout.split()
                lane_pids=[int(a)for a,b in zip(ps[::2],ps[1::2])if int(b)==proc.pid];assert len(lane_pids)==2,lane_pids
                for x in lane_pids:os.kill(x,signal.SIGSTOP)
            t0=time.time();proc.send_signal(signal.SIGTERM);so,se=proc.communicate(timeout=120);took=time.time()-t0
        finally:   # whatever happened, nothing of this worker's session outlives the case (its lanes included)
            left=subprocess.run(['ps','-eo','pid=,pgid='],capture_output=True,text=True).stdout.split()
            stray=[int(a)for a,b in zip(left[::2],left[1::2])if int(b)==proc.pid and int(a)!=proc.pid]
            try:os.killpg(proc.pid,signal.SIGKILL)
            except OSError:pass
            if case=='stuck_lanes':   # the frozen lanes' runs (own sessions) and natives: Slurm kills them at the job's end
                for x in natives:
                    try:os.killpg(os.getpgid(x),signal.SIGKILL)
                    except OSError:pass
        assert proc.returncode==143 and took<S,(case,proc.returncode,round(took,2),S,so[-800:],se[-800:])
        assert not stray,(case,'processes of the worker session were still running',stray)
        assert wait_for(lambda:not any(alive(x)for x in natives),30),(case,'a native worker survived')
        assert not list(scr.iterdir()),(case,[x.name for x in scr.rglob('*')][:10])
        assert 'stopping on signal 15: SIGTERM forwarded to 2 lane(s)'in so,(case,so[-800:])
        assert len(list((d/'lanes/claims').glob('*.json')))==2 and not list((d/'lanes').glob('failures/*.json')),case
        logs=sorted((d/'lanes/logs').glob('idx*.6500.*.log'));assert len(logs)==2,logs
        if case=='forwarded':assert 'lane exit codes [143, 143]'in so and all('stopped by signal 15'in x.read_text()for x in logs),(so[-800:],[x.read_text()[-300:]for x in logs])
        elif case=='stuck_native':assert 'lane exit codes [143, 143]'in so and f'its session killed at {(1-lanes.REAP_FRACTION)*(lanes.LANE_STOP_FRACTION*4.):g} s'in so,so[-800:]
        else:assert 'lane exit codes [-9, -9]'in so and f'2 lane(s) killed at {(1-lanes.REAP_FRACTION)*((1-lanes.CLEANUP_FRACTION)*4.):g} s'in so and 'removed 2 lane scratch director(ies) left behind'in so,so[-800:]
        # the same job id again (a requeued job): its own stale claims are released and the campaign completes
        cp=E.t('lanes.py','worker',d,check=False,SLURM_JOB_ID='6500',C8_LANE_SECONDS='36000',C8_LANES='2',SLURM_TMPDIR=scr)
        assert cp.returncode==0 and cp.stdout.count('released own stale claim')==2,(case,cp.returncode,cp.stdout[-600:],cp.stderr[-600:])
        must(E.t('production.py','status',d,'--fast',check=False),0,'every checkpoint block is committed');assert not list(scr.iterdir())
        out[case]=round(took,2)
    ok('F7 and S2-R2-005: StopGuard.drain keeps one deadline from the signal, kills every survivor before reaping any and never waits past '
       'the deadline for a delayed reap; SIGTERM to the lane worker is forwarded to its lanes and their runs, and every case exits 143 within '
       'the configured C8_LANE_STOP_SECONDS (25 s; 4 s with a native ignoring SIGTERM, its run\'s session killed at 0.95 x 0.7 x 4 s; 4 s with '
       'both lanes frozen, killed together at 0.95 x 0.88 x 4 s and their scratch removed by the worker): scratch and runtimes removed, no '
       'process of the worker\'s session left, claims stale with no failure record; the same job id then completes the campaign',
       stop_seconds=out,drain=unit)
