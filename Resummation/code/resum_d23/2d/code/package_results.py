#!/usr/bin/env python3
"""Data assembly only: no physics fit, numerical solve, or new resummation."""
import csv, json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(name):
    with (ROOT/"results"/name).open() as f:
        return [{k:(float(v) if k not in ("mode","method","shape") else v) for k,v in r.items()} for r in csv.DictReader(f)]
curves=read("curves.csv")
mc=json.loads((ROOT/"inputs/monte_carlo.json").read_text())
refs=[]
for r in mc["points"]:
    x=(2-r["s"])/2
    near=min(curves,key=lambda p:abs(p["Delta_sigma"]-x))
    assert abs(x-near["Delta_sigma"])<1e-12
    refs.append(dict(x=x,y=2-r["inverse_nu"],error=r["reported_error"],s=r["s"],
                     residual=2-r["inverse_nu"]-near["curvature_CB8"]))
with (ROOT/"results/reference_comparison.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=refs[0]);w.writeheader();w.writerows(refs)
plot=dict(curves=curves,held_out=read("held_out.csv"),ratios=read("ratios.csv"),references=refs)
ht=json.loads((ROOT/"results/ht_prod1_comparison.json").read_text())
plot.update(ht_main=ht["main"],ht_latest=ht["latest"],ht_counts=ht["counts"])
(ROOT/"inputs/plot_data.json").write_text(json.dumps(plot,separators=(",",":"),allow_nan=False))
sources={
 "GFF":"<PROJECT>/GFF/LRI_condensed_note/long_range_ising_condensed.tex",
 "SRI":"<PROJECT>/SRI/LRI_C2_final_method/note/C2_final_method.tex",
 "SRI_summary":"<PROJECT>/SRI/LRI_C2_final_method/outputs/summary.json"}
snapshots={"GFF":"inputs/sources/long_range_ising_condensed.tex",
           "SRI":"inputs/sources/C2_final_method.tex","SRI_summary":"inputs/sri_summary.json"}
manifest=dict(sources={k:dict(original_path=v,snapshot=snapshots[k],
                             sha256=hashlib.sha256((ROOT/snapshots[k]).read_bytes()).hexdigest()) for k,v in sources.items()},
              files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(ROOT.rglob("*")) if p.is_file() and p.name!="manifest.json"
                     and "__pycache__" not in p.parts and "qa" not in p.parts and "history" not in p.parts})
(ROOT/"manifest.json").write_text(json.dumps(manifest,indent=2))
print("Packaged",len(curves),"curve points,",len(refs),"reference points.")
