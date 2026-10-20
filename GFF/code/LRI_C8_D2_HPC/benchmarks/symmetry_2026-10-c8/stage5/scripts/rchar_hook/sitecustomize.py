"""J-SMK-4 measurement hook (NOT part of the package; symmetry Stage 5). PLAN A-ORC-13 (real-Slurm part) and R07 ask
that each `production.py run` log its /proc/self/io rchar at exit; the package at 5d7586e does not, so the throughput
drill puts this directory on PYTHONPATH (exported into the lane worker job, inherited by every lane and run process).
Python imports sitecustomize at start-up; for a `production.py run` process only, an atexit handler reads
/proc/self/io once at normal interpreter exit (rchar there includes the reaped children: the native worker and the
fingerprint's ldd) and writes one JSON file into $C8_RCHAR_DIR, with the process's own peak RSS and the largest peak RSS of its reaped
children (getrusage; the native worker), for A-ORC-5's per-lane peak RSS (native + Python) on the smoke. Every other process is untouched. It never reads or
writes anything else, never changes sys.path or the run's arguments, and fails silently."""
import os,sys
def _c8_rchar():
    try:
        import json,resource,time
        a=sys.argv
        if len(a)<3 or not a[0].endswith('production.py') or a[1]!='run':return
        d=os.environ.get('C8_RCHAR_DIR')
        if not d:return
        with open('/proc/self/io')as f:io=dict(l.split(':',1)for l in f.read().strip().splitlines())
        idx=a[a.index('--index')+1]if '--index'in a else None
        rec={'pid':os.getpid(),'index':idx,'argv':a[1:],'end_epoch':time.time(),'job':os.environ.get('SLURM_JOB_ID'),
             'restart':os.environ.get('SLURM_RESTART_COUNT'),**{k.strip():int(v)for k,v in io.items()},
             'ru_maxrss_self_kb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'ru_maxrss_children_kb':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}
        with open(os.path.join(d,f'rchar.{idx}.{os.getpid()}.{time.time_ns()}.json'),'x')as f:f.write(json.dumps(rec)+'\n')
    except Exception:pass
import atexit;atexit.register(_c8_rchar)  # sys.argv is checked at exit (it may not be set yet while site runs)
