"""Final delivery manifest and immutable result copies; no new integrals."""
import json,hashlib,csv,os
from pathlib import Path
import numpy as np
W=Path(__file__).resolve().parents[1]
if __name__=='__main__':
 reps=json.load(open(W/'verification/reported_values.json'))
 final={}
 for d in (2,3):
  j=json.load(open(W/f'verification/precision_d{d}_prod_a_prod_b.json'))
  j['reporting']=reps[str(d)];j[f'full_C6_{d}']=j['C6'];j['reported_value']=reps[str(d)]['reported_estimate'];j['empirical_uncertainty']=reps[str(d)]['empirical_allowance'];j['scope']='Precision update in the retained complete physical six-loop framework; not a new independent graph or field-theory derivation.'
  (W/f'verification/C6_d{d}_precision_result.json').write_text(json.dumps(j,indent=2));final[d]=j
 with (W/'verification/precision_summary.csv').open('w')as f:
  w=csv.writer(f);w.writerow(['dimension','epsilon','C6_estimate','sampling_standard_error','reported_center','empirical_allowance','L3_SE','L4_SE','L5_SE','L6_SE','shared_known_SE'])
  for d,j in final.items():
   r=reps[str(d)];w.writerow([d,f'2s-{d}',j['C6'],j['sampling_standard_error'],r['reported_estimate'],r['empirical_allowance'],*[j['error_by_loop'][str(L)]for L in range(3,7)],j['known76_common_uncertainty']])
 (W/'verification/precision_results.json').write_text(json.dumps({str(d):j for d,j in final.items()},indent=2))
 # Complete production manifest, reconstructed from declared plan and actually saved records.
 plan=json.load(open(W/'inputs/production_plan.json'));manifest=[]
 for row in plan:
  tag,d,L=row['tag'],row['d'],row['L'];p=W/f'records/{tag}_d{d}_L{L}.json';r=json.load(open(p))
  assert r['replicates']==row['replicates']==64
  assert r['seed']==row['seed']+1279*L and r['bits']==row['bits']
  assert r['N']==r['replicates']*sum(r['counts_per_replicate'])
  assert all(n>0 and not (n&(n-1)) for n in r['counts_per_replicate'])
  g=np.array(r['graph_batches']);assert g.shape[0]==64
  assert np.max(np.abs(g.sum(1)-np.array(r['batches']))) <1e-6
  cf=W/f'inputs/{tag}_d{d}_L{L}_counts.txt';nf=W/f'inputs/{tag}_d{d}_L{L}_net.bin'
  manifest.append({**row,'samples':r['N'],'result':str(p.relative_to(W)),'result_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'counts_sha256':hashlib.sha256(cf.read_bytes()).hexdigest(),'net_sha256':hashlib.sha256(nf.read_bytes()).hexdigest(),'quad_fallbacks':r['quad_fallbacks'],'mp_fallbacks':r['mp_fallbacks']})
 (W/'verification/complete_production_manifest.json').write_text(json.dumps(manifest,indent=2))
 # Hash all scientific source, records and delivery files, excluding ephemeral builds.
 excluded={'.aux','.log','.out','.toc','.synctex.gz','.so'}
 hashes={}
 for p in W.rglob('*'):
  if not p.is_file()or p.name=='SHA256SUMS.json'or'__pycache__'in p.parts:continue
  if p.suffix in excluded or (p.suffix=='' and os.access(p,os.X_OK)):continue
  hashes[str(p.relative_to(W))]=hashlib.sha256(p.read_bytes()).hexdigest()
 (W/'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2))
 print('All 16 production streams passed count/seed/aggregate checks; files hashed:',len(hashes))
