#!/usr/bin/env python3
"""R3a development profile (informative, not a gate): where does the time of the R3a worker go now?

  r3a_prof.py --exe NAME=PATH [--exe NAME=PATH ...] --output DIR [--block heavy_free_L8] [--tasks 32] [--threads 16]
              [--scratch DIR] [--perf perf]

The first --tasks tasks of the fixture block (benchmarks/fixtures8; graphs staged from the pinned packs and checked
against the inventory sha256) run once per executable at --threads threads pinned to the job's first cores, under
`perf record -F 999 -N`; then `perf report --no-children --sort symbol --stdio -n` (the P1 report) and, for every
executable, `perf annotate --stdio` of its calculate_shared<__float128> symbol. Records the run times, the rows digest
(equal across executables) and the parsed symbol shares (tools/benchkit.py, as P1).
"""
from __future__ import annotations
import argparse,json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools'))
import benchkit as bk
from common import digest,load

def main()->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--exe',action='append',required=True);p.add_argument('--output',required=True);p.add_argument('--block',default='heavy_free_L8')
    p.add_argument('--tasks',type=int,default=32);p.add_argument('--threads',type=int,default=16);p.add_argument('--scratch');p.add_argument('--perf',default='perf')
    a=p.parse_args();out=Path(a.output).resolve();out.mkdir(parents=True)
    m=bk.load_fixtures();I=m['_inputs'];inv=load(I.where('inventory.json'));b=bk.block_of(m,a.block);n=m['native']
    sc=Path(tempfile.mkdtemp(prefix='c8d2_r3aprof_',dir=a.scratch or tempfile.gettempdir()))
    order,L,rows=bk.read_tasks(Path(b['tasks_path']));rows=rows[:a.tasks];tasks=sc/'tasks';bk.write_tasks(tasks,order,L,rows)
    st=bk.stage_graphs(I,inv,b['sector'],b['L'],sorted({r[2]for r in rows}),sc/'graphs')
    cpus=sorted(os.sched_getaffinity(0))[:a.threads];rec={'schema':'c8-d2-r3a-prof-1','block':a.block,'tasks':len(rows),'threads':a.threads,'staging':st,'runs':{}}
    try:
        for spec in a.exe:
            name,path=spec.split('=',1);exe=Path(path).resolve();o=sc/f'{name}.json';data=sc/f'{name}.perf.data'
            cmd=[a.perf,'record','-F','999','-N','-o',str(data),'--',*bk.native_cmd(exe,sc/'graphs',I.where(bk.GAMMA),b['net_path'],tasks,o,b['native_seed'],n['layout'],n['rate'],a.threads,n['sum_mode'])]
            t0=time.time();cp=subprocess.run([str(c)for c in cmd],capture_output=True,text=True,env=bk.omp_env(a.threads),preexec_fn=bk.pinner(cpus),timeout=3600)
            if cp.returncode:raise RuntimeError(f'{name}: {cp.stderr[-1500:]}')
            nat=json.loads(o.read_text());r={'sha256':digest(exe),'integration_seconds':nat['integration_seconds'],'wall_seconds':round(time.time()-t0,2),
               'rows_digest':bk.combined_digest(bk.rows_digest(nat['rows'])),'quad':sum(x['quad']for x in nat['rows']),'mp':sum(x['mp']for x in nat['rows']),
               'record':bk.parse_perf_record_stderr(cp.stderr)}
            rep=subprocess.run([a.perf,'report','-i',str(data),'--no-children','--stdio','-n','--sort','symbol','--percent-limit','0.01'],capture_output=True,text=True,timeout=1800)
            (out/f'{name}.report_symbol.txt').write_text(rep.stdout);parsed=bk.parse_perf_report(rep.stdout)
            r['top']=bk.symbol_table(parsed.get('rows',[]))[:30]if isinstance(parsed,dict)else None
            try:r['shares']=bk.perf_shares(parsed.get('rows',[]),exe.name)
            except Exception as e:r['shares']={'error':str(e)}
            sym=next((x['symbol']for x in parsed.get('rows',[])if 'calculate_shared<__float128'in x.get('symbol','')),None)
            if sym:
                an=subprocess.run([a.perf,'annotate','-i',str(data),'--stdio','-s',sym],capture_output=True,text=True,timeout=1800)
                (out/f'{name}.annotate_quad.txt').write_text(an.stdout)
            rec['runs'][name]=r;print(json.dumps({name:{k:r[k]for k in('integration_seconds','rows_digest','quad','mp')}}),flush=True)
        rec['rows_identical']=len({r['rows_digest']for r in rec['runs'].values()})==1
    finally:
        (out/'r3a_prof.json').write_text(json.dumps(rec,indent=1,default=str)+'\n');shutil.rmtree(sc,ignore_errors=True)
    return 0 if rec.get('rows_identical')else 1

if __name__=='__main__':sys.exit(main())
