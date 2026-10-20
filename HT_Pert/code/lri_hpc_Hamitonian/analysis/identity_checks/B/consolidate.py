import json, glob, csv, numpy as np, sys
sys.path.insert(0,'<PROJECT>/lri_eh_hpc/lri_eh')
from exact import fast
from fitlib import load
R=load()
V=['raw','g2D','g2D+g3W','Dfull_raw','Dfull_c']
rows=[]
for L,d in R.items():
    for v in V:
        x=d['variants'][v]
        row={'L':L,'variant':v,'r2':x['r'][2],'r3':x['r'][3],'r4':x['r'][4],'g1':x['g'][1],'g2':x['g'][2],'g3':x['g'][3],'g4':x['g'][4],
             'C2':x['C'][2],'C3':x['C'][3],'C4':x['C'][4]}
        for p in (1,2,3):
            for k in (2,3,4): row[f'dphi{p}_e{k}']=x[f'spacing_d{p}'][k]
        row['dC4_exact_g2D']=fast(L) if v=='g2D' else None
        rows.append(row)
for f in sorted(glob.glob('d1_L*.json')):
    d=json.load(open(f))
    if d['L'] in R: continue
    for v in V:
        x=d['variants'][v]
        rows.append({'L':d['L'],'variant':v,'r2':x['r'][2],'r3':x['r'][3],'r4':x['r'][4],**{f'dphi1_e{k}':x['spacing_d1'][k] for k in (2,3,4)}})
keys=sorted({k for r in rows for k in r},key=lambda k:(k not in('L','variant'),k))
with open('results_table.csv','w') as fh:
    w=csv.DictWriter(fh,fieldnames=keys); w.writeheader()
    for r in sorted(rows,key=lambda r:(r['L'],V.index(r['variant']))): w.writerow({k:(repr(r[k]) if isinstance(r.get(k),float) else r.get(k)) for k in keys})
json.dump(rows,open('results_table.json','w'),indent=0)
print(len(rows),'rows written')
