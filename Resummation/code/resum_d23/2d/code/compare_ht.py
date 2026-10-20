#!/usr/bin/env python3
"""Compare the fixed Borel protocol to the prod1 HT snapshot under Slurm.

No HT solve, fitted parameters, curve interpolation or cutoff extrapolation.
All 348 input rows are retained, including basis checks and moving references.
"""
from pathlib import Path
import csv, json, hashlib, os
import numpy as np
import calculate as c

R=Path(__file__).resolve().parents[1]
I=R/"inputs/ht_prod1"
index=json.loads((I/"index.json").read_text())
for name, expected in index["files"].items():
    assert hashlib.sha256((I/name).read_bytes()).hexdigest()==expected
def read(name):
    return list(csv.DictReader((I/name).open()))
rows=read("points.csv")
assert len(rows)==348
for r in rows:
    for k in ("x","s","Delta_thermal","tuning_residual","max_eigenvector_residual","window_fixed_point"):
        r[k]=float(r[k]); assert np.isfinite(r[k])
    r["L"]=int(r["L"]);r["nz"]=int(r["nz"])
    assert abs(r["s"]-(2-2*r["x"]))<1e-12
    assert .125<=r["x"]<=.5
    odd=json.loads(r["odd_gaps"]); even=json.loads(r["even_gaps"])
    assert max(abs(odd[0]-r["x"]),abs(odd[1]-(2-r["x"])))<1e-8
    assert abs(even[1]-r["Delta_thermal"])<1e-12
    r["benchmark"]=r["x"]==.125
    r["Delta_sigma"]=r["x"]
    r["epsilon"]=2-4*r["x"]
    r["delta_SR"]=r["x"]-.125
    r["kind"]="moving_reference" if r["chain"].startswith("ref") else r["role"]
    assert r["tuning_residual"]<1e-8 and r["max_eigenvector_residual"]<1e-8
xs=np.array(sorted(set(r["x"] for r in rows)))
assert len(xs)==13
cb=c.cb("curvature",8,x=xs)
pb, p1=c.pb("curvature",8,x=xs)
pb0,p0=c.pb("curvature",8,b=0,x=xs)
assert pb is not None and pb0 is None
pb0old,_=c.pb("curvature",7,b=0,x=xs)
assert pb0old is not None
cb120=c.cb("curvature",8,x=xs,nquad=120)
assert np.max(abs(cb-cb120))<2e-10
core=[c.cb("curvature",n,b,a,x=xs) for n in c.P["core_scan"]["orders"]
      for b in c.P["core_scan"]["b"] for a in c.P["core_scan"]["alpha"]]
lo,hi=np.min(core,axis=0),np.max(core,axis=0)
values={x:dict(CB8=float(cb[i]),PB8_b35=float(pb[i]),PB8_b0=None,PB7_b0=float(pb0old[i]),
               core_low=float(lo[i]),core_high=float(hi[i])) for i,x in enumerate(xs)}
for r in rows:
    r.update(values[r["x"]])
    r["HT_minus_CB8"]=r["Delta_thermal"]-r["CB8"]
    r["HT_minus_PB8_b35"]=r["Delta_thermal"]-r["PB8_b35"]
    r["HT_minus_PB8_b0"]=None
    r["HT_minus_PB7_b0"]=r["Delta_thermal"]-r["PB7_b0"]
main=sorted((r for r in rows if r["kind"]=="main"),key=lambda r:(r["x"],r["L"]))
assert len(main)==115 and all(r["nz"]==16 for r in main)
lookup={(r["chain"],r["L"],r["nz"]):r for r in rows}
assert len(lookup)==len(rows)
nested=read("nested.csv")
assert len(nested)==230
for n in nested:
    a=lookup[(n["chain"],int(n["L"]),int(n["nz"]))]
    b=lookup[(n["chain"],int(n["L"]),16)]
    assert abs((a["Delta_thermal"]-b["Delta_thermal"])-float(n["dDelta_thermal"]))<1e-14
latest=[]
for x in xs:
    seq=[r for r in main if r["x"]==x];r=seq[-1].copy()
    assert [t["L"] for t in seq]==list(range(8,r["L"]+1,2))
    assert r["L"]==(22 if x in (.125,.126) else 24)
    r["last_cutoff_step"]=r["Delta_thermal"]-seq[-2]["Delta_thermal"]
    for nz in (12,20):
        r["nz%d_minus_nz16"%nz]=lookup[(r["chain"],r["L"],nz)]["Delta_thermal"]-r["Delta_thermal"]
    latest.append(r)
moving=[]
for r in rows:
    if r["kind"]=="moving_reference":
        q=r.copy();q["moving_minus_density"]=r["Delta_thermal"]-lookup[("x%.3f"%r["x"],14,16)]["Delta_thermal"]
        moving.append(q)
desc=read("descendants.csv")
amb=sum(r["ambiguous"]=="True" for r in desc)
flags=(I/"flags.txt").read_text().splitlines()
assert len(desc)==2070 and amb==len(flags)==1678
assert all("ambiguous" in s for s in flags)
def write(name,rr):
    with (R/"results"/name).open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
write("ht_prod1_all_comparison.csv",rows)
write("ht_prod1_latest.csv",latest)
write("ht_prod1_moving_reference.csv",moving)
report=dict(date="2026-10-12",job_id=os.getenv("SLURM_JOB_ID"),main=main,latest=latest,
    moving_references=moving,counts=dict(all_rows=len(rows),main_ladder=len(main),nested_checks=len(nested),
       moving_references=len(moving),abscissae=len(xs),descendant_tests=len(desc),ambiguous_descendants=amb),
    max_GL120_240_difference=float(np.max(abs(cb-cb120))),
    max_tuning_residual=max(r["tuning_residual"] for r in rows),
    max_eigenvector_residual=max(r["max_eigenvector_residual"] for r in rows),
    max_window_residual=max(r["window_fixed_point"] for r in rows),
    max_nested_20_16=max(abs(float(n["dDelta_thermal"])) for n in nested if n["nz"]=="20"),
    max_nested_12_16=max(abs(float(n["dDelta_thermal"])) for n in nested if n["nz"]=="12"),
    max_moving_reference_difference=max(abs(r["moving_minus_density"]) for r in moving),
    poles=p1+p0,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    source_index_sha256=hashlib.sha256((I/"index.json").read_bytes()).hexdigest(),
    scope="Collected finite-cutoff data; no original per-solve JSON acceptance checks repeated. "
          "x=1/8 is a crossover benchmark. Cutoff and nested basis differences are diagnostics, not continuum error bars.")
(R/"results/ht_prod1_comparison.json").write_text(json.dumps(report,indent=2))
for r in latest:
    print("x=%.3f L=%d HT=%.10f CB=%.10f HT-CB=%+.7g laststep=%+.7g nz20-nz16=%+.3g"%
          (r["x"],r["L"],r["Delta_thermal"],r["CB8"],r["HT_minus_CB8"],r["last_cutoff_step"],r["nz20_minus_nz16"]),flush=True)
print("DIAGNOSTICS",{k:v for k,v in report.items() if k.startswith("max_")},flush=True)
print("MOVING",[(r["x"],r["moving_minus_density"]) for r in moving],flush=True)
print("VALIDATION PASSED",flush=True)
