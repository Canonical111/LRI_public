#!/usr/bin/env python3
"""Uninstrumented comparisons, thread scaling, and a 64-real-graph RSS test.

Do not run other CPU workloads concurrently. These are performance fixtures,
not complete physical campaigns and not new estimates of C8.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time
from benchmark_c8 import make_net
from io_utils import ROOT, digest

FIELDS=("uid","rep","graph","begin","end","total","quad","mp","values","max_abs")

def execute(binary, sector, loop, ids, points, td, threads, batch=8, trial=0):
    tasks=[[i,rep,gid,0,points,points] for i,(rep,gid) in enumerate((rep,gid) for rep in range(4) for gid in ids)]
    (td/"tasks").write_text(f"C8D3TASKS1 {loop} {len(tasks)}\n"+"".join(" ".join(map(str,t))+"\n" for t in tasks))
    make_net(td/"net",4*loop-1,52,4,9158+loop)
    command=[str(binary),str(ROOT/"inputs"/sector),str(ROOT/"inputs/gamma_d3_8.txt"),str(td/"net"),str(td/"tasks"),str(td/"out"),
             "716397108621","0",".8",str(threads),"compensated","-"]
    started=time.perf_counter()
    cp=subprocess.run(["/usr/bin/time","-f","C8RSS %M",*command],check=True,capture_output=True,text=True,
                      env={**os.environ,"C8_GRAPH_BATCH":str(batch),"C8_LOAD_THREADS":"1","OMP_PROC_BIND":"close","OMP_PLACES":"cores"})
    result=json.loads((td/"out").read_text());result["wall_seconds"]=time.perf_counter()-started
    result["rss_kib"]=int(next(line.split()[1] for line in cp.stderr.splitlines() if line.startswith("C8RSS ")))
    return result


def exact(a,b):
    if len(a["rows"])!=len(b["rows"]):raise AssertionError("Row-count mismatch")
    for x,y in zip(a["rows"],b["rows"]):
        for k in FIELDS:
            if x[k]!=y[k]:raise AssertionError(f"Mismatch {k} at graph {x['graph']}")


def summary(rows):
    return {key:statistics.median(r[key] for r in rows) for key in ("wall_seconds","load_seconds","integration_seconds","rss_kib")}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repeats",type=int,default=3)
    p.add_argument("--threads",nargs="+",type=int,default=[1,2,4])
    p.add_argument("--output",type=Path,default=ROOT/"verification/performance/final_benchmark.json")
    a=p.parse_args()
    if a.repeats<1 or not a.threads or min(a.threads)<1:raise ValueError("Invalid benchmark size")
    baseline=ROOT/"bin/c8d3_baseline";optimized=ROOT/"bin/c8d3_optimized"
    cpu=next((ln.split(":",1)[1].strip() for ln in Path("/proc/cpuinfo").read_text().splitlines() if ln.startswith("model name")),"unknown")
    quota=Path("/sys/fs/cgroup/cpu.max")
    report={"scope":"Local CPU benchmarks only; not multi-node validation, not a new coefficient calculation",
            "cpu":cpu,"cpu_quota":quota.read_text().strip() if quota.exists() else None,
            "platform":platform.platform(),"repeats":a.repeats,"aggregation":"median",
            "baseline_sha256":digest(baseline),"optimized_sha256":digest(optimized),"workloads":[],"memory":[]}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    def publish():a.output.write_text(json.dumps(report,indent=2)+"\n")
    with tempfile.TemporaryDirectory(prefix="c8_performance_") as temp:
        td=Path(temp)
        for w in json.loads((ROOT/"tests/performance_workloads.json").read_text()):
            variants={"baseline":[],**{f"optimized_{t}":[] for t in a.threads}}
            expected=None
            for rep in range(a.repeats):
                names=list(variants) if rep%2==0 else list(reversed(variants))
                for name in names:
                    t=1 if name=="baseline" else int(name.split("_")[1]);binary=baseline if name=="baseline" else optimized
                    r=execute(binary,w["sector"],w["L"],w["graphs"],w["points"],td,t)
                    if expected is None:expected=r
                    else:exact(expected,r)
                    variants[name].append(r)
            row={**w,"identical_scientific_rows":True,"timings":{name:summary(rs) for name,rs in variants.items()}}
            if "optimized_1" in variants:
                row["single_core_speedup"]=row["timings"]["baseline"]["integration_seconds"]/row["timings"]["optimized_1"]["integration_seconds"]
                row["thread_speedups"]={str(t):row["timings"]["optimized_1"]["integration_seconds"]/row["timings"][f"optimized_{t}"]["integration_seconds"] for t in a.threads}
            report["workloads"].append(row);publish();print(json.dumps({k:row.get(k) for k in ("L","sector","single_core_speedup","thread_speedups")}),flush=True)
        ids=[r["id"] for r in json.loads((ROOT/"tests/memory_graphs.json").read_text())]
        old=execute(baseline,"free",8,ids,4,td,1)
        report["memory"].append({"variant":"baseline-all-graphs",**{k:old[k] for k in ("rss_kib","load_seconds","integration_seconds","wall_seconds")},"resident_graphs":len(ids)})
        for batch in (1,4,8):
            new=execute(optimized,"free",8,ids,4,td,1,batch=batch);exact(old,new)
            report["memory"].append({"variant":f"optimized-batch-{batch}",**{k:new[k] for k in ("rss_kib","load_seconds","integration_seconds","wall_seconds")},
                "resident_graphs":new["peak_graphs_resident"],"graph_vector_bytes":new["peak_graph_vector_bytes"],"identical_scientific_rows":True})
            publish()
    report["status"]="passed";publish();print(json.dumps(report["memory"],indent=2))

if __name__=="__main__":main()
