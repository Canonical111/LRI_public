#!/usr/bin/env python3
"""Original versus optimized power-sector jets at one quadrature degree, on any inputs directory.

Used for new degrees (e.g. N7 on a validation directory from make_validation_inputs.py).
Differences are reported per slot relative to that slot's largest reference magnitude,
structurally zero (cancelled-pole) slots against the largest slot of the case.
"""
from __future__ import annotations
import argparse, decimal, json, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from workloads import files
from campaign import digest
D=decimal.Decimal

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--degree',type=int,required=True)
    p.add_argument('--L',type=int,nargs='+',default=[5,6,7]);p.add_argument('--out',type=Path,required=True);p.add_argument('--tol',type=float,default=1e-13);a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);inputs=a.inputs.resolve();env=dict(os.environ,OMP_NUM_THREADS='1')
    if not (ROOT/'bin/reference_power').exists():subprocess.run([sys.executable,ROOT/'tools/build_reference.py'],check=True)
    report={'degree':a.degree,'inputs':str(inputs),'executables':{n:digest(ROOT/'bin'/n) for n in ('reference_power','c7_integrate')},'cases':[]};worst=0.
    for L in a.L:
        w=files(out/f'L{L}',inputs,L,'power',2,2,6);ref=out/f'ref_L{L}.json';new=out/f'new_L{L}.json'
        for cmd,log in [([ROOT/'bin/reference_power',inputs,L,a.degree,2,2,41927510,ref,'power','.8',w['counts']],out/f'ref_L{L}.log'),
                        ([ROOT/'bin/c7_integrate','--mode','power','--inputs',inputs,'--L',L,'--tasks',w['tasks'],'--seed',41927510,'--rate','.8','--output',new,'--threads',1,'--tile',128,'--degree',a.degree],out/f'new_L{L}.log')]:
            with log.open('w') as f:subprocess.run(list(map(str,cmd)),check=True,stdout=f,stderr=subprocess.STDOUT,env=env)
        r=json.loads(ref.read_text(),parse_float=D);n=json.loads(new.read_text(),parse_float=D);scale=[D(0)]*14;diff=[D(0)]*14
        for row in n['rows']:
            x=r['graph_batches'][row['replicate']][row['graph']]
            for k in range(14):scale[k]=max(scale[k],abs(D(x[k])));diff[k]=max(diff[k],abs(D(row['value'][k])-D(x[k])))
        # Structurally zero slots (cancelled poles: below 1e-12 of the largest slot) hold only rounding noise in the
        # original; they are measured against the largest slot of the case, genuine slots against their own scale.
        floor=max(scale)*D('1e-12');eff=[s if s>=floor else max(scale) for s in scale];rel=[float(d/s) if s else (0. if d==0 else float('inf')) for d,s in zip(diff,eff)];worst=max(worst,max(rel))
        report['cases'].append({'L':L,'rows':len(n['rows']),'max_abs_difference':list(map(float,diff)),'slot_scale':list(map(float,scale)),'structural_zero_slots':[k for k,s in enumerate(scale) if s<floor],
                                'max_relative_to_slot_scale':max(rel)})
        print(f'L{L} N{a.degree}: max |new-original| / slot scale = {max(rel):.3g}',flush=True)
    report['passed']=worst<=a.tol;(out/'check_degree.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['passed']:sys.exit(f'degree {a.degree}: difference {worst:.3g} exceeds {a.tol:g} of slot scale')
if __name__=='__main__':main()
