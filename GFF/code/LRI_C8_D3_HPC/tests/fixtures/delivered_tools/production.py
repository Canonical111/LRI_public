#!/usr/bin/env python3
"""Bounded-memory, restartable complete C7(3) campaigns (both forest sectors).

Scientific point identities do not depend on scheduler, chunk or thread IDs.
SQLite task tables and sorted deterministic Decimal merges are disk backed.
"""
from __future__ import annotations
import argparse,decimal,hashlib,heapq,itertools,json,os,shutil,sqlite3,struct,subprocess,sys,tempfile,time
from pathlib import Path
import numpy as np
from common import ROOT,checked,digest,dump,load,object_hash,pow2,publish
from prepare_inputs import prepare
D=decimal.Decimal

def dbopen(path,readonly=False):
    c=sqlite3.connect(f'file:{path}?mode=ro'if readonly else str(path),uri=readonly)
    c.execute('PRAGMA cache_size=-8192');c.execute('PRAGMA temp_store=FILE');return c

def make_net(path,B,dim,bits,seed):
    from scipy.stats import qmc
    import scipy
    rng=np.random.default_rng(seed)
    with path.open('xb')as f:
        f.write(struct.pack('<III',B,dim,bits))
        for _ in range(B):
            engine=qmc.Sobol(d=dim,scramble=True,bits=bits,seed=int(rng.integers(1,2**32-1)))
            sv=engine._sv.copy();state=engine._shift.copy();pts=[]
            for n in range(16):
                if n:state^=sv[:,(n&-n).bit_length()-1]
                pts.append(state.copy())
            if not np.array_equal(np.array(pts,dtype=np.float64)/2**bits,engine.random_base2(4)):
                raise RuntimeError('Sobol export failed public-API reconstruction test')
            f.write(sv.astype('<u8').tobytes())
    return dict(scipy=scipy.__version__,seed=seed,B=B,dim=dim,bits=bits,sha256=digest(path),public_API_points_checked=16*B)

def exe_for(backend):return ROOT/'bin'/('c7d3_gmp'if backend=='gmp'else'c7d3_decimal')

def plan(a):
    prepare();out=a.directory.resolve();exe=exe_for(a.backend)
    if not exe.exists():raise FileNotFoundError('Build selected backend with make or make gmp')
    if out.exists():raise FileExistsError('Use a new campaign directory')
    if min(a.replicates-1,a.shards,a.threads,a.checkpoint_tasks,a.chunk_points)<1:raise ValueError('invalid sizes')
    if any(not pow2(n)for n in (a.multiplier,a.power_multiplier,a.primitive_points))or(a.points is not None and not pow2(a.points)):raise ValueError('counts and multipliers must be powers of two')
    if not 0<=a.seed<2**63:raise ValueError('seed outside [0,2^63)')
    out.mkdir(parents=True);(out/'groups').mkdir();inv=load(ROOT/'inputs/inventory.json');groups=[];jobs=[];total_samples=0
    build=json.loads(subprocess.check_output([exe,'--describe'],text=True))
    cost_model=load(a.cost_model)if a.cost_model else None
    costs={}
    if cost_model:
        if cost_model.get('schema')!='c7-d3-cost-model-1' or cost_model['dimension']!=3 or cost_model['order']!=7 or cost_model['backend']!=a.backend:raise ValueError('Wrong cost-model dimension/order/backend')
        costs=cost_model['seconds_per_point']
        if any(not float(v)>0 or not np.isfinite(float(v))for v in costs.values()):raise ValueError('Invalid measured cost')
        dump(out/'cost_model.json',cost_model)
    unknown_cost=max(costs.values(),default=1.)
    if build['dimension']!=3 or build['order']!=7:raise ValueError('wrong executable')
    for campaign in ('a','b'):
      for sector in ('free','power'):
        for L in range(3,8):
            name=f'{campaign}_{sector}_L{L}';p=out/'groups'/name;p.mkdir();rows=inv[sector][str(L)];counts={}
            for r in rows:
                if sector=='free'and L==7 and r['primitive']:
                    n=0 if a.primitive_mode=='retained'else(a.points or a.primitive_points)
                else:
                    n=a.points if a.points is not None else max(4,r['points'])
                counts[r['id']]=n*a.multiplier*(a.power_multiplier if sector=='power'else 1)
            if a.test_graphs:
                # Explicitly labelled incomplete workflow test; never a production result.
                selected={r['id']for r in sorted(rows,key=lambda r:(r['cost'],r['id']))[:a.test_graphs]}
                counts={g:(n if g in selected else 0)for g,n in counts.items()}
            bits=52 if campaign=='a'else 60
            offset=(0 if sector=='free'else 0x156ad267)+(0 if campaign=='a'else 0x614ef703)
            seed=(a.seed+L*1279+offset)%(2**64)
            if max(counts.values())>2**bits:raise ValueError('Sobol period exceeded')
            net=make_net(p/'sobol.bin',a.replicates,4*L-1,bits,(a.seed+18743*L+offset*13)%(2**63))
            db=dbopen(p/'tasks.sqlite');db.executescript('CREATE TABLE tasks(uid INTEGER PRIMARY KEY,rep INTEGER,gi INTEGER,lo INTEGER,hi INTEGER,total INTEGER,cost REAL,shard INTEGER); CREATE TABLE expected(rep INTEGER,gi INTEGER,total INTEGER,PRIMARY KEY(rep,gi));')
            uid=0
            for rep in range(a.replicates):
                for row in rows:
                    gi=row['id'];total=counts[gi];db.execute('INSERT INTO expected VALUES(?,?,?)',(rep,gi,total))
                    for start in range(0,total,a.chunk_points):
                        stop=min(total,start+a.chunk_points);cost=(stop-start)*float(costs.get(f'{sector}:{L}:{gi}',row['cost'] if not costs else unknown_cost))
                        db.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,NULL)',(uid,rep,gi,start,stop,total,cost));uid+=1
            nshards=min(a.shards,uid);heap=[(0.,i)for i in range(nshards)];heapq.heapify(heap)
            for tid,cost in db.execute('SELECT uid,cost FROM tasks ORDER BY cost DESC,uid'):
                c,i=heapq.heappop(heap);db.execute('UPDATE tasks SET shard=? WHERE uid=?',(i,tid));heapq.heappush(heap,(c+cost,i))
            db.execute('CREATE INDEX shard_order ON tasks(shard,uid)');db.execute('CREATE INDEX stream_order ON tasks(rep,gi,lo)');db.commit();db.close()
            cfg=dict(schema='c7-d3-group-1',name=name,campaign=campaign,sector=sector,L=L,seed=seed,layout=0,rate='.8'if campaign=='a'else'.7',replicates=a.replicates,counts={str(k):v for k,v in counts.items()},net=net,sum_mode=a.sum_mode,primitive_mode=a.primitive_mode,shards=nshards,tasks=uid,tasks_sha256=digest(p/'tasks.sqlite'),samples=sum(counts.values())*a.replicates,build=build)
            dump(p/'config.json',cfg);groups.append({'name':name,'sha256':digest(p/'config.json')});base=len(jobs)
            jobs.extend({'id':base+i,'group':name,'shard':i}for i in range(nshards));total_samples+=cfg['samples']
    manifest=dict(schema='c7-d3-production-1',tool_sha256={n:digest(ROOT/'tools'/n)for n in ('production.py','assemble.py','common.py','prepare_inputs.py')},dimension=3,order=7,epsilon='2s-3',package=str(ROOT),inputs_manifest_sha256=digest(ROOT/'inputs/manifest.json'),backend=a.backend,build=build,executable_sha256=digest(exe),threads=a.threads,checkpoint_tasks=a.checkpoint_tasks,primitive_mode=a.primitive_mode,groups=groups,jobs=jobs,campaign_weights={'a':.5,'b':.5},groups_independent_by_loop_campaign_sector=True,sampling_unit='complete graph-summed randomized replicate, not chunk',power_sector='explicitly integrated; NOT assumed zero',test_only=bool(a.test_graphs),cost_model_sha256=digest(out/'cost_model.json')if cost_model else None,point_override=a.points,allocation_multiplier=a.multiplier,power_multiplier=a.power_multiplier,primitive_points=a.primitive_points)
    dump(out/'manifest.json',manifest);print(json.dumps(dict(directory=str(out),jobs=len(jobs),samples=total_samples,backend=a.backend,test_only=manifest['test_only']),indent=2))

def verify_base(directory):
    m=load(directory/'manifest.json')
    if m['schema']!='c7-d3-production-1'or m['dimension']!=3 or m['order']!=7:raise ValueError('wrong production schema')
    for n,h in m['tool_sha256'].items():checked(ROOT/'tools'/n,h)
    checked(ROOT/'inputs/manifest.json',m['inputs_manifest_sha256']);checked(exe_for(m['backend']),m['executable_sha256'])
    im=load(ROOT/'inputs/manifest.json')
    if m.get('cost_model_sha256'):checked(directory/'cost_model.json',m['cost_model_sha256'])
    for name in ('gamma_d3_7.txt','two_loop.json','primitive_reference.json','inventory.json'):checked(ROOT/'inputs'/name,im['sha256'][name])
    return m,im

def rows_for(db,shard):return db.execute('SELECT uid,rep,gi,lo,hi,total FROM tasks WHERE shard=? ORDER BY uid',(shard,))

def validate_checkpoint(doc,block,cfg,mh):
    if doc.get('manifest_sha256')!=mh or doc.get('config_hash')!=object_hash(cfg):raise ValueError('checkpoint identity mismatch')
    n=doc['native']
    if object_hash(n)!=doc.get('payload_sha256'):raise ValueError('checkpoint payload corruption')
    expected={'schema':'c7-d3-hpc-native-1','L':cfg['L'],'seed':cfg['seed'],'layout':cfg['layout'],'bits':cfg['net']['bits'],'sum_mode':cfg['sum_mode'],'mp_backend':cfg['build']['mp_backend'],'mp_digits10':cfg['build']['mp_digits10'],'long_double_bits':cfg['build']['long_double_bits']}
    for k,v in expected.items():
        if n.get(k)!=v:raise ValueError('native metadata mismatch: '+k)
    if abs(D(n['rate'])-D(cfg['rate']))>D(2)**(-cfg['build']['long_double_bits']+1):raise ValueError('importance rate mismatch')
    if len(n['rows'])!=len(block):raise ValueError('incomplete checkpoint')
    for expected,r in zip(block,n['rows']):
        if tuple(r[k]for k in ('uid','rep','graph','begin','end','total'))!=tuple(expected):raise ValueError('wrong task coordinates')
        if len(r['values'])!=2*(8-cfg['L'])or any(not D(v).is_finite()for v in r['values']):raise ValueError('invalid jet')
        if not 0<=r['mp']<=r['quad']<=r['end']-r['begin']:raise ValueError('invalid promotion counters')
    return n

def stage_graphs(td,cfg,block,inventory):
    """Seek only assigned graph blobs and verify their content hashes."""
    root=td/'graphs';dest=root/f'L{cfg["L"]}';dest.mkdir(parents=True)
    pack=ROOT/f'inputs/packs/{cfg["sector"]}_L{cfg["L"]}.pack'
    with pack.open('rb')as f:
        for gi in sorted({r[2]for r in block}):
            row=inventory[gi];f.seek(row['offset']);data=f.read(row['length'])
            if len(data)!=row['length']or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Packed graph content mismatch')
            (dest/f'G{gi}.txt').write_bytes(data)
    return root

def run(a):
    directory=a.directory.resolve();m,im=verify_base(directory);idx=a.index
    if idx is None:idx=int(os.environ.get('SLURM_ARRAY_TASK_ID','0'))+int(os.environ.get('C7_ARRAY_OFFSET','0'))
    if not 0<=idx<len(m['jobs']):raise ValueError('job outside plan')
    j=m['jobs'][idx];p=directory/'groups'/j['group'];cfg=load(p/'config.json');checked(p/'config.json',next(g['sha256']for g in m['groups']if g['name']==j['group']))
    checked(p/'tasks.sqlite',cfg['tasks_sha256']);checked(p/'sobol.bin',cfg['net']['sha256']);mh=digest(directory/'manifest.json');threads=a.threads or m['threads']
    if threads<1:raise ValueError('invalid thread count')
    # One small inventory index in Python. Native memory is bounded by the work block.
    inv={r['id']:r for r in load(ROOT/'inputs/inventory.json')[cfg['sector']][str(cfg['L'])]}
    db=dbopen(p/'tasks.sqlite',True);cursor=rows_for(db,j['shard']);part=0
    (p/'checkpoints').mkdir(exist_ok=True);(p/'logs').mkdir(exist_ok=True)
    while block:=list(itertools.islice(cursor,m['checkpoint_tasks'])):
        name=f's{j["shard"]:06d}_p{part:06d}';dest=p/'checkpoints'/f'{name}.json';part+=1
        if dest.exists():validate_checkpoint(load(dest),block,cfg,mh);continue
        with tempfile.TemporaryDirectory(prefix='c7d3_',dir=a.scratch)as temp:
            td=Path(temp);graphroot=stage_graphs(td,cfg,block,inv);tasks=td/'tasks.txt'
            tasks.write_text(f'C7D3TASKS1 {cfg["L"]} {len(block)}\n'+''.join(' '.join(map(str,r))+'\n'for r in block));out=td/'native.json'
            cmd=list(map(str,[exe_for(m['backend']),graphroot,ROOT/'inputs/gamma_d3_7.txt',p/'sobol.bin',tasks,out,cfg['seed'],cfg['layout'],cfg['rate'],threads,cfg['sum_mode'],'-']))
            try:
                with (td/'native.log').open('w')as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
            except subprocess.CalledProcessError as exc:
                message=(td/'native.log').read_text();publish(p/'logs'/f'{name}.failure.{time.time_ns()}.log',message);raise RuntimeError(message[-4000:])from exc
            n=load(out);doc=dict(manifest_sha256=mh,config_hash=object_hash(cfg),native=n,payload_sha256=object_hash(n),task_file_sha256=digest(tasks))
            validate_checkpoint(doc,block,cfg,mh)
            try:dump(dest,doc)
            except FileExistsError:
                prior=validate_checkpoint(load(dest),block,cfg,mh)
                for x,y in zip(prior['rows'],n['rows']):
                    if any(x[k]!=y[k]for k in ('uid','rep','graph','begin','end','total','values','quad','mp','max_abs')):raise ValueError('Conflicting duplicate execution')
            print(f'committed {j["group"]}/{name}',flush=True)
    db.close()

def merge_group(directory:Path,m:dict,name:str,scratch=None):
    p=directory/'groups'/name;config=load(p/'config.json');checked(p/'config.json',next(g['sha256']for g in m['groups']if g['name']==name));checked(p/'tasks.sqlite',config['tasks_sha256']);mh=digest(directory/'manifest.json')
    dest=p/'merged.json'
    if dest.exists():raise FileExistsError('Merged result already exists: '+str(dest))
    source=dbopen(p/'tasks.sqlite',True);dim=2*(8-config['L']);fallbacks={'quad':0,'mp':0};count=0;seconds=0
    with tempfile.TemporaryDirectory(prefix='c7d3_merge_',dir=scratch)as td:
        db=dbopen(Path(td)/'merge.sqlite');db.execute('CREATE TABLE actual(uid INTEGER PRIMARY KEY,rep INTEGER,gi INTEGER,lo INTEGER,hi INTEGER,total INTEGER,vals TEXT)')
        for shard in range(config['shards']):
            cur=rows_for(source,shard);part=0
            while block:=list(itertools.islice(cur,m['checkpoint_tasks'])):
                f=p/'checkpoints'/f's{shard:06d}_p{part:06d}.json';part+=1
                if not f.exists():raise FileNotFoundError('Incomplete campaign: '+str(f))
                n=validate_checkpoint(load(f),block,config,mh);seconds+=n['integration_seconds']
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
                with csvtmp.open('rb')as i,os.fdopen(fd,'wb')as o:
                    shutil.copyfileobj(i,o);o.flush();os.fsync(o.fileno())
                try:os.link(tname,target)
                except FileExistsError:checked(target,digest(csvtmp))
            finally:os.unlink(tname)
        merged={'schema':'c7-d3-merged-1','complete':True,'L':config['L'],'dimension':3,'config_hash':object_hash(config),'manifest_sha256':mh,'replicates':config['replicates'],'samples':config['samples'],'primitive_mode':config['primitive_mode'],'sector':config['sector'],'order':7,'batches':batches,'fallbacks':fallbacks,'integration_seconds_sum':seconds,'graph_replicates_sha256':digest(target)}
        merged['payload_sha256']=object_hash(merged)
        dump(dest,merged);db.close()
    source.close();return dest

def merge(a):
    directory=a.directory.resolve();m,_=verify_base(directory)
    names=[a.group]if a.group else[g['name']for g in m['groups']]
    if any(n not in {g['name']for g in m['groups']}for n in names):raise ValueError('unknown group')
    for n in names:print(merge_group(directory,m,n,a.scratch),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('plan');q.add_argument('directory',type=Path);q.add_argument('--seed',type=int,required=True);q.add_argument('--replicates',type=int,default=32);q.add_argument('--multiplier',type=int,default=1);q.add_argument('--power-multiplier',type=int,default=1);q.add_argument('--shards',type=int,default=32);q.add_argument('--threads',type=int,default=8);q.add_argument('--checkpoint-tasks',type=int,default=32);q.add_argument('--chunk-points',type=int,default=65536);q.add_argument('--primitive-mode',choices=['recompute','retained'],default='recompute');q.add_argument('--primitive-points',type=int,default=16384);q.add_argument('--points',type=int,help='Override all stratum counts (power of 2), for full pilots/tests');q.add_argument('--cost-model',type=Path,help='Frozen task timing model; affects placement, never sample counts');q.add_argument('--backend',choices=['decimal','gmp'],default='gmp');q.add_argument('--sum-mode',choices=['compensated','legacy'],default='compensated');q.add_argument('--test-graphs',type=int,default=0,help='INCOMPLETE workflow test only; number of cheap graphs per group');q.set_defaults(func=plan)
    q=s.add_parser('run');q.add_argument('directory',type=Path);q.add_argument('--index',type=int);q.add_argument('--threads',type=int);q.add_argument('--scratch');q.set_defaults(func=run)
    q=s.add_parser('merge');q.add_argument('directory',type=Path);q.add_argument('--group');q.add_argument('--scratch');q.set_defaults(func=merge)
    a=p.parse_args();a.func(a)
if __name__=='__main__':main()
