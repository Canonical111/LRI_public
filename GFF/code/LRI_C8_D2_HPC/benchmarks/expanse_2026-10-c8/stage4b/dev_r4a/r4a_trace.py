#!/usr/bin/env python3
"""R4a call-sequence evidence (Stage 4b development): the mpf calls of the Stage-3 baseline worker and of the R4a worker,
recorded by the LD_PRELOAD shim mpf_trace.so (mpf_trace.c), compared record by record.

  r4a_trace.py --base DIR --new DIR --shim mpf_trace.so --output OUT [--scratch DIR]

DIR/c8d2_gmp and DIR/c8d2_gmp_ratiohist are the release (NeedError=false) and ratio-histogram (NeedError=true) workers.
Steps, all at 1 thread on the fixture blocks' own nets, seeds and native settings (benchmarks/fixtures8):
  1. point finder: the heaviest graph of heavy_power_L8, 64 one-point tasks with the baseline (no shim): the first point
     whose row has mp = 1 is "the point";
  2. full trace of that point, baseline and R4a, MPF_TRACE_FULL=1: every top-level mpf call. Rule: after dropping the
     lifetime calls (init2, clear) and the pure copies (set, swap, with get_prec, the precision query Boost's copy
     constructor and copy assignment make), the two record sequences are identical (operation,
     operand representations, destination precision, result representation, in call order). Reported: the counts per
     operation and how many init2/clear/set/swap R4a no longer makes;
  3. digest traces on a larger sample (the 4 heaviest graphs of each heavy L8 block and the 2 heaviest of each heavy L7
     block, 64 points per graph), release and ratio-histogram builds: the digests of the value-producing (V) and query
     (Q) records and their interleaving (VQ) are identical, and so are the per-operation counts of every V and Q op;
  4. the native rows of every pair of runs are identical (scientific fields), and the sample has MP points.
Exit 0 when every rule holds, 1 otherwise. Writes OUT/trace_summary.json, the full-trace logs gzipped
(OUT/point_{base,new}.log.gz) and the shim summaries.
"""
from __future__ import annotations
import argparse,gzip,hashlib,json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
import benchkit as bk
from common import load

LIFETIME={'init2','clear'};COPIES={'set','swap','get_prec'}  # get_prec: the precision query of Boost's copy constructor/assignment

def run(cmd,env_extra,log):
    env={**bk.omp_env(1),**env_extra};t0=time.perf_counter()
    with open(log,'w')as lf:cp=subprocess.run(cmd,stdout=lf,stderr=subprocess.STDOUT,env=env)
    if cp.returncode:raise RuntimeError(f'{cmd[0]} exit {cp.returncode}: {Path(log).read_text()[-800:]}')
    return time.perf_counter()-t0

def scientific(rows):return [[r.get(k)for k in bk.SCIENTIFIC]for r in rows]

def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base',type=Path,required=True);ap.add_argument('--new',type=Path,required=True)
    ap.add_argument('--shim',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--scratch')
    a=ap.parse_args();out=a.output.resolve();out.mkdir(parents=True)
    sc=Path(tempfile.mkdtemp(prefix='r4a_trace_',dir=a.scratch or os.environ.get('TMPDIR')or None))
    m=bk.load_fixtures();I=m['_inputs'];inv=load(I.where('inventory.json'));gamma=I.where(bk.GAMMA);n=m['native']
    blocks={}
    for name in('heavy_power_L8','heavy_free_L8','heavy_power_L7','heavy_free_L7'):
        b=bk.block_of(m,name);g=sc/'graphs'/name;b['staging']=bk.stage_graphs(I,inv,b['sector'],b['L'],b['graphs'],g);b['root']=str(g);blocks[name]=b
    def heaviest(b,k):return sorted(b['graphs'],key=lambda gid:(-b['seconds_per_point'][str(gid)]if isinstance(b['seconds_per_point'],dict)else 0,gid))[:k]
    def cmd(exe,b,tasks,o):return bk.native_cmd(exe,b['root'],gamma,b['net_path'],tasks,o,b['native_seed'],n['layout'],n['rate'],1,n['sum_mode'])
    exes={'base':a.base/'c8d2_gmp','new':a.new/'c8d2_gmp','base_err':a.base/'c8d2_gmp_ratiohist','new_err':a.new/'c8d2_gmp_ratiohist'}
    rec={'schema':'c8-d2-r4a-trace-1','executables':{k:{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for k,p in exes.items()},
         'shim':{'path':str(a.shim),'sha256':hashlib.sha256(a.shim.read_bytes()).hexdigest()},'rules':[],'ok':True}
    def rule(name,ok,**kw):
        rec['rules'].append({'rule':name,'ok':bool(ok),**kw});rec['ok']&=bool(ok);print(f'{"PASS" if ok else "FAIL"} {name} {kw if not ok else ""}',flush=True)
    # 1. the point
    hp=blocks['heavy_power_L8'];gid=heaviest(hp,1)[0];total=64
    t1=sc/'finder.tasks';bk.write_tasks(t1,8,8,[(i,0,gid,i,i+1,total)for i in range(total)])
    run(cmd(exes['base'],hp,t1,sc/'finder.json'),{},sc/'finder.log');rows=load(sc/'finder.json')['rows']
    mp_points=[r['begin']for r in rows if r['mp']];quad_points=[r['begin']for r in rows if r['quad']]
    if not mp_points:raise SystemExit(f'no MP point among the first {total} points of graph {gid}')
    pt=mp_points[0];rec['point']={'block':'heavy_power_L8','graph':gid,'point_index':pt,'net_rep':0,'mp_points_in_first_64':mp_points,'quad_points_in_first_64':len(quad_points)}
    # 2. full trace of the point
    t2=sc/'point.tasks';bk.write_tasks(t2,8,8,[(0,0,gid,pt,pt+1,total)])
    seqs={};natives={}
    for k in('base','new'):
        o=sc/f'point_{k}.json';so=sc/f'point_{k}.trace.json'
        sec=run(cmd(exes[k],hp,t2,o),{'LD_PRELOAD':str(a.shim),'MPF_TRACE_OUT':str(so),'MPF_TRACE_FULL':'1'},sc/f'point_{k}.log')
        natives[k]=load(o)['rows'];summ=load(so);shutil.copy2(so,out/f'point_{k}.trace.json')
        lines=Path(str(so)+'.log').read_text().splitlines()
        with gzip.open(out/f'point_{k}.log.gz','wt')as z:z.write('\n'.join(lines)+'\n')
        seqs[k]={'lines':lines,'summary':summ,'seconds':sec}
    rule('point rows identical',scientific(natives['base'])==scientific(natives['new'])and natives['base'][0]['mp']==1,mp=natives['base'][0]['mp'])
    def ops(lines):return [l.split(' ',1)[0]for l in lines]
    def strict(lines):return [l for l in lines if l.split(' ',1)[0]not in LIFETIME|COPIES]
    sb,sn=strict(seqs['base']['lines']),strict(seqs['new']['lines'])
    first=next((i for i,(x,y)in enumerate(zip(sb,sn))if x!=y),None)
    cnt={k:{}for k in seqs}
    for k in seqs:
        for o in ops(seqs[k]['lines']):cnt[k][o]=cnt[k].get(o,0)+1
    rec['point_trace']={'records':{k:len(seqs[k]['lines'])for k in seqs},'strict_records':{'base':len(sb),'new':len(sn)},
        'first_difference':None if first is None else {'index':first,'base':sb[first],'new':sn[first]},
        'counts':cnt,'removed':{o:cnt['base'].get(o,0)-cnt['new'].get(o,0)for o in sorted(set(cnt['base'])|set(cnt['new']))},
        'strict_sha256':{k:hashlib.sha256('\n'.join(v).encode()).hexdigest()for k,v in(('base',sb),('new',sn))},
        'shim_digests':{k:seqs[k]['summary']['classes']for k in seqs},'seconds_under_shim':{k:seqs[k]['seconds']for k in seqs}}
    rule('point: identical sequence of non-lifetime, non-copy mpf calls (V and Q)',sb==sn and first is None,lengths=(len(sb),len(sn)))
    rule('point: R4a adds no call of any kind',all(cnt['new'].get(o,0)<=c for o,c in cnt['base'].items())and set(cnt['new'])<=set(cnt['base']))
    # 3. digest traces
    sample=[]
    for name,k in(('heavy_power_L8',4),('heavy_free_L8',4),('heavy_power_L7',2),('heavy_free_L7',2)):sample+= [(name,g)for g in heaviest(blocks[name],k)]
    rec['digest_sample']={'graphs':[{'block':b,'graph':g}for b,g in sample],'points_per_graph':64}
    dig={}
    for build in('','_err'):
        for name in dict.fromkeys(b for b,_ in sample):
            b=blocks[name];L=b['L'];ids=[g for bb,g in sample if bb==name]
            t3=sc/f'digest_{name}.tasks';bk.write_tasks(t3,8,L,[(u,0,g,0,64,64)for u,g in enumerate(ids)])
            res={}
            for side in('base','new'):
                k=side+build;o=sc/f'd_{k}_{name}.json';so=sc/f'd_{k}_{name}.trace.json'
                sec=run(cmd(exes[k],b,t3,o),{'LD_PRELOAD':str(a.shim),'MPF_TRACE_OUT':str(so)},sc/f'd_{k}_{name}.log')
                res[side]={'rows':load(o)['rows'],'trace':load(so),'seconds':sec};shutil.copy2(so,out/so.name)
            tb,tn=res['base']['trace'],res['new']['trace'];cb,cn=tb['counts'],tn['counts']
            vq={o for o in set(cb)|set(cn)if o not in LIFETIME|COPIES}
            mp=sum(r['mp']for r in res['base']['rows'])
            entry={'block':name,'build':'ratiohist (NeedError=true)'if build else 'release (NeedError=false)','graphs':ids,'mp_points':mp,
                   'quad_points':sum(r['quad']for r in res['base']['rows']),'digests':{s:res[s]['trace']['classes']for s in res},
                   'counts':{'base':cb,'new':cn},'seconds_under_shim':{s:res[s]['seconds']for s in res}}
            ok=(scientific(res['base']['rows'])==scientific(res['new']['rows'])and mp>0
                and all(tb['classes'][c]==tn['classes'][c]for c in('V','Q','VQ'))and all(cb.get(o,0)==cn.get(o,0)for o in vq))
            dig[f'{name}{build}']=entry
            rule(f'digest {name} {entry["build"]}: rows identical, V/Q/VQ digests and V/Q op counts identical, mp > 0',ok,mp_points=mp)
    rec['digest_traces']=dig
    (out/'trace_summary.json').write_text(json.dumps(rec,indent=1)+'\n')
    shutil.rmtree(sc,ignore_errors=True)
    print(json.dumps({k:v for k,v in rec.items()if k not in('digest_traces',)},indent=1)[:6000])
    return 0 if rec['ok']else 1

if __name__=='__main__':sys.exit(main())
