#!/usr/bin/env python3
"""Plan, run, checkpoint, check and merge complete d=2 C6 RQMC campaigns.

Scientific stream identities are (group, replicate, graph, point), independent
of nodes, thread counts, shard IDs and checkpoint boundaries. A chunk is NEVER
an independent statistical replicate. SQLite makes task sorting/merging disk
backed. The native process handles at most checkpoint_tasks at a time, and runs
only from a verified job-private copy of the executable and inputs.
"""
from __future__ import annotations
import argparse,decimal,hashlib,heapq,itertools,json,math,os,shlex,shutil,sqlite3,struct,subprocess,sys,tempfile,time
from pathlib import Path
import numpy as np
from common import ROOT,canon,checked,digest,dump,load,object_hash,pow2,publish,umask_mode
from prepare_inputs import prepare,PIDS
import primitive_allocation as pa
D=decimal.Decimal
SCHEMA='c6-d2-production-2'
TOOLS=('production.py','assemble.py','common.py','prepare_inputs.py','primitive_allocation.py')
MAX_ARRAY=1000  # Expanse MaxArraySize: array indices 0..999
RETAINED_PRIMITIVE_SE=0.041404328278345545
# Seconds per estimated cost unit on one core, measured on SDSC Expanse (AMD EPYC 7742, GCC 13.3 -O3, job 54499273,
# 2026-09-28; sum of native task seconds / shard cost): L6 4.2-4.9e-9 (a_L6 with grid, b_L6 without), L5 6.3e-9.
# L3/L4 use the L5 value. Planning estimates only.
CALIBRATION={'hardware':'SDSC Expanse AMD EPYC 7742 (one core), GCC 13.3 -O3','date':'2026-09-28','source':'job 54499273',
             'seconds_per_cost_unit':{'3':6.3e-9,'4':6.3e-9,'5':6.3e-9,'6':4.7e-9},'assumed_thread_efficiency':0.85}

def dbopen(path:Path,readonly=False):
    c=sqlite3.connect(f'file:{path}?mode=ro' if readonly else str(path),uri=readonly)
    c.execute('PRAGMA cache_size=-8192');c.execute('PRAGMA temp_store=FILE');return c

def make_net(path:Path,B:int,dim:int,bits:int,seed:int):
    from scipy.stats import qmc
    import scipy
    rng=np.random.default_rng(seed)
    with path.open('xb')as f:
        f.write(struct.pack('<III',B,dim,bits))
        for b in range(B):
            engine=qmc.Sobol(d=dim,scramble=True,bits=bits,seed=int(rng.integers(1,2**32-1)))
            # Freeze matrices. Verify the private export against the PUBLIC API
            # every time rather than assuming a particular future SciPy layout.
            sv=engine._sv.copy();state=engine._shift.copy();pts=[]
            for n in range(16):
                if n:state^=sv[:,(n&-n).bit_length()-1]
                pts.append(state.copy())
            if not np.array_equal(np.array(pts,dtype=np.float64)/2**bits,engine.random_base2(4)):
                raise RuntimeError('SciPy Sobol matrix export does not reconstruct public API')
            f.write(sv.astype('<u8').tobytes())
    return {'scipy':scipy.__version__,'seed':seed,'B':B,'dim':dim,'bits':bits,'sha256':digest(path),'public_API_points_checked':16*B}

LEGACY_OFFSETS={'a':(0,0),'b':(0x614ef703,12347771)}
def derive_seeds(seed:int,campaign:str,L:int,scheme:str)->dict:
    """Native (digital-shift) and net seeds of one group. 'legacy' is the archived driver arithmetic, kept for replay
    tests; 'hashed' (default) makes every group's seeds independent functions of the user seed."""
    if campaign not in LEGACY_OFFSETS:raise ValueError('unknown campaign')
    if scheme=='legacy':
        native,net=LEGACY_OFFSETS[campaign];return {'native':(seed+L*1279+native)%(2**64),'net':(seed+18743*L+net)%(2**63)}
    if scheme!='hashed':raise ValueError('unknown seed scheme '+str(scheme))
    h=lambda role:int.from_bytes(hashlib.sha256(f'c6-d2|{seed}|{campaign}|L{L}|{role}'.encode()).digest()[:8],'little')%(2**63)
    return {'native':h('native'),'net':h('net')}

def archived_base_seeds()->set[int]:
    return {int(p['seed'])for p in load(ROOT/'reference/inputs/frozen_production_plan.json')['plan']}

def self_test(exe:Path):
    """Run the executable on one tiny task before its hash is frozen (a foreign or stale binary fails here)."""
    advice=f'the executable {exe} does not run on this machine; rebuild it on this architecture with `make clean && make`'
    inv=load(ROOT/'inputs/inventory.json');g=inv['3'][0]['id']
    with tempfile.TemporaryDirectory(prefix='c6_selftest_')as td:
        td=Path(td);make_net(td/'net.bin',2,11,52,20260928)  # the native worker requires B>=2; replicate 0 is used
        (td/'tasks.txt').write_text(f'C6TASKS1 3 1\n0 0 {g} 0 4 4\n')
        cmd=[str(exe),str(ROOT/'inputs/graphs'),str(ROOT/'inputs/gamma_d2.txt'),str(td/'net.bin'),str(td/'tasks.txt'),str(td/'out.json'),'1','0','1','1','compensated','-']
        try:cp=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        except (OSError,subprocess.SubprocessError)as e:raise RuntimeError(f'Self-test failed ({e}): {advice}')from e
        if cp.returncode:raise RuntimeError(f'Self-test failed (exit {cp.returncode}: {(cp.stderr or cp.stdout)[-2000:].strip()}): {advice}')
        try:n=json.loads((td/'out.json').read_text());ok=n['schema']=='c6-d2-native-1'and len(n['rows'])==1 and all(D(v).is_finite()for v in n['rows'][0]['values'])
        except Exception as e:raise RuntimeError(f'Self-test produced unreadable output ({e}): {advice}')from e
        if not ok:raise RuntimeError('Self-test produced invalid output: '+advice)

def plan(a):
    out=a.directory.resolve();exe=ROOT/'bin/c6_integrate'
    # All argument checks come before any filesystem or native work.
    if out.exists():raise FileExistsError('Use a new campaign directory')
    if a.replicates<2 or a.shards<1 or a.threads<1 or a.checkpoint_tasks<1 or a.chunk_points<1:raise ValueError('invalid sizes')
    if a.checkpoint_tasks>100000:raise ValueError('checkpoint_tasks exceeds the native task-file limit (100000)')
    if not pow2(a.multiplier)or not pow2(a.primitive_points)or(a.points is not None and not pow2(a.points)):raise ValueError('point counts and multipliers must be powers of two')
    if not 0<=a.seed<2**63:raise ValueError('seed must be in [0,2^63)')
    if a.seed_scheme=='legacy'and a.seed in archived_base_seeds():
        raise ValueError(f'seed {a.seed} is an archived production base seed (reference/inputs/frozen_production_plan.json); '
                         'under --seed-scheme legacy it would replay archived streams. Choose a fresh seed.')
    prepare();inv=load(ROOT/'inputs/inventory.json')
    table=load(ROOT/'inputs/primitive_allocation_d2.json');n_uniform=a.primitive_points*a.multiplier;prim=None
    if a.primitive_mode=='recompute'and a.points is None:
        if n_uniform<4:raise ValueError('recompute mode needs primitive_points x multiplier >= 4 per primitive '
                                        '(use --points for tiny smoke plans, or --primitive-mode retained)')
        prim=pa.allocate(table,n_uniform,52)if a.primitive_allocation=='neyman'else pa.uniform(n_uniform)
    if not exe.exists():raise FileNotFoundError('Run make first: '+str(exe))
    self_test(exe)
    out.mkdir(parents=True);(out/'groups').mkdir();pending=[]
    for campaign in ('a','b'):
        for L in range(3,7):
            name=f'{campaign}_L{L}';p=out/'groups'/name;p.mkdir();rows=inv[str(L)]
            frozen=load(ROOT/f'inputs/counts_L{L}.json')
            # The archive's frozen tables map IDs directly to point counts.
            if 'counts' in frozen:frozen=frozen['counts']
            counts={r['id']:int(frozen.get(str(r['id']),0))for r in rows}
            for r in rows:
                gi=r['id']
                if L==6 and gi in PIDS:
                    # --points overrides every stratum, primitives included; otherwise the frozen primitive allocation.
                    counts[gi]=0 if a.primitive_mode=='retained'else(a.points*a.multiplier if a.points is not None else prim[gi])
                else:counts[gi]=(a.points if a.points is not None else max(4,counts[gi]))*a.multiplier
            bits=52 if campaign=='a'else 60;layout=0;seeds=derive_seeds(a.seed,campaign,L,a.seed_scheme)
            if max(counts.values())>2**bits:raise ValueError('Sobol period exceeded')
            net=make_net(p/'sobol.bin',a.replicates,4*L-1,bits,seeds['net'])
            grid='grid_d2_top11.txt'if(a.grid=='frozen'and campaign=='a'and L==6)else None
            db=dbopen(p/'tasks.sqlite');db.executescript('CREATE TABLE tasks(uid INTEGER PRIMARY KEY,rep INTEGER,gi INTEGER,lo INTEGER,hi INTEGER,total INTEGER,cost REAL,shard INTEGER,pos INTEGER); CREATE TABLE expected(rep INTEGER,gi INTEGER,total INTEGER,PRIMARY KEY(rep,gi));')
            uid=0;total_cost=0.
            for rep in range(a.replicates):
                for row in rows:
                    gi=row['id'];total=counts[gi];db.execute('INSERT INTO expected VALUES(?,?,?)',(rep,gi,total))
                    for start in range(0,total,a.chunk_points):
                        stop=min(total,start+a.chunk_points);cost=(stop-start)*max(32,row['additions']);total_cost+=cost
                        db.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,NULL,NULL)',(uid,rep,gi,start,stop,total,cost));uid+=1
            db.commit()
            pending.append(dict(name=name,campaign=campaign,L=L,p=p,db=db,tasks=uid,cost=total_cost,seed=seeds['native'],layout=layout,counts=counts,net=net,grid=grid))
    cmax=max(g['cost']for g in pending);groups=[];jobs=[];estimates={}
    for g in pending:
        want=a.shards if a.shard_policy=='uniform'else max(1,round(a.shards*g['cost']/cmax))
        nshards=min(want,g['tasks']);db=g['db'];heap=[(0.,i)for i in range(nshards)];heapq.heapify(heap);shard_cost=[0.]*nshards
        # Greedy longest-processing-time shard assignment on estimated cost. Both passes stream from SQLite's sorter
        # (file-backed, no index on the sort keys) and write in bounded batches: Python memory stays O(shards).
        def batched(query,update,step):
            out=db.cursor();buf=[]
            for row in db.execute(query):
                buf.append(step(row))
                if len(buf)>=100000:out.executemany(update,buf);buf.clear()
            if buf:out.executemany(update,buf)
        def lpt(row):
            tid,cost=row;c,i=heapq.heappop(heap);heapq.heappush(heap,(c+cost,i));shard_cost[i]+=cost;return (i,tid)
        batched('SELECT uid,cost FROM tasks ORDER BY cost DESC,uid','UPDATE tasks SET shard=? WHERE uid=?',lpt)
        # Frozen position inside each shard: estimated cost descending, so a checkpoint block holds similar tasks.
        state={'shard':None,'pos':0}
        def position(row):
            tid,shard=row
            if shard!=state['shard']:state.update(shard=shard,pos=0)
            state['pos']+=1;return (state['pos']-1,tid)
        batched('SELECT uid,shard FROM tasks ORDER BY shard,cost DESC,uid','UPDATE tasks SET pos=? WHERE uid=?',position)
        db.execute('CREATE INDEX shard_order ON tasks(shard,pos)');db.execute('CREATE INDEX stream_order ON tasks(rep,gi,lo)');db.commit();db.close()
        spu=CALIBRATION['seconds_per_cost_unit'][str(g['L'])];eff=CALIBRATION['assumed_thread_efficiency']
        estimates[g['name']]={'core_hours':g['cost']*spu/3600,'shards':nshards,'max_shard_wall_seconds':max(shard_cost)*spu/(a.threads*eff)}
        config={'schema':'c6-d2-group-2','name':g['name'],'campaign':g['campaign'],'L':g['L'],'seed':g['seed'],'seed_scheme':a.seed_scheme,'layout':g['layout'],'rate':'1','replicates':a.replicates,'counts':{str(k):v for k,v in g['counts'].items()},'net':g['net'],'grid':g['grid'],'sum_mode':a.sum_mode,'primitive_mode':a.primitive_mode,'shards':nshards,'block_order':'pos: estimated cost descending, then uid','tasks':g['tasks'],'tasks_sha256':digest(g['p']/'tasks.sqlite'),'samples':sum(g['counts'].values())*a.replicates}
        dump(g['p']/'config.json',config);groups.append({'name':g['name'],'sha256':digest(g['p']/'config.json')})
        base_id=len(jobs);jobs.extend({'id':base_id+i,'group':g['name'],'shard':i}for i in range(nshards))
    wall=max(e['max_shard_wall_seconds']for e in estimates.values());suggested=max(900,math.ceil(3*wall/60)*60)
    primitive=None
    if prim is not None:
        primitive={'allocation':a.primitive_allocation,'counts':{str(k):v for k,v in prim.items()},'n_uniform':n_uniform,
                   'projected_block_se':pa.projected_se(table,prim,a.replicates),'projected_uniform_block_se':pa.projected_se(table,pa.uniform(n_uniform),a.replicates),
                   'table_sha256':digest(ROOT/'inputs/primitive_allocation_d2.json'),'note':'MC-scaling projection from archived pilot variances; not an error estimate'}
    manifest={'schema':SCHEMA,'tool_sha256':{name:digest(ROOT/'tools'/name)for name in TOOLS},'dimension':2,'epsilon':'2s-2','package':str(ROOT),'inputs_manifest_sha256':digest(ROOT/'inputs/manifest.json'),'executable_sha256':digest(exe),'executable_self_test':'passed','threads':a.threads,'checkpoint_tasks':a.checkpoint_tasks,'primitive_mode':a.primitive_mode,'primitive_allocation':primitive,'seed':a.seed,'seed_scheme':a.seed_scheme,'shard_policy':a.shard_policy,'groups':groups,'jobs':jobs,'campaign_weights':{'a':.5,'b':.5},'groups_independent_by_loop_and_campaign':True,'sampling_unit':'complete independently randomized graph-summed replicate; never a chunk','analytic_power_compensation':'retained from the separately audited reference calculation; not recomputed by this package','point_override':a.points,'allocation_multiplier':a.multiplier,'primitive_points':a.primitive_points,'grid':a.grid,
              'estimates':{'calibration':CALIBRATION,'groups':estimates,'total_core_hours':sum(e['core_hours']for e in estimates.values()),'max_shard_wall_seconds':wall,'suggested_time_seconds':suggested,'note':'estimates from a hardware-specific calibration, not measurements'}}
    dump(out/'manifest.json',manifest)
    if len(jobs)>MAX_ARRAY:print(f'warning: {len(jobs)} jobs exceed a single array of {MAX_ARRAY}; submit with slurm/submit.sh (splits arrays with C6_INDEX_OFFSET)',file=sys.stderr)
    if primitive and primitive['projected_block_se']>RETAINED_PRIMITIVE_SE:
        print(f'warning: projected primitive-block SE {primitive["projected_block_se"]:.3g} exceeds the retained input\'s {RETAINED_PRIMITIVE_SE:.3g}; raise --primitive-points or --multiplier',file=sys.stderr)
    print(json.dumps({'directory':str(out),'jobs':len(jobs),'samples':sum(load(out/'groups'/g['name']/'config.json')['samples']for g in groups),'primitive_mode':a.primitive_mode,
                      'estimated_core_hours':round(manifest['estimates']['total_core_hours'],3),'estimated_max_shard_wall_seconds':round(wall,1),'suggested_sbatch_time':hms(suggested),
                      'projected_primitive_block_se':primitive and round(primitive['projected_block_se'],4)},indent=2))

def hms(seconds:int)->str:
    d,s=divmod(int(seconds),86400);return (f'{d}-'if d else'')+time.strftime('%H:%M:%S',time.gmtime(s))

def read_verified(path:Path,expected:str)->dict:
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=expected:raise ValueError(f'Checksum mismatch: {path}')
    return json.loads(data)

def verify_base(directory:Path,check_executable=True):
    data=(directory/'manifest.json').read_bytes();m=json.loads(data);mh=hashlib.sha256(data).hexdigest()
    if m.get('schema')!=SCHEMA:raise ValueError(f'campaign schema {m.get("schema")} is not {SCHEMA}; plans made by older tools must be re-planned')
    for name,h in m.get('tool_sha256',{}).items():checked(ROOT/'tools'/name,h)
    im=read_verified(ROOT/'inputs/manifest.json',m['inputs_manifest_sha256'])
    if check_executable:checked(ROOT/'bin/c6_integrate',m['executable_sha256'])
    return m,im,mh

def rows_for(db,shard):
    return db.execute('SELECT uid,rep,gi,lo,hi,total FROM tasks WHERE shard=? ORDER BY pos',(shard,))

def validate_checkpoint(doc,block,config,m,mh):
    if doc.get('manifest_sha256')!=mh or doc.get('config_hash')!=object_hash(config):raise ValueError('checkpoint identity mismatch')
    rt=doc.get('runtime')or{}
    if doc.get('executable_sha256')!=m['executable_sha256']or rt.get('executable_sha256')!=m['executable_sha256']:raise ValueError('checkpoint was produced by a different executable')
    if rt.get('inputs_manifest_sha256')!=m['inputs_manifest_sha256']:raise ValueError('checkpoint was produced from different inputs')
    if rt.get('net_sha256')!=config['net']['sha256']:raise ValueError('checkpoint was produced from a different Sobol net')
    n=doc['native']
    if object_hash(n)!=doc.get('payload_sha256'):raise ValueError('checkpoint payload corruption')
    for k,v in [('schema','c6-d2-native-1'),('L',config['L']),('seed',config['seed']),('layout',config['layout']),('bits',config['net']['bits']),('sum_mode',config['sum_mode'])]:
        if n.get(k)!=v:raise ValueError('native metadata mismatch: '+k)
    if D(n['rate'])!=D(config['rate']):raise ValueError('rate mismatch')
    if len(n['rows'])!=len(block):raise ValueError('incomplete checkpoint')
    for expected,r in zip(block,n['rows']):
        if tuple(r[k]for k in ('uid','rep','graph','begin','end','total'))!=tuple(expected):raise ValueError('wrong task coordinates')
        if len(r['values'])!=2*(7-config['L'])or any(not D(v).is_finite()for v in r['values']):raise ValueError('invalid jet')
        if not 0<=r['mp']<=r['quad']<=r['end']-r['begin']:raise ValueError('invalid fallback counters')
    return n

def group_of(directory:Path,m:dict,name:str):
    p=directory/'groups'/name;config=read_verified(p/'config.json',next(g['sha256']for g in m['groups']if g['name']==name));checked(p/'tasks.sqlite',config['tasks_sha256']);return p,config

def stage_runtime(runtime:Path,m:dict,im:dict,config:dict,graphs:set[int],net:Path)->dict:
    """Copy the executable, the group's Sobol net and exactly the needed inputs into a job-private directory; verify
    every COPY and use only the copies."""
    exe=runtime/'c6_integrate';shutil.copyfile(ROOT/'bin/c6_integrate',exe);os.chmod(exe,0o700)
    exe_sha=digest(exe)
    if exe_sha!=m['executable_sha256']:raise ValueError('bin/c6_integrate differs from the planned executable; never rebuild inside a campaign')
    names=['gamma_d2.txt']+([config['grid']]if config['grid']else[])+[f'graphs/L{config["L"]}/G{gi}.txt'for gi in sorted(graphs)]
    for rel in names:
        dst=runtime/'inputs'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'inputs'/rel,dst);checked(dst,im['sha256'][rel])
    netcopy=runtime/'sobol.bin';shutil.copyfile(net,netcopy);net_sha=digest(netcopy)
    if net_sha!=config['net']['sha256']:raise ValueError('the Sobol net differs from the plan: '+str(net))
    return {'executable':exe,'inputs':runtime/'inputs','net':netcopy,'executable_sha256':exe_sha,'inputs_manifest_sha256':m['inputs_manifest_sha256'],'net_sha256':net_sha}

def run(a):
    directory=a.directory.resolve();m,im,mh=verify_base(directory);idx=a.index
    if idx is None:
        if 'SLURM_ARRAY_TASK_ID'not in os.environ:raise ValueError('give --index or run inside a Slurm array (SLURM_ARRAY_TASK_ID)')
        idx=int(os.environ.get('C6_INDEX_OFFSET','0'))+int(os.environ['SLURM_ARRAY_TASK_ID'])
    if not 0<=idx<len(m['jobs']):raise ValueError('job index outside plan')
    j=m['jobs'][idx];p,config=group_of(directory,m,j['group']);checked(p/'sobol.bin',config['net']['sha256'])
    threads=a.threads or m['threads'];T=m['checkpoint_tasks']
    if threads<1:raise ValueError('invalid thread count')
    if threads>T:raise ValueError(f'{threads} threads exceed checkpoint_tasks={T}: at most {T} threads can ever be busy; use fewer threads or re-plan')
    if T<16*threads:print(f'warning: checkpoint_tasks={T} < 16 x {threads} threads; per-block barriers and start-up will idle cores',file=sys.stderr)
    scratch=a.scratch or os.environ.get('SLURM_TMPDIR')or None
    db=dbopen(p/'tasks.sqlite',True);graphs={gi for (gi,)in db.execute('SELECT DISTINCT gi FROM tasks WHERE shard=?',(j['shard'],))}
    runtime=Path(tempfile.mkdtemp(prefix='c6_d2_runtime_',dir=scratch))
    try:
        rt=stage_runtime(runtime,m,im,config,graphs,p/'sobol.bin');cursor=rows_for(db,j['shard']);part=0;done=0
        (p/'checkpoints').mkdir(exist_ok=True);(p/'logs').mkdir(exist_ok=True)
        grid=rt['inputs']/config['grid']if config['grid']else None
        while block:=list(itertools.islice(cursor,T)):
            name=f's{j["shard"]:06d}_p{part:06d}';dest=p/'checkpoints'/f'{name}.json';part+=1
            if dest.exists():validate_checkpoint(load(dest),block,config,m,mh);continue
            if a.max_blocks is not None and done>=a.max_blocks:print(f'stopped after {done} blocks (--max-blocks)',flush=True);break
            with tempfile.TemporaryDirectory(prefix='c6_d2_',dir=runtime)as td:
                td=Path(td);tasks=td/'tasks.txt';tasks.write_text(f'C6TASKS1 {config["L"]} {len(block)}\n'+''.join(' '.join(map(str,r))+'\n'for r in block));out=td/'native.json'
                cmd=[str(rt['executable']),str(rt['inputs']/'graphs'),str(rt['inputs']/'gamma_d2.txt'),str(rt['net']),str(tasks),str(out),str(config['seed']),str(config['layout']),config['rate'],str(threads),config['sum_mode'],str(grid)if grid else'-']
                try:
                    with (td/'native.log').open('w')as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
                except subprocess.CalledProcessError as exc:
                    message=(td/'native.log').read_text()
                    publish(p/'logs'/f'{name}.failure.{time.time_ns()}.log',message)
                    raise RuntimeError('Native work block failed: '+message[-4000:]) from exc
                n=load(out);doc={'manifest_sha256':mh,'config_hash':object_hash(config),'native':n,'payload_sha256':object_hash(n),'executable_sha256':rt['executable_sha256'],'task_file_sha256':digest(tasks),
                                 'runtime':{'executable_sha256':rt['executable_sha256'],'inputs_manifest_sha256':rt['inputs_manifest_sha256'],'net_sha256':rt['net_sha256']}}
                validate_checkpoint(doc,block,config,m,mh)
                try:dump(dest,doc)
                except FileExistsError:
                    prior=validate_checkpoint(load(dest),block,config,m,mh)
                    if prior['rows']!=n['rows']:
                        # Wall-clock fields differ on a duplicate execution; compare scientific fields.
                        for x,y in zip(prior['rows'],n['rows']):
                            if any(x[k]!=y[k]for k in ('uid','rep','graph','begin','end','total','values','quad','mp','max_abs')):raise ValueError('conflicting duplicate result')
                done+=1;print(f'committed {j["group"]}/{name}',flush=True)
    finally:
        db.close();shutil.rmtree(runtime,ignore_errors=True)

def validate_merged(p:Path,config:dict,m:dict,mh:str)->dict:
    d=load(p/'merged.json')
    if d.get('schema')!='c6-d2-merged-1'or d.get('complete')is not True or d.get('manifest_sha256')!=mh or d.get('config_hash')!=object_hash(config)or d.get('primitive_mode')!=m['primitive_mode']or d.get('L')!=config['L']:
        raise ValueError('existing merged.json does not belong to this plan: '+str(p/'merged.json'))
    if object_hash({k:v for k,v in d.items()if k!='payload_sha256'})!=d.get('payload_sha256'):raise ValueError('merged payload checksum mismatch: '+str(p/'merged.json'))
    checked(p/'graph_replicates.csv',d['graph_replicates_sha256'])
    if len(d['batches'])!=config['replicates']or d.get('replicates')!=config['replicates']:raise ValueError('merged replicate count mismatch')
    return d

def blocks_of(db,shard,T):
    n=db.execute('SELECT COUNT(*) FROM tasks WHERE shard=?',(shard,)).fetchone()[0];return (n+T-1)//T

def merge_group(directory:Path,m:dict,name:str,scratch=None,mh=None):
    p,config=group_of(directory,m,name);mh=mh or digest(directory/'manifest.json')
    dest=p/'merged.json'
    if dest.exists():validate_merged(p,config,m,mh);print(f'{name}: already merged and valid; skipped',flush=True);return dest
    source=dbopen(p/'tasks.sqlite',True);dim=2*(7-config['L']);fallbacks={'quad':0,'mp':0};count=0;seconds=0
    with tempfile.TemporaryDirectory(prefix='c6_merge_',dir=scratch)as td:
        db=dbopen(Path(td)/'merge.sqlite');db.execute('CREATE TABLE actual(uid INTEGER PRIMARY KEY,rep INTEGER,gi INTEGER,lo INTEGER,hi INTEGER,total INTEGER,vals TEXT)')
        for shard in range(config['shards']):
            cur=rows_for(source,shard);part=0
            while block:=list(itertools.islice(cur,m['checkpoint_tasks'])):
                f=p/'checkpoints'/f's{shard:06d}_p{part:06d}.json';part+=1
                if not f.exists():raise FileNotFoundError('Incomplete campaign: '+str(f))
                n=validate_checkpoint(load(f),block,config,m,mh);seconds+=n['integration_seconds']
                for r in n['rows']:
                    db.execute('INSERT INTO actual VALUES(?,?,?,?,?,?,?)',(r['uid'],r['rep'],r['graph'],r['begin'],r['end'],r['total'],json.dumps(r['values'])));count+=1
                    for k in fallbacks:fallbacks[k]+=r[k]
        if count!=config['tasks']:raise ValueError('wrong total task coverage')
        db.commit();db.execute('CREATE INDEX stream_sort ON actual(rep,gi,lo)')
        batches=[];csvtmp=Path(td)/'graph_replicates.csv';actual=iter(db.execute('SELECT rep,gi,lo,hi,total,vals FROM actual ORDER BY rep,gi,lo'));r=next(actual,None)
        with decimal.localcontext()as ctx,csvtmp.open('w')as f:
            ctx.prec=50;f.write('replicate,graph,'+','.join(f'jet_{i}'for i in range(dim))+'\n');batch=[D(0)]*dim;prevrep=0
            for rep,gi,total in source.execute('SELECT rep,gi,total FROM expected ORDER BY rep,gi'):
                if rep!=prevrep:batches.append([float(v)for v in batch]);batch=[D(0)]*dim;prevrep=rep
                graph=[D(0)]*dim;end=0
                while r is not None and (r[0],r[1])==(rep,gi):
                    rr,gg,lo,hi,tt,vals=r
                    if lo!=end or tt!=total or not 0<=lo<hi<=total:raise ValueError('incomplete, overlapping or inconsistent sample intervals')
                    graph=[x+D(v)for x,v in zip(graph,json.loads(vals))];end=hi;r=next(actual,None)
                if end!=total:raise ValueError(f'missing samples rep={rep},graph={gi}')
                f.write(f'{rep},{gi},'+','.join(map(str,graph))+'\n');batch=[x+y for x,y in zip(batch,graph)]
            if r is not None:raise ValueError('unexpected streams')
            batches.append([float(v)for v in batch])
        if len(batches)!=config['replicates']:raise ValueError('missing replicates')
        # Stream-copy the optional diagnostic table; never construct B x G x jet in RAM.
        target=p/'graph_replicates.csv'
        if target.exists():
            checked(target,digest(csvtmp))
        else:
            fd,tname=tempfile.mkstemp(prefix='graph_replicates.tmp.',dir=p)
            try:
                os.fchmod(fd,umask_mode())
                with csvtmp.open('rb')as i,os.fdopen(fd,'wb')as o:
                    shutil.copyfileobj(i,o);o.flush();os.fsync(o.fileno())
                try:os.link(tname,target)
                except FileExistsError:checked(target,digest(csvtmp))
            finally:os.unlink(tname)
        merged={'schema':'c6-d2-merged-1','complete':True,'L':config['L'],'dimension':2,'config_hash':object_hash(config),'manifest_sha256':mh,'replicates':config['replicates'],'samples':config['samples'],'primitive_mode':config['primitive_mode'],'batches':batches,'fallbacks':fallbacks,'integration_seconds_sum':seconds,'graph_replicates_sha256':digest(target)}
        merged['payload_sha256']=object_hash(merged)
        dump(dest,merged);db.close()
    source.close();return dest

def merge(a):
    directory=a.directory.resolve();m,_,mh=verify_base(directory,check_executable=False)
    names=[a.group]if a.group else[g['name']for g in m['groups']]
    if any(n not in {g['name']for g in m['groups']}for n in names):raise ValueError('unknown group')
    for n in names:print(merge_group(directory,m,n,a.scratch,mh),flush=True)

def campaign_tag(directory:Path)->str:
    """Slurm --comment tag of one campaign's jobs: c6:<sha256(resolved campaign path + manifest sha256)[:12]>.
    Identically planned campaigns in different directories get different tags. Do not move a campaign directory
    while its jobs are queued (the tag would change)."""
    d=Path(directory).resolve();return 'c6:'+hashlib.sha256(f'{d}\n{digest(d/"manifest.json")}'.encode()).hexdigest()[:12]

def ranges(ids):
    out=[];ids=sorted(ids)
    for k,g in itertools.groupby(enumerate(ids),lambda t:t[1]-t[0]):
        g=[x for _,x in g];out.append(str(g[0])if len(g)==1 else f'{g[0]}-{g[-1]}')
    return ','.join(out)

def windows(indices,size:int)->list[dict]:
    """Rebase global job indices into array windows [off, off+size) with in-window task ids."""
    if size<1:raise ValueError('array window size must be positive')
    return [{'offset':off,'array':ranges([i-off for i in indices if off<=i<off+size])}for off in sorted({i//size*size for i in indices})]

def status_report(directory:Path,exclude=(),max_array:int=MAX_ARRAY,listing=False):
    directory=directory.resolve();m,_,mh=verify_base(directory,check_executable=False);T=m['checkpoint_tasks'];missing=[];groups={};lines=[]
    for g in m['groups']:
        p,config=group_of(directory,m,g['name']);db=dbopen(p/'tasks.sqlite',True);done_g=total_g=0
        for j in (j for j in m['jobs']if j['group']==g['name']):
            nb=blocks_of(db,j['shard'],T);have=sum((p/'checkpoints'/f's{j["shard"]:06d}_p{k:06d}.json').exists()for k in range(nb))
            done_g+=have;total_g+=nb
            if have<nb:missing.append(j['id'])
            if have<nb or listing:lines.append(f'job {j["id"]:6d} {g["name"]} shard {j["shard"]:4d}: {have}/{nb} blocks')
        db.close();groups[g['name']]={'committed':done_g,'total':total_g,'merged':(p/'merged.json').exists()}
        lines.append(f'group {g["name"]}: {done_g}/{total_g} blocks, {"merged"if groups[g["name"]]["merged"]else"not merged"}')
    active=sorted(set(exclude)&set(missing));todo=[i for i in missing if i not in active]
    return {'complete':not missing,'missing_jobs':missing,'active_not_resubmitted':active,'groups':groups,'result_present':(directory/'C6_result.json').exists(),
            'threads':m['threads'],'suggested_time':hms(m['estimates']['suggested_time_seconds']),'resubmit':windows(todo,max_array),'campaign_tag':campaign_tag(directory),'lines':lines}

def parse_ids(text):return [int(x)for x in filter(None,(text or'').split(','))]

def status(a):
    """Committed/total checkpoint blocks per job index; exit 0 only when every block is committed."""
    size=a.max_array if getattr(a,'max_array',None)is not None else None
    if size is None:  # the site's array limit, as submit.sh/resubmit.sh use it
        env=os.environ.get('C6_MAX_ARRAY','')
        if env and not env.isdigit():raise ValueError('C6_MAX_ARRAY must be a positive integer')
        size=int(env)if env else MAX_ARRAY
    r=status_report(a.directory,parse_ids(getattr(a,'exclude',None)),size,getattr(a,'all',False));lines=r.pop('lines')
    if getattr(a,'json',False):print(json.dumps(r))
    else:
        print('\n'.join(lines));print('result: '+('C6_result.json present'if r['result_present']else'no C6_result.json'))
        if r['missing_jobs']:
            print(f'{len(r["missing_jobs"])} incomplete job indices: {ranges(r["missing_jobs"])}')
            if r['active_not_resubmitted']:print(f'still queued or running (not resubmitted): {ranges(r["active_not_resubmitted"])}')
            for w in r['resubmit']:
                # Each line goes through the same guarded submission path as submit.sh/resubmit.sh (tools/slurm_submit.py),
                # with the campaign and package bound explicitly; site options come from the (validated) C6_SBATCH_ARGS.
                print(f'resubmit: C6_MAX_ARRAY={size} C6_RUN={shlex.quote(str(Path(a.directory).resolve()))} C6_PACKAGE={shlex.quote(str(ROOT))} '
                      f'{shlex.quote(str(ROOT/"slurm/submit.sh"))} --window {w["offset"]}:{w["array"]}')
            print('then submit slurm/merge.sh once complete; or run slurm/resubmit.sh instead, which submits the missing windows and a merge that waits for them and for live work (cancel any merge still pending first)')
        else:print('complete: every checkpoint block is committed')
    if r['missing_jobs']:sys.exit(1)

# Slurm job states for recovery (squeue %T). LIVE may still run or be released (SPECIAL_EXIT: requeued and held).
# TERMINAL finished for good. COMPLETING and STAGE_OUT hide the job's outcome while Slurm cleans up, and PREEMPTED does
# not say whether a requeue follows: these, and any other state, are UNCERTAIN, so recovery refuses and is rerun later.
LIVE_STATES=frozenset('PENDING RUNNING SUSPENDED CONFIGURING REQUEUED REQUEUE_HOLD REQUEUE_FED SPECIAL_EXIT RESIZING SIGNALING STOPPED RESV_DEL_HOLD POWER_UP_NODE'.split())
TERMINAL_STATES=frozenset('COMPLETED CANCELLED FAILED TIMEOUT NODE_FAIL BOOT_FAIL DEADLINE OUT_OF_MEMORY REVOKED'.split())

def recovery_plan(directory:Path,queue_text:str,max_array:int=MAX_ARRAY)->dict:
    """Pure recovery decision from a squeue snapshot ('%comment|%K|%T|%i' per line, from squeue --all --states=all -r).
    Returns refuse={code,message} or the arrays to resubmit and the live tasks the merge must also wait for."""
    directory=directory.resolve();tag=campaign_tag(directory);tagged=[]
    for line in queue_text.splitlines():
        parts=[x.strip()for x in line.split('|')]
        if len(parts)!=4 or not parts[0].startswith(tag+':'):continue
        comment,task,state,jobid=parts;tagged.append({'comment':comment,'task':task,'state':state,'jobid':jobid})
    def refuse(code,msg):return {'refuse':{'code':code,'message':msg},'tag':tag}
    uncertain=[j for j in tagged if j['state']not in LIVE_STATES|TERMINAL_STATES]
    if uncertain:return refuse(69,'tagged job(s) '+','.join(f'{j["jobid"]}={j["state"]}'for j in uncertain)+' are completing, preempted or in an unrecognised state; '
                                   'nothing submitted. Rerun once Slurm has settled them (requeued, finished or gone).')
    live=[j for j in tagged if j['state']in LIVE_STATES];merges=[j['jobid']for j in live if j['comment']==tag+':merge']
    if merges:return refuse(65,f'merge job(s) {",".join(merges)} of this campaign are still queued or running; scancel them (or let them finish), then rerun')
    active=[];deps=[]
    for j in live:
        off=j['comment'][len(tag)+1:]
        if not off.startswith('off=')or not off[4:].isdigit()or not j['task'].isdigit():
            return refuse(69,f'unexpected record for tagged job {j["jobid"]} ({j["comment"]}, task {j["task"]}); was squeue run with -r? nothing submitted')
        active.append(int(off[4:])+int(j['task']));deps.append(j['jobid'])
    r=status_report(directory,active,max_array);r.pop('lines')
    return {'refuse':None,'tag':tag,'threads':r['threads'],'suggested_time':r['suggested_time'],'complete':r['complete'],'missing_jobs':r['missing_jobs'],
            'live_indices':sorted(set(active)),'live_missing_not_resubmitted':r['active_not_resubmitted'],'arrays':r['resubmit'],'merge_waits_on_live_tasks':sorted(set(deps))}

# sbatch options that C6_SBATCH_ARGS and extra script arguments may carry (exact spellings only: getopt-style
# abbreviations such as --arr are refused). Everything else, in particular array, dependency, export, export-file,
# comment, output, clusters and positional words, is refused, because the scripts set or rely on those themselves.
# Every allowed value option takes a REQUIRED argument in Slurm 23.02 (options with optional arguments, e.g. --nice,
# are excluded: sbatch would not consume the next token, so this parser would skip over it).
SBATCH_LONG_VALUE=frozenset('account partition qos reservation constraint mem mem-per-cpu time cpus-per-task gres tmp mail-type mail-user begin signal job-name exclude licenses wckey'.split())
SBATCH_LONG_FLAG=frozenset('requeue no-requeue hold'.split())
SBATCH_SHORT_VALUE=frozenset('ApqCtcJxL')

def check_sbatch_args(tokens)->str|None:
    """None if every token is an allowed sbatch option (with its value), else the reason for refusing."""
    i=0
    while i<len(tokens):
        tok=tokens[i]
        if tok.startswith('--'):
            name,eq,_=tok[2:].partition('=')
            if name in SBATCH_LONG_FLAG and not eq:i+=1;continue
            if name not in SBATCH_LONG_VALUE:return f'sbatch option {tok} is not allowed'
            i+=1 if eq else 2
            if not eq and i>len(tokens):return f'sbatch option {tok} needs a value'
        elif tok.startswith('-')and len(tok)>=2:
            if tok[1]not in SBATCH_SHORT_VALUE:return f'sbatch option {tok} is not allowed'
            i+=1 if len(tok)>2 else 2
            if len(tok)==2 and i>len(tokens):return f'sbatch option {tok} needs a value'
        else:return f'unexpected word {tok!r} (only sbatch options are allowed)'
    return None

def check_args(a):
    why=check_sbatch_args(a.args[1:]if a.args[:1]==['--']else a.args)
    if why:sys.exit(f'C6: {why}. Allowed: --'+' --'.join(sorted(SBATCH_LONG_VALUE|SBATCH_LONG_FLAG))+' and -'+' -'.join(sorted(SBATCH_SHORT_VALUE)))

def recover(a):
    size=a.max_array if a.max_array is not None else MAX_ARRAY
    print(json.dumps(recovery_plan(a.directory,Path(a.queue).read_text(),size)))

def tag(a):print(campaign_tag(a.directory))

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('plan');q.add_argument('directory',type=Path);q.add_argument('--seed',type=int,required=True);q.add_argument('--seed-scheme',choices=['hashed','legacy'],default='hashed');q.add_argument('--replicates',type=int,default=32);q.add_argument('--multiplier',type=int,default=1);q.add_argument('--shards',type=int,default=32,help='shards of the most expensive group (others scale with cost unless --shard-policy uniform)');q.add_argument('--shard-policy',choices=['cost','uniform'],default='cost');q.add_argument('--threads',type=int,default=8);q.add_argument('--checkpoint-tasks',type=int,default=256);q.add_argument('--chunk-points',type=int,default=65536);q.add_argument('--primitive-mode',choices=['recompute','retained'],default='recompute');q.add_argument('--primitive-points',type=int,default=16384);q.add_argument('--primitive-allocation',choices=['neyman','uniform'],default='neyman');q.add_argument('--points',type=int,help='Override all stratum counts, primitives included, for tests or pilot runs; power of 2');q.add_argument('--grid',choices=['frozen','none'],default='frozen');q.add_argument('--sum-mode',choices=['compensated','legacy'],default='compensated');q.set_defaults(func=plan)
    q=s.add_parser('run');q.add_argument('directory',type=Path);q.add_argument('--index',type=int);q.add_argument('--threads',type=int);q.add_argument('--scratch',type=str);q.add_argument('--max-blocks',type=int,help='commit at most this many new blocks, then stop (time slicing, tests)');q.set_defaults(func=run)
    q=s.add_parser('merge');q.add_argument('directory',type=Path);q.add_argument('--group');q.add_argument('--scratch',type=str);q.set_defaults(func=merge)
    q=s.add_parser('status');q.add_argument('directory',type=Path);q.add_argument('--all',action='store_true',help='also list complete jobs');q.add_argument('--json',action='store_true',help='machine-readable report (slurm/resubmit.sh)');q.add_argument('--exclude',help='comma-separated job indices still queued or running; left out of the resubmission lines');q.add_argument('--max-array',type=int,default=None,help='largest array per resubmission line (default: $C6_MAX_ARRAY, else 1000)');q.set_defaults(func=status)
    q=s.add_parser('recover',help='recovery decision from a squeue snapshot (used by slurm/resubmit.sh)');q.add_argument('directory',type=Path);q.add_argument('--queue',required=True,help="file with 'squeue --all --states=all -u $USER -h -r -o %%200k|%%K|%%T|%%i' output");q.add_argument('--max-array',type=int,default=MAX_ARRAY);q.set_defaults(func=recover)
    q=s.add_parser('tag',help='print the campaign\'s Slurm comment tag');q.add_argument('directory',type=Path);q.set_defaults(func=tag)
    q=s.add_parser('check-sbatch-args',help='allowlist check of user sbatch options (slurm/submit.sh, slurm/resubmit.sh)');q.add_argument('args',nargs=argparse.REMAINDER);q.set_defaults(func=check_args)
    a=p.parse_args();a.func(a)
if __name__=='__main__':main()
