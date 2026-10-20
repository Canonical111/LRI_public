#!/usr/bin/env python3
"""Relocated runtime, member staging and a frozen cost model (PLAN component F, D.15, A-ORC-16; C7(3)'s staging.py
ported to C8(3) after C62d's form), for every built backend: with the REAL worker in the package (Expanse, J-VAL-1/2)
or, with --fake, in a scratch package (tests/c8pkg.py; Mac).

A test-only `--plan-role validation` plan on the bootstrap basis (--test-graphs 1); tools/stage_runtime.py stages
index 0 of the a_free_L7 group (only the members of its blocks, at their offsets in a sparse pack; no vendor/, no
reference/; the pack read only with os.pread, exactly the members' bytes, under a read spy: F12); `production.py run` from the staged copy commits its blocks; a rerun from the package with another thread
count leaves them unchanged; a whole-pack copy is refused above the 1 GB limit (the free L7 pack at a lowered limit).
The frozen-cost-model check uses the labelled synthetic fixture (tests/fixtures/cost_model_synthetic.json), since
make_cost_model.py refuses a validation campaign (65, checked here): a second validation plan freezes the fixture
(cost_basis synthetic, its sha256 in the manifest, estimates present). The record goes only to --output.
Usage: python3 -B tests/staging.py [--fake] [--output FILE]"""
from pathlib import Path
import argparse,json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
from common import digest,dump,load

# F12: stage_runtime.stage in a fresh process under a read spy: os.pread counted, the shared pack never opened with open()
SPY='''import builtins,io,json,os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import stage_runtime as s
pk=os.path.realpath(sys.argv[5]);n=[0,0];rp,ro,rpo=os.pread,builtins.open,Path.open
def chk(f):
    if isinstance(f,(str,os.PathLike))and os.path.realpath(f)==pk:raise AssertionError('the pack was opened through open(): '+str(f))
def pread(fd,k,off):
    b=rp(fd,k,off);n[0]+=len(b);n[1]+=1;return b
def opn(f,*a,**k):
    chk(f);return ro(f,*a,**k)
def popen(p,*a,**k):
    chk(p);return rpo(p,*a,**k)
os.pread=pread;builtins.open=opn;io.open=opn;Path.open=popen
s.stage(Path(sys.argv[2]),Path(sys.argv[3]),int(sys.argv[4]),False)
print(json.dumps({'pread_bytes':n[0],'preads':n[1]}))
'''

def caller(pkg:Path):
    def call(script,*args,ok=True,code=None):
        e={k:v for k,v in os.environ.items()if not k.startswith(('SLURM_','SBATCH_','SQUEUE_','C8_FAKE_'))and k!='C8_SITE'}
        e.update(OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')   # C8_SITE dropped: see check_vendored.run_spy
        p=subprocess.run([sys.executable,'-B',str(script if Path(str(script)).is_absolute()else pkg/'tools'/script),*map(str,args)],capture_output=True,text=True,env=e)
        if ok and p.returncode:raise RuntimeError(f'{script} {args}: exit {p.returncode}\n{p.stderr[-3000:]}')
        if not ok and (p.returncode==0 or (code is not None and p.returncode!=code)):raise AssertionError(f'accepted or wrong code {p.returncode}: {script} {args}')
        return p
    return call

def run(pkg:Path,t:Path,backend:str)->dict:
    call=caller(pkg);r=t/'run';stage=t/'stage';scr=t/'scratch';scr.mkdir()
    call('production.py','plan',r,'--seed',816615,'--pilot','--points',8,'--replicates',2,'--test-graphs',1,'--plan-role','validation','--bootstrap-chunk',8,'--shards',1,
         '--threads',1,'--checkpoint-tasks',8,'--backend',backend,'--scratch',scr)
    m=load(r/'manifest.json');j=next(x for x in m['jobs']if x['group']=='a_free_L7')
    idir=Path(m['inputs'])if os.path.isabs(m['inputs'])else pkg/m['inputs'];rel=idir.resolve().relative_to(pkg.resolve())
    pack=stage/rel/'packs/free_L7.pack';full=idir/'packs/free_L7.pack'
    e={k:v for k,v in os.environ.items()if not k.startswith(('SLURM_','SBATCH_','SQUEUE_','C8_FAKE_'))and k!='C8_SITE'};e.update(OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
    sp=subprocess.run([sys.executable,'-B','-c',SPY,str(pkg/'tools'),str(r),str(stage),str(j['id']),str(full)],capture_output=True,text=True,env=e)
    if sp.returncode:raise RuntimeError(f'stage_runtime under the read spy: exit {sp.returncode}\n{sp.stderr[-3000:]}')
    reads=json.loads(sp.stdout.strip().splitlines()[-1])
    assert pack.stat().st_size==full.stat().st_size and not (stage/'vendor').exists()and not (stage/'reference').exists()
    inv={x['id']:x for x in load(idir/'inventory.json')['free']['7']}
    gids={int(l.split()[2])for l in (r/j['tasks_file']).read_text().splitlines()if l.strip()}
    assert reads['pread_bytes']==sum(inv[g]['length']for g in gids),('F12: pack bytes read',reads,sum(inv[g]['length']for g in gids))
    data=pack.read_bytes();src=full.read_bytes()
    for g in gids:x=inv[g];assert data[x['offset']:x['offset']+x['length']]==src[x['offset']:x['offset']+x['length']]
    other=[x for g,x in inv.items()if g not in gids][:50];assert all(not any(data[x['offset']:x['offset']+x['length']])for x in other),'a non-member was staged'
    call(stage/'tools/production.py','run',r,'--index',j['id'],'--scratch',scr)
    files=sorted((r/'groups/a_free_L7/checkpoints').glob(f's{j["shard"]:06d}_p*.json'));before={p.name:digest(p)for p in files}
    if not files:raise AssertionError('the staged run committed nothing')
    call('production.py','run',r,'--index',j['id'],'--threads',2,'--scratch',scr)
    if before!={p.name:digest(p)for p in files}:raise AssertionError('a relocated restart changed data')
    w=subprocess.run([sys.executable,'-B','-c','import sys;sys.path.insert(0,sys.argv[1]);import stage_runtime as s;s.WHOLE_PACK_LIMIT=1000\n'
                      'try:s.stage(__import__("pathlib").Path(sys.argv[2]),__import__("pathlib").Path(sys.argv[3]),int(sys.argv[4]),True)\n'
                      'except ValueError as e:print("REFUSED",e);sys.exit(3)',str(pkg/'tools'),str(r),str(t/'stage_whole'),str(j['id'])],capture_output=True,text=True,
                     env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    assert w.returncode==3 and '> 1 GB'in w.stdout,(w.stdout,w.stderr[-500:])
    for x in m['jobs']:call('production.py','run',r,'--index',x['id'],'--threads',2,'--scratch',scr)
    call('production.py','merge',r,'--jobs',2,'--scratch',scr)
    call('make_cost_model.py',r,t/'costs.json',ok=False,code=65);assert not (t/'costs.json').exists()
    fx=ROOT/'tests/fixtures/cost_model_synthetic.json'
    call('production.py','plan',t/'plan2','--seed',816616,'--pilot','--points',8,'--replicates',2,'--test-graphs',1,'--plan-role','validation','--shards',2,'--threads',2,
         '--backend',backend,'--cost-model',fx,'--scratch',scr)
    m2=load(t/'plan2/manifest.json')
    if m2.get('synthetic_cost_model_sha256')!=digest(fx)or m2.get('cost_basis')!='synthetic'or any(x['est_core_seconds']is None for x in m2['jobs']):
        raise AssertionError('the synthetic fixture was not frozen')
    assert digest(t/'plan2/synthetic_cost_model.json')==digest(fx)and not (t/'plan2/cost_model.json').exists()
    return dict(backend=backend,status='passed',members_staged=len(gids),pack_members=len(inv),pack_bytes_read=reads['pread_bytes'],pack_preads=reads['preads'],relocated_worker_verified=True,vendor_and_reference_not_staged=True,
                whole_pack_above_limit_refused=True,make_cost_model_refuses_validation=True,synthetic_fixture_frozen=True,resume_across_staged_and_shared_unchanged=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--output',type=Path,help='write the JSON record here')
    ap.add_argument('--fake',action='store_true',help='a scratch package with the fake worker (Mac)');a=ap.parse_args();res=[]
    if a.fake:backends=['gmp','decimal']
    else:
        backends=[b for b in ('decimal','gmp')if (ROOT/f'bin/c8d3_{b}').exists()]
        if not backends:raise SystemExit('build bin/c8d3_decimal and bin/c8d3_gmp first, or run with --fake')
    for backend in backends:
        with tempfile.TemporaryDirectory(prefix='c8d3_stage_',dir=os.environ.get('TMPDIR'))as temp:
            if a.fake:
                import c8pkg
                counts={s:dict(v)for s,v in c8pkg.DEFAULT_COUNTS.items()};counts['free'][7]=40
                pkg=c8pkg.make(Path(temp),counts=counts);(Path(temp)/'w').mkdir();res.append(run(pkg,Path(temp)/'w',backend))
            else:res.append(run(ROOT,Path(temp),backend))
    rec={'status':'passed','worker':'fake'if a.fake else'real','tests':res}
    if a.output:dump(a.output,rec)
    print(json.dumps(rec,indent=2,default=str))
