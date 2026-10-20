#!/usr/bin/env python3
"""tools/thru_report.py (J-SMK-4's report: A-PERF-3, A-ORC-13 real Slurm, A-ORC-5) on fake lane campaigns. Mac; about two
minutes; C8_SITE=fake, the fake worker in a scratch package (tests/c8pkg.py), nothing in the package written.

Setup: a fake cost_sweep (tools/sweep.py) made into the measured model M by make_cost_model.py; role-campaign test plans
on M run by `lanes.py worker` with SLURM_JOB_ID=J and C8_LANES=2 (real idx logs and fingerprint lines), the worker's
stdout written to RUN/slurm_logs/lane-J.log; a synthetic accounting JSON (one work attempt of W seconds and alloc_cpus =
the lanes' cores, W chosen so that busy = 0.95); hook records (schema c8-d3-host-io-hook-1) synthesized from the idx logs with rchar = a constant + the own
bytes of the process computed here independently + the staged bytes once more (the reaped native child's reads, as Linux counts them: F13-d3).
  * PASS: busy equals the hand sum / (cores x W); OpenMP efficiency 1.0 (fake worker); throughput with a given
    reference equal to the drill's own value (ratio 1); speed against --sweep (ratio 1); one fingerprint_bytes value per
    key; orc5's ratios equal the hand computation; non_own equals the constant for every paired run (own_bytes = the
    process's own bytes + native_staged_reads; non_own_raw = the constant + the staged bytes, the Stage-5 model, which
    fails this check: F13-d3); the report minus made_utc is identical on two runs.
  * Stage 6 on J-SMK-4's committed records (benchmarks/symmetry_2026-10-c8/stage5_59d4922/smk4/thru_report.json and the 82
    hook records of smk4_hook/): --rederive re-reads every rchar from its hook record and reproduces the Stage-5 medians
    under the old model (30,049,197 and 1,389,313,912 bytes: FAIL), while the new model's agree (30,046,840 and
    31,734,238: PASS; F13-d3); the fits (rchar slope 2.001, non_own slope ~0); the OpenMP rule per block makes the
    Stage-5 PASS a SHORTFALL (blocks at 0.916, 0.929 and 0.936, all short few-task blocks; S4-007); the committed
    smk4/thru_report_s6b.json equals this re-derivation (up to its own time, host and paths) and fix round 1's
    thru_report_s6.json (kept) differs from it only in the OpenMP cause analysis (S4-R2-002); the record with one block
    untimed re-derives to INCOMPLETE beside passing blocks and keeps its SHORTFALL otherwise (S4-R2-001). A changed or
    missing hook record (65), RUN or another option beside --rederive (64) and an existing output (64) are refused.
  * FAIL, each with its number: W doubled (busy); twice the lanes' cores allocated (busy: the denominator is the node's
    allocated cores, PLAN; the lane widths only when the accounting has no alloc_cpus); without --sweep the speed and
    A-PERF-3 are INCOMPLETE, never PASS; C8_FAKE_OMP_EFF=0.9 (OpenMP: every block a SHORTFALL); one block's
    efficiency set to 0.9 in a copy (its payload digest renewed) while the time-weighted mean stays >= 0.95 (S4-007: the
    PLAN's rule is per block, so a SHORTFALL listing that block with its cause analysis; the Stage-5 rule on the mean
    passed it); one checkpoint's integration_seconds set to 0 beside blocks at 1.0 (OpenMP INCOMPLETE; S4-R2-001); a
    reference 1.1 x the drill
    (throughput); a drill at 1.2 x the sweep's seconds per point (speed); one idx log's fingerprint_bytes changed in a
    copy (fingerprint); a Python peak above 1.2 x est_peak_bytes (orc5); the small campaign's sizing; orc13's group
    comparison here is INCOMPLETE "not applicable" (tasks.sqlite sizes within 10x).
  * Pure functions: the OpenMP rule per block (omp_part: SHORTFALL with a mean >= 0.95, the cause analysis with the
    longest row's bound; PASS, INCOMPLETE; S4-R2-001: mixed timed and untimed blocks never PASS, a known SHORTFALL kept;
    S4-R2-002: causes established or possible, one thread, one lane, fewer tasks than threads) and SHORTFALL in the
    verdict combination; run_bytes (NATIVE_RULE's balance), the A-ORC-13 tolerance (1.9 MB agrees, 2.1 MB does not with
    small medians; the 10% branch with large ones; the raw model reported beside it, never the verdict), the time-weighted OpenMP statistics, the opt_speed and P4 re-expressions, J-SMK-4's sizing thresholds (128: 140,
    64: 72 busy core-h), the verdict combination, the allocated-core source and its refusals.
  * Refusals: a bootstrap-basis campaign, a one-byte change of cost_model.json, a changed checkpoint payload, a job
    without checkpoints, a missing lane log, --sweep of another campaign (65); two references, an existing --output,
    orc13 without --hook-dir, --job missing with two work jobs (64); hook records of another schema or campaign are
    counted as foreign and change nothing else.
Usage: python3 -B tests/thru_report_test.py [--keep]
"""
from __future__ import annotations
import argparse,hashlib,json,shutil,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import c8pkg  # noqa: E402
import lanes  # noqa: E402
import thru_report as TR  # noqa: E402
from common import Refuse,object_hash  # noqa: E402
RESULTS=[];SEED=771100231;J='4711';HOOK='c8-d3-host-io-hook-1';C=12_345_678
def ok(name,**info):RESULTS.append({'test':name,**info});print('PASS',name,flush=True)

def pure()->None:
    r=lambda g,x,y=None:{'group':g,'non_own':x,'non_own_wo_fp':x if y is None else y}
    sizes={'s':1000,'l':20000}
    for d,want in ((1_900_000,'PASS'),(2_100_000,'FAIL')):
        c=TR.compare_groups([r('s',10_000_000),r('l',10_000_000+d)],sizes);assert c['verdict']==want and c['size_ratio']==20,(d,c)
    assert TR.compare_groups([r('s',100_000_000),r('l',109_000_000)],sizes)['verdict']=='PASS'      # 10% of 109 MB = 10.9 MB > 9 MB
    assert TR.compare_groups([r('s',100_000_000),r('l',112_000_000)],sizes)['verdict']=='FAIL'      # 11.2 MB < 12 MB
    assert TR.compare_groups([r('s',5_000_000,5_000_000),r('l',5_000_000,7_100_000)],sizes)['verdict']=='FAIL'   # without fingerprint_bytes too
    c=TR.compare_groups([r('s',1),r('l',1)],{'s':1000,'l':10000});assert c['verdict']=='INCOMPLETE'and 'not applicable'in c['why']
    # S4-007: the PLAN's OpenMP rule is per block; a block below 0.95 is a SHORTFALL even when the time-weighted mean passes
    assert TR.verdict('PASS','SHORTFALL','INCOMPLETE')=='SHORTFALL'and TR.verdict('SHORTFALL','FAIL')=='FAIL'and TR.verdict('PASS',True)=='PASS'
    bl=[{'index':i,'group':'a_free_L8','block':f'b{i}','L':8,'tasks':256,'threads':8,'row_seconds':800.,'integration_seconds':100.}for i in range(9)]
    tiny={'index':9,'group':'a_power_L3','block':'s000000_p000000','L':3,'tasks':8,'threads':8,'row_seconds':0.04,'integration_seconds':0.04/(8*0.92),
          'max_row_seconds':0.0055,'graphs':[0],'points':32768,'host':'h1'}
    o=TR.omp_part(bl+[tiny],{'host':'h1','cores':64,'lane_cores':64,'widths':[8]*8})
    assert o['all']['time_weighted_mean']>=0.95 and o['verdict']=='SHORTFALL'and [x['index']for x in o['shortfall']['blocks']]==[9],o
    x=o['shortfall']['blocks'][0];assert abs(x['efficiency']-0.92)<1e-12 and abs(x['balance_bound']-0.04/(8*0.0055))<1e-12 and abs(x['residual']-0.92*8*0.0055/0.04)<1e-12,x
    assert x['graphs']==[0]and x['points']==32768 and x['wall_rank'].startswith('1 of 10')and [c[:5]for c in x['established']]==['tail:'],x['established']
    assert len(x['possible'])==2 and all('(not measured)'in c for c in x['possible'])and x['possible'][0].startswith('per-launch overhead')and x['possible'][1].startswith('end-of-block imbalance'),x['possible']
    s=o['shortfall'];assert s['summary']['all_below_short_and_few_tasks']and s['summary']['min_efficiency_blocks_ge_1s']==1.0 and s['summary']['untimed_blocks']==0
    assert 'POSSIBLE explanations, not measured: per-launch overhead and end-of-block imbalance between threads'in s['conclusion']and 'established for 1 of them'in s['conclusion'],s['conclusion']
    assert s['co_tenancy']['configured_capacity'].startswith('the job was configured with 8 lane(s)')and 'covering all of its allocated cores'in s['co_tenancy']['configured_capacity']
    assert s['co_tenancy']['observed_concurrency'].startswith('not recorded')and 'other 7 lane(s)'in s['co_tenancy']['observed_concurrency']and 'neither confirmed nor excluded'in s['conclusion']
    assert s['records_cannot_show']and TR.omp_part(bl,{})['verdict']=='PASS'
    # S4-R2-002: a short failing block with one task on one thread has no imbalance between threads (established), only possible overhead;
    # a single-lane job ran no other lane beside it; fewer tasks than threads is established by the counts
    one={'index':11,'group':'a_free_L3','block':'s000000_p000001','L':3,'tasks':1,'threads':1,'row_seconds':0.009,'integration_seconds':0.01,'host':'h1'}
    s1=TR.omp_part(bl+[one],{'host':'h1','cores':8,'lane_cores':8,'widths':[8]})['shortfall'];x=s1['blocks'][0]
    assert x['established']==['one thread: no imbalance between threads is possible; the idle core-seconds are time of the launch outside its rows']and [c[:19]for c in x['possible']]==['per-launch overhead'],x
    assert s1['co_tenancy']['observed_concurrency']=='a single lane: no other lane of this job ran beside these blocks'and 'single lane'in s1['conclusion']and 'imbalance'not in s1['conclusion'],s1['conclusion']
    assert 'POSSIBLE explanations, not measured: per-launch overhead;'in s1['conclusion']and s1['summary']['single_thread_blocks_below']==1,s1['conclusion']
    few={**tiny,'tasks':4,'max_row_seconds':None,'row_seconds':0.03,'integration_seconds':0.03/(8*0.4)}
    x=TR.omp_part(bl+[few],{})['shortfall']['blocks'][0];assert x['established']==['fewer tasks than threads: 4 on 8 threads, so 4 thread(s) had no task (efficiency at most 0.500)'],x
    # S4-R2-001: a block without valid timing is never evaluated and keeps the OpenMP verdict from PASS; a known SHORTFALL stays
    for bad,why in (({'integration_seconds':0.},'integration_seconds'),({'integration_seconds':None},'integration_seconds'),({'integration_seconds':float('nan')},'integration_seconds'),
                    ({'integration_seconds':float('inf')},'integration_seconds'),({'integration_seconds':-1.},'integration_seconds'),({'threads':0},'threads'),({'threads':-8},'threads'),
                    ({'threads':True},'threads'),({'threads':None},'threads'),({'row_seconds':float('nan')},'row_seconds'),({'row_seconds':-1.},'row_seconds')):
        u={**bl[0],'index':10,'block':'b10',**bad};m=TR.omp_part(bl+[u],{})
        assert m['verdict']=='INCOMPLETE'and m['all']['untimed']==1 and m['all']['untimed_blocks'][0]['index']==10 and m['all']['untimed_blocks'][0]['why'].startswith(why),(bad,m['verdict'],m['all'])
        assert m['all']['min']==1.0 and m['all']['time_weighted_mean']==1.0 and 'no valid timing'in m['why'],(bad,m['all'])
        m=TR.omp_part(bl+[tiny,u],{'widths':[8]*8});assert m['verdict']=='SHORTFALL'and m['shortfall']['summary']['untimed_blocks']==1 and '1 block(s) have no valid timing'in m['shortfall']['conclusion'],(bad,m['verdict'])
    assert TR.omp_part([{**tiny,'integration_seconds':0.}],{})['verdict']=='INCOMPLETE'
    # F13-d3: own_bytes = the process's own bytes + the native child's staged reads; non_own decides, non_own_raw (the Stage-5 model) is reported
    own={'tasks_bytes':10,'staged_bytes':1000,'checkpoint_bytes':5};x=TR.run_bytes(5_000_000+1015+1000,own,1000,700)
    assert x=={'own_bytes_process':1015,'native_staged_reads':1000,'own_bytes':2015,'non_own':5_000_000,'non_own_wo_fp':4_999_300,'non_own_raw':5_001_000,'non_own_raw_wo_fp':5_000_300},x
    rr=lambda g,stg:{'group':g,**TR.run_bytes(C+stg*2+100,{'staged_bytes':stg,'tasks_bytes':100},stg,0)}
    c=TR.compare_groups([rr('s',10**4),rr('l',10**9)],sizes)
    assert c['verdict']=='PASS'and c['smallest']['median_non_own']==C==c['largest']['median_non_own']and c['raw_model']['agree_non_own_raw']is False,c
    assert c['largest']['median_non_own_raw']==C+10**9 and 'never the verdict'in c['raw_model']['note']
    b=lambda n,rs,th,ig:{'block':n,'group':'g','tasks':3,'row_seconds':rs,'threads':th,'integration_seconds':ig}
    o=TR.omp_stats([b('b1',90.,10,10.),b('b2',200.,20,10.)])
    assert abs(o['time_weighted_mean']-290/300)<1e-15 and o['min']==0.9 and abs(o['median']-0.95)<1e-15 and o['share_ge_0_95']==0.5 and [x['block']for x in o['below_0_95']]==['b1'],o
    assert TR.pct([1,2,3,4,5,6,7,8,9,10],.1)==1.9 and TR.pct([3],.9)==3 and TR.pct([],.5)is None
    rec={'schema':'c8-d3-stage4b-opt-speed-1','smoke':False,'status':'passed','binaries':{'CAND':{'sha256':'ab'*32}},'shapes':{'CAND':'8x8'},
         'runs':[{'binary':'CAND','shape':'8x8','node_wall_seconds':w}for w in (10.,12.,11.)]+[{'binary':'B0','shape':'8x8','node_wall_seconds':1.}],
         'workload':{'sizes':{'heavy':1,'free':1,'power':1},'replicates':2,'points':512,'mp_check':'on'}}
    spp={'a:free:8:1':0.001,'a:free:8:2':0.002,'a:power:8:3':0.003,'b:free:8:1':9.}
    x=TR.ref_opt_speed(rec,'CAND',None,spp,{},1.0,lambda inv,sizes:{'free':[1,2],'power':[3]})
    assert abs(x['throughput_per_node_second']-0.006*2*512/11)<1e-15 and x['median_node_wall_seconds']==11. and x['binary_sha256']=='ab'*32,x
    assert abs(TR.ref_opt_speed(rec,'CAND','8x8',spp,{},1.5,lambda inv,s:{'free':[1,2],'power':[3]})['throughput_per_node_second']-1.5*0.006*1024/11)<1e-15
    for bad in ({'smoke':True},{'status':'failed'},{'schema':'x'}):
        try:TR.ref_opt_speed({**rec,**bad},'CAND',None,spp,{},1.,lambda i,s:{'free':[1]});raise AssertionError(f'accepted {bad}')
        except Refuse as e:assert e.code==65,e
    try:TR.ref_opt_speed(rec,'CAND',None,spp,{},1.,lambda i,s:{'free':[7]});raise AssertionError('missing key accepted')
    except Refuse as e:assert e.code==65 and 'no entry'in str(e)
    items=[(0.5*256,('pf',0),[0,0,1,0,256,256]),(1.5*512,('pp',1),[1,0,3,0,512,512])];parts={'pf':{'sector':'free','L':8},'pp':{'sector':'power','L':8}}
    p4={'schema':'c8-d3-prof-p4-1','best_shape':'16x8','shapes':[{'shape':'8x16','throughput_cost_model_s_per_node_s':50.,'errors':[]},
        {'shape':'16x8','throughput_cost_model_s_per_node_s':100.,'errors':[]}],'workload':{'cost_model_seconds':0.5*256+1.5*512},
        'identity':{'executables':{'worker':{'sha256':'cd'*32}}},'settings':{'mp_check':'on'}}
    sp={'a:free:8:1':0.25,'a:power:8:3':3.0}
    y=TR.ref_p4(p4,None,items,parts,sp,1.0);camp=0.25*256+3.0*512
    assert y['shape']=='16x8'and abs(y['throughput_per_node_second']-100*camp/(0.5*256+1.5*512))<1e-12 and y['binary_sha256']=='cd'*32,y
    assert abs(TR.ref_p4(p4,'8x16',items,parts,sp,2.0)['throughput_per_node_second']-50*2*camp/(0.5*256+1.5*512))<1e-12
    try:TR.ref_p4({**p4,'workload':{'cost_model_seconds':1.}},None,items,parts,sp,1.);raise AssertionError('another fixture accepted')
    except Refuse as e:assert e.code==65
    # J-SMK-4's sizing on the node's allocated cores: >= 3,600 s of L8 work per core; >= 140 busy core-h on 128 cores (PLAN), >= 72 on 64 (A1)
    for cores,need in ((128,140.),(64,72.)):
        assert TR.sizing_of(3600.*cores,need*3600,cores)['verdict']=='PASS'and TR.sizing_of(3600.*cores,need*3600-1,cores)['busy_core_hours_verdict']=='FAIL'
        assert TR.sizing_of(3600.*cores-1,need*3600,cores)['L8_work_verdict']=='FAIL'and TR.sizing_of(3600.*cores-1,need*3600,cores)['verdict']=='FAIL'
    z=TR.sizing_of(1e9,1e9,10);assert z['busy_core_hours_verdict']=='INCOMPLETE'and z['verdict']=='INCOMPLETE'and 'no rule for 10 cores'in z['busy_core_hours_rule'],z
    assert TR.verdict('PASS','PASS','PASS','INCOMPLETE','PASS','PASS')=='INCOMPLETE'and TR.verdict('PASS','INCOMPLETE','FAIL')=='FAIL'   # A-PERF-3 without --sweep: never PASS
    ln={'job':'7','widths':[8,8,8]};at=lambda *v:[{'alloc_cpus':x}if x!='-'else{}for x in v]
    assert TR.alloc_cores(at(64,64),ln,'')==(64,'accounting alloc_cpus (sacct AllocTRES cpu)')and TR.alloc_cores(at('-'),ln,'')[0]==24
    for bad,txt in ((at(64,32),''),(at(64,'-'),''),(at('-'),'C8 lanes: memory guard: 8 lanes x 30.0 GiB > ...'),(at(0),'')):
        try:TR.alloc_cores(bad,ln,txt);raise AssertionError(f'accepted {bad}')
        except Refuse as e:assert e.code==65,e
    ok('pure functions: the OpenMP rule per block (a block at 0.92 beside a time-weighted mean >= 0.95 is a SHORTFALL listed with its wall rank, '
       'tasks per thread, the longest row\'s bound 0.909 (established) and the residual, overhead and imbalance only possible; one thread: no '
       'imbalance, overhead possible; a single lane: no other lane beside it; fewer tasks than threads established; S4-R2-002; no block below: '
       'PASS; one block without valid timing (integration_seconds 0, None, NaN, inf or negative; threads 0, negative, True or None; row seconds '
       'NaN or negative) beside passing blocks: INCOMPLETE, beside a block below: SHORTFALL with it counted; S4-R2-001; none timed: INCOMPLETE) and SHORTFALL between '
       'FAIL and INCOMPLETE in the verdict; run_bytes (own_bytes = the process\'s own bytes + native_staged_reads; non_own and non_own_raw with and without '
       'fingerprint_bytes); the raw (Stage-5) model reported beside the verdict, which a group comparison decides on the corrected non_own; '
       'the A-ORC-13 tolerance max(10%, 2,000,000 bytes) (1.9 MB agrees, 2.1 MB does not; 9 MB of 109 MB agrees, 12 of 112 does not; both '
       'medians), a size ratio of 10 is not applicable; the time-weighted OpenMP mean, min, P10, median, share and blocks below 0.95; the opt_speed '
       're-expression (campaign-a seconds x replicates x points x mp factor over the median node wall of the binary\'s runs; smoke, failed and foreign '
       'records refused) and the P4 re-expression (shape throughput x campaign model seconds / fixture seconds of the same workload); J-SMK-4\'s '
       'sizing thresholds on the allocated cores (140 busy core-h on 128, 72 on 64, 3,600 s of L8 work per core; other counts INCOMPLETE); one '
       'INCOMPLETE part keeps a verdict from PASS; the allocated cores from the accounting\'s alloc_cpus (one value) or the lane widths without it '
       '(65 for disagreeing or partial values, or a memory-guard cut)')

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--keep',action='store_true');a=ap.parse_args()
    pure()
    td=Path(tempfile.mkdtemp(prefix='c8d3_thru_'))
    try:
        pkg=c8pkg.make(td);scr=td/'scratch';scr.mkdir()
        T=lambda script,*args,check=True,**x:c8pkg.tool(pkg,script,*args,check=check,**{'C8_LANES':'2','C8_LANE_SECONDS':'3600',**x})
        T('sweep.py',td/'sweep','--seed',SEED,'--output',td/'M.json','--scratch',scr,'--threads',2,C8_FAKE_SPP='0.001')
        M=json.loads((td/'M.json').read_text())
        def drill(name,seed,**x):
            d=td/name;T('production.py','plan',d,'--seed',seed,'--pilot','--test-only','--replicates',2,'--threads',2,'--cost-model',td/'M.json','--scratch',scr,SLURM_JOB_ID='9999')
            m=c8pkg.manifest(d);lanes.write_queue(d,sorted(((j['id'],float(j['est_core_seconds']))for j in m['jobs']),key=lambda t:(-t[1],t[0])))
            cp=T('lanes.py','worker',d,SLURM_JOB_ID=J,C8_FAKE_SPP=x.pop('spp','0.001'),C8_FAKE_FAST='1',**x)
            (d/'slurm_logs').mkdir();(d/'slurm_logs'/f'lane-{J}.log').write_text(cp.stdout)
            return d,m,cp.stdout
        D,m,lane_out=drill('drill',SEED+1)
        assert m['plan_role']=='campaign'and m['cost_basis']=='measured'and m['test_only'],m['plan_role']
        lane=TR.LANE_RE.search(lane_out);cores=sum(int(x)for x in lane.group(6).split(','));assert lane.group(1)==J,lane_out
        # the hand sums from the checkpoint files
        cks=[json.loads(f.read_text())for f in sorted(D.glob('groups/*/checkpoints/*.json'))];assert cks and all(c['runtime']['fingerprint']['slurm']['SLURM_JOB_ID']==J for c in cks)
        rsec=sum(float(r['seconds'])for c in cks for r in c['native']['rows']);W=rsec/(cores*0.95)
        acc=lambda w,jobs=(J,),ac=cores:{'attempts':[{'job':j,'name':f'c8d3-lane-x-{j}','state':'COMPLETED','elapsed':w,'billing':float(cores),'su':0.,'class':'work',
                                                      **({'alloc_cpus':ac}if ac is not None else{})}for j in jobs]}
        (td/'acc.json').write_text(json.dumps(acc(W)));(td/'acc2.json').write_text(json.dumps(acc(2*W)));(td/'acc_two.json').write_text(json.dumps(acc(W,(J,'4712'))))
        (td/'acc_alloc2.json').write_text(json.dumps(acc(W,ac=2*cores)));(td/'acc_noalloc.json').write_text(json.dumps(acc(W,ac=None)))
        # hook records from the idx logs: rchar = C + own bytes computed here
        inv=json.loads((pkg/'inputs/inventory.json').read_text());L={(s,int(l),r['id']):r['length']for s in ('free','power')for l,rows in inv[s].items()for r in rows}
        hooks=td/'hooks';hooks.mkdir();own_hand={};staged_hand={};est={j['id']:j['est_peak_bytes']for j in m['jobs']};pyk=100_000
        for f in sorted((D/'lanes/logs').glob('idx*.log')):
            idx=int(f.name[3:].split('.')[0]);j=m['jobs'][idx];g=D/'groups'/j['group']
            own=j['tasks_bytes']+(D/j['blocks_file']).stat().st_size+(g/'sobol.bin').stat().st_size;staged=0
            cfg=json.loads((g/'config.json').read_text())
            for k in range(j['blocks']):
                c=json.loads((g/'checkpoints'/f's{j["shard"]:06d}_p{k:06d}.json').read_text())
                sb=sum(L[(cfg['sector'],cfg['L'],gi)]for gi in {r['graph']for r in c['native']['rows']});own+=sb+len(json.dumps(c['native']));staged+=sb
            own_hand[idx]=own;staged_hand[idx]=staged
            # rchar as Linux counts it: the process's reads, and the reaped native child's read of each block's staged copy (F13-d3)
            rec={'schema':HOOK,'pid':1000+idx,'host':'fakehost','job':J,'argv':[str(pkg/'tools/production.py'),'run',str(D),'--index',str(idx),'--threads','5','--scratch','/x'],
                 'utc':'2026-10-05T00:00:00Z','io':{'rchar':C+own+staged,'wchar':1},'ru_maxrss_self_kb':pyk,'ru_maxrss_children_kb':1024}
            (hooks/f'fakehost_{idx}.json').write_text(json.dumps(rec))
        assert len(own_hand)==len(m['jobs'])
        def rep(out,*x,run=D,check=True):
            cp=T('thru_report.py',run,'--output',td/out,*x,check=False)
            if check:assert cp.returncode==0,(out,cp.returncode,cp.stderr[-1500:])
            return cp,(json.loads((td/out).read_text())if (td/out).exists()else None)
        cp,r=rep('r1.json','--accounting',td/'acc.json','--sweep',td/'sweep','--reference-throughput',1.0,'--reference-note','placeholder','--hook-dir',hooks)
        thr=r['a_perf_3']['throughput']['per_node_second']
        cp,r=rep('r2.json','--accounting',td/'acc.json','--sweep',td/'sweep','--reference-throughput',repr(thr),'--reference-note','the drill itself (test)','--hook-dir',hooks)
        p3=r['a_perf_3']
        assert abs(p3['busy']['value']-rsec/(cores*W))<1e-12 and p3['busy']['verdict']=='PASS'and p3['busy']['cores']==cores,p3['busy']
        assert p3['busy']['cores_source'].startswith('accounting alloc_cpus')and p3['references']=={'throughput':'given','speed':'sweep','cores':p3['busy']['cores_source']},p3['references']
        assert abs(p3['openmp']['all']['time_weighted_mean']-1)<1e-12 and abs(p3['openmp']['L8']['time_weighted_mean']-1)<1e-12 and p3['openmp']['verdict']=='PASS',p3['openmp']
        assert abs(p3['throughput']['ratio_to_reference']-1)<1e-12 and p3['throughput']['verdict']=='PASS'
        assert abs(p3['speed']['ratio']-1)<1e-9 and p3['speed']['verdict']=='PASS'and p3['speed']['reference_label']=='the --sweep campaign\'s L8 median'
        assert p3['cpu_matches_model']['verdict']=='PASS'and p3['sizing']['verdict']=='FAIL'and p3['sizing']['L8_work_verdict']=='FAIL'and p3['verdict']=='FAIL'
        o13=r['a_orc_13'];assert o13['fingerprint_bytes']['verdict']=='PASS'and all(len(v['values'])==1 for v in o13['fingerprint_bytes']['per_key'].values())
        assert o13['paired_runs']==len(own_hand)and all(x['non_own']==C and x['own_bytes']==own_hand[x['index']]+staged_hand[x['index']]for x in r['runs']),[(x['index'],x['non_own'])for x in r['runs']]
        assert all(x['own_bytes_process']==own_hand[x['index']]and x['native_staged_reads']==staged_hand[x['index']]==x['own']['staged_bytes']>0 and x['non_own_raw']==C+staged_hand[x['index']]
                   and x['non_own_wo_fp']==C-x['fingerprint_bytes']for x in r['runs']),r['runs'][:2]
        assert r['schema']=='c8-d3-thru-report-2'and 'Linux adds a reaped child'in o13['native_child_reads']and 'native_staged_reads'in o13['own_bytes_model']
        assert abs(o13['fit_non_own_on_staged_bytes']['slope'])<1e-9 and o13['fit_non_own_on_staged_bytes']['intercept']==C,o13['fit_non_own_on_staged_bytes']
        assert o13['non_own']['verdict']=='INCOMPLETE'and 'not applicable'in o13['non_own']['why']and o13['verdict']=='INCOMPLETE',o13['non_own']
        o5=r['a_orc_5']
        for e in o5['indices']:
            want=(1024*1024+pyk*1024)/est[e['index']];assert abs(e['ratio']-want)<1e-12 and e['verdict']=='PASS',(e,want)
        assert o5['verdict']=='PASS'and r['inputs']['hook']['kept']==len(own_hand)and r['inputs']['hook']['foreign']==0
        cp,r2=rep('r3.json','--accounting',td/'acc.json','--sweep',td/'sweep','--reference-throughput',repr(thr),'--reference-note','the drill itself (test)','--hook-dir',hooks)
        strip=lambda x:{k:v for k,v in x.items()if k!='made_utc'}
        assert strip(r)==strip(r2),'the report is not deterministic'
        ok('A-PERF-3 on the fake drill: busy = row seconds / (cores x W) by hand (0.95, PASS), OpenMP 1.0, throughput ratio 1 to the drill\'s own value, '
           'speed ratio 1 to the --sweep campaign, the lane log\'s CPU equals the model\'s, sizing FAIL (a small campaign); A-ORC-13: one fingerprint_bytes '
           'value per key, non_own = the constant for every paired run (own bytes = the hand computation + the native child\'s staged reads; '
           'non_own_raw = the constant + the staged bytes; the fit of non_own on the staged bytes: slope 0), the group comparison not applicable '
           '(sizes within 10x); A-ORC-5 ratios equal the hand values; the report minus made_utc is identical on two runs',cores=cores,busy=p3['busy']['value'])
        # negative controls, each with its number
        _,r=rep('n_busy.json','--accounting',td/'acc2.json','--reference-throughput',repr(thr),'--reference-note','x')
        assert abs(r['a_perf_3']['busy']['value']-0.475)<1e-12 and r['a_perf_3']['busy']['verdict']=='FAIL',r['a_perf_3']['busy']
        _,r=rep('n_thr.json','--accounting',td/'acc.json','--reference-throughput',repr(1.1*thr),'--reference-note','x')
        assert abs(r['a_perf_3']['throughput']['ratio_to_reference']-1/1.1)<1e-12 and r['a_perf_3']['throughput']['verdict']=='FAIL'
        # busy's denominator is the node's allocated cores (the accounting's alloc_cpus), not the lanes' widths: twice the
        # cores the lanes use halves busy (FAIL) and is noted; without alloc_cpus the lane log's widths are the cores
        _,r=rep('n_alloc.json','--accounting',td/'acc_alloc2.json','--reference-throughput',repr(thr),'--reference-note','x');p=r['a_perf_3']
        assert abs(p['busy']['value']-0.475)<1e-12 and p['busy']['verdict']=='FAIL'and p['busy']['cores']==2*cores and r['job']['lane_cores']==cores,p['busy']
        assert abs(p['sizing']['L8_work_seconds_per_core']-p['sizing']['L8_row_seconds']/(2*cores))<1e-12 and any('idle cores count against busy'in n for n in r['notes']),r['notes']
        _,r=rep('n_noalloc.json','--accounting',td/'acc_noalloc.json','--reference-throughput',repr(thr),'--reference-note','x');p=r['a_perf_3']
        assert p['busy']['cores']==cores and p['busy']['cores_source'].startswith('lane log')and abs(p['busy']['value']-0.95)<1e-12,p['busy']
        # without --sweep (the PLAN's comparator) the speed is reported against 1.0 but INCOMPLETE, so A-PERF-3 is never PASS
        _,r=rep('n_nosweep.json','--accounting',td/'acc.json','--reference-throughput',repr(thr),'--reference-note','x');p=r['a_perf_3']
        assert abs(p['speed']['ratio']-1)<1e-9 and p['speed']['verdict']=='INCOMPLETE'and p['speed']['reference_kind']=='model_definition'and p['verdict']!='PASS',p['speed']
        assert p['references']['speed']=='model_definition'and any('no --sweep'in n for n in r['notes']),(p['references'],r['notes'])
        Do,_,_=drill('drill_omp',SEED+2,C8_FAKE_OMP_EFF='0.9');(td/'acc_o.json').write_text(json.dumps(acc(W)))
        _,r=rep('n_omp.json','--accounting',td/'acc_o.json',run=Do)
        o=r['a_perf_3']['openmp'];assert abs(o['all']['time_weighted_mean']-0.9)<1e-12 and o['verdict']=='SHORTFALL'and r['a_perf_3']['busy']['verdict']!='FAIL'
        assert len(o['shortfall']['blocks'])==o['all']['blocks']and all(abs(x['efficiency']-0.9)<1e-9 for x in o['shortfall']['blocks']),o['shortfall']['summary']
        # S4-007: one block at 0.9 while the time-weighted mean stays >= 0.95: the Stage-5 rule (the mean) passed it, the PLAN's per-block rule does not
        Dw=td/'drill_omp1';shutil.copytree(D,Dw);cks=sorted(Dw.glob('groups/*/checkpoints/*.json'))
        f=min(cks,key=lambda f:sum(float(x['seconds'])for x in json.loads(f.read_text())['native']['rows']));c=json.loads(f.read_text());n=c['native']
        n['integration_seconds']=sum(float(x['seconds'])for x in n['rows'])/(n['threads']*0.9);c['payload_sha256']=object_hash(n);f.unlink();f.write_text(json.dumps(c,indent=2)+'\n')
        _,r=rep('n_omp1.json','--accounting',td/'acc.json','--sweep',td/'sweep','--reference-throughput',repr(thr),'--reference-note','x',run=Dw);o=r['a_perf_3']['openmp']
        assert o['all']['time_weighted_mean']>=0.95 and o['all']['min']<0.95 and o['verdict']=='SHORTFALL',(o['verdict'],o['all']['time_weighted_mean'],o['all']['min'])
        sb=o['shortfall']['blocks'];assert len(sb)==1 and sb[0]['index']==c['index']and abs(sb[0]['efficiency']-0.9)<1e-9 and sb[0]['graphs']and sb[0]['points']>0,sb
        assert sb[0]['threads']==n['threads']and sb[0]['host']and 'balance_bound'in sb[0]and o['shortfall']['conclusion']and r['a_perf_3']['busy']['verdict']=='PASS',sb
        # S4-R2-001 in report mode: one checkpoint's integration_seconds set to 0 (payload digest renewed) beside blocks at 1.0: not evaluated, never PASS
        Du=td/'drill_untimed';shutil.copytree(D,Du);f=sorted(Du.glob('groups/*/checkpoints/*.json'))[0];c=json.loads(f.read_text());n=c['native']
        n['integration_seconds']=0.;c['payload_sha256']=object_hash(n);f.unlink();f.write_text(json.dumps(c,indent=2)+'\n')
        _,r=rep('n_untimed.json','--accounting',td/'acc.json',run=Du);o=r['a_perf_3']['openmp']
        assert o['verdict']=='INCOMPLETE'and o['all']['untimed']==1 and o['all']['min']>=0.95 and o['all']['untimed_blocks'][0]['index']==c['index'],(o['verdict'],o['all'])
        assert [b['omp_efficiency']for b in r['block_detail']].count(None)==1 and r['a_perf_3']['causes']['untimed_blocks']==1,r['a_perf_3']['causes']
        Ds,_,_=drill('drill_slow',SEED+3,spp='0.0012')
        _,r=rep('n_speed.json','--accounting',td/'acc.json','--sweep',td/'sweep',run=Ds)
        assert abs(r['a_perf_3']['speed']['ratio']-1/1.2)<1e-9 and r['a_perf_3']['speed']['verdict']=='FAIL'and r['a_perf_3']['throughput']['verdict']=='INCOMPLETE',r['a_perf_3']['speed']
        Dc=td/'drill_fp';shutil.copytree(D,Dc);f=sorted((Dc/'lanes/logs').glob('idx*.log'))[0];t=f.read_text()
        f.write_text(TR.FP_RE.sub(lambda x:f'fingerprint {x.group(1)} ({x.group(2)}); fingerprint_bytes {int(x.group(3))+1}',t,count=1))
        _,r=rep('n_fp.json','--parts','orc13,orc5','--hook-dir',hooks,run=Dc)
        assert r['a_orc_13']['fingerprint_bytes']['verdict']=='FAIL'and r['a_orc_13']['verdict']=='FAIL',r['a_orc_13']['fingerprint_bytes']
        hb=td/'hooks_big';shutil.copytree(hooks,hb);g=sorted(hb.glob('*.json'))[0];h=json.loads(g.read_text());h['ru_maxrss_self_kb']=int(2*est[int(h['argv'][4])]/1024);g.write_text(json.dumps(h))
        _,r=rep('n_rss.json','--parts','orc5','--hook-dir',hb)
        bad=[e for e in r['a_orc_5']['indices']if e['verdict']=='FAIL'];assert len(bad)==1 and bad[0]['ratio']>2 and r['a_orc_5']['verdict']=='FAIL',r['a_orc_5']
        _,r=rep('n_nohook.json','--parts','orc5')
        assert r['a_orc_5']['verdict']=='INCOMPLETE'and all(e['ratio']is None and e['native_only_ratio']>0 for e in r['a_orc_5']['indices'])
        ok('negative controls: W doubled (busy 0.475, FAIL); twice the lanes\' cores allocated (busy 0.475, FAIL, noted; the widths only without '
           'alloc_cpus); no --sweep (speed ratio 1 reported, INCOMPLETE; A-PERF-3 not PASS); C8_FAKE_OMP_EFF=0.9 (OpenMP 0.9, every block a SHORTFALL); '
           'one block at 0.9 beside a time-weighted mean >= 0.95 (a SHORTFALL listing that block, its graphs, points, threads, host and the longest row\'s '
           'bound; S4-007); one block untimed beside blocks at 1.0 (OpenMP INCOMPLETE, the block listed; S4-R2-001); a reference 1.1 x '
           'the drill (throughput 0.909, FAIL); a drill at 1.2 x the sweep\'s seconds per point (speed 0.833, FAIL); one idx log\'s fingerprint_bytes '
           'changed (FAIL); a Python peak of 2 x est_peak_bytes (orc5 FAIL); without the hook orc5 is INCOMPLETE with the native-only ratios')
        # refusals
        def refused(code,needle,*x,run=D,out='rf.json'):
            if (td/out).exists():(td/out).unlink()
            cp,_=rep(out,*x,run=run,check=False);assert cp.returncode==code and needle in cp.stderr and not (td/out).exists(),(x,cp.returncode,cp.stderr[-600:])
        refused(65,'measured basis','--accounting',td/'acc.json',run=td/'sweep')
        Dm=td/'drill_cm';shutil.copytree(D,Dm);b=bytearray((Dm/'cost_model.json').read_bytes());b[-2]^=1;(Dm/'cost_model.json').write_bytes(bytes(b))
        refused(65,'cost_model.json','--accounting',td/'acc.json',run=Dm)
        Dk=td/'drill_ck';shutil.copytree(D,Dk);f=sorted(Dk.glob('groups/*/checkpoints/*.json'))[0];c=json.loads(f.read_text());c['native']['rows'][0]['seconds']+=1.0;f.write_text(json.dumps(c))
        refused(65,'payload','--accounting',td/'acc.json',run=Dk)
        refused(65,'committed no checkpoint','--accounting',td/'acc.json','--job','999')
        Dl=td/'drill_nolog';shutil.copytree(D,Dl);(Dl/'slurm_logs'/f'lane-{J}.log').unlink();refused(65,'lane worker','--accounting',td/'acc.json',run=Dl)
        refused(65,'--sweep','--accounting',td/'acc.json','--sweep',Ds)
        refused(64,'one reference','--accounting',td/'acc.json','--reference-throughput',1,'--reference-note','x','--reference-p4',td/'p4.json')
        refused(64,'--hook-dir','--parts','orc13')
        refused(64,'--job is required','--accounting',td/'acc_two.json')
        refused(64,'--accounting','--parts','perf3')
        refused(64,'--reference-note','--accounting',td/'acc.json','--reference-throughput',1)
        (td/'exists.json').write_text('{}');cp=T('thru_report.py',D,'--output',td/'exists.json','--accounting',td/'acc.json',check=False)
        assert cp.returncode==64 and 'never overwritten'in cp.stderr and (td/'exists.json').read_text()=='{}'
        hf=td/'hooks_foreign';shutil.copytree(hooks,hf)
        (hf/'other_schema.json').write_text(json.dumps({'schema':'x','argv':[str(pkg/'tools/production.py'),'run',str(D),'--index','0'],'job':J,'io':{'rchar':1}}))
        (hf/'other_run.json').write_text(json.dumps({'schema':HOOK,'argv':[str(pkg/'tools/production.py'),'run',str(td/'sweep'),'--index','0'],'job':J,'io':{'rchar':1},'ru_maxrss_self_kb':1}))
        (hf/'not_run.json').write_text(json.dumps({'schema':HOOK,'argv':[str(pkg/'tools/production.py'),'merge',str(D)],'job':J,'io':{'rchar':1}}))
        (hf/'garbage.json').write_text('not json')
        _,ra=rep('fa.json','--parts','orc13,orc5','--hook-dir',hooks);_,rb=rep('fb.json','--parts','orc13,orc5','--hook-dir',hf)
        assert rb['inputs']['hook']['foreign']==4 and rb['inputs']['hook']['unreadable']==1 and rb['inputs']['hook']['kept']==ra['inputs']['hook']['kept']
        drop=lambda x:{k:v for k,v in x.items()if k not in('made_utc','inputs')}
        assert drop(ra)==drop(rb),'foreign hook records changed the result'
        # Stage 6 on J-SMK-4's committed records: F13-d3 (A-ORC-13) and S4-007 (the OpenMP rule per block)
        SMK=ROOT/'benchmarks/symmetry_2026-10-c8/stage5_59d4922';src=SMK/'smk4/thru_report.json';hk=SMK/'smk4_hook';old=json.loads(src.read_text())
        cp=T('thru_report.py','--rederive',src,'--hook-dir',hk,'--output',td/'s6.json',check=False);assert cp.returncode==0,cp.stderr[-800:];s6=json.loads((td/'s6.json').read_text())
        n=s6['a_orc_13']['non_own'];o=old['a_orc_13']['non_own']
        assert old['a_orc_13']['verdict']=='FAIL'and (o['smallest']['median_non_own'],o['largest']['median_non_own'])==(30049197,1389313912)
        assert (n['smallest']['median_non_own_raw'],n['largest']['median_non_own_raw'])==(30049197,1389313912)and n['raw_model']['agree_non_own_raw']is False,n
        assert (n['smallest']['median_non_own'],n['largest']['median_non_own'])==(30046840,31734238)and n['verdict']=='PASS'and s6['a_orc_13']['verdict']=='PASS',n
        assert abs(s6['a_orc_13']['fit_rchar_on_staged_bytes']['slope']-2.001052953255861)<1e-9 and abs(s6['a_orc_13']['fit_non_own_on_staged_bytes']['slope'])<1e-3
        om=s6['a_perf_3']['openmp'];assert old['a_perf_3']['openmp']['verdict']=='PASS'and old['a_perf_3']['verdict']=='PASS'
        assert om['verdict']=='SHORTFALL'and s6['a_perf_3']['verdict']=='SHORTFALL'and [round(x['efficiency'],3)for x in om['shortfall']['blocks']]==[0.916,0.929,0.936],om['shortfall']['blocks']
        assert om['shortfall']['summary']['all_below_short_and_few_tasks']and s6['rederived']['hook']['used']==82 and s6['schema']=='c8-d3-thru-report-2'and s6['a_orc_5']==old['a_orc_5']
        sh=om['shortfall'];assert all(x['established']==[]and len(x['possible'])==2 and all('(not measured)'in c for c in x['possible'])for x in sh['blocks']),sh['blocks']
        assert 'POSSIBLE explanations, not measured'in sh['conclusion']and sh['co_tenancy']['observed_concurrency'].startswith('not recorded')and 'other 7 lane(s)'in sh['co_tenancy']['observed_concurrency']
        com=json.loads((SMK/'smk4/thru_report_s6b.json').read_text())
        strip=lambda x:{**x,'rederived':{k:v for k,v in x['rederived'].items()if k not in('made_utc','made_on','hook','from')}}  # noqa: E731
        assert strip(com)==strip(s6)and com['rederived']['from']['sha256']==s6['rederived']['from']['sha256']==hashlib.sha256(src.read_bytes()).hexdigest(),'smk4/thru_report_s6b.json is not this re-derivation'
        # fix round 1's record (thru_report_s6.json, kept) differs only in the OpenMP rule text, the untimed list and the cause analysis, and the rederived block
        s6o=json.loads((SMK/'smk4/thru_report_s6.json').read_text());oo=s6o['a_perf_3']['openmp']
        cut=lambda x:{**{k:v for k,v in x.items()if k!='rederived'},'a_perf_3':{k:v for k,v in x['a_perf_3'].items()if k!='openmp'}}  # noqa: E731
        assert cut(s6o)==cut(s6)and oo['verdict']==om['verdict']and oo['all']=={k:v for k,v in om['all'].items()if k!='untimed_blocks'}and om['all']['untimed_blocks']==[]
        assert [x['efficiency']for x in oo['shortfall']['blocks']]==[x['efficiency']for x in sh['blocks']]and oo['shortfall']['summary'].items()<=sh['summary'].items()
        # S4-R2-001 through --rederive: J-SMK-4's record with one other block's integration_seconds set to 0, and the three blocks below raised to 1.0
        # (mixed_pass: INCOMPLETE, never PASS) or kept (mixed_short: the SHORTFALL stays, the untimed block counted)
        below={(x['index'],x['block'])for x in sh['blocks']}
        for name,raise_ in (('mixed_pass',True),('mixed_short',False)):
            rec=json.loads(src.read_text());u=next(b for b in rec['block_detail']if (b['index'],b['block'])not in below);u['integration_seconds']=0.
            for b in rec['block_detail']:
                if raise_ and (b['index'],b['block'])in below:b['integration_seconds']=b['row_seconds']/b['threads']
            (td/f'{name}.json').write_text(json.dumps(rec))
            cp=T('thru_report.py','--rederive',td/f'{name}.json','--output',td/f'{name}_out.json',check=False);assert cp.returncode==0,cp.stderr[-800:]
            q=json.loads((td/f'{name}_out.json').read_text())['a_perf_3'];qo=q['openmp']
            if raise_:assert qo['verdict']=='INCOMPLETE'and qo['all']['min']>=0.95 and q['verdict']=='INCOMPLETE',(name,qo['verdict'],q['verdict'],qo['all']['min'])
            else:assert qo['verdict']=='SHORTFALL'==q['verdict']and qo['shortfall']['summary']['untimed_blocks']==1 and len(qo['shortfall']['blocks'])==3,(name,qo['verdict'])
            assert qo['all']['untimed']==1 and qo['all']['untimed_blocks'][0]['index']==u['index'],(name,qo['all'])
        hx=td/'smk4_hook_x';shutil.copytree(hk,hx);f=sorted(hx.glob('*.json'))[0];h=json.loads(f.read_text());h['io']['rchar']+=1;f.unlink();f.write_text(json.dumps(h))
        cp=T('thru_report.py','--rederive',src,'--hook-dir',hx,'--output',td/'s6x.json',check=False);assert cp.returncode==65 and 'rchar'in cp.stderr and not (td/'s6x.json').exists(),cp.stderr
        f.unlink();cp=T('thru_report.py','--rederive',src,'--hook-dir',hx,'--output',td/'s6x.json',check=False);assert cp.returncode==65 and 'no c8-d3-host-io-hook-1 record'in cp.stderr,cp.stderr
        cp=T('thru_report.py',D,'--rederive',src,'--output',td/'s6y.json',check=False);assert cp.returncode==64 and '--rederive takes only'in cp.stderr,cp.stderr
        cp=T('thru_report.py','--rederive',src,'--output',td/'s6.json',check=False);assert cp.returncode==64 and 'never overwritten'in cp.stderr,cp.stderr
        cp=T('thru_report.py','--output',td/'s6z.json',check=False);assert cp.returncode==64 and 'RUN is required'in cp.stderr,cp.stderr
        ok('Stage 6 on J-SMK-4 (--rederive, from the committed report and its 82 hook records): A-ORC-13 FAIL -> PASS (F13-d3: non_own medians 30,046,840 '
           'and 31,734,238 bytes; the Stage-5 model\'s 30,049,197 and 1,389,313,912 reproduced as non_own_raw; fits 2.001 and ~0); A-PERF-3 PASS -> '
           'SHORTFALL (S4-007: blocks at 0.916, 0.929, 0.936, all short few-task blocks; overhead and imbalance only POSSIBLE, the other 7 lanes\' '
           'activity not recorded: S4-R2-002); the committed smk4/thru_report_s6b.json is this record and the kept thru_report_s6.json differs only in '
           'the OpenMP cause analysis; with one block untimed (S4-R2-001) the record re-derives to INCOMPLETE when every timed block passes and keeps '
           'its SHORTFALL otherwise; a changed or missing hook record (65), RUN or another option beside --rederive, an existing output and no RUN '
           '(64) are refused')
        ok('refusals: a bootstrap-basis campaign, cost_model.json changed by one byte, a changed checkpoint payload, a job without checkpoints, a missing '
           'lane log and --sweep of another campaign (65); two references, orc13 without --hook-dir, --job missing with two work jobs, perf3 without '
           '--accounting, a reference without its note and an existing --output (64); hook records of another schema, campaign or command and an '
           'unreadable file are counted as foreign and change nothing else')
    finally:
        if a.keep:print('kept',td,file=sys.stderr)
        else:shutil.rmtree(td,ignore_errors=True)
    print(json.dumps({'status':'passed','tests':len(RESULTS)}));return 0
if __name__=='__main__':sys.exit(main())
