#!/usr/bin/env python3
"""Orchestration tests with a fake native worker (tests/fake_worker.py); run anywhere, no C++ build needed.

The tools run from an isolated copy of the package (tools/, inputs/, the archived seed plan and a fake
bin/c6_integrate), so nothing in the real package is written. Numerical equivalence with the original code is
tested separately with the real worker (validate.py, workflow.py, force_levels.py, e2e_reference.py).
"""
from __future__ import annotations
import concurrent.futures,json,math,os,shutil,sqlite3,stat,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from common import digest
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,**info});print('PASS',name,flush=True)

def make_package(td:Path)->Path:
    pkg=td/'pkg';(pkg/'tools').mkdir(parents=True)
    for f in (ROOT/'tools').glob('*.py'):shutil.copy2(f,pkg/'tools'/f.name)
    shutil.copytree(ROOT/'inputs',pkg/'inputs',ignore=shutil.ignore_patterns('.DS_Store'))
    (pkg/'reference/inputs').mkdir(parents=True);shutil.copy2(ROOT/'reference/inputs/frozen_production_plan.json',pkg/'reference/inputs/')
    (pkg/'reference/baseline_previous/inputs').mkdir(parents=True);shutil.copy2(ROOT/'reference/baseline_previous/inputs/production_plan.json',pkg/'reference/baseline_previous/inputs/')
    shutil.copytree(ROOT/'slurm',pkg/'slurm')
    (pkg/'bin').mkdir();fake=pkg/'bin/c6_integrate';fake.write_text(f'#!{sys.executable}\n'+(ROOT/'tests/fake_worker.py').read_text());fake.chmod(0o755)
    return pkg

def tool(pkg,script,*args,env=None,check=True):
    e={**os.environ,'PYTHONDONTWRITEBYTECODE':'1',**(env or{})}
    for k in ('SLURM_ARRAY_TASK_ID','C6_INDEX_OFFSET','SLURM_TMPDIR'):
        if env is None or k not in env:e.pop(k,None)
    cp=subprocess.run([sys.executable,'-B',str(pkg/'tools'/script),*map(str,args)],capture_output=True,text=True,env=e,preexec_fn=lambda:os.umask(0o022))
    if check and cp.returncode:raise AssertionError(f'{script} {args} failed ({cp.returncode}):\n{cp.stderr[-3000:]}\n{cp.stdout[-1000:]}')
    return cp

def plan(pkg,d,*extra,check=True):
    return tool(pkg,'production.py','plan',d,'--seed',771100231,'--replicates',2,'--threads',2,'--checkpoint-tasks',64,'--shards',3,*extra,check=check)

def manifest(d):return json.loads((d/'manifest.json').read_text())
def config(d,g):return json.loads((d/'groups'/g/'config.json').read_text())
def run_all(pkg,d,**kw):
    for j in manifest(d)['jobs']:tool(pkg,'production.py','run',d,'--index',j['id'],'--threads',2,**kw)
def tree(d):return {str(p.relative_to(d)):digest(p)for p in sorted(d.rglob('*'))if p.is_file()and 'tasks.sqlite-journal'not in p.name}

def test_archived_seeds():
    """Legacy-scheme refusal list covers both production plans and the archived d=3 development/validation records."""
    import production as prod
    seeds=prod.archived_base_seeds()
    must={882040358:'new_a L6 base (frozen_production_plan)',1299074358:'new_b L6 base',2609832058:'previous prod_a (baseline_previous plan)',
          7406804278:'previous prod_b',98273288:'validation_grid (L6 allocation training)',58390123:'validation',43672819:'pilot'}
    missing={k:v for k,v in must.items()if k not in seeds};assert not missing,missing
    assert prod.derive_seeds(882040358,'a',6,'legacy')=={'native':882048032,'net':882040358+18743*6}
    h=prod.derive_seeds(882040358,'a',6,'hashed');assert h!=prod.derive_seeds(882040358,'b',6,'hashed')and h!=prod.derive_seeds(882040358,'a',5,'hashed')
    ok('archived_seeds',count=len(seeds))

def test_plan_guards(pkg,td):
    d=td/'legacy'
    for seed in (882040358,2609832058,7406804278):
        cp=tool(pkg,'production.py','plan',d,'--seed',seed,'--seed-scheme','legacy','--replicates',2,check=False)
        assert cp.returncode and 'archived production or development base seed'in cp.stderr and not d.exists(),(seed,cp.stderr[-500:])
    for opt in (('--primitive-points','4'),('--primitive-mode','retained'),('--primitive-allocation','uniform')):
        d=td/'removed_option';cp=plan(pkg,d,*opt,check=False)
        assert cp.returncode and not d.exists(),(opt,cp.returncode)
    d=td/'broken';bad=td/'badpkg';shutil.copytree(pkg,bad);(bad/'bin/c6_integrate').write_text('#!/bin/sh\nexit 7\n')
    cp=plan(bad,d,'--points',4,check=False)
    assert cp.returncode and 'make clean && make'in cp.stderr and not d.exists(),cp.stderr[-500:]
    ok('plan_guards',checks=['archived legacy seeds refused (fresh and previous production)','removed primitive options refused','failing self-test refused'])

def test_plan_allocation_and_order(pkg,td):
    d=td/'frozen2';plan(pkg,d,'--multiplier',2);m=manifest(d)
    assert m['allocation']['zero_targets_raised_to']==4 and m['allocation']['multiplier']==2 and m['allocation']['point_override']is None
    for g in m['groups']:
        c=config(d,g['name']);frozen=json.loads((ROOT/f'inputs/counts_L{c["L"]}.json').read_text())['counts']
        assert c['counts']=={str(r):max(4,int(frozen.get(str(r),0)))*2 for r in map(int,c['counts'])},g['name']
    assert m['estimates']['projected_C6_sampling_se']==0.02811931498555694/math.sqrt(2*2/32)
    # Seconds-scaled shards and cost-descending block positions; uid identity unchanged.
    secs={}
    for g in m['groups']:
        L=config(d,g['name'])['L'];spu=m['estimates']['calibration']['seconds_per_cost_unit'][str(L)]
        db=sqlite3.connect((d/'groups'/g['name']/'tasks.sqlite').resolve().as_uri()+'?mode=ro',uri=True);secs[g['name']]=db.execute('SELECT SUM(cost) FROM tasks').fetchone()[0]*spu
        rows=db.execute('SELECT uid,shard,pos,cost FROM tasks ORDER BY shard,pos').fetchall()
        assert sorted(r[0]for r in rows)==list(range(len(rows)))
        for sh in {r[1]for r in rows}:
            part=[r for r in rows if r[1]==sh];assert [r[2]for r in part]==list(range(len(part)))
            assert all(x[3]>=y[3]for x,y in zip(part,part[1:]))
        db.close()
    smax=max(secs.values())
    for g in m['groups']:
        assert config(d,g['name'])['shards']==min(max(1,round(3*secs[g['name']]/smax)),config(d,g['name'])['tasks'])
    assert m['estimates']['suggested_time_seconds']>=900 and m['seed_scheme']=='hashed'
    ok('plan_frozen_allocation_shards_positions',shards={g['name']:config(d,g['name'])['shards']for g in m['groups']})

def test_points_override(pkg,td):
    d=td/'points_recompute';plan(pkg,d,'--points',8)
    for g in manifest(d)['groups']:
        c=config(d,g['name'])
        assert all(n==8 for n in c['counts'].values()),(g['name'],c['counts'])
    assert manifest(d)['allocation']['point_override']==8 and manifest(d)['estimates']['projected_C6_sampling_se']is None
    ok('points_override_all_strata_primitives_included')

def test_pipeline(pkg,td):
    d=td/'camp';plan(pkg,d,'--points',4,'--chunk-points',2);m=manifest(d);scratch=td/'scratch';scratch.mkdir();log=td/'fake.log'
    # A-M1: native calls use only a verified job-private runtime, removed afterwards.
    tool(pkg,'production.py','run',d,'--index',0,'--threads',2,'--scratch',scratch,env={'C6_FAKE_LOG':str(log)})
    calls=[json.loads(x)for x in log.read_text().splitlines()]
    assert calls and all(c['executable'].startswith(str(scratch/'c6_d3_runtime_'))and c['args'][0].startswith(str(scratch/'c6_d3_runtime_'))
                         and c['args'][2].startswith(str(scratch/'c6_d3_runtime_'))for c in calls)  # executable, graphs and the Sobol net are private copies
    assert not any(scratch.iterdir())
    cp0=json.loads(next((d/'groups/a_L3/checkpoints').glob('*.json')).read_text())
    assert cp0['runtime']=={'executable_sha256':m['executable_sha256'],'inputs_manifest_sha256':m['inputs_manifest_sha256'],'net_sha256':config(d,'a_L3')['net']['sha256']}and cp0['executable_sha256']==m['executable_sha256']
    # Forced native failure: failure log, no checkpoint, runtime removed.
    j=m['jobs'][-1];before=set((d/'groups'/j['group']/'checkpoints').glob('*.json'))if(d/'groups'/j['group']/'checkpoints').exists()else set()
    cp=tool(pkg,'production.py','run',d,'--index',j['id'],'--scratch',scratch,env={'C6_FAKE_FAIL':'1'},check=False)
    assert cp.returncode and 'forced native failure'in cp.stderr and not any(scratch.iterdir())
    assert set((d/'groups'/j['group']/'checkpoints').glob('*.json'))==before and list((d/'groups'/j['group']/'logs').glob('*.failure.*.log'))
    # Thread guard and index offset.
    cp=tool(pkg,'production.py','run',d,'--index',0,'--threads',128,check=False);assert cp.returncode and 'exceed checkpoint_tasks'in cp.stderr
    cp=tool(pkg,'production.py','run',d,check=False);assert cp.returncode and 'give --index'in cp.stderr  # never a silent index 0
    run_all(pkg,d)
    tool(pkg,'production.py','run',d,env={'SLURM_ARRAY_TASK_ID':'0','C6_INDEX_OFFSET':str(len(m['jobs'])-1)})
    st=tool(pkg,'production.py','status',d);assert 'complete: every checkpoint block is committed'in st.stdout
    ok('run_private_runtime_failure_threads_offset',native_calls_logged=len(calls))
    # Status/recovery, --max-blocks and recompute of a deleted checkpoint.
    g=m['groups'][-1]['name'];cps=sorted((d/'groups'/g/'checkpoints').glob('s000000_p*.json'));assert len(cps)>=2
    saved={p:p.read_bytes()for p in cps[:2]}
    for p in saved:p.unlink()
    jid=next(j['id']for j in m['jobs']if j['group']==g and j['shard']==0)
    st=tool(pkg,'production.py','status',d,check=False)
    want=f'resubmit: C6_MAX_ARRAY=1000 C6_RUN={d.resolve()} C6_PACKAGE={pkg.resolve()} {pkg.resolve()/"slurm/submit.sh"} --window {jid//1000*1000}:{jid%1000}'
    assert st.returncode==1 and want in st.stdout,st.stdout[-800:]
    js=json.loads(tool(pkg,'production.py','status',d,'--json',check=False).stdout)
    assert js['complete']is False and js['missing_jobs']==[jid] and js['resubmit']==[{'offset':0,'array':str(jid)}] and js['threads']==m['threads']
    import hashlib;assert js['campaign_tag']=='c6:'+hashlib.sha256(f'{d.resolve()}\n{digest(d/"manifest.json")}'.encode()).hexdigest()[:12]
    js=json.loads(tool(pkg,'production.py','status',d,'--json','--exclude',f'{jid},99999',check=False).stdout)
    assert js['active_not_resubmitted']==[jid] and js['resubmit']==[] and js['complete']is False
    # --max-array (C6_MAX_ARRAY) windows: missing indices are rebased into offset windows of at most that size.
    for p2 in cps[2:4]:p2.unlink()
    extra=[j['id']for j in m['jobs']if j['group']==g and j['shard']==0]
    js=json.loads(tool(pkg,'production.py','status',d,'--json','--max-array',2,check=False).stdout)
    assert js['resubmit']and all(r['offset']%2==0 and all(0<=int(x)<2 for part in r['array'].split(',')for x in part.split('-'))for r in js['resubmit']),js['resubmit']
    assert sorted(r['offset']+int(x)for r in js['resubmit']for x in r['array'].split(','))==js['missing_jobs'],js
    # --max-array windows: indices are rebased into offset windows of at most that many elements.
    ids=[j['id']for j in m['jobs']];camp_missing=list(ids)
    js=json.loads(tool(pkg,'production.py','status',d,'--json','--max-array',2,check=False).stdout)
    assert all(int(x)<2 for r in js['resubmit']for part in r['array'].split(',')for x in part.split('-'))and all(r['offset']%2==0 for r in js['resubmit'])
    tool(pkg,'production.py','run',d,'--index',jid,'--max-blocks',1)
    assert cps[0].exists()and not cps[1].exists()
    tool(pkg,'production.py','run',d,'--index',jid,'--threads',1)
    assert tool(pkg,'production.py','status',d).returncode==0
    for p,data in saved.items():
        x,y=json.loads(p.read_text()),json.loads(data)
        assert [{k:r[k]for k in('uid','values','quad','mp')}for r in x['native']['rows']]==[{k:r[k]for k in('uid','values','quad','mp')}for r in y['native']['rows']]
    ok('status_recovery_max_blocks_recompute')
    # Concurrent duplicate executions of one index.
    for p in cps[:2]:p.unlink()
    with concurrent.futures.ThreadPoolExecutor(2)as ex:
        rcs=list(ex.map(lambda _:tool(pkg,'production.py','run',d,'--index',jid,check=False).returncode,range(2)))
    assert rcs==[0,0],rcs
    ok('concurrent_duplicate_runs')
    # Merge, assemble, idempotent rerun of the complete merge.sh sequence.
    tool(pkg,'production.py','merge',d,'--group','a_L3');tool(pkg,'production.py','merge',d);tool(pkg,'assemble.py',d,'--bootstrap',64)
    snap=tree(d);tool(pkg,'production.py','merge',d);cp=tool(pkg,'assemble.py',d,'--bootstrap',64)
    assert 'identical result already present'in cp.stdout and tree(d)==snap
    for f in (d/'manifest.json',d/'C6_result.json',d/'groups/a_L3/merged.json',d/'groups/a_L3/graph_replicates.csv',cps[0]):
        assert stat.S_IMODE(f.stat().st_mode)==0o644,(f,oct(f.stat().st_mode))
    res=json.loads((d/'C6_result.json').read_text());assert set(res['input_sha256'])=={'inputs/manifest.json','inputs/two_loop.json'}
    assert res['coefficients'][0]==1.5 and res['shared_reference_standard_error']==0 and res['dimension']==3 and res['primitive_mode']=='recompute'
    ok('merge_resume_idempotent_assembly_permissions')
    # Tampering is rejected: merged.json, C6_result.json, assembly inputs, runtime digest, foreign-plan checkpoint.
    def rejected(path:Path,edit,cmd,needle):
        orig=path.read_bytes();path.write_bytes(edit(orig))
        try:
            cp=tool(pkg,*cmd,check=False);assert cp.returncode and needle in cp.stderr,(path,cp.stderr[-600:])
        finally:path.write_bytes(orig)
    def bump(b):
        x=json.loads(b);x['batches'][0][0]+=1.0;return (json.dumps(x,indent=2)+'\n').encode()
    rejected(d/'groups/b_L4/merged.json',bump,('production.py','merge',d),'merged payload checksum mismatch')
    rejected(d/'C6_result.json',lambda b:json.dumps({**json.loads(b),'C6':1.0}).encode(),('assemble.py',d),'differs from the recomputed result')
    rejected(pkg/'inputs/two_loop.json',lambda b:b+b' ',('assemble.py',d,'--output',td/'x.json'),'Checksum mismatch: inputs/two_loop.json')
    rejected(pkg/'inputs/manifest.json',lambda b:b+b' ',('assemble.py',d,'--output',td/'x.json'),'Checksum mismatch')
    cpf=cps[0]
    def runtime_edit(b):
        x=json.loads(b);x['runtime']['executable_sha256']='0'*64;return json.dumps(x).encode()
    (d/'groups'/g/'merged.json').unlink()
    rejected(cpf,runtime_edit,('production.py','merge',d,'--group',g),'different executable')
    def net_edit(b):
        x=json.loads(b);x['runtime']['net_sha256']='1'*64;return json.dumps(x).encode()
    rejected(cpf,net_edit,('production.py','merge',d,'--group',g),'different Sobol net')
    tool(pkg,'production.py','merge',d,'--group',g);assert tree(d)==snap
    other=td/'other';plan(pkg,other,'--points',4,'--chunk-points',2,'--seed',771100232)
    tool(pkg,'production.py','run',other,'--index',0)
    foreign=next((other/'groups/a_L3/checkpoints').glob('*.json'))
    rejected(d/'groups/a_L3/checkpoints'/foreign.name,lambda b:foreign.read_bytes(),('production.py','run',d,'--index',0),'checkpoint identity mismatch')
    ok('tamper_and_foreign_checkpoint_rejected')

def test_concurrent_merge_and_uri_path(pkg,td):
    # A-URI: '#', '?', '%' and a space in the campaign path (SQLite read-only opens use a percent-encoded file: URI).
    d=td/'we#ird?dir %41 x';plan(pkg,d,'--points',4,'--chunk-points',2);run_all(pkg,d)
    assert tool(pkg,'production.py','status',d).returncode==0
    # A-L3: two concurrent merges of the same complete campaign both succeed and leave one identical merged.json per group.
    with concurrent.futures.ThreadPoolExecutor(2)as ex:
        cps=list(ex.map(lambda _:tool(pkg,'production.py','merge',d,check=False),range(2)))
    assert [c.returncode for c in cps]==[0,0],[c.stderr[-400:]for c in cps]
    snap=tree(d);tool(pkg,'production.py','merge',d);assert tree(d)==snap
    tool(pkg,'assemble.py',d,'--bootstrap',16);assert json.loads((d/'C6_result.json').read_text())['dimension']==3
    ok('uri_reserved_campaign_path_and_concurrent_merge',path=str(d.name))

def expand(spec):
    out=[]
    for part in spec.split('%')[0].split(','):
        lo,_,hi=part.partition('-');out.extend(range(int(lo),int(hi or lo)+1))
    return out

def incomplete_campaign(pkg,td,name,n_missing=4,extra=()):
    """A small campaign run to completion, then the last checkpoint of n_missing jobs deleted."""
    d=td/name;plan(pkg,d,'--points',4,'--chunk-points',2,*extra);run_all(pkg,d);m=manifest(d);picked=[]
    for j in m['jobs']:
        cps=sorted((d/'groups'/j['group']/'checkpoints').glob(f's{j["shard"]:06d}_p*.json'))
        if cps and len(picked)<n_missing:cps[-1].unlink();picked.append(j['id'])
    return d,m,picked

def test_recovery_plan(pkg,td):
    """Pure recovery decisions (tools/production.py recovery_plan) from squeue snapshots."""
    import importlib;sys.path.insert(0,str(pkg/'tools'));prod=importlib.import_module('production')
    d,m,(A,B,C,D)=incomplete_campaign(pkg,td,'rp');tag=prod.campaign_tag(d)
    twin=td/'rp_twin';plan(pkg,twin,'--points',4,'--chunk-points',2)
    assert (d/'manifest.json').read_bytes()==(twin/'manifest.json').read_bytes()and prod.campaign_tag(twin)!=tag  # same plan, other directory
    R=lambda lines,size=1000:prod.recovery_plan(d,'\n'.join(lines),size)
    k=f'{tag}:off=0'
    r=R([f'{k}|{A}|RUNNING|900_{A}',f'{k}|{B}|SUSPENDED|900_{B}',f'{k}|{C}|CANCELLED|900_{C}',f'{tag}:merge|N/A|COMPLETED|901',
         f'{prod.campaign_tag(twin)}:off=0|{D}|RUNNING|950_{D}',f'{prod.campaign_tag(twin)}:merge|N/A|PENDING|951','other|N/A|RUNNING|5'])
    assert r['refuse']is None and sorted(i for w in r['arrays']for i in expand(w['array']))==sorted([C,D])and r['merge_waits_on_live_tasks']==sorted([f'900_{A}',f'900_{B}']),r
    assert r['live_missing_not_resubmitted']==sorted([A,B])
    r=R([f'{k}|{A}|SPECIAL_EXIT|910_{A}'])                           # held work is live
    assert r['refuse']is None and A not in [i for w in r['arrays']for i in expand(w['array'])]and r['merge_waits_on_live_tasks']==[f'910_{A}']
    done=[j['id']for j in m['jobs']if j['id']not in (A,B,C,D)][0]
    r=R([f'{k}|{done}|RUNNING|920_{done}'])                          # a live task with no missing block is still waited on
    assert r['refuse']is None and r['merge_waits_on_live_tasks']==[f'920_{done}']and sorted(i for w in r['arrays']for i in expand(w['array']))==sorted([A,B,C,D])
    for lines in ([],['other|N/A|RUNNING|5','x|3|PENDING|6_3','']):  # empty / unrelated only
        r=R(lines);assert r['refuse']is None and sorted(i for w in r['arrays']for i in expand(w['array']))==sorted([A,B,C,D])and r['merge_waits_on_live_tasks']==[]
    for lines,code in (([f'{tag}:merge|N/A|PENDING|902'],65),([f'{tag}:merge|N/A|SUSPENDED|902'],65),([f'{tag}:merge|N/A|SPECIAL_EXIT|902'],65),
                       ([f'{k}|{A}|COMPLETING|900_{A}'],69),([f'{k}|{A}|STAGE_OUT|900_{A}'],69),([f'{k}|{A}|PREEMPTED|900_{A}'],69),
                       ([f'{tag}:merge|N/A|COMPLETING|902'],69),([f'{k}|{A}|WEIRDSTATE|900_{A}'],69),([f'{k}|2-3%64|PENDING|900_[2-3%64]'],69)):
        r=R(lines);assert r['refuse']and r['refuse']['code']==code,(lines,r)
    # Windows: live element at a non-zero offset; the union of the windows is exactly missing minus live.
    r=R([f'{tag}:off=2|{B-2}|RUNNING|930_{B-2}']if B>=2 else[f'{k}|{B}|RUNNING|930_{B}'],2)
    got=sorted(w['offset']+i for w in r['arrays']for i in expand(w['array']))
    assert got==sorted({A,B,C,D}-{B})and all(w['offset']%2==0 and all(i<2 for i in expand(w['array']))for w in r['arrays']),r
    js=json.loads(tool(pkg,'production.py','status',d,'--json','--max-array',2,check=False).stdout)
    assert sorted(w['offset']+i for w in js['resubmit']for i in expand(w['array']))==js['missing_jobs']
    cp=tool(pkg,'production.py','status',d,'--max-array',0,check=False);assert cp.returncode and 'positive'in cp.stderr
    st=tool(pkg,'production.py','status',d,check=False).stdout
    assert f'resubmit: C6_MAX_ARRAY=1000 C6_RUN={d.resolve()} C6_PACKAGE={pkg.resolve()} {pkg.resolve()/"slurm/submit.sh"} --window 0:'in st and '$'not in st.split('resubmit: ',1)[1].splitlines()[0],st[-500:] and '--export=ALL 'in st
    ok('recovery_plan',tag=tag,twin_tag=prod.campaign_tag(twin))

FAKE_SQUEUE="""#!/bin/bash
# Fake squeue. Fixture lines: comment|task|state|jobid[|hidden]. Models an inherited SQUEUE_STATES filter, the default
# state set (no SUSPENDED/finished jobs unless --states=all), hidden partitions (--all), and -r (without it, pending
# tasks of one array collapse into a single range record, as real squeue prints them).
echo "SQUEUE_STATES=${SQUEUE_STATES:-unset} args=$*" >> "$FAKE_LOG"
[[ -n "${FAKE_SQUEUE_FAIL:-}" ]] && exit 1
declare -A pend
while IFS='|' read -r c k s i h; do
  [[ -z "$c" ]] && continue
  if [[ -n "${SQUEUE_STATES:-}" && ",${SQUEUE_STATES}," != *",$s,"* ]]; then continue; fi
  if [[ " $* " != *" --states=all "* && "$s" =~ ^(SUSPENDED|COMPLETED|CANCELLED|SPECIAL_EXIT)$ ]]; then continue; fi
  if [[ "$h" == hidden && " $* " != *" --all "* ]]; then continue; fi
  if [[ " $* " != *" -r "* && "$s" == PENDING && "$i" == *_* ]]; then pend["$c|${i%%_*}"]+="${i##*_},"; continue; fi
  printf '%-200s|%s|%s|%s\n' "$c" "$k" "$s" "$i"
done < "$FAKE_SQUEUE_LINES"
for key in "${!pend[@]}"; do r=${pend[$key]%,}; printf '%-200s|%s|PENDING|%s_[%s]\n' "${key%%|*}" "$r" "${key##*|}" "$r"; done
"""
FAKE_SBATCH="""#!/bin/bash
# FAKE_SBATCH_BLOCK=<fifo>: the first call blocks until a line is written to the FIFO (lock tests); FAKE_SBATCH_FAIL fails.
if [[ -n "${FAKE_SBATCH_BLOCK:-}" && -p "$FAKE_SBATCH_BLOCK" ]]; then read -r _ < "$FAKE_SBATCH_BLOCK"; rm -f "$FAKE_SBATCH_BLOCK"; fi
[[ -n "${FAKE_SBATCH_FAIL:-}" ]] && { echo "sbatch: error: fake failure" >&2; exit 1; }
# Records the EFFECTIVE C6_INDEX_OFFSET a job would see: with --export=ALL[,...] the submitting environment takes
# precedence over explicit VAR=value entries (sbatch man page); otherwise the explicit value applies.
n=$(( $(cat "$FAKE_COUNTER" 2>/dev/null || echo 700) + 1 )); echo $n > "$FAKE_COUNTER"
exp=""; for a in "$@"; do [[ "$a" == --export=* ]] && exp="${a#--export=}"; done
eff=unset; explicit=$(tr ',' '\\n' <<< "$exp" | sed -n 's/^C6_INDEX_OFFSET=//p' | tail -1)
if [[ ",$exp," == *",ALL,"* && -n "${C6_INDEX_OFFSET+x}" ]]; then eff=$C6_INDEX_OFFSET; elif [[ -n "$explicit" ]]; then eff=$explicit; fi
echo "$n ENVMARK=${C6_TEST_MARK:-none} ARRAYINX=${SBATCH_ARRAY_INX:-unset} DEP=${SBATCH_DEPENDENCY:-unset} SEXPORT=${SBATCH_EXPORT:-unset} SACCOUNT=${SBATCH_ACCOUNT:-unset} RUN=${C6_RUN:-unset} PKG=${C6_PACKAGE:-unset} EFFOFF=$eff ARGS $*" >> "$FAKE_SBATCH_LOG"; echo "$n"
"""
def test_slurm_helpers_fake(pkg,td):
    """slurm/submit.sh, slurm/resubmit.sh, `submit.sh --window` and the status lines against fake squeue/sbatch."""
    import importlib;sys.path.insert(0,str(pkg/'tools'));prod=importlib.import_module('production')
    d,m,(A,B,C,D)=incomplete_campaign(pkg,td,'fs');tag=prod.campaign_tag(d);n=len(m['jobs'])
    fb=td/'fakebin';fb.mkdir();(fb/'squeue').write_text(FAKE_SQUEUE);(fb/'sbatch').write_text(FAKE_SBATCH)
    for f in fb.iterdir():f.chmod(0o755)
    envsh=td/'env.sh';envsh.write_text(f'export C6_PYTHON={sys.executable}\nexport C6_TEST_MARK=sourced\n')
    base={**os.environ,'PATH':f'{fb}:{os.environ["PATH"]}','C6_PACKAGE':str(pkg),'C6_RUN':str(d),'C6_ENV_SETUP':str(envsh),'C6_SBATCH_ARGS':'-A acct -p part',
          'SQUEUE_STATES':'PENDING','SBATCH_ARRAY_INX':'0-3','SBATCH_DEPENDENCY':'afterok:1','SBATCH_EXPORT':'NONE','SBATCH_ACCOUNT':'site','C6_INDEX_OFFSET':'0',
          'FAKE_LOG':str(td/'squeue.log'),'FAKE_SQUEUE_LINES':str(td/'lines.txt'),'FAKE_SBATCH_LOG':str(td/'sbatch.log'),'FAKE_COUNTER':str(td/'counter'),'USER':'tester','C6_MAX_ARRAY':'2','C6_THROTTLE':'3'}
    base.pop('C6_PYTHON',None)
    for k in ('SBATCH_CLUSTERS','SLURM_CLUSTERS','SQUEUE_CLUSTERS'):base.pop(k,None)
    def call(script,lines=(),args=(),cmd=None,**extra):
        (td/'lines.txt').write_text('\n'.join(lines)+'\n');(td/'sbatch.log').unlink(missing_ok=True)
        cp=subprocess.run(cmd or['bash',str(ROOT/'slurm'/script),*args],capture_output=True,text=True,env={**base,**extra})
        return cp,((td/'sbatch.log').read_text().splitlines()if(td/'sbatch.log').exists()else[])
    def argv(c):return c.split(' ARGS ',1)[1].split()
    def last(args,opt):return [a for a in args if a.startswith(opt+'=')][-1].split('=',1)[1]
    def field(c,k):return c.split(f' {k}=',1)[1].split()[0]
    eff=lambda c:int(field(c,'EFFOFF'))
    k=f'{tag}:off=0';lines=[f'{k}|{A}|RUNNING|900_{A}',f'{k}|{B}|PENDING|900_{B}|hidden',f'{k}|{C}|CANCELLED|900_{C}',f'{tag}:merge|N/A|COMPLETED|901']
    # Recovery: live A (running) and B (pending, hidden partition) kept; C (cancelled) and D (missing) resubmitted.
    cp,calls=call('resubmit.sh',lines,['--time=00:05:00'])
    assert cp.returncode==0,cp.stderr[-800:]
    q=(td/'squeue.log').read_text().splitlines()[-1];toks=q.split('args=',1)[1].split()
    assert 'SQUEUE_STATES=unset'in q and all(o in toks for o in('--all','--states=all','-r','-h','-u'))and toks[toks.index('-u')+1]=='tester',q
    works=[c for c in calls if 'run_array.sh'in c];merge=[c for c in calls if 'merge.sh'in c]
    assert len(merge)==1 and sorted(eff(c)+i for c in works for i in expand(last(argv(c),'--array')))==sorted([C,D]),(works,merge)
    for c in calls:  # clean sbatch environment: offending SBATCH_* inputs removed, allowed ones kept, paths bound
        assert field(c,'ENVMARK')=='sourced'and field(c,'ARRAYINX')=='unset'and field(c,'DEP')=='unset'and field(c,'SEXPORT')=='unset'and field(c,'SACCOUNT')=='site',c
        assert field(c,'RUN')==str(d.resolve())and field(c,'PKG')==str(pkg.resolve()),c
    for c in works:
        w=argv(c);off=eff(c)
        assert last(w,'--comment')==f'{tag}:off={off}'and last(w,'--array').endswith('%3')and off%2==0 and all(i<2 for i in expand(last(w,'--array')))
        assert last(w,'--time')=='00:05:00'and last(w,'--cpus-per-task')==str(m['threads'])and w[:4]==['--parsable','-A','acct','-p']
    mw=argv(merge[0]);dep=last(mw,'--dependency');assert field(merge[0],'EFFOFF')=='unset'and last(mw,'--comment')==f'{tag}:merge'
    assert f'900_{A}'in dep and f'900_{B}'in dep and f'900_{C}'not in dep and not any(x.startswith(('--array','-a'))for x in mw),mw
    # Every refusal submits nothing.
    (td/'envfile').write_text(f'C6_RUN={d}\nC6_PACKAGE={pkg}\n')
    for script in ('resubmit.sh','submit.sh'):
        for bad in ('-A acct --array=0-3','-a0-3 -p part','-A acct -d afterok:1','-A acct --export=NONE','-A acct --comment=x','-A acct -o /tmp/x',
                    f'-A acct --export-file={td/"envfile"}','-A acct --export-f=x','-A acct --arr=0-3','-A acct --nice --export-file=x','-A acct -M other','-A acct stray',
                    '-A acct --job-name','-A acct "unbalanced'):
            cp,calls=call(script,lines,C6_SBATCH_ARGS=bad);assert cp.returncode==64 and not calls,(script,bad,cp.returncode,cp.stderr[-300:],calls)
        for extra in (['--comment=evil'],['--export=NONE'],[f'--export-file={td/"envfile"}'],['--arr=0-99'],['-a','1'],['--dependency=afterok:1']):
            cp,calls=call(script,lines,extra);assert cp.returncode==64 and not calls,(script,extra,cp.stderr[-300:],calls)
        # R-ARG-01: a trailing value option in C6_SBATCH_ARGS cannot swallow a protected extra option (validated separately).
        cp,calls=call(script,lines,['--dependency=afterok:12345'],C6_SBATCH_ARGS='-A acct --job-name');assert cp.returncode==64 and not calls
        for envbad in ({'SBATCH_CLUSTERS':'other'},{'SLURM_CLUSTERS':'other'},{'SQUEUE_CLUSTERS':'other'},{'C6_THROTTLE':'64 --dependency=afterok:1'},{'C6_THROTTLE':'0'},{'C6_MAX_ARRAY':'x'},
                       {'C6_SBATCH_ARGS':'-A acct\n-p part'}):
            cp,calls=call(script,lines,**envbad);assert cp.returncode==64 and not calls,(script,envbad,cp.stderr[-300:],calls)
    for lines2,code,needle,extra in (([f'{tag}:merge|N/A|SPECIAL_EXIT|903'],65,'still queued or running',{}),([f'{k}|{A}|COMPLETING|900_{A}'],69,'completing, preempted',{}),
                                     ([],69,'squeue failed',{'FAKE_SQUEUE_FAIL':'1'})):
        cp,calls=call('resubmit.sh',lines2,**extra);assert cp.returncode==code and needle in cp.stderr and not calls,(needle,cp.returncode,cp.stderr[-300:],calls)
    # Without -r a pending array collapses into a range record; resubmit asks for -r, so tasks are seen one by one.
    cp,calls=call('resubmit.sh',[f'{k}|{A}|PENDING|900_{A}',f'{k}|{B}|PENDING|900_{B}'])
    assert cp.returncode==0 and f'900_{A}'in last(argv([c for c in calls if 'merge.sh'in c][0]),'--dependency'),(cp.stderr[-300:],calls)
    # submit.sh: windows of C6_MAX_ARRAY cover the plan exactly (stale inherited offset 0), tags, the user may set the time.
    cp,calls=call('submit.sh',args=['--time=00:07:00']);assert cp.returncode==0,cp.stderr[-600:]
    works=[c for c in calls if 'run_array.sh'in c];merge=[c for c in calls if 'merge.sh'in c]
    assert len(works)>=2 and len(merge)==1 and sorted(eff(c)+i for c in works for i in expand(last(argv(c),'--array')))==list(range(n)),works
    assert all(last(argv(c),'--comment')==f'{tag}:off={eff(c)}'and last(argv(c),'--time')=='00:07:00'and last(argv(c),'--array').endswith('%3')for c in works)
    bad=td/'nomanifest';bad.mkdir();cp,calls=call('submit.sh',C6_RUN=str(bad));assert cp.returncode==64 and not calls
    # submit.sh --window: one validated window, no merge.
    cp,calls=call('submit.sh',args=['--window','2:0-1']);assert cp.returncode==0 and len(calls)==1 and eff(calls[0])==2 and last(argv(calls[0]),'--array')=='0-1%3',(cp.stderr,calls)
    for spec in ('x:1','0:','0:3-1','-1:0',f'0:{n}',f'{n}:0','0:0-5'):
        cp,calls=call('submit.sh',args=['--window',spec]);assert cp.returncode==64 and not calls,(spec,cp.stderr[-200:])
    # The status lines run the same guarded path with bound campaign/package: execute them against fake sbatch.
    rs=[l.split('resubmit: ',1)[1]for l in tool(pkg,'production.py','status',d,env={'C6_MAX_ARRAY':'2'},check=False).stdout.splitlines()if l.startswith('resubmit: ')]
    assert rs and all(int(x.split('--window ')[1].split(':')[0])%2==0 for x in rs)  # windows follow C6_MAX_ARRAY
    for envx,expect_ok in (({},True),({'C6_SBATCH_ARGS':f'-A acct --export-file={td/"envfile"}'},False),({'C6_SBATCH_ARGS':'--nice --export-file=x'},False),
                           ({'C6_SBATCH_ARGS':'-A acct --arr=0-3'},False),({'C6_THROTTLE':'64 --dependency=afterok:1'},False),({'SBATCH_CLUSTERS':'x'},False)):
        cp,calls=call(None,cmd=['bash','-c',rs[0]],C6_RUN='/stale/run',C6_PACKAGE='/stale/pkg',C6_INDEX_OFFSET='999',**envx)
        if expect_ok:
            off=int(rs[0].split('--window ')[1].split(':')[0])
            assert cp.returncode==0 and len(calls)==1 and eff(calls[0])==off and field(calls[0],'RUN')==str(d.resolve()),(envx,cp.stderr[-300:],calls)
        else:assert cp.returncode!=0 and not calls,(envx,cp.returncode,calls)
    # An explicit status --max-array wider than the inherited C6_MAX_ARRAY: the printed lines carry their own size.
    wide=[l.split('resubmit: ',1)[1]for l in tool(pkg,'production.py','status',d,'--max-array',6,env={'C6_MAX_ARRAY':'2'},check=False).stdout.splitlines()if l.startswith('resubmit: ')]
    assert wide and all(x.startswith('C6_MAX_ARRAY=6 ')for x in wide)and any(len(expand(x.split(':')[-1]))>2 for x in wide),wide
    for x in wide:
        cp,calls=call(None,cmd=['bash','-c',x],C6_MAX_ARRAY='2');assert cp.returncode==0 and len(calls)==1,(x,cp.stderr[-300:])
    # Campaign submission lock (plan review R1): one submission at a time per campaign, removed on every exit path.
    lock=d/'.c6_submit.lock';fifo=td/'block.fifo';os.mkfifo(fifo)
    (td/'lines.txt').write_text('\n'.join(lines)+'\n');(td/'sbatch.log').unlink(missing_ok=True)
    first=subprocess.Popen(['bash',str(ROOT/'slurm/resubmit.sh')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**base,'FAKE_SBATCH_BLOCK':str(fifo)})
    for _ in range(1200):
        if (lock/'owner.json').exists()and(td/'squeue.log').exists():break
        time.sleep(0.05)
    assert (lock/'owner.json').exists(),'first resubmit did not take the lock'
    for script,args in (('resubmit.sh',[]),('submit.sh',[]),('submit.sh',['--window','0:0'])):   # (i) concurrent calls refuse
        cp=subprocess.run(['bash',str(ROOT/'slurm'/script),*args],capture_output=True,text=True,env=base)
        assert cp.returncode==75 and 'holds'in cp.stderr,(script,cp.returncode,cp.stderr[-300:])
    assert not(td/'sbatch.log').exists()  # the first call is still blocked in its first sbatch; the refused calls submitted nothing
    with open(fifo,'w')as f:f.write('go\n')
    out,err=first.communicate(timeout=300);assert first.returncode==0,err[-500:]
    assert not lock.exists()
    mid=[c.split()[0]for c in (td/'sbatch.log').read_text().splitlines()if 'merge.sh'in c][0]
    cp,calls=call('resubmit.sh',[f'{tag}:merge|N/A|PENDING|{mid}']);assert cp.returncode==65 and not calls and not lock.exists()   # (ii)
    cp,calls=call('resubmit.sh',[],FAKE_SQUEUE_FAIL='1');assert cp.returncode==69 and not calls and not lock.exists()             # (iii)
    for script in ('resubmit.sh','submit.sh'):
        cp,calls=call(script,lines,FAKE_SBATCH_FAIL='1');assert cp.returncode not in (0,75) and not lock.exists(),(script,cp.returncode)
    lock.mkdir();(lock/'owner.json').write_text('{"host":"elsewhere","pid":1}\n');qlen=len((td/'squeue.log').read_text().splitlines())
    for script,args in (('resubmit.sh',[]),('submit.sh',[]),('submit.sh',['--window','0:0'])):                                   # (iv)
        cp,calls=call(script,lines,args);assert cp.returncode==75 and not calls and 'elsewhere'in cp.stderr,(script,cp.returncode,cp.stderr[-300:])
    assert len((td/'squeue.log').read_text().splitlines())==qlen and lock.exists()
    shutil.rmtree(lock)
    # R-LOCK-02: a failure while writing owner.json releases this invocation's lock.
    import importlib,unittest.mock as um;ss=importlib.import_module('slurm_submit');real=Path.write_text
    def boom(self,*a,**k):
        if self.name=='owner.json':raise OSError(28,'No space left on device (injected)')
        return real(self,*a,**k)
    with um.patch.object(Path,'write_text',boom):
        try:
            with ss.CampaignLock(d,'test'):pass
        except OSError:pass
        else:raise AssertionError('owner.json failure not raised')
    assert not lock.exists(),'lock left behind after an owner.json failure'
    # R-SLURM-01: a '%' in the campaign path is escaped in --output (Slurm filename patterns), for work and merge jobs.
    pct=td/'run%jdir%%x';plan(pkg,pct,'--points',4,'--chunk-points',2)
    cp,calls=call('submit.sh',C6_RUN=str(pct));assert cp.returncode==0 and calls,cp.stderr[-400:]
    esc=str(pct.resolve()/'slurm_logs').replace('%','%%')
    outs=[last(argv(c),'--output')for c in calls]
    assert all(o.startswith(esc+'/')for o in outs)and any('/work-%A_%a.log'in o for o in outs)and any('/merge-%j.log'in o for o in outs),outs
    ok('slurm_helpers_fake',resubmitted=[C,D],live=[A,B],submission_lock=['concurrent calls refused (75)','later call sees the live merge (65)','removed after 69 and sbatch failure','existing lock refuses before any Slurm call'])

def test_sbatch_allowlist():
    import importlib;sys.path.insert(0,str(ROOT/'tools'));prod=importlib.import_module('production')
    good=[[],['-A','yun124','-p','shared'],['-Ayun124','--partition=shared','--time=00:10:00','-c','4','--mem=8G','--qos=normal','--requeue','-J','x']]
    bad=[['--nice','--export-file=f'],['--nice'],['--nice=5'],['--export-file=f'],['--export-f=f'],['--export=ALL'],['--arr=0-3'],['--array','0-3'],['-a','0-3'],['-a0-3'],['--dep','x'],['-d','afterok:1'],
         ['--comment=x'],['--comm=x'],['-o','x'],['--output=x'],['--parsable'],['-M','other'],['--clusters=x'],['foo'],['--nodes=2'],['--wrap=cmd'],['-A'],['--time']]
    assert all(prod.check_sbatch_args(g)is None for g in good),[prod.check_sbatch_args(g)for g in good]
    assert all(prod.check_sbatch_args(b)for b in bad),[b for b in bad if not prod.check_sbatch_args(b)]
    ok('sbatch_allowlist',refused=len(bad))

def run():
    test_archived_seeds();test_sbatch_allowlist()
    with tempfile.TemporaryDirectory(prefix='c6_orch_')as td:
        td=Path(td);pkg=make_package(td)
        test_plan_guards(pkg,td);test_plan_allocation_and_order(pkg,td);test_points_override(pkg,td);test_pipeline(pkg,td);test_concurrent_merge_and_uri_path(pkg,td)
        test_recovery_plan(pkg,td);test_slurm_helpers_fake(pkg,td)
    return {'status':'passed','tests':RESULTS}
if __name__=='__main__':print(json.dumps(run(),indent=2,default=str))
