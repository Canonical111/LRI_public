#!/usr/bin/env python3
"""Tiny full-workflow tests (PLAN component F; C7(3)'s workflow.py ported to C8(3) with 24 groups, after C62d's form),
for every built backend: with the REAL worker in the package (bin/c8d3_gmp, bin/c8d3_decimal; Expanse, J-VAL-1/2) or,
with --fake, in a scratch package (tests/c8pkg.py: the fake worker and synthetic inputs; Mac).

The plans are test-only, `--plan-role validation` on the bootstrap basis (D.5, B: a validation plan needs no cost model,
so this runs on a binary that has none yet), --test-graphs 1, never physics. The campaign path holds '#', '?', '%' and
a space (A-URI). Covers: a merge of an incomplete campaign refused ("Incomplete campaign"); the job-private runtime
removed after every run; a deleted checkpoint recomputed with another thread count, its scientific fields unchanged;
a corrupt checkpoint rejected by run (the skip validates it) and merge; merge --jobs 2, an idempotent re-merge and an
idempotent assembly; the test-only result keys (no physical number at the top level, values under test_partial);
merged data of the wrong sector rejected by assemble; the gmp campaign with --mp-check on and the decimal one with off
(the worker then omits the MP self-check fields, C.3); every group's graph_tails.csv and graph_promotions.csv equal to
tools/tails.py's merge of the checkpoint rows (A-KER-6 (d) inside production.py merge). The record goes only to --output.
Usage: python3 -B tests/workflow.py [--fake] [--output FILE]"""
import argparse,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
from common import digest,dump,load
SCIENTIFIC=('uid','rep','graph','begin','end','total','values','quad','mp','max_abs','tail_top','tail_sum','tail_argmax','nondirect','nonmoderate',
            'mp_checked','mp_hist','mp_min_log10','mp_alarm')

def caller(pkg:Path):
    def call(script,*args,ok=True):
        e={k:v for k,v in os.environ.items()if not k.startswith(('SLURM_','SBATCH_','SQUEUE_','C8_FAKE_'))and k!='C8_SITE'}
        e.update(OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')   # C8_SITE dropped: see check_vendored.run_spy
        p=subprocess.run([sys.executable,'-B',str(pkg/'tools'/script),*map(str,args)],capture_output=True,text=True,env=e)
        if ok and p.returncode:raise RuntimeError(f'{script} {args}: exit {p.returncode}\n{p.stderr[-4000:]}')
        if not ok and not p.returncode:raise AssertionError('Bad input accepted: '+' '.join(map(str,args)))
        return p
    return call

def sci(doc):return [{k:r.get(k)for k in SCIENTIFIC}for r in doc['native']['rows']]

# The gmp campaign checks every MP point (--mp-check on); the decimal one runs with the check off, where the worker omits
# the MP self-check fields (C.3), so both row forms go through run, merge and assemble.
MP_CHECK={'gmp':'on','decimal':'off'}

def tails_cross_check(pkg:Path,t:Path)->int:
    """A-KER-6 (d) inside production.py merge: every group's graph_tails.csv and graph_promotions.csv equal, byte for
    byte, tools/tails.py's independent in-memory merge of the raw rows of the group's checkpoints. Returns the rows."""
    sys.path.insert(0,str(pkg/'tools'));import tails;n=0
    for g in sorted((t/'groups').iterdir()):
        rows=[r for ck in sorted((g/'checkpoints').glob('*.json'))for r in load(ck)['native']['rows']];n+=len(rows)
        for name,fn in (('graph_tails.csv',tails.tails_csv),('graph_promotions.csv',tails.promotions_csv)):
            if (g/name).read_text()!=fn(rows):raise AssertionError(f'{g.name}/{name} differs from tools/tails.py\'s merge of the checkpoint rows')
    return n

def run(pkg:Path,tmp:Path,backend:str)->dict:
    call=caller(pkg);t=tmp/f'{backend} #?%41 dir';scratch=tmp/f'scratch_{backend}';scratch.mkdir()
    call('production.py','plan',t,'--seed',7611826,'--pilot','--points',16,'--replicates',2,'--test-graphs',1,'--shards',1,'--threads',2,'--checkpoint-tasks',8,
         '--plan-role','validation','--bootstrap-chunk',8,'--backend',backend,'--scratch',scratch,'--mp-check',MP_CHECK[backend])
    m=load(t/'manifest.json');assert m['test_only']and m['backend']==backend and len(m['groups'])==24 and m['plan_role']=='validation'and m['cost_basis']=='bootstrap'
    assert m['mp_check']==MP_CHECK[backend]
    call('production.py','run',t,'--index',0,'--threads',2,'--max-blocks',1,'--scratch',scratch)
    r=call('production.py','merge',t,'--scratch',scratch,ok=False);assert 'Incomplete campaign'in r.stderr,r.stderr[-400:]
    for j in m['jobs']:call('production.py','run',t,'--index',j['id'],'--threads',2,'--scratch',scratch)
    assert not [p for p in scratch.iterdir()if p.name.startswith('c8d3_runtime_')],'a job-private runtime directory was left behind'
    call('production.py','status',t)
    j=max(m['jobs'],key=lambda j:j['blocks']);ck=sorted((t/'groups'/j['group']/'checkpoints').glob(f's{j["shard"]:06d}_p*.json'))[0]
    before=load(ck);ck.unlink();call('production.py','run',t,'--index',j['id'],'--threads',1,'--scratch',scratch);after=load(ck)
    assert sci(before)==sci(after)and after['native']['threads']==1,'the recomputed block differs'
    good=ck.read_bytes();doc=json.loads(good);doc['native']['rows'][0]['values'][0]=str(float(doc['native']['rows'][0]['values'][0])+1.0);ck.unlink();ck.write_text(json.dumps(doc))
    r=call('production.py','run',t,'--index',j['id'],'--threads',2,'--scratch',scratch,ok=False);r2=call('production.py','merge',t,'--scratch',scratch,ok=False);ck.unlink();ck.write_bytes(good)
    assert all('payload corruption'in x.stderr for x in (r,r2)),(r.stderr[-300:],r2.stderr[-300:])
    call('production.py','merge',t,'--jobs',2,'--scratch',scratch);snap={str(p.relative_to(t)):digest(p)for p in sorted((t/'groups').rglob('merged.json'))}
    tails_rows=tails_cross_check(pkg,t)
    call('production.py','merge',t,'--jobs',2,'--scratch',scratch);assert snap=={str(p.relative_to(t)):digest(p)for p in sorted((t/'groups').rglob('merged.json'))}
    call('assemble.py',t,'--bootstrap',16);res=t/'C8_test_result.json';h=digest(res)
    call('assemble.py',t,'--bootstrap',16);assert digest(res)==h
    x=load(res);assert x['test_only']is True and x.get('C8_full')is None and isinstance(x['test_partial']['C8_full'],float)and x['label']=='test',sorted(x)
    bad=tmp/f'{backend}_wrong_sector';shutil.copytree(t,bad)
    src=bad/'groups/a_free_L5/merged.json';dst=bad/'groups/a_power_L5/merged.json';dst.unlink();dst.write_bytes(src.read_bytes())
    r=call('assemble.py',bad,'--bootstrap',0,'--output',tmp/f'{backend}_wrong.json',ok=False)
    return dict(backend=backend,mp_check=MP_CHECK[backend],status='passed',jobs=len(m['jobs']),incomplete_merge_refused=True,runtime_removed=True,recomputed_block_identical=True,
                corrupt_checkpoint_rejected=True,idempotent_merge_and_assembly=True,tails_and_promotions_equal_tools_tails=tails_rows,test_only_result_keys=True,wrong_sector_rejected=True,
                wrong_sector_message=(r.stderr.strip().splitlines()or[''])[-1][:200])

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--output',type=Path,help='write the JSON record here')
    ap.add_argument('--fake',action='store_true',help='a scratch package with the fake worker (Mac)');a=ap.parse_args();res=[]
    with tempfile.TemporaryDirectory(prefix='c8d3_workflow_',dir=os.environ.get('TMPDIR'))as tmp:
        if a.fake:
            import c8pkg
            pkg=c8pkg.make(Path(tmp));backends=['gmp','decimal']
        else:
            pkg=ROOT;backends=[b for b in ('decimal','gmp')if (ROOT/f'bin/c8d3_{b}').exists()]
            if not backends:raise SystemExit('build bin/c8d3_decimal and bin/c8d3_gmp first, or run with --fake')
        for b in backends:res.append(run(pkg,Path(tmp),b))
    rec={'status':'passed','worker':'fake'if a.fake else'real','tests':res}
    if a.output:dump(a.output,rec)
    print(json.dumps(rec,indent=2,default=str))
