#!/usr/bin/env python3
"""The C8(3) pipeline end to end with fakes (PLAN F, test_pipeline row; A-DES-7 (a)-(e), A-ORC-3's fake lane-mode rule,
A-ASM-6 on real campaign directories). Mac only; no native build, no Slurm.

A scratch package with synthetic complete inputs (tests/c8pkg.py) and the stateful fake Slurm as executables (sbatch,
squeue, sacct, ...). Every plan runs as a real job body would: a `raw --role plan` job is admitted by the fake, then
slurm/plan.sh runs with that job's id and name (production.py plan on its scratch with its seed reservation, ledger.py register).
Lane mode: `slurm_submit.py lanes N` is admitted, the test runs tools/lanes.py worker as each fake lane job, then the
real slurm/merge.sh as the merge job. Every lane-mode plan has role campaign on a model that make_cost_model.py
measured from the pipeline's fake cost_sweep (tools/sweep.py), never the synthetic fixture (HC7).

  1. sweep (cost_sweep, bootstrap) -> make_cost_model.py -> the measured model M
  2. pilot_select stage-a -> PA (pilot_subset, L8 only, P1c nested; reduced-scale P1c injected, see pa_selection)
     -> lanes -> the real merge.sh -> subset-check -> pilot_report stage-a                         [A-DES-7 (a)]
     the runbook's stage-a line verbatim (GO, with every A-PIL-2 field), then NO-GO on copies with an injected
     mp_alarm, a worker failure record, a pilot line below a branch's peak reservation, and no line   [A-PIL-2]
  3. PF (pilot_full) -> lanes -> merge.sh -> assemble -> C8_pilot_result.json labelled pilot; the coverage guard on
     tampered copies                                                                            [A-DES-7 (d)]
     then tools/accounting.py on PF against the hand sum (a requeued attempt, a job without a ledger record) and the
     unknown-job refusal                                                                        [A-ORC-9 fakes]
  4. the runbook's confirm (--screen PF --pa PA) and count lines verbatim (the old --screen FILE --pf form gives the same
     selection) -> PC (pilot_subset, one sector) -> lanes -> merge.sh -> subset-check -> the runbook's full line verbatim
     (pilot_report.json, PILOT_REPORT.md, the growth and sigma/cost files)                          [(b), A-PIL-5]
     The zero-channel L8 graph 3 (s_G = 4 in tests/c8pkg.py, heavy-tailed here) is reported as "zero-channel heavy
     tail, not confirmed" and never flagged or selected (host refinement, Stage 3a repair round 3)
  5. the empty-PC branch: confirm writes "groups": {} with its reason, count prints 0, plan --graphs exits 65
     creating nothing, full with --pc-selection alone (the runbook's skip branch verbatim) succeeds and records the
     reason                                                                                       [(c)]
  6. refusals: the result tools on a pilot_subset campaign (65), subset-check on tampered copies, --graphs with
     --test-graphs or --design, a non-test --graphs plan of another selection role, full's --pc rules, merge.sh on an
     unknown role (64)                                                                            [(e)]
  7. design_fallback freeze (test-only) on PF -> plan --design (two batches) -> run -> merge -> assemble -> combine
     (A-ASM-6 on directories); freeze --pc PC (the conservative tail rule, RECON:1373) on the real PF and PC records PC's
     identity bound to PF's and monitors exactly the graphs the full report confirmed; the PA as --pc and a PF copy whose
     scientific identity changed (step 4's pf_sci) are refused, no bundle left
  Stage 6 group B: S3-005 the screen and the PC selection record PF's and PA's identities; confirm refuses a screen
     file of another PF or PA (or without identities) and full a selection whose screen names another PF or PA;
     S3-006 verify_result.py RUN and full refuse a PF whose C8_pilot_result.json, still a valid result, names another
     source manifest, merged file or allocation; S3-009 report.py on a test batch and on PF keeps C8 and its SE null with
     the values under test_partial / sizing_only; S3-011 design_adapter view of PF copies (new inodes, 0444) and leaves
     every source file's permissions as they were
  Stage 6 fix round 2, group P: S3-R2-001 the PC selection planned at more replicates than it was priced at (--replicates,
     or --group-replicates for its dearer sector) is refused before anything is created; S3-R2-009 after the completed
     PA/PF/PC chain, a timing-only re-merge of PA and of PF (copies: one checkpoint and its group's merged.json deleted, the
     index recomputed with other row seconds, merge, then subset-check or assemble, which supersede) leaves full working
     on the same PC selection and PC (its screen is bound by scientific identities, not by merged.json bytes), while a
     scientific change of a PA or PF table (graph_tails.csv tail_sum, re-pinned) is still refused; a screen file whose PF
     identity differs only in a merged.json sha256 is accepted by confirm, one whose scientific identity differs refused
  8. J-DRL-9 (the subset-pilot drill, Stage 5): tools/drill_select.py drl9 on M -> a test-only --pilot --graphs plan in
     a raw plan job (pilot_subset) -> the empty confirm plan exits 65 creating nothing -> lanes 1 --dry-run in drill
     mode names the subset merge path -> lanes 1 (drill) -> merge.sh: subset-check, no assemble.py, subset_summary.json,
     no C8_*result.json, 2 prefix rows per group, prefix_verify.py passes

The runbook lines come from tests/fixtures/runbook_stage7_pilot_tools.txt, a verbatim copy of PLAN "Pilot (Stage 7)"
(checked line by line against the approved PLAN when it is reachable: C8_PLAN_MD, or ../LRI_C8_D3_HPC_loop/PLAN.md);
the operator's placeholders <date> and <registered> are filled in, and the commands run in bash from the package
directory with python3 on PATH, as the runbook's jobs run them.

  python3 -B tests/test_pipeline.py [--keep]
"""
from __future__ import annotations
import hashlib,json,math,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import c8pkg
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,**info});print('PASS',name,flush=True)
COUNTS={'free':{3:2,4:2,5:3,6:3,7:4,8:24},'power':{3:1,4:2,5:2,6:3,7:3,8:16}}
HEAVY='8:3,8:5,7:2'      # L8 graphs 3 and 5 with a Pareto(1.5) tail (C8_FAKE_HEAVY, both sectors): the screen and the confirmation;
                         # L7 graph 2 too: actions 1-5 act on L8 only (A-DES-3), so it is a diagnostic and in no action's output;
                         # L8 graph 3 has s_G = 4 (tests/c8pkg.py: gid % 7 == 3), a zero channel: reported, never flagged
DATE='20261005';RUNBOOK=ROOT/'tests/fixtures/runbook_stage7_pilot_tools.txt'
ZC_NOTE='zero-channel heavy tail, not confirmed'
SPY=r'''
import os,sys
def _hook(ev,args):
    if ev=='import'and args and isinstance(args[0],str)and ('order8_assembly'in args[0]):
        with open(os.environ['C8_SPY_LOG'],'a')as f:f.write('import '+args[0]+'\n')
sys.addaudithook(_hook)
with open(os.environ['C8_SPY_LOG'],'a')as f:f.write('argv '+' '.join(sys.argv)+'\n')
'''

class Pipe:
    def __init__(self,td:Path):
        self.td=td;self.pkg=c8pkg.make(td,counts=COUNTS);self.site=c8pkg.SlurmSite(td);self.scr=td/'scratch';self.scr.mkdir()
        self.seeds=self.site.root/'forbidden_seeds.json';self.spy=td/'spy';self.spy.mkdir();(self.spy/'sitecustomize.py').write_text(SPY)
        self.tool('seeds.py','init','--log',self.seeds,'--from',self.pkg/'designs/forbidden_seeds.json')   # as on symmetry (A1, HD6)
    def env(self,**x)->dict:
        return self.site.env(C8_SEEDS=self.seeds,C8_FAKE_SPP='0.0005',C8_FAKE_HEAVY=HEAVY,C8_PACKAGE=self.pkg,C8_PYTHON=sys.executable,**x)
    def tool(self,script,*args,check=True,**x):
        cp=subprocess.run([sys.executable,'-B',str(self.pkg/'tools'/script),*map(str,args)],capture_output=True,text=True,env=c8pkg.env(**self.env(**x)))
        if check and cp.returncode:raise AssertionError(f'{script} {args}: {cp.returncode}\n{cp.stderr[-2500:]}\n{cp.stdout[-800:]}')
        return cp
    def newest(self,before:set)->list:return [j for j in self.site.jobs()if j['id']not in before]
    def runbook(self,cmd:str,E:Path,seed=None,check=True,**x):
        """One runbook command as the job runs it: bash from the package directory, python3 on PATH, $C8_ROOT and $E set,
        the operator's placeholders <date> and <registered> filled in."""
        shim=self.td/'shim';shim.mkdir(exist_ok=True)
        if not (shim/'python3').exists():(shim/'python3').symlink_to(sys.executable)
        cmd=cmd.replace('<date>',DATE).replace('<registered>',str(seed));e=self.env(E=E,**x);e['PATH']=f'{shim}:{e["PATH"]}'
        cp=subprocess.run(['bash','-c','set -eo pipefail; '+cmd],cwd=self.pkg,capture_output=True,text=True,env=c8pkg.env(**e))
        if check and cp.returncode:raise AssertionError(f'runbook `{cmd[:160]}`: {cp.returncode}\n{cp.stderr[-2500:]}\n{cp.stdout[-800:]}')
        return cp
    def job_body(self,cmd:list,jid:str,check=True,**x):
        j=next(j for j in self.site.jobs()if j['id']==jid);tmp=self.scr/f'job_{jid}';tmp.mkdir(exist_ok=True)
        cp=subprocess.run(cmd,capture_output=True,text=True,env=c8pkg.env(**self.env(SLURM_JOB_ID=jid,SLURM_JOB_NAME=j['name'],SLURM_TMPDIR=tmp,SLURM_CPUS_PER_TASK=2,**x)))
        if check and cp.returncode:raise AssertionError(f'job {jid} {cmd[:3]}: {cp.returncode}\n{cp.stderr[-3000:]}\n{cp.stdout[-800:]}')
        return cp
    def plan(self,name:str,*args,check=True,role='plan'):
        """A raw plan job admitted by the fake, then slurm/plan.sh as its body."""
        run=self.site.run_dir(name);before={j['id']for j in self.site.jobs()}
        cp=self.site.submit(self.pkg,'raw','--role',role,'--dir',run,'--','-A','yun124','-p','shared','--nodes=1','-c','4','--mem=16G','-t','01:00:00',
                            '--wrap',f'{self.pkg}/slurm/plan.sh {run} '+' '.join(map(str,args)))
        assert cp.returncode==0,cp.stderr[-1500:]
        jid=self.newest(before)[0]['id']
        r=self.job_body(['bash',str(self.pkg/'slurm/plan.sh'),str(run),*map(str,args)],jid,check=check)
        self.site.fake.finish(jid,'COMPLETED' if r.returncode==0 else 'FAILED',elapsed=30)
        return run,r
    def lanes(self,run:Path,n:int=1,merge=True,**x):
        before={j['id']for j in self.site.jobs()}
        cp=self.site.submit(self.pkg,'lanes',str(n),C8_RUN=run);assert cp.returncode==0,cp.stderr[-2000:]
        new=self.newest(before);lanes=[j for j in new if j['name'].startswith('c8d3-lane-')];merges=[j for j in new if j['name'].startswith('c8d3-merge-')]
        assert len(lanes)==n and len(merges)==1,(n,[j['name']for j in new])
        for j in lanes:
            self.job_body([sys.executable,'-B',str(self.pkg/'tools/lanes.py'),'worker',str(run)],j['id'],C8_RUN=run,C8_LANES='2',**x)
            self.site.fake.finish(j['id'],'COMPLETED',elapsed=60)
        m=merges[0]['id'];out=None
        if merge:
            log=self.td/f'spy_{run.name}.log'
            out=self.job_body(['bash',str(self.pkg/'slurm/merge.sh')],m,C8_RUN=run,C8_BOOTSTRAP=64,PYTHONPATH=self.spy,C8_SPY_LOG=log)
            self.site.fake.finish(m,'COMPLETED',elapsed=20);out.spy=log.read_text()if log.exists()else''
        return out

def selection_digest(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def runbook_commands()->tuple[dict,str]:
    """The Stage-7 runbook's pilot-tool commands from the verbatim fixture: {'stage-a', 'confirm', 'full': the command a
    job's --wrap runs after "$JOB; ", 'count': the login-node line, 'pc_args': [the two PC_ARGS assignments]}, and where
    the fixture was checked against the approved PLAN (every fixture line must be a line of it), or why not."""
    text=RUNBOOK.read_text();plan=Path(os.environ.get('C8_PLAN_MD')or ROOT.parent/'LRI_C8_D3_HPC_loop/PLAN.md')
    if plan.is_file():
        lines=set(plan.read_text().splitlines());missing=[l for l in text.splitlines()if l.strip()and l not in lines]
        assert not missing,f'runbook fixture lines not in {plan}: {missing}'
        where=f'checked against {plan}'
    else:where=f'PLAN not reachable at {plan}: fixture only'
    cmds={'pc_args':[]}
    for line in text.replace('\\\n','').splitlines():   # bash removes backslash-newline inside double quotes
        if '--wrap "'in line:
            body=line.split('--wrap "',1)[1].rsplit('"',1)[0];assert body.startswith('$JOB; '),body;body=body[len('$JOB; '):]
            cmds[body.split()[3]]=body
        elif line.startswith('PC_N=$('):cmds['count']=line.split('#',1)[0].strip()
        elif line.startswith('PC_ARGS='):cmds['pc_args'].append(line.split('#',1)[0].strip())
    assert set(cmds)=={'stage-a','confirm','full','count','pc_args'}and len(cmds['pc_args'])==2,cmds
    return cmds,where

def pa_selection(P:Pipe,seed:int)->Path:
    """pilot_select stage-a on the synthetic L8 inventory. At this reduced scale no stratum holds the 16 stage-A graphs
    P1c needs (1/32 of a stratum's stratified part, rounded), so free L8 graphs 1 and 2 are made p1c (points 32,768, nest
    [4096]) in the file (relabelled, or added): the reduced-scale stand-in for P1c; pilot_select's own P1c rule is
    tested at full scale in tests/test_pilot_report.py (A-DES-4)."""
    P.tool('seeds.py','add','--seed',seed,'--label','pilot stage A','--log',P.seeds)
    f=P.td/'pa_selection.json';P.tool('pilot_select.py','stage-a','--seed',seed,'--cost-model',P.td/'M.json','--out',f,'--seeds-log',P.seeds,'--inputs',P.pkg/'inputs')
    doc=json.loads(f.read_text());rows=doc['groups']['free:8'];have={r['id']for r in rows}
    for g in (1,2):   # two P1c graphs (relabelled, or added when stage A did not draw them at this scale)
        if g in have:next(r for r in rows if r['id']==g).update(points=32768,nest=[4096],label='p1c')
        else:rows.append({'id':g,'points':32768,'nest':[4096],'label':'p1c'})
    if 3 not in have:rows.append({'id':3,'points':4096,'label':'stratified'})
    doc['groups']['free:8']=sorted(rows,key=lambda r:r['id']);doc['note']='tests/test_pipeline.py: two stratified graphs relabelled p1c (reduced scale)'
    f.unlink();f.write_text(json.dumps(doc,indent=1)+'\n');return f

def retable(run:Path,group:str,name:str,fn)->None:
    """Rewrite one merged table of a COPY and re-pin it in merged.json (so validate_merged passes and the subset
    comparison itself is what fails)."""
    sys.path.insert(0,str(ROOT/'tools'));from common import object_hash
    p=run/'groups'/group;lines=(p/f'{name}.csv').read_text().splitlines();new=fn(lines);(p/f'{name}.csv').unlink();(p/f'{name}.csv').write_text('\n'.join(new)+'\n')
    d=json.loads((p/'merged.json').read_text());key=f'{name}_sha256';d[key]=hashlib.sha256((p/f'{name}.csv').read_bytes()).hexdigest()
    if name=='graph_prefixes':d['prefix_rows']=len(new)-1
    d.pop('payload_sha256');d['payload_sha256']=object_hash(d);(p/'merged.json').unlink();(p/'merged.json').write_text(json.dumps(d,indent=2)+'\n')

def timing_remerge(P:Pipe,src:Path,dst:Path,group:str|None=None)->str:
    """S3-R2-009: a copy dst of the completed campaign src re-merged after a recovered index, timing only: the first
    checkpoint of its largest index (of `group`, when given) and its group's merged.json deleted, the index recomputed with other row seconds
    (C8_FAKE_SPP_FILE), production.py merge. The scientific tables stay byte for byte, graph_costs.csv and merged.json
    change (reported "timing only"). Returns the group."""
    import production as prod
    shutil.copytree(src,dst);m=json.loads((dst/'manifest.json').read_text());j=max((j for j in m['jobs']if group in(None,j['group'])),key=lambda j:(j['blocks'],-j['id']))
    g=dst/'groups'/j['group']
    sci=('graph_replicates.csv','graph_tails.csv','graph_promotions.csv')+(('graph_prefixes.csv',)if (g/'graph_prefixes.csv').exists()else())
    saved={f:(g/f).read_bytes()for f in (*sci,'graph_costs.csv','merged.json')};(g/'checkpoints'/f'{prod.block_name(j["shard"],0)}.json').unlink();(g/'merged.json').unlink()
    spp=P.td/'spp_slow.json';spp.write_text(json.dumps({f'{L}:{x}':0.0015 for L in range(3,9)for x in range(256)}))
    P.tool('production.py','run',dst,'--index',j['id'],'--threads',2,'--scratch',P.scr,C8_FAKE_SPP_FILE=spp)
    out=P.tool('production.py','merge',dst,'--scratch',P.scr).stdout
    assert f'{j["group"]}: replaced the uncommitted graph_costs.csv'in out and 'timing only'in out and 'SCIENTIFIC'not in out,out[-800:]
    assert all((g/f).read_bytes()==saved[f]for f in sci)and (g/'graph_costs.csv').read_bytes()!=saved['graph_costs.csv']and (g/'merged.json').read_bytes()!=saved['merged.json']
    return j['group']

def f39_su_per_hour(j:dict)->float:
    """F39 by hand: 128 per node on compute; max(CPUs, ceil(mem_GiB/2)) on shared and debug (the fake's mem is MiB)."""
    return 128.*j['nodes']if j['partition']=='compute'else float(max(j['cpus'],math.ceil(j['mem']/2048-1e-9)))

def accounting_checks(P:Pipe,run:Path)->float:
    """A-ORC-9 (fakes): tools/accounting.py on a real fake campaign equals the hand sum of the billing value x
    ElapsedRaw/3600 over every sacct -X --duplicates attempt of its jobs (the fake prints F39's AllocTRES strings), with a
    requeued lane attempt and one c8d3- lane job of the campaign that has no ledger record; eta_node equals the hand
    ratio of allocated work core-seconds to the checkpoint rows' busy seconds; every attempt's alloc_cpus is its AllocTRES
    cpu; a checkpoint naming a job id that sacct does not show refuses (69, "allocation unknown"). Returns the hand eta_node."""
    import budget,ledger
    from fake_slurm.core import FINISHED
    C=ledger.dir_sha12(run);now=P.site.fake.now();named=set();busy=0.
    for f in sorted((run/'groups').glob('*/checkpoints/*.json')):
        d=json.loads(f.read_text());sl=d['runtime']['fingerprint']['slurm'];named.add(sl.get('SLURM_ARRAY_JOB_ID')or sl['SLURM_JOB_ID'])
        busy+=sum(float(r['seconds'])for r in d['native']['rows'])
    worker=next(j for j in P.site.jobs()if j['name'].startswith(f'c8d3-lane-{C}-')and j['id']in named)
    P.site.fake.requeue(worker['id'],'NODE_FAIL',elapsed=45)                                   # attempt 1: NODE_FAIL after 45 s
    P.site.fake.set(worker['id'],state='COMPLETED',start=now-50,end=now,elapsed=50)            # attempt 2: completed after 50 s
    ghost=f'c8d3-lane-{C}-{"e"*12}'
    P.site.fake.add_job(ghost,state='COMPLETED',partition='shared',cpus=4,mem='12G',elapsed=100,start_ago=150,end_ago=50,submit_ago=200)
    led=[json.loads(l)['rec']for l in (P.site.root/'ledger.jsonl').read_text().splitlines()if l.strip()]
    assert not any(ghost in json.dumps(r)for r in led)
    hand=0.;work=0.;attempts=0
    for j in P.site.jobs():
        if not j['name'].startswith('c8d3-')or budget.name_info(j['name'])['c']!=C:continue
        for a in j['attempts']+[{'state':j['state'],'elapsed':j['elapsed']}]:
            if a['state']not in FINISHED:continue
            attempts+=1;hand+=f39_su_per_hour(j)*a['elapsed']/3600
            if budget.name_info(j['name'])['role']=='lane':work+=(128*j['nodes']if j['partition']=='compute'else j['cpus'])*a['elapsed']
    r=json.loads(P.tool('accounting.py',run,'--json').stdout);eta=work/busy
    assert abs(r['su_total']-hand)<=1e-9*hand and len(r['attempts'])==attempts and abs(r['eta_node']-eta)<=1e-9*eta,(r['su_total'],hand,len(r['attempts']),attempts,r['eta_node'],eta)
    assert sorted(a['state']for a in r['attempts']if a['job']==worker['id'])==['COMPLETED','NODE_FAIL']and any(a['name']==ghost for a in r['attempts'])
    assert abs(next(a['su']for a in r['attempts']if a['name']==ghost)-6*100/3600)<=1e-12   # cpu=4,mem=12G: 6 core-equivalents
    byname={j['name']:j for j in P.site.jobs()}   # each attempt's allocated CPUs, sacct's AllocTRES cpu (thru_report's busy denominator)
    assert all(a['alloc_cpus']==(128*byname[a['name']]['nodes']if byname[a['name']]['partition']=='compute'else byname[a['name']]['cpus'])for a in r['attempts'])and \
        next(a['alloc_cpus']for a in r['attempts']if a['name']==ghost)==4,[(a['name'],a.get('alloc_cpus'))for a in r['attempts']]
    P.site.fake.set(worker['id'],no_record=True)                                               # sacct no longer shows the worker
    cp=P.tool('accounting.py',run,'--json',check=False);P.site.fake.set(worker['id'],no_record=False)
    assert cp.returncode==69 and 'allocation unknown'in cp.stderr and worker['id']in cp.stderr,(cp.returncode,cp.stderr[-500:])
    ok('A-ORC-9 (fakes): accounting.py equals the hand sum of the F39 billing value x ElapsedRaw/3600 over every sacct -X --duplicates attempt '
       '(%d attempts: a requeued lane worker NODE_FAIL + COMPLETED, a c8d3- lane job without a ledger record at cpu=4,mem=12G = 6 SU/h) = %.6f SU; '
       'eta_node = allocated work core-seconds / busy seconds = %.4f by hand; a checkpoint naming a job id sacct does not show refuses (69, '
       '"allocation unknown")'%(attempts,hand,eta),su=hand,eta_node=eta)
    return eta

def hand_lane(est:float,n:int,w:int,H:float)->float:
    """D.10 by hand: T = ceil(max(1.5 W + 900, need + 900)/900) x 900 s, W = est/(n x 128 x 0.9), need the largest index's
    est/(w x 0.9) x 1.5 + 300 with indices of at most H x 3600 x w x 0.9 core-seconds."""
    k=max(1,math.ceil(est/(H*3600*w*0.9)));need=est/k/(w*0.9)*1.5+300;W=est/(n*128*0.9)
    return min(math.ceil(max(1.5*W+900,need+900)/900)*900,47*3600+1800)

def stage_a_checks(P:Pipe,pa:Path,td:Path,cmds:dict,where:str,E:Path)->None:
    """A-PIL-2 on the fake PA. The runbook's stage-a line (verbatim) with C8_BUDGET_LINE=pilot and C8_PILOT_SU_CAP=1300 (eta
    from tools/accounting.py, the committed SU from tools/budget.py, both on the fake Slurm) gives GO with every A-PIL-2
    field, and its re-projection equals a hand computation from PA's measured model (PF busy hours per branch, the auto
    lane time, the reservations and the peaks). NO-GO, each with its reason: a copy with one injected mp_alarm
    (graph_promotions.csv re-pinned), a copy with one lane failure record, a line below every branch's peak, a line
    that only the R = 8 branch fits, and no line at all (not evaluated)."""
    P.runbook(cmds['stage-a'],E,C8_BUDGET_LINE='pilot',C8_PILOT_SU_CAP=1300)
    r=json.loads((E/'stageA.json').read_text())
    assert r['go']=='GO'and r['go_reasons']==[],r['go_reasons']
    for k in ('histograms','screen','p1c','action4','alpha','efficiency','queue_latency','failures','reprojection'):assert r.get(k)is not None,k
    assert r['histograms']['mp_alarm_total']==0 and r['failures']['count']==0 and r['failures']['scheduler_evaluated']and 'work'in r['queue_latency']
    eff=r['efficiency'];assert eff['f_E']>0 and eff['eta_allocated_over_busy']>0 and 'accounting'in eff['eta_source']
    assert r['alpha']['bootstrap_unit'].startswith('graph')and ('free',3)not in {(x['sector'],x['graph'])for x in r['screen']['flagged']}
    rp=r['reprojection'];assert rp['evaluated']and rp['cap_su']==1300 and set(rp['branches'])>={'PF R=8','PF R=16 at L8'},rp
    m=json.loads((pa/'manifest.json').read_text());model=json.loads((pa/'cost_model.json').read_text())['seconds_per_point']
    inv=json.loads((P.pkg/'inputs/inventory.json').read_text());f=eff['f_E'];eta=eff['eta_allocated_over_busy'];mpf=float(m['mp_check_factor']);w=int(m['threads'])
    meas=sum(float(l.split(',')[2])for g in m['groups']for l in (pa/'groups'/g['name']/'graph_costs.csv').read_text().splitlines()[1:])
    pred=sum(float(model[f'{c["campaign"]}:{c["sector"]}:8:{l.split(",")[0]}'])*int(l.split(',')[1])*mpf
             for g in m['groups']for c in [json.loads((pa/'groups'/g['name']/'config.json').read_text())]for l in (pa/'groups'/g['name']/'graph_costs.csv').read_text().splitlines()[1:])
    assert abs(f-meas/pred)<=1e-12*f,(f,meas/pred)
    peaks={}
    for name,R8 in (('PF R=8',8),('PF R=16 at L8',16)):
        busy=sum(float(model[f'{t}:{s}:{L}:{g["id"]}'])*4096*(R8 if L=='8'else 8)*mpf for s in ('free','power')for L,rows in inv[s].items()for g in rows for t in 'ab')
        busy8=sum(float(model[f'{t}:{s}:8:{g["id"]}'])*4096*R8*mpf for s in ('free','power')for g in inv[s]['8']for t in 'ab')
        b=rp['branches'][name];T=hand_lane(max(busy,f*busy),4,w,0.25);Tc=hand_lane(max(.25*f*busy8,f*.25*f*busy8),2,w,0.25)
        assert abs(b['pf']['busy_core_hours_model']-busy/3600)<=1e-9*busy/3600 and abs(b['pf']['lane_reservation_su']-4*128*T/3600)<=1e-9,(b['pf'],T)
        assert abs(b['pc']['lane_reservation_su']-2*128*Tc/3600)<=1e-9 and abs(b['pf']['lane_expected_su']-f*busy*eta/3600)<=1e-9*(1+f*busy*eta/3600)
        S0=rp['committed_su'];st={x['step']:x for x in b['steps']}
        pf_peak=S0+8+max(4*128*T/3600,f*busy*eta/3600)+48     # PF plan (8 cores, 16G, 1 h) spent, then 4 lanes + the 2-h 24-core merge
        assert abs(st['PF lanes + merge']['peak_su']-pf_peak)<=1e-9,(st,pf_peak)
        assert abs(b['peak_su']-max(x['peak_su']for x in b['steps']))<=1e-12 and b['within_line']is True;peaks[name]=b['peak_su']
    # NO-GO: an injected mp_alarm (one point of one graph), a worker failure record, a line below the peaks, no line
    opts=['--eta-node',0.9,'--spent',0]
    d=td/'pa_alarm';shutil.copytree(pa,d)
    def alarm(L):
        h=L[0].split(',');i=h.index('mp_alarm');x=L[1].split(',');x[i]=str(int(x[i])+1);return [L[0],','.join(x)]+L[2:]
    retable(d,'a_free_L8','graph_promotions',alarm)
    r1=json.loads(P.tool('pilot_report.py','stage-a',d,'--output',td/'sa_alarm.json','--line-cap',100000,*opts).stdout)
    # the copied campaign's job ids are unknown to the fake sacct, so the failure check is also not evaluated (a reason of its own)
    assert r1['go']=='NO-GO'and r1['go_reasons'][0].startswith('MP self-check alarm: 1 alarmed')and all(x.startswith('worker failures not evaluated')for x in r1['go_reasons'][1:]),r1
    d=td/'pa_fail';shutil.copytree(pa,d);(d/'lanes/failures').mkdir(parents=True,exist_ok=True)
    (d/'lanes/failures/0.123.0.0.1.json').write_text(json.dumps({'index':0,'exit_code':1}))
    r2=json.loads(P.tool('pilot_report.py','stage-a',d,'--output',td/'sa_fail.json','--line-cap',100000,*opts).stdout)
    assert r2['go']=='NO-GO'and r2['go_reasons'][0].startswith('worker failure: 1 failure records')and all(x.startswith('worker failures not evaluated')for x in r2['go_reasons'][1:]),r2
    # --eta-node with the accounting refusing (a copy whose job ids sacct does not show): NO-GO, the failure check is not evaluated
    d=td/'pa_noacct';shutil.copytree(pa,d)
    r6=json.loads(P.tool('pilot_report.py','stage-a',d,'--output',td/'sa_noacct.json','--line-cap',100000,*opts).stdout)
    assert r6['go']=='NO-GO'and len(r6['go_reasons'])==1 and r6['go_reasons'][0].startswith('worker failures not evaluated'),r6
    r3=json.loads(P.tool('pilot_report.py','stage-a',pa,'--output',td/'sa_line.json','--line-cap',min(peaks.values())/2,*opts).stdout)
    assert r3['go']=='NO-GO'and sum('exceeds the pilot line'in x for x in r3['go_reasons'])==len(json.loads((td/'sa_line.json').read_text())['reprojection']['branches']),r3
    r0=json.loads(P.tool('pilot_report.py','stage-a',pa,'--output',td/'sa_ok.json','--line-cap',100000,*opts).stdout);assert r0['go']=='GO',r0
    sa0=json.loads((td/'sa_ok.json').read_text());p8=sa0['reprojection']['branches']['PF R=8']['peak_su'];p16=sa0['reprojection']['branches']['PF R=16 at L8']['peak_su']
    if p16>p8+1e-6:   # a line that only the R = 8 branch fits: the R = 16 branch alone stops the pilot
        r4=json.loads(P.tool('pilot_report.py','stage-a',pa,'--output',td/'sa_r16.json','--line-cap',(p8+p16)/2,*opts).stdout)
        assert r4['go']=='NO-GO'and all('PF R=16'in x for x in r4['go_reasons']),r4
    r5=json.loads(P.tool('pilot_report.py','stage-a',pa,'--output',td/'sa_noline.json','--eta-node',0.9).stdout)
    assert r5['go']=='NO-GO'and any('not evaluated'in x for x in r5['go_reasons']),r5
    ok('A-PIL-2 (fakes): the runbook\'s stage-a line (verbatim; %s) gives GO on the PA with the MP histogram, the screen, P1c, action 4, alpha '
       '(graph bootstrap), eta from the accounting, f_E = measured/model busy (hand), queue latency, the failure check and the re-projection of '
       'PF R = 8 and R = 16 (busy hours, auto lane time, reservations and peaks equal the hand values; peaks %.1f / %.1f SU, line 1,300); '
       'NO-GO on an injected mp_alarm and on a lane failure record; NO-GO when --eta-node is given but the accounting refuses (failures not '
       'evaluated); NO-GO naming every branch below its peak; NO-GO "not evaluated" without a pilot line'%(where,peaks['PF R=8'],peaks['PF R=16 at L8']),peaks=peaks)

def run_all(P:Pipe,run:Path):
    for j in json.loads((run/'manifest.json').read_text())['jobs']:P.tool('production.py','run',run,'--index',j['id'],'--threads',2,'--scratch',P.scr)

def main(keep=False)->dict:
    td=Path(tempfile.mkdtemp(prefix='c8d3_pipe_'));t0=time.time()
    try:
        P=Pipe(td);base=['--forbid-seeds-from',P.seeds,'--threads',2,'--index-hours',0.25]
        # 1. the sweep and the first measured model (D.14, HC7)
        before={j['id']for j in P.site.jobs()}
        cp=P.site.submit(P.pkg,'raw','--role','sweep','--dir',P.site.run_dir('sweep1'),'--','-A','yun124','-p','debug','-c','2','--mem=4G','-t','00:30:00','--wrap','sweep');assert cp.returncode==0,cp.stderr
        jid=P.newest(before)[0]['id']
        P.job_body([sys.executable,'-B',str(P.pkg/'tools/sweep.py'),str(P.site.run_dir('sweep1')),'--seed','91000001','--output',str(td/'M.json'),'--threads','2'],jid)
        P.site.fake.finish(jid,'COMPLETED',elapsed=60)
        M=json.loads((td/'M.json').read_text());assert M['measured']and M['scheduled_with']['basis']=='bootstrap'and len(M['seconds_per_point'])==2*sum(sum(v.values())for v in COUNTS.values())
        sw=json.loads((P.site.run_dir('sweep1')/'manifest.json').read_text());assert sw['plan_role']=='cost_sweep'and sw['cost_basis']=='bootstrap'and sw['campaign_role']=='test'
        reg=[json.loads(l)for l in (P.site.root/'ledger.jsonl').read_text().splitlines()]
        assert any(r['rec']['kind']=='register'and r['rec']['role']=='sweep'for r in reg)
        ok('sweep: a cost_sweep on the bootstrap basis, registered in the ledger, gives the first measured model (scheduled_with bootstrap)')
        common=[*base,'--cost-model',td/'M.json']
        # 2. PA
        pa_sel=pa_selection(P,92000001)
        pa,_=P.plan(f'pilotA-{DATE}','--seed',93000001,'--pilot','--graphs',pa_sel,*common)
        m=json.loads((pa/'manifest.json').read_text())
        assert m['campaign_role']=='pilot_subset'and not m['test_only']and m['plan_role']=='campaign'and m['cost_basis']=='measured'
        assert sorted(g['name']for g in m['groups'])==['a_free_L8','a_power_L8','b_free_L8','b_power_L8']and m['selection']['role']=='stage_a'
        out=P.lanes(pa,1)
        assert (pa/'subset_summary.json').exists()and not list(pa.glob('C8_*result.json')),list(pa.iterdir())
        assert 'assemble.py'not in out.spy and 'order8_assembly'not in out.spy and 'pilot_report.py subset-check'in out.spy,out.spy[-800:]
        sa=json.loads(P.tool('pilot_report.py','stage-a',pa,'--out',td/'stage_a.json').stdout)   # --out: the old spelling, an alias of --output
        sa=json.loads((td/'stage_a.json').read_text());assert sa['p1c']['graphs']==2 and set(sa['action4'])=={'free','power'}
        ok('A-DES-7 (a): PA plans exactly the four L8 groups as pilot_subset; its merge job runs subset-check, writes subset_summary.json, '
           'no C8_*result.json; neither assemble.py nor the vendored assembly runs (spy); pilot_report stage-a accepts it')
        cmds,where=runbook_commands();E=td/'evidence';E.mkdir()
        stage_a_checks(P,pa,td,cmds,where,E)
        # 3. PF
        pf,_=P.plan(f'pilotF-{DATE}','--seed',93000002,'--pilot',*common)
        mf=json.loads((pf/'manifest.json').read_text());assert mf['campaign_role']=='pilot_full'and len(mf['groups'])==24
        P.lanes(pf,2)
        res=json.loads((pf/'C8_pilot_result.json').read_text());assert res['label']=='pilot'and res['final']is False and res['C8_full']is None and res['sizing_only']['C8_full']is not None
        import assemble as asm,production as prod
        cfgs={}
        for g in mf['groups']:
            c=json.loads((pf/'groups'/g['name']/'config.json').read_text());cfgs[(c['campaign'],c['sector'],c['L'])]=c
        inv=json.loads((P.pkg/'inputs/inventory.json').read_text());asm.coverage_guard(mf,cfgs,inv)
        def refuses(mod):
            c2={k:json.loads(json.dumps(v))for k,v in cfgs.items()};m2=json.loads(json.dumps(mf));mod(c2,m2)
            try:asm.coverage_guard(m2,c2,inv);return False
            except ValueError:return True
        k8=('a','free',8)
        assert refuses(lambda c,m:c[k8]['counts'].pop(next(iter(c[k8]['counts']))))   # a missing inventory graph
        assert refuses(lambda c,m:c.pop(('b','power',5)))                              # a missing group
        assert refuses(lambda c,m:c[k8]['counts'].update({next(iter(c[k8]['counts'])):8192}))   # one graph at 8,192 points
        assert refuses(lambda c,m:c[('a','free',4)].update(replicates=16))               # another replicate count
        cp_dir=td/'pf_copy';shutil.copytree(pf,cp_dir);(cp_dir/'groups/a_free_L3/merged.json').unlink()
        assert P.tool('assemble.py',cp_dir,check=False).returncode!=0
        ok('A-DES-7 (d): --pilot without --graphs is pilot_full; its merge assembles C8_pilot_result.json labelled pilot (values only under '
           'sizing_only); the coverage guard refuses a missing graph, a missing group, a graph at 8,192 points and another replicate count')
        eta_hand=accounting_checks(P,pf)
        # 4. the runbook's confirm and count lines (verbatim) -> PC -> the runbook's full line (verbatim)
        P.tool('pilot_report.py','screen','--pf',pf,'--pa',pa,'--out',td/'screen.json')
        scr=json.loads((td/'screen.json').read_text());flagged={(x['sector'],x['graph'])for x in scr['flagged']}
        zch={(x['sector'],x['graph'])for x in scr['zero_channel_heavy_tail']}
        assert ('free',5)in flagged and not any(g==3 for _,g in flagged),scr['flagged']   # graph 3: heavy but a zero channel
        assert ('free',3)in zch and all(x['status']==ZC_NOTE for x in scr['zero_channel_heavy_tail']),scr['zero_channel_heavy_tail']
        assert scr['pf_identity']['manifest_sha256']==selection_digest(pf/'manifest.json')and scr['pa_identity']['manifest_sha256']==selection_digest(pa/'manifest.json')
        assert scr['pf_identity']['merged_sha256']=={g['name']:selection_digest(pf/'groups'/g['name']/'merged.json')for g in mf['groups']}and scr['pa_identity']['campaign_role']=='pilot_subset'
        assert set(scr['pf_identity']['science_sha256'])=={g['name']for g in mf['groups']}and all(asm.science_ok(x)for x in scr['pf_identity']['science_sha256'].values())   # S3-R2-009
        P.tool('seeds.py','add','--seed',92000002,'--label','pilot confirm','--log',P.seeds)
        P.runbook(cmds['confirm'],E,seed=92000002)                                         # --screen PF --pa PA (the screen computed inside)
        pc_sel=E/'pc.json';pcs=json.loads(pc_sel.read_text());sel_ids={(k.split(':')[0],r['id'])for k,v in pcs['groups'].items()for r in v}
        assert pcs['role']=='confirm'and pcs['groups']and all(r['points']==32768 and r['nest']==[4096]for v in pcs['groups'].values()for r in v)
        assert ('free',5)in sel_ids and sel_ids<=flagged and not any(g==3 for _,g in sel_ids),sel_ids   # never a zero-channel graph
        assert pcs['screen']['flagged']==scr['flagged']and pcs['screen']['pf']==str(pf.resolve())and ('free',3)in {(x['sector'],x['graph'])for x in pcs['zero_channel']['heavy_tail']}
        P.tool('pilot_select.py','confirm','--screen',td/'screen.json','--seed',92000002,'--cost-model',td/'M.json','--pf',pf,'--out',td/'pc_sel_old.json','--seeds-log',P.seeds,'--inputs',P.pkg/'inputs')
        assert json.loads((td/'pc_sel_old.json').read_text())['groups']==pcs['groups']                # the old form: the same selection
        assert pcs['screen']['pf_identity']==scr['pf_identity']and pcs['screen']['pa_identity']==scr['pa_identity']and pcs['pricing']['mp_check_factor']==1.0
        # S3-005: a screen file of another PF (one scientific identity of its PF changed, S3-R2-009), of another PA (with --pa), or without
        # identities (or without scientific identities: an older screen) is refused
        for tag,mod in (('pf',lambda d:d['pf_identity']['science_sha256']['a_free_L3'].__setitem__('graph_tails.csv','0'*64)),('pa',lambda d:d['pa_identity'].__setitem__('manifest_sha256','0'*64)),
                        ('none',lambda d:d.pop('pf_identity')),('noscience',lambda d:d['pf_identity'].pop('science_sha256'))):
            x=json.loads(json.dumps(scr));mod(x);f=td/f'screen_{tag}.json';f.write_text(json.dumps(x))
            cp=P.tool('pilot_select.py','confirm','--screen',f,'--seed',92000002,'--cost-model',td/'M.json','--pf',pf,'--pa',pa,'--out',td/f'pc_bad_{tag}.json','--seeds-log',P.seeds,
                      '--inputs',P.pkg/'inputs',check=False)
            assert cp.returncode==1 and ('another campaign'in cp.stderr or 'no recorded campaign identity'in cp.stderr or 'no recorded scientific identity'in cp.stderr)\
                and not (td/f'pc_bad_{tag}.json').exists(),(tag,cp.returncode,cp.stderr[-500:])
        # S3-R2-009: a screen whose PF identity differs only in a merged.json sha256 (a timing-only re-merge) still names PF
        x=json.loads(json.dumps(scr));x['pf_identity']['merged_sha256']['a_free_L3']='0'*64;(td/'screen_tm.json').write_text(json.dumps(x))
        P.tool('pilot_select.py','confirm','--screen',td/'screen_tm.json','--seed',92000002,'--cost-model',td/'M.json','--pf',pf,'--pa',pa,'--out',td/'pc_sel_tm.json','--seeds-log',P.seeds,'--inputs',P.pkg/'inputs')
        assert json.loads((td/'pc_sel_tm.json').read_text())['groups']==pcs['groups']
        npc=P.runbook(cmds['count']+'; echo "$PC_N"',E).stdout.strip();assert npc==str(len(sel_ids)),npc
        # S3-R2-001: the PC planner prices what it will run: the selection (priced at 8 replicates) at more replicates, for every
        # group or for its dearer sector alone, exceeds the cap and is refused before anything is created (before: planned)
        Mspp=json.loads((td/'M.json').read_text())['seconds_per_point'];cap=pcs['cap']
        sec={k.split(':')[0]:sum((Mspp[f'a:{k}:{r["id"]}']+Mspp[f'b:{k}:{r["id"]}'])*32768*8 for r in v)for k,v in pcs['groups'].items()}
        assert abs(sum(sec.values())-cap['used_seconds'])<=1e-9*cap['used_seconds']and cap['used_seconds']<=cap['cap_seconds'],(sec,cap)
        dear=max(sec,key=sec.get);Rg=8*(math.ceil(cap['cap_seconds']/sec[dear])+1);Rall=8*(math.ceil(cap['cap_seconds']/cap['used_seconds'])+1)
        for tag,args in (('replicates',['--replicates',Rall]),('group',['--group-replicates',f'{dear}:8={Rg}'])):   # as the PC plan job runs (slurm/plan.sh)
            run_x,cp=P.plan(f'pc_over_{tag}','--seed',93000011,'--pilot','--graphs',pc_sel,*args,*common,check=False)
            assert cp.returncode!=0 and 'selection\'s cap'in cp.stderr and 'S3-R2-001'in cp.stderr and not run_x.exists(),(tag,cp.returncode,cp.stderr[-800:])
        ok('S3-R2-001: the PC selection (priced at 8 replicates, %.4g of %.4g s) planned at %d replicates, or with --group-replicates %s:8=%d, costs more '
           'than its cap and is refused before anything is created'%(cap['used_seconds'],cap['cap_seconds'],Rall,dear,Rg))
        pc,_=P.plan(f'pilotC-{DATE}','--seed',93000003,'--pilot','--graphs',pc_sel,*common)
        assert json.loads((pc/'manifest.json').read_text())['campaign_role']=='pilot_subset'and len(json.loads((pc/'manifest.json').read_text())['groups'])==2*len(pcs['groups'])
        P.lanes(pc,1);assert (pc/'subset_summary.json').exists()
        P.runbook(cmds['pc_args'][0]+'; '+cmds['full'],E)                                  # eta from the accounting
        rep=json.loads((E/'pilot_report.json').read_text());md=(E/'PILOT_REPORT.md').read_text()
        assert md.startswith('# C8(3) pilot report')and 'Cost vs precision'in md and 'Decisions for the user'in md and (E/'sigma_cost.csv').exists()
        conf={(x['sector'],x['graph'])for x in rep['action2_confirm']['possible_infinite_variance']}
        assert conf and conf==sel_ids and pcs['cap']['used_seconds']<=pcs['cap']['cap_seconds'],(rep['action2_confirm'],pcs['cap'])
        assert rep['cost_table']['rows']and all(r['allocated_su']>0 for r in rep['cost_table']['rows']if r.get('SE'))and (E/'growth_c63d.csv').exists()
        assert all(r['band']['allocated_su'][0]<=r['allocated_su']<=r['band']['allocated_su'][1]for r in rep['cost_table']['rows']if r.get('SE'))
        assert abs(rep['cost_table']['eta_allocated_over_busy']-eta_hand)<=1e-9*eta_hand,(rep['cost_table']['eta_allocated_over_busy'],eta_hand)
        assert all(isinstance(v,dict)for v in rep['cost_table']['queue_latency'].values())and set(rep['cost_table']['queue_latency'])=={'PA','PF','PC'}
        st=rep['cost_table']['site'];assert st['site']=='expanse'and st['allocated_cpus_per_node']==128 and st['target_cpu']is None and not st['cost_scaled']and 'Target site expanse'in md,st
        assert rep['pf_result']['bound_to']['manifest_sha256']==selection_digest(pf/'manifest.json')
        zr={(x['sector'],x['graph'])for x in rep['zero_channel_heavy_tail']['graphs']};assert ('free',3)in zr,zr
        assert not any(x['graph']==3 for x in rep['action1_screen']['flagged'])
        # the heavy L7 graph 2 (both sectors): a diagnostic (item 2) and in no action's output (actions 1-5 act on L8 only)
        l7=[x for x in rep['tails']['per_graph']if x['L']==7 and x['graph']==2]
        assert len(l7)==4 and all(x['xi']>0.38 for x in l7),l7
        assert {x['graph']for x in rep['action1_screen']['flagged']}<={5}and not any(x['graph']==2 for x in scr['flagged'])
        assert all(k.startswith(('free|T','power|T'))for k in rep['action5']['strata'])and set(rep['action3_hold'])<={'free','power'}
        assert all(x['graph']==5 for x in rep['action2_confirm']['confirmations']+rep['action2b']['p1c']['confirmations']if x.get('confirmed'))
        ok('A-DES-7 (b), A-PIL-5: the screen flags the heavy-tailed L8 graph 5 and reports the heavy zero-channel graph 3 as "zero-channel heavy tail, '
           'not confirmed"; the runbook\'s confirm line (--screen PF --pa PA, verbatim; %s) writes a non-empty PC without graph 3, the same selection as '
           'the old --screen FILE --pf form; its count line prints the graph count; PC plans 2 groups per sector as pilot_subset, merges through '
           'subset-check; the runbook\'s full line (verbatim) writes pilot_report.json, PILOT_REPORT.md, growth_c63d.csv and sigma_cost.csv, confirms '
           'the PC graphs (within 25%% of PF\'s L8 cost), takes eta from tools/accounting.py (the hand ratio) and queue latency per step, every SU '
           'inside its row band; the heavy L7 graph is a diagnostic (xi > 0.38 in item 2) and in no action\'s output (A-DES-3: L8 only)'%where,
           confirmed=sorted(conf))
        # S3-R2-009: a timing-only re-merge of PA and of PF after the completed chain (copies); full on the same PC selection and PC
        pa_rm,pf_rm=td/'pa_rm',td/'pf_rm';ga=timing_remerge(P,pa,pa_rm);gf=timing_remerge(P,pf,pf_rm,'a_free_L8')   # PF: an L8 group, so PF's L8 row seconds change
        assert 'superseded: only timing digests changed'in P.tool('pilot_report.py','subset-check',pa_rm).stdout
        assert 'superseded: scientific content unchanged'in P.tool('assemble.py',pf_rm,'--bootstrap',64).stdout
        reps={}
        for tag,(A_,F_) in {'pa':(pa_rm,pf),'pf':(pa,pf_rm),'both':(pa_rm,pf_rm)}.items():
            P.tool('pilot_report.py','full','--pa',A_,'--pf',F_,'--pc-selection',pc_sel,'--pc',pc,'--out',td/f'r_rm_{tag}','--eta-node',0.9);reps[tag]=json.loads((td/f'r_rm_{tag}/pilot_report.json').read_text())
        r0=reps['pa'];assert {(x['sector'],x['graph'])for x in r0['action2_confirm']['possible_infinite_variance']}==conf and r0['pc_cap']['within_cap_at_current']is True
        pcc=reps['pf']['pc_cap'];assert pcc['recorded_pf_l8_seconds']==cap['pf_l8_seconds']and pcc['current_pf_l8_seconds']>cap['pf_l8_seconds']and pcc['within_cap_at_current']is True,(pcc,gf)
        # ... and a scientific change (a tail_sum of graph_tails.csv, re-pinned in merged.json) of PA or PF is still refused
        def tails2(L):
            h=L[0].split(',');i=h.index('tail_sum');x=L[1].split(',');x[i]=repr(2*float(x[i])+1.);return [L[0],','.join(x)]+L[2:]
        for tag,src in (('pa',pa),('pf',pf)):
            d=td/f'{tag}_sci';shutil.copytree(src,d);retable(d,'a_free_L8','graph_tails',tails2)
            args=['--pa',d,'--pf',pf]if tag=='pa'else['--pa',pa,'--pf',d]
            cp=P.tool('pilot_report.py','full',*args,'--pc-selection',pc_sel,'--pc',pc,'--out',td/f'r_sci_{tag}','--eta-node',0.9,check=False)
            assert cp.returncode==1 and 'another campaign'in cp.stderr and 'science_sha256'in cp.stderr,(tag,cp.returncode,cp.stderr[-600:])
        ok('S3-R2-009: after the completed PA/PF/PC chain, a timing-only re-merge of PA (%s) and of PF (%s) (copies; the index recomputed with other row '
           'seconds; subset-check and assemble supersede) leaves full working on the same PC selection and PC, for PA, PF and both re-merged; the '
           'report records the PC cap against PF\'s current L8 row seconds; a scientific change of a PA or PF table (tail_sum, re-pinned) is refused '
           '("another campaign", science_sha256)'%(ga,gf))
        # 5. the empty-PC branch (the runbook's skip branch: PC_ARGS without --pc)
        empty={**scr,'flagged':[],'p1c_unscreened_confirmed':[]};(td/'screen_empty.json').write_text(json.dumps(empty))
        P.tool('seeds.py','add','--seed',92000003,'--label','pilot confirm (empty)','--log',P.seeds)
        P.tool('pilot_select.py','confirm','--screen',td/'screen_empty.json','--seed',92000003,'--cost-model',td/'M.json','--pf',pf,'--out',td/'pc_empty.json','--seeds-log',P.seeds,'--inputs',P.pkg/'inputs')
        pe=json.loads((td/'pc_empty.json').read_text());assert pe['groups']=={}and 'no L8 graph screened (0 of'in pe['empty_reason']and '0 of'in pe['empty_reason'].split('and')[1]
        assert P.tool('pilot_select.py','count',td/'pc_empty.json').stdout.strip()=='0'
        run_e=P.site.run_dir('pc_empty');before=set(os.listdir(P.site.root/'runs'))
        cp=P.tool('production.py','plan',run_e,'--seed',93000004,'--pilot','--graphs',td/'pc_empty.json',*common,'--reserve-seed',P.seeds,'--scratch',P.scr,check=False)
        assert cp.returncode==65 and 'empty selection'in cp.stderr and set(os.listdir(P.site.root/'runs'))==before and not list(P.site.root.rglob('*.tmp.*')),cp.stderr
        assert not any(p.suffix=='.sqlite'for p in (P.site.root/'runs').rglob('*')if 'pc_empty'in str(p))
        E2=td/'evidence_empty';E2.mkdir();shutil.copy2(td/'pc_empty.json',E2/'pc.json')
        P.runbook(cmds['pc_args'][1]+'; '+cmds['full'],E2)
        rep2=json.loads((E2/'pilot_report.json').read_text());assert rep2['pc']is None and rep2['pc_note'].startswith('PC: no graph selected (no L8 graph screened')
        assert 'PC: no graph selected'in (E2/'PILOT_REPORT.md').read_text()
        ok('A-DES-7 (c): confirm on no flag and no unscreened confirmation writes "groups": {} with its empty_reason (both counts); count prints 0; '
           'plan --graphs exits 65 "empty selection" creating no campaign directory and no SQLite file; the runbook\'s skip branch (PC_ARGS with '
           '--pc-selection alone, verbatim) succeeds and records the reason in pilot_report.json and PILOT_REPORT.md')
        # 6. refusals
        for tool,args in (('assemble.py',[pa]),('combine.py',[pa,'--output',td/'cmb_pa']),('report.py',[pa,'--output',td/'rep_pa.json']),('verify_result.py',[pa]),
                          ('design_fallback.py',['freeze','--pilot',pa,'--cost-model',td/'M.json','--out',td/'b_pa','--test-only','--eta-node','0.9','--target-se','1']),
                          ('design_adapter.py',['view',pa,'--out',td/'v_pa'])):
            cp=P.tool(tool,*args,check=False);assert cp.returncode==65 and 'subset-check'in cp.stderr,(tool,cp.returncode,cp.stderr[-400:])
        def tampered(name,group,table,fn,want):
            d=td/f'pa_t_{name}';shutil.copytree(pa,d);(d/'subset_summary.json').unlink()
            if table:retable(d,group,table,fn)
            else:fn(d)
            cp=P.tool('pilot_report.py','subset-check',d,check=False);assert cp.returncode!=0 and want in cp.stderr,(name,cp.stderr[-600:]);shutil.rmtree(d)
        g8='a_free_L8'
        tampered('missing','a_free_L8','graph_replicates',lambda L:[L[0]]+[x for x in L[1:]if x.split(',')[1]!=L[1].split(',')[1]],'graph set differs')
        tampered('extra','a_free_L8','graph_replicates',lambda L:L+[','.join(['0','999']+L[1].split(',')[2:])],'graph set differs')
        tampered('points','a_free_L8','graph_tails',lambda L:[L[0]]+[','.join(x.split(',')[:2]+['8192']+x.split(',')[3:])for x in L[1:]],'points')
        tampered('replicate','a_free_L8','graph_replicates',lambda L:[x for x in L if not x.startswith('7,')],'replicates')
        tampered('prefix_missing',g8,'graph_prefixes',lambda L:L[:-1],'prefix')
        tampered('prefix_extra',g8,'graph_prefixes',lambda L:L+[L[-1]],'prefix')
        def flipsel(d):
            p=d/'selection.json';b=bytearray(p.read_bytes());b[-2]^=1;p.unlink();p.write_bytes(bytes(b))
        tampered('selection',None,None,flipsel,'selection.json')
        cp=P.tool('production.py','plan',P.site.run_dir('x1'),'--seed',93000005,'--pilot','--graphs',pa_sel,'--test-graphs',2,*common,'--reserve-seed',P.seeds,'--scratch',P.scr,check=False)
        assert cp.returncode==1 and '--graphs refuses --test-graphs'in cp.stderr
        cp=P.tool('production.py','plan',P.site.run_dir('x2'),'--seed',93000005,'--graphs',pa_sel,'--design',td,*common,'--reserve-seed',P.seeds,'--scratch',P.scr,check=False)
        assert cp.returncode==1 and ('exactly one allocation source'in cp.stderr or '--graphs requires --pilot'in cp.stderr)
        bad=json.loads(pa_sel.read_text());bad['role']='other';(td/'bad_role.json').write_text(json.dumps(bad))
        run_b,cpb=P.plan('x3','--seed',93000006,'--pilot','--graphs',td/'bad_role.json',*common,check=False)
        assert cpb.returncode!=0 and 'role stage_a or confirm'in cpb.stderr and not run_b.exists()
        cp=P.tool('pilot_report.py','full','--pa',pa,'--pf',pf,'--pc-selection',td/'pc_empty.json','--pc',pc,'--out',td/'r1','--eta-node',0.9,check=False)
        assert cp.returncode==1 and 'empty PC selection'in cp.stderr
        cp=P.tool('pilot_report.py','full','--pa',pa,'--pf',pf,'--pc-selection',pc_sel,'--out',td/'r2','--eta-node',0.9,check=False)
        assert cp.returncode==1 and '--pc RUN is required'in cp.stderr
        other=json.loads(pc_sel.read_text());other['seed']=1;(td/'pc_other.json').write_text(json.dumps(other))
        cp=P.tool('pilot_report.py','full','--pa',pa,'--pf',pf,'--pc-selection',td/'pc_other.json','--pc',pc,'--out',td/'r3','--eta-node',0.9,check=False)
        assert cp.returncode==1 and 'another selection'in cp.stderr
        # S3-005: full refuses a PC selection whose recorded screen names another PF or PA, or no identity (the empty selection: no --pc)
        for tag,mod in (('pf',lambda d:d['screen']['pf_identity'].__setitem__('manifest_sha256','0'*64)),
                        ('pa',lambda d:d['screen']['pa_identity']['science_sha256']['a_free_L8'].__setitem__('merged_science','0'*64)),
                        ('none',lambda d:d['screen'].pop('pa_identity'))):
            x=json.loads((td/'pc_empty.json').read_text());mod(x);f=td/f'pce_{tag}.json';f.write_text(json.dumps(x))
            cp=P.tool('pilot_report.py','full','--pa',pa,'--pf',pf,'--pc-selection',f,'--out',td/f'r_pce_{tag}','--eta-node',0.9,check=False)
            assert cp.returncode==1 and ('another campaign'in cp.stderr or 'no recorded campaign identity'in cp.stderr),(tag,cp.returncode,cp.stderr[-500:])
        # S3-006: a PF whose C8_pilot_result.json, still a valid result on its own, names another source manifest, merged file or allocation
        vr0=json.loads(P.tool('verify_result.py',pf).stdout);assert vr0['verified']and vr0['bound_to_campaign']==str(pf.resolve()),vr0
        for tag,mod in (('manifest',lambda r:r.__setitem__('source_manifest_sha256','0'*64)),('merged',lambda r:r['merged_sha256'].__setitem__('a_free_L3','0'*64)),
                        ('allocation',lambda r:r['allocation'].__setitem__('points',8192))):
            x=td/f'pf_res_{tag}';shutil.copytree(pf,x);f=x/'C8_pilot_result.json';r=json.loads(f.read_text());mod(r);f.unlink();f.write_text(json.dumps(r))
            assert P.tool('verify_result.py',f).returncode==0,tag   # file mode: a valid result on its own
            cp=P.tool('verify_result.py',x,check=False);assert cp.returncode==1 and 'does not belong to this campaign'in cp.stderr,(tag,cp.stderr[-400:])
            cp=P.tool('pilot_report.py','full','--pa',pa,'--pf',x,'--pc-selection',pc_sel,'--pc',pc,'--out',td/f'r_res_{tag}','--eta-node',0.9,check=False)
            assert cp.returncode==1 and 'does not belong to this campaign'in cp.stderr,(tag,cp.returncode,cp.stderr[-400:])
        stub=td/'stubpkg';(stub/'tools').mkdir(parents=True);shutil.copytree(P.pkg/'slurm',stub/'slurm')
        (stub/'tools/production.py').write_text('import sys\nprint("bogus" if sys.argv[1]=="role" else "")\n')
        cp=subprocess.run(['bash',str(stub/'slurm/merge.sh')],capture_output=True,text=True,env=c8pkg.env(C8_PACKAGE=stub,C8_RUN=pa,SLURM_TMPDIR=td,SLURM_CPUS_PER_TASK=2,C8_PYTHON=sys.executable))
        assert cp.returncode==64 and 'unknown campaign role'in cp.stderr,cp.stderr
        ok('A-DES-7 (e): assemble, combine, report, verify_result, design_fallback and design_adapter refuse a pilot_subset campaign (65, naming '
           'subset-check); subset-check fails on a missing or unselected graph, other points, a missing replicate, a missing or extra prefix row and a '
           'one-byte change of selection.json; --graphs with --test-graphs or --design, a non-test --graphs plan of another role, full\'s --pc rules '
           'and merge.sh on an unknown role (64) are refused; S3-005: confirm refuses a screen file of another PF or PA or without identities, and full a '
           'selection whose screen names another PF or PA or none; S3-006: verify_result.py RUN binds PF\'s result to PF, and both it and full refuse a '
           'copy whose C8_pilot_result.json (still valid on its own) names another source manifest, merged file or allocation')
        # 7. design -> two batches -> combine (A-ASM-6 on directories)
        cp=P.tool('design_fallback.py','freeze','--pilot',pf,'--cost-model',td/'M.json','--out',td/'bundle','--test-only','--eta-node',0.9,'--budget-core-hours',4,
                  '--min-replicates',32,'--max-replicates',32,'--seeds-log',P.seeds)
        meta=json.loads((td/'bundle/design_meta.json').read_text());assert meta['label']=='fallback'and meta['test_only']and mf['seed']in meta['forbidden_seeds']
        P.tool('design_fallback.py','freeze','--pilot',pf,'--cost-model',td/'M.json','--out',td/'bundle_acct','--test-only','--budget-core-hours',1000000,
               '--min-replicates',32,'--max-replicates',32,'--seeds-log',P.seeds)   # no --eta-node: eta_node from the ledger accounting
        ea=json.loads((td/'bundle_acct/design.json').read_text())['eta']
        assert abs(ea['value']-1/max(1.,eta_hand))<=1e-12 and 'accounting'in ea['source'],(ea,eta_hand)
        assert P.tool('design_fallback.py','freeze','--pilot',pf,'--cost-model',td/'M.json','--out',td/'bundle','--test-only','--eta-node',0.9,'--budget-core-hours',2,check=False).returncode!=0
        # --pc (RECON:1373; user decision 2026-10-08) on the real PF and PC campaigns
        fz=['--cost-model',td/'M.json','--test-only','--eta-node',0.9,'--budget-core-hours',4,'--min-replicates',32,'--max-replicates',32]
        P.tool('design_fallback.py','freeze','--pilot',pf,'--pc',pc,'--out',td/'bundle_pc',*fz,'--seeds-log',P.seeds)
        dpc=json.loads((td/'bundle_pc/design.json').read_text());mpc=json.loads((td/'bundle_pc/design_meta.json').read_text());tr=dpc['conservative_tail_rule']
        assert mpc['pc']['manifest_sha256']==selection_digest(pc/'manifest.json')and mpc['pc']['selection_sha256']==selection_digest(pc_sel)and mpc['pc']['campaign_role']=='pilot_subset'
        assert mpc['pc']['pf_identity']['manifest_sha256']==selection_digest(pf/'manifest.json')and mpc['pc']['science_sha256']and mpc['monitored_graphs']==tr['monitored']
        assert {(x['sector'],x['graph'])for x in tr['monitored']}==conf and tr['graph_campaigns']==2*len(sel_ids)==len(tr['raised'])+len(tr['unchanged']),(tr['monitored'],conf)
        assert all(x['sigma_alloc']>x['sigma_before']for x in tr['raised'])and all(x['sigma_pc_32768']<=x['sigma_before']for x in tr['unchanged'])
        rpc=json.loads(P.tool('design_fallback.py','report','--pilot',pf,'--pc',pc,'--cost-model',td/'M.json').stdout)   # eta from the accounting (PF is not test-only)
        assert rpc['conservative_tail_rule']['raised']==tr['raised']and rpc['conservative_tail_rule']['monitored']==tr['monitored']
        for args,why in ((['--pilot',pf,'--pc',pa],'not confirm'),(['--pilot',td/'pf_sci','--pc',pc],'another campaign')):
            cp=P.tool('design_fallback.py','freeze',*args,'--out',td/'bundle_pc_bad',*fz,check=False)
            assert cp.returncode==1 and why in cp.stderr and not (td/'bundle_pc_bad').exists(),(args,cp.returncode,cp.stderr[-600:])
        # A-DES-3: the report's alpha = 1/2 plug-in SE of the frozen design equals the design tool's own prediction to 1%
        P.tool('pilot_report.py','full','--pa',pa,'--pf',pf,'--pc-selection',pc_sel,'--pc',pc,'--out',td/'report_x','--eta-node',0.9,'--design-bundle',td/'bundle')
        x=json.loads((td/'report_x/pilot_report.json').read_text())['crosscheck']
        assert x['agree_1pct']and x['label']=='fallback'and x['column'].startswith('plug-in'),x
        batches=[]
        for i,seed in enumerate((94000001,94000002)):
            r,_=P.plan(f'batch{i}','--seed',seed,'--design',td/'bundle','--test-only',*common)
            mb=json.loads((r/'manifest.json').read_text());assert mb['campaign_role']=='test'and mb['design']['label']=='fallback'
            for j in mb['jobs']:P.tool('production.py','run',r,'--index',j['id'],'--threads',2,'--scratch',P.scr,C8_FAKE_FAST=1)
            P.tool('production.py','merge',r,'--jobs',2,'--scratch',P.scr);P.tool('assemble.py',r,'--bootstrap',0);batches.append(r)
        K=json.loads((td/'bundle/design.json').read_text())['batches']
        # S3-009: report.py keeps a test or pilot campaign's physical fields null (assemble.py's test_partial / sizing_only views)
        for run,key,label in ((batches[0],'test_partial','test'),(pf,'sizing_only','pilot')):
            out=td/f'report_{label}.json';P.tool('report.py',run,'--output',out,'--bootstrap',0);d=json.loads(out.read_text())
            asmb=d['assembly'];assert d['C8']is None and d['sampling_standard_error']is None and asmb['C8_full']is None and asmb['label']==label and asmb['final']is False,(label,d['C8'])
            assert isinstance(asmb[key]['C8_full'],float)and asmb['coefficients']is None and d['existing_result']['max_relative_difference']<=1e-12,(label,sorted(asmb)[:8])
        # S3-011: design_adapter view of PF: independent copies (new inodes, 0444); every source file keeps its permissions
        import stat
        before={str(q.resolve()):q.stat().st_mode for root in (pf,P.pkg/'inputs')for q in root.rglob('*')if q.is_file()}
        P.tool('design_adapter.py','view',pf,'--out',td/'view_pf');vj=json.loads((td/'view_pf/view.json').read_text())
        assert len(vj['files'])>=24*6+4
        for rel,x in vj['files'].items():
            src=Path(x['source']);dst=td/'view_pf'/rel
            assert src.stat().st_mode==before[str(src.resolve())]and src.stat().st_ino!=dst.stat().st_ino and stat.S_IMODE(dst.stat().st_mode)==0o444 and x['sha256']==selection_digest(src),(rel,oct(src.stat().st_mode))
        assert all(q.stat().st_mode==m for q,m in ((Path(k),v)for k,v in before.items()))
        cp=P.tool('combine.py',*batches,'--output',td/'combined',*(['--partial']if K>2 else[]),'--bootstrap',0,check=False)
        assert cp.returncode==0 if K>=2 else cp.returncode!=0,cp.stderr[-800:]
        if cp.returncode==0:
            r=json.loads(next((td/'combined').glob('C8_*.json')).read_text());assert r['label']=='partial'and r['final']is False and r['C8_full']is None
            assert r['partial_values']['batches']['count']==2 and r['partial_values']['batches']['chi2_about_combined']is not None
        ok('design: a --test-only fallback freeze on PF (label fallback, forbidden seeds include PF\'s) is never overwritten; without --eta-node the '
           'freeze takes eta_node from tools/accounting.py (1/max(1, the hand ratio)); freeze and report --pc PC bind PC to PF, record PC\'s identity '
           'and monitor exactly the graphs the full report confirmed, and refuse the PA as --pc and a PF whose scientific identity changed; pilot_report full --design-bundle recomputes its alpha = 1/2 plug-in SE within 1% of the design tool\'s (A-DES-3); two batches of the bundle '
           'are planned, run, merged, assembled and combined; S3-009: report.py on a test batch and on PF keeps C8 and its SE null (values under '
           'test_partial / sizing_only); S3-011: design_adapter view of PF holds independent read-only copies and every source file keeps its permissions')
        # 8. J-DRL-9: drill_select's selections -> a test-only --pilot --graphs plan -> the empty refusal -> lanes 1 (drill) -> merge.sh
        sel=td/'drl9';rd=json.loads(P.tool('drill_select.py','drl9','--cost-model',td/'M.json','--out-dir',sel).stdout)
        zc={(s,g)for s in ('free','power')for g in rd['graphs'][s]if g%7==3}   # tests/c8pkg.py: s_G = 4 (a zero channel) for gid % 7 == 3
        assert all(len(v)==2 for v in rd['graphs'].values())and not zc,rd
        dargs=['--pilot','--replicates',2,'--test-only',*common]
        d9,_=P.plan('drl9-test','--seed',95000001,'--graphs',sel/'stage_a_drl9.json',*dargs)
        md=json.loads((d9/'manifest.json').read_text())
        assert md['test_only']and md['campaign_role']=='pilot_subset'and md['plan_role']=='campaign'and sorted(g['name']for g in md['groups'])==['a_free_L8','a_power_L8','b_free_L8','b_power_L8']
        assert P.tool('production.py','role',d9).stdout.strip()=='pilot_subset'
        runs=P.site.root/'runs';before=sorted(os.listdir(runs));sq=sorted(map(str,runs.rglob('*.sqlite')))
        de,cpe=P.plan('drl9-empty','--seed',95000002,'--graphs',sel/'confirm_empty_drl9.json',*dargs,check=False)
        assert cpe.returncode==65 and 'empty selection'in cpe.stderr and not de.exists()and sorted(os.listdir(runs))==before and sorted(map(str,runs.rglob('*.sqlite')))==sq,(cpe.returncode,cpe.stderr[-600:])
        drill={'C8_LANE_DRILL':'1','C8_LANE_CPUS':'2','C8_SBATCH_ARGS':'-A yun124 -p debug','C8_LANE_MEM':'4G','C8_LANE_TIME':'00:20:00'}
        cp=P.site.submit(P.pkg,'lanes','1','--dry-run',C8_RUN=d9,**drill);assert cp.returncode==0 and 'subset-check (no coefficient assembly)'in cp.stdout+cp.stderr,cp.stderr[-800:]
        before={j['id']for j in P.site.jobs()};cp=P.site.submit(P.pkg,'lanes','1',C8_RUN=d9,**drill);assert cp.returncode==0,cp.stderr[-1500:]
        new=P.newest(before);ws=[j for j in new if j['name'].startswith('c8d3-lane-')];mg=[j for j in new if j['name'].startswith('c8d3-merge-')]
        assert len(ws)==1 and len(mg)==1 and ws[0]['partition']=='debug'and '--exclusive'not in ws[0]['argv'],[(j['name'],j['partition'])for j in new]
        P.job_body([sys.executable,'-B',str(P.pkg/'tools/lanes.py'),'worker',str(d9)],ws[0]['id'],C8_RUN=d9,C8_LANE_DRILL='1',C8_LANES='2');P.site.fake.finish(ws[0]['id'],'COMPLETED',elapsed=60)
        log=td/'spy_drl9.log';out=P.job_body(['bash',str(P.pkg/'slurm/merge.sh')],mg[0]['id'],C8_RUN=d9,C8_BOOTSTRAP=64,PYTHONPATH=P.spy,C8_SPY_LOG=log)
        P.site.fake.finish(mg[0]['id'],'COMPLETED',elapsed=20);spy=log.read_text()
        assert 'pilot_report.py subset-check'in spy and 'assemble.py'not in spy and 'order8_assembly'not in spy,spy[-800:]
        assert (d9/'subset_summary.json').is_file()and not list(d9.glob('C8_*result.json')),sorted(os.listdir(d9))
        for g in md['groups']:
            rows=[l for l in (d9/'groups'/g['name']/'graph_prefixes.csv').read_text().splitlines()[1:]if l.strip()];assert len(rows)==2,(g['name'],rows)
        assert P.tool('prefix_verify.py',d9).returncode==0
        ok('J-DRL-9 (fakes): drill_select drl9 on the measured model; a test-only --pilot --graphs plan of the stage_a selection is pilot_subset (4 L8 '
           'groups); the empty confirm selection exits 65 creating no directory and no SQLite file; lanes 1 --dry-run in drill mode names the subset '
           'merge path; after a drill lane worker and merge.sh: subset-check, no assemble.py, subset_summary.json, no C8_*result.json, 2 prefix rows '
           'per group (1 nested graph x 2 replicates), equal to prefix_verify.py\'s recomputation')
        return {'status':'passed','tests':len(RESULTS),'seconds':round(time.time()-t0,1),'results':RESULTS}
    finally:
        if keep:print('kept',td)
        else:shutil.rmtree(td,ignore_errors=True)

if __name__=='__main__':print(json.dumps(main('--keep'in sys.argv),indent=1,default=str))
