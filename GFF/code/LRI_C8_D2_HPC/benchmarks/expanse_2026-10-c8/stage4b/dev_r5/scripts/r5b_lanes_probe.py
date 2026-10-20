#!/usr/bin/env python3
"""R5b development check (Stage 4b; not a plan gate): the lane shapes that tools/lanes.py (the lane worker's
worker_lanes) and tools/sweep.py (the sweep's process slots) choose on the real topology of the node this runs on,
read from sysfs and /proc/cpuinfo inside the job's affinity set. For C8_LANES unset with plans of --threads 8 and 16,
C8_LANES=numa and C8_LANES=16, it records the lane sizes, each lane's CPUs and NUMA nodes, and whether every lane lies
inside one NUMA node. Expected on an Expanse compute node (2 x EPYC 7742, 8 NUMA nodes of 16 cores): default at
--threads 8 -> 16 x 8, NUMA-aligned; default at --threads 16 -> 8 x 16; numa -> 8 x 16; 16 -> 16 x 8.

  cd <package export>; python3 -B <this script> --output FILE"""
from __future__ import annotations
import argparse,contextlib,io,json,os,sys,tempfile
from pathlib import Path
from types import SimpleNamespace as NS

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--package',type=Path,default=Path.cwd());a=ap.parse_args()
    sys.path.insert(0,str(a.package.resolve()/'tools'))
    import lanes,sweep
    cpus=sorted(os.sched_getaffinity(0));nodes=lanes.numa_nodes();where={c:n for n,cl in nodes.items()for c in cl}
    rec={'schema':'c8-d2-dev-r5b-lanes-probe-1','host':os.uname().nodename,'affinity_cpus':len(cpus),'vendor':lanes.cpu_vendor(),
         'physical_cores':len(lanes.physical(cpus)),'numa_nodes':{str(n):len(c)for n,c in sorted(nodes.items())},'lanes_py':str(Path(lanes.__file__).resolve()),'cases':{}}
    expect={'default_threads8':[8]*16,'default_threads16':[16]*8,'numa_threads8':[16]*8,'equal16_threads8':[8]*16}
    ok=True
    for name,spec,threads in (('default_threads8',None,8),('default_threads16',None,16),('numa_threads8','numa',8),('equal16_threads8','16',8)):
        ls,what=lanes.worker_lanes(cpus,spec,{'threads':threads,'checkpoint_tasks':256})
        aligned=all(len({where.get(c,-1)for c in l})==1 for l in ls)
        c={'spec':spec,'plan_threads':threads,'sizes':[len(l)for l in ls],'what':what,'numa_aligned':aligned,
           'lanes':[{'cpus':f'{l[0]}-{l[-1]}'if l==list(range(l[0],l[-1]+1))else l,'numa_nodes':sorted({where.get(x,-1)for x in l})}for l in ls]}
        c['as_expected']=c['sizes']==expect[name]and aligned;ok&=c['as_expected'];rec['cases'][name]=c
        print(f'{name}: {len(ls)} lanes of {sorted(set(c["sizes"]))} cores, NUMA-aligned {aligned}; {what}',flush=True)
    with tempfile.TemporaryDirectory()as td:
        run=Path(td);(run/'manifest.json').write_text(json.dumps({'jobs':[]}))
        for th,want in ((8,[8]*16),(16,[16]*8)):
            out=io.StringIO()
            with contextlib.redirect_stdout(out):sweep.run_indices(run,NS(threads=th,procs=None,scratch=None),{})
            line=out.getvalue().strip();good=f'{len(want)} process slots of {want} CPUs'in line;ok&=good
            rec['cases'][f'sweep_threads{th}']={'line':line,'as_expected':good};print(f'sweep --threads {th}: {line}',flush=True)
    rec['status']='passed'if ok else'failed'
    a.output.write_text(json.dumps(rec,indent=1)+'\n');print(rec['status'])
    return 0 if ok else 1

if __name__=='__main__':sys.exit(main())
