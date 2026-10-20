#!/usr/bin/env python3
"""R4a speed check (Stage 4b development; A-PERF-2 style, median of repeats on one node).

  r4a_speed.py --variant base=DIR --variant r4a=DIR [--variant NAME=DIR ...] --output OUT [--blocks heavy_free_L8,heavy_power_L8]
               [--repeats 3] [--threads 64] [--scratch DIR]

DIR/c8d2_gmp of each variant runs every fixture block (benchmarks/fixtures8, the block's own net, seed and native
settings) REPEATS times at THREADS threads. The node's cores are split into two NUMA-aligned sets of THREADS physical
cores (one socket each on a 2 x EPYC 7742 node); two streams of runs go on at the same time, one per set, so both
sockets are always loaded. The runs of each (block, repeat) are rotated across the variants and handed alternately to
the two streams, so every variant runs on both sockets. Per run: the worker's integration_seconds (graph loading
excluded), the wall seconds, the task seconds, and a digest of every row's scientific fields. Per (variant, block): the
median integration seconds; speedup = median(base) / median(variant). Rule: within a block, every run of every
variant has the same rows digest (exactness on the block; mp > 0 rows included). Exit 0 when it holds.
"""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,json,os,shutil,statistics,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
import benchkit as bk
from common import load

def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--variant',action='append',required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--blocks',default='heavy_free_L8,heavy_power_L8');ap.add_argument('--repeats',type=int,default=3)
    ap.add_argument('--threads',type=int,default=64);ap.add_argument('--scratch')
    a=ap.parse_args();out=a.output.resolve();out.mkdir(parents=True)
    variants={}
    for v in a.variant:
        name,d=v.split('=',1);exe=Path(d)/'c8d2_gmp'
        if not exe.is_file():raise SystemExit(f'{exe} missing')
        variants[name]=exe
    if 'base'not in variants:raise SystemExit('a variant named base is required')
    sc=Path(tempfile.mkdtemp(prefix='r4a_speed_',dir=a.scratch or os.environ.get('TMPDIR')or None))
    m=bk.load_fixtures();I=m['_inputs'];inv=load(I.where('inventory.json'));gamma=I.where(bk.GAMMA);n=m['native']
    blocks={}
    for name in a.blocks.split(','):
        b=bk.block_of(m,name);g=sc/'graphs'/name;b['staging']=bk.stage_graphs(I,inv,b['sector'],b['L'],b['graphs'],g);b['root']=str(g);blocks[name]=b
    cores=bk.host_cores();sets=bk.partition(cores,2,a.threads)
    names=list(variants);jobs=[]
    for bn in blocks:
        for rep in range(a.repeats):
            k=rep%len(names);jobs+= [(v,bn,rep)for v in names[k:]+names[:k]]
    streams=[jobs[0::2],jobs[1::2]]
    ident={k:{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'describe':json.loads(subprocess.run([str(p),'--describe'],capture_output=True,text=True).stdout)}for k,p in variants.items()}
    runs=[]
    def stream(si):
        for v,bn,rep in streams[si]:
            b=blocks[bn];o=sc/f'{v}_{bn}_{rep}.json';log=out/f'{v}_{bn}_{rep}.log'
            cmd=bk.native_cmd(variants[v],b['root'],gamma,b['net_path'],b['tasks_path'],o,b['native_seed'],n['layout'],n['rate'],a.threads,n['sum_mode'])
            t0=time.perf_counter();t_start=time.time()
            with open(log,'w')as lf:cp=subprocess.run(cmd,stdout=lf,stderr=subprocess.STDOUT,env=bk.omp_env(a.threads),preexec_fn=bk.pinner(sets[si]))
            wall=time.perf_counter()-t0
            if cp.returncode:raise RuntimeError(f'{v} {bn} {rep}: exit {cp.returncode}: {log.read_text()[-600:]}')
            nat=load(o);s=bk.native_summary(nat,a.threads);dg=bk.combined_digest(bk.rows_digest(nat['rows']));o.unlink()
            r={'variant':v,'block':bn,'repeat':rep,'stream':si,'cpus':[sets[si][0],sets[si][-1]],'start_unix':t_start,'wall_seconds':wall,
               'integration_seconds':s['integration_seconds'],'load_seconds':s['load_seconds'],'task_seconds':s['task_seconds'],
               'openmp_efficiency':s['openmp_efficiency'],'points':s['points'],'quad':s['quad'],'mp':s['mp'],'max_rss_kb':s['max_rss_kb'],'rows_digest':dg}
            runs.append(r);print(f'{v:8s} {bn} rep {rep} stream {si}: integration {r["integration_seconds"]:.2f} s, wall {wall:.2f} s, mp {s["mp"]}, digest {dg[:12]}',flush=True)
    t0=time.time()
    with concurrent.futures.ThreadPoolExecutor(2)as ex:
        for f in [ex.submit(stream,i)for i in range(2)]:f.result()
    res={'schema':'c8-d2-r4a-speed-1','threads':a.threads,'repeats':a.repeats,'cpu_sets':[[s[0],s[-1],len(s)]for s in sets],'executables':ident,
         'host':os.uname().nodename,'slurm_job':os.environ.get('SLURM_JOB_ID'),'wall_seconds':time.time()-t0,'runs':sorted(runs,key=lambda r:(r['block'],r['variant'],r['repeat'])),'blocks':{},'ok':True}
    tot={v:0.0 for v in names}
    for bn in blocks:
        rb=[r for r in runs if r['block']==bn];digests=sorted({r['rows_digest']for r in rb})
        med={v:statistics.median(r['integration_seconds']for r in rb if r['variant']==v)for v in names}
        medt={v:statistics.median(r['task_seconds']for r in rb if r['variant']==v)for v in names}
        for v in names:tot[v]+=med[v]
        res['blocks'][bn]={'rows_identical':len(digests)==1,'rows_digest':digests,'mp_points':rb[0]['mp'],'quad_points':rb[0]['quad'],'points':rb[0]['points'],
            'median_integration_seconds':med,'median_task_seconds':medt,
            'speedup_vs_base':{v:med['base']/med[v]for v in names},'speedup_task_seconds_vs_base':{v:medt['base']/medt[v]for v in names},
            'integration_seconds':{v:[r['integration_seconds']for r in sorted(rb,key=lambda r:r['repeat'])if r['variant']==v]for v in names}}
        res['ok']&=len(digests)==1
    res['both_blocks']={'median_integration_seconds_sum':tot,'speedup_vs_base':{v:tot['base']/tot[v]for v in names}}
    (out/'speed.json').write_text(json.dumps(res,indent=1)+'\n')
    shutil.rmtree(sc,ignore_errors=True)
    print(json.dumps({k:v for k,v in res.items()if k not in('runs','executables')},indent=1))
    return 0 if res['ok']else 1

if __name__=='__main__':sys.exit(main())
