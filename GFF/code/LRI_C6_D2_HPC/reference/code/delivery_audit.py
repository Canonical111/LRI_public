"""Audit delivered production coverage, portable reassembly, sources and PDFs."""
from pathlib import Path
import json,hashlib,sys,platform
import numpy as np
import scipy,fitz
W=Path(__file__).resolve().parents[1]
def read(p):return json.loads((W/p).read_text())
plan=read('inputs/frozen_production_plan.json')['plan']
rows=[];totals={2:0,3:0}
for p in plan:
 tag,d,L=p['tag'],p['d'],p['L']
 r=read(f'records/{tag}_d{d}_L{L}.json');m=read(f'inputs/{tag}_d{d}_L{L}_manifest.json')
 assert r['replicates']==p['replicates']==len(r['batches'])
 assert r['N']==sum(r['counts_per_replicate'])*r['replicates']
 assert all(n==0 or n&(n-1)==0 for n in r['counts_per_replicate'])
 assert np.isfinite(np.array(r['batches'])).all()
 rows.append({'tag':tag,'d':d,'L':L,'samples':r['N'],'replicates':r['replicates'],'record':f'records/{tag}_d{d}_L{L}.json','elapsed_seconds':m['seconds']})
 totals[d]+=r['N']
assert len(rows)==16 and sum(totals.values())==782893056
(W/'verification/production_manifest.json').write_text(json.dumps(rows,indent=2))
aux=read('verification/cross_production_manifest.json')
for x in aux:
 r=read(f"records/paired_{x['tag']}_d2_L6.json")
 assert r['N']==x['samples']
assert sum(x['samples']for x in aux)==34144256
frozen=read('verification/production_source_hashes.json')
changed={p:sha for p,sha in frozen.items()if hashlib.sha256((W/p).read_bytes()).hexdigest()!=sha}
assert not changed
r=read('verification/method_precision_results.json');reported=read('verification/reported_values.json')
for d in ('2','3'):
 assert r[d]['C6']==reported[d]['underlying_mean']
 assert r[d]['sampling_standard_error']==reported[d]['sampling_standard_error']
 assert r[d]['weights']=={'prod_a':.25,'prod_b':.25,'new_a':.25,'new_b':.25}
replays={d:read(f'verification/delivery_replay_d{d}_L4.json')for d in [2,3]}
assert all(x['max_absolute_graph_replicate_difference']==0 for x in replays.values())
pdfs={}
for name in ['long_range_ising_complete.pdf','C6_numerical_methods.pdf']:
 with fitz.open(W/name)as doc:
  pdfs[name]={'pages':len(doc),'size_bytes':(W/name).stat().st_size}
assert pdfs['long_range_ising_complete.pdf']['pages']==204
assert pdfs['C6_numerical_methods.pdf']['pages']==8
logs={}
for base in ['long_range_ising_complete','C6_numerical_methods']:
 path=W/f'{base}.log'
 if not path.exists():path=W/f'verification/latex_artifacts/{base}.log'
 text=path.read_text(errors='replace')
 logs[base]={'overfull':text.count('Overfull'),'undefined_reference_warning':('There were undefined references' in text),'undefined_citation_warning':('There were undefined citations' in text)}
 assert not logs[base]['overfull'] and not logs[base]['undefined_reference_warning'] and not logs[base]['undefined_citation_warning']
out={'primary_campaign_loop_streams':16,'primary_samples_by_dimension':totals,'primary_samples':sum(totals.values()),'auxiliary_paired_samples':sum(x['samples']for x in aux),'auxiliary_control_in_primary_report':False,'frozen_source_or_input_changes':changed,'portable_reassembly_matches_reported_values':True,'portable_saved_net_replays':replays,'pdfs':pdfs,'appendix':'X, printed pages 195--202','latex_warnings':logs,'source_preservation':read('verification/source_preservation.json'),'visual_qa':'All eight standalone appendix pages rendered and visually inspected; no observed clipping, overlap or broken mathematics.','software':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'platform':platform.platform()},'evidence_scope':'Master/integrand, algebra, sampling and reproduction checks; no new independent graph or field-theory derivation, no rigorous interval bound, no rerun of analytic power compensation.'}
(W/'verification/delivery_audit.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
