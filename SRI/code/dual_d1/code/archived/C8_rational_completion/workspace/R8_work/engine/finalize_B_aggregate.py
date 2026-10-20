"""Independent standard-library acceptance of a weighted Task-B completion.
Uses exact Fractions, lower-moment Laurent polynomials, complete input coverage,
and every terminal partition. No prospective C8 value is an input.
"""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json,itertools,argparse
ROOT=Path(__file__).resolve().parent.parent

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(2**20),b''):h.update(x)
 return h.hexdigest()
def resolve(path):
 p=Path(path); marker='/R8_work/'
 if marker in str(p): return ROOT/str(p).split(marker,1)[1]
 if p.is_absolute(): raise ValueError('Unportable input path: '+str(p))
 return ROOT/p
def add(a,b,scale=F(1)):
 out=dict(a)
 for k,v in b.items():
  z=out.get(k,F(0))+scale*v
  if z:out[k]=z
  else:out.pop(k,None)
 return out
def mul(a,b):
 out={}
 for (p,l,j),x in a.items():
  for (q,m,k),y in b.items():
   if j+k<=1:
    key=(p+q,l+m,j+k);out[key]=out.get(key,F(0))+x*y
 return {k:v for k,v in out.items() if v}
def powp(a,n):
 out={(0,0,0):F(1)}
 for _ in range(n):out=mul(out,a)
 return out
def lower_predictions():
 src=json.loads((ROOT/'lower_controls.json').read_text());raw=src['lower_moments']
 def jet(name):
  return {(int(p),l,j):F(v) for j,suffix in enumerate(('base','v')) for p,poly in raw[f'{name}_{suffix}'].items() for l,v in enumerate(poly) if F(v)}
 Q2,Q4,Q6,Z2,Z4,Z6=map(jet,['Q2','Q4','Q6','Z2','Z4','Z6'])
 ans=mul(Q6,Z2);ans=add(ans,mul(Q4,powp(Z2,2)),-1);ans=add(ans,mul(Q4,Z4));ans=add(ans,mul(Q2,powp(Z2,3)));ans=add(ans,mul(mul(Q2,Z2),Z4),-2);ans=add(ans,mul(Q2,Z6))
 ref=json.loads((ROOT/'lower_reference_checks.json').read_text())['Q8_base_singular_polynomials'];base={};targets={}
 for p in (-3,-2,-1):
  row=list(map(F,ref[str(p)]));got=[ans.get((p,l,0),F(0)) for l in range(max(l for (a,l,v) in ans if a==p and v==0)+1)];assert got==row,(p,got,row);base[p]=row
  targets[p]=[ans.get((p,m,1),F(0)) for m in (0,1)];assert targets[p]==list(map(F,src['six_targets'][str(p)]))
 return base,targets

def inverse(poly,p):
 # Unique polynomial h with h'+p*h=poly; solve downward.
 out=[F(0)]*len(poly)
 for k in range(len(poly)-1,-1,-1):out[k]=(poly[k]-(k+1)*(out[k+1] if k+1<len(poly) else 0))/p
 assert all(p*out[k]+(k+1)*(out[k+1] if k+1<len(out) else 0)==poly[k] for k in range(len(out)))
 return out

def accept():
 specpath=ROOT/'remaining_aggregate/remaining_spec.json';spec=json.loads(specpath.read_text());work=specpath.parent/'remaining_spec_work';r=json.loads((work/'result_parallel.json').read_text());meta=json.loads((work/'combined_meta.json').read_text())
 assert r['status']=='complete_weighted_boundary_aggregate' and meta['status']=='complete_exact_linear_combination';assert meta['spec_sha256']==sha(specpath);assert sha(work/'combined_stage4.jsonl')==r['source_sha256']==meta['output_sha256']
 all_names=[]
 for face,n in ((1,8),(2,13),(3,8),(4,8)):
  m=json.loads((ROOT/'scaled_blocks'/f'n8_face{face}_manifest.json').read_text());assert m['source_complete'] and len(m['blocks'])==n
  for row in m['blocks']:
   assert row['source_sha256']==sha(ROOT/'scaled_blocks'/row['id']/'stage1.jsonl');all_names.append(row['id'])
 archived=spec['archived_complete_blocks'];remaining=spec['remaining_blocks'];assert len(all_names)==37 and len(set(all_names))==37;assert set(all_names)=={d['block'] for d in archived}|{d['block'] for d in remaining};assert len(archived)+len(remaining)==37
 old=[F(0)]*7
 for d in archived:
  folder=ROOT/'scaled_blocks'/d['block'];path=folder/'result.json';a=json.loads(path.read_text());assert sha(path)==d['result_sha256'] and a['source_sha256']==d['source_sha256'];assert a['status']=='complete_block_not_full_integral' and len(a['dimensionless_negative_inverse_euler'])==6;w=F(d['weight']);assert w==(1 if '_f4_' in d['block'] else 2)
  vals=[F(a['value'])]+list(map(F,a['dimensionless_negative_inverse_euler']));old=[x+w*y for x,y in zip(old,vals)]
 checked_sources=[]
 for d in remaining:
  folder=ROOT/'scaled_blocks'/d['block'];assert F(d['weight'])==(1 if '_f4_' in d['block'] else 2);assert sha(folder/'stage1.jsonl')==d['source1_sha256'];p=folder/'chunks_250/source_manifest.json';m=json.loads(p.read_text());assert m['status']=='complete_disjoint_stage4_sources';assert sha(p)==d['chunk_manifest_sha256'] and sha(folder/'stage3.jsonl')==d['source3_sha256'];start=0
  with (folder/'stage3.jsonl').open() as inp:
   for row in m['parts']:
    assert row['start']==start;lines=[next(inp) for _ in range(row['rows'])];assert hashlib.sha256(''.join(lines).encode()).hexdigest()==row['source_sha256'];path=folder/'chunks_250'/row['part']/'stage4.jsonl';assert sha(path)==row['output_sha256'];checked_sources.append((str(path),row['output_sha256'],str(d['weight'])));start+=row['rows']
   assert not inp.read()
  assert start==d['source3_rows']
 assert len(checked_sources)==len(spec['sources']);assert set(checked_sources)=={(str(resolve(d['path'])),d['sha256'],d['weight']) for d in spec['sources']}
 # Independently regenerate the exact source-to-bucket partition (without
 # parsing symbolic coefficients), then verify complete output concatenation.
 partition=json.loads((work/'partition_meta.json').read_text());nb=partition['buckets'];assert nb==meta['buckets'] and partition['spec_sha256']==sha(specpath)
 digests=[hashlib.sha256() for _ in range(nb)];input_rows=0
 for source in spec['sources']:
  weight=str(F(source['weight']))
  for line in resolve(source['path']).open():
   ww,ll,cs=json.loads(line);key=json.dumps([ww,ll],separators=(',',':'));j=int.from_bytes(hashlib.sha256(key.encode()).digest()[:4],'little')%nb
   digests[j].update((json.dumps([weight,ww,ll,cs],separators=(',',':'))+'\n').encode());input_rows+=1
 assert input_rows==partition['input_rows']==meta['input_rows'] and len(meta['bucket_outputs'])==nb
 concatenated=hashlib.sha256()
 for i,row in enumerate(meta['bucket_outputs']):
  assert row['name']==f'out{i:03d}.jsonl' and partition['bucket_files'][i]['sha256']==digests[i].hexdigest()==row['input_sha256']
  path=work/row['name'];assert sha(path)==row['output_sha256']
  with path.open('rb') as inp:
   for buf in iter(lambda:inp.read(2**20),b''):concatenated.update(buf)
 assert concatenated.hexdigest()==meta['output_sha256']
 # Recompute each terminal slice from its stored exact output, after checking its
 # disjoint source bytes. This is an output/source assembly, not reintegration.
 termdir=work/r['terminal_directory'];current=[F(0)]*7;start=0;rowsizes=[];parts=sorted(termdir.glob('part[0-9][0-9][0-9][0-9].json'))
 with (work/'combined_stage4.jsonl').open() as inp:
  for part in parts:
   a=json.loads(part.read_text());assert a['status']=='complete_exact_terminal_partition' and a['start']==start;lines=[next(inp) for _ in range(a['rows'])];assert hashlib.sha256(''.join(lines).encode()).hexdigest()==a['source_sha256'];vals=[F(a['value'])]+list(map(F,a['negative']));current=[x+y for x,y in zip(current,vals)];start+=a['rows'];rowsizes.append(a['rows'])
  assert not inp.read()
 assert start==r['source_rows']==meta['output_rows'];assert current==[F(r['value'])]+list(map(F,r['negative']))
 tail=json.loads((ROOT/'independent_terminal_tail_value.json').read_text());last=json.loads((ROOT/'independent_terminal_tail_fast.json').read_text())
 assert tail['status']=='independent_complete_terminal_slice_evaluated' and tail['source_start']==last['source_start']==80000 and tail['source_rows']==last['source_rows']==16
 with (work/'combined_stage4.jsonl').open() as inp:
  for _ in range(80000):next(inp)
  segment=list(itertools.islice(inp,16))
 assert hashlib.sha256(''.join(segment).encode()).hexdigest()==tail['source_sha256']==last['source_sha256']
 assert F(tail['value'])==F(last['value']) and list(map(F,tail['negative']))==list(map(F,last['negative']))
 base,targets=lower_predictions();combined=[a+b for a,b in zip(old,current)];checks=[]
 for i,p in enumerate((-3,-2,-1)):
  inv=inverse(base[p],p)
  for m in (0,1):
   val=combined[1+2*i+m]+8*(inv[m] if m<len(inv) else 0)-8*(base[p][m-1] if m>0 else 0);checks.append({'power':p,'log_degree':m,'actual':str(val),'independent_lower_prediction':str(targets[p][m]),'exact_equal':val==targets[p][m]})
 good=all(c['exact_equal'] for c in checks);R8=-combined[0]
 result={'status':'Task_B_complete' if good else 'DO_NOT_ACCEPT_divergence_failure','definition':'pi_0 [epsilon^0 log(epsilon)] partial_v Q8 at v=1,delta=0','R8':str(R8),'C8_rational_contribution':str(-R8/8),'updated_C8_constant':str(F(-298171,3)-R8/8),'independent_fixed_word_terminal_check_rows':16,'independent_fixed_word_terminal_check_all_seven_exact':True,'source_to_bucket_partition_independently_rebuilt':True,'all_bucket_outputs_concatenate_exactly':True,'source_blocks':37,'archived_individual_blocks':len(archived),'new_jointly_integrated_blocks':len(remaining),'complete_disjoint_source_coverage':True,'new_stage4_source_parts':len(checked_sources),'final_combined_source_rows':start,'final_terminal_slices':len(parts),'archived_weighted_values':list(map(str,old)),'new_weighted_values':list(map(str,current)),'complete_weighted_values':list(map(str,combined)),'six_divergence_checks':checks,'C8_not_finished':True,'C8_conjecture_used':False,'remaining_C8_groups':['R_tail','R9'],'result_proof_stage':'exact weighted source integration with independent rational acceptance controls'}
 (ROOT/'Task_B_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert good,'The exact total must pass all six independent controls.'
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--controls-only',action='store_true');a=p.parse_args()
 if a.controls_only:
  b,t=lower_predictions();print(json.dumps({'exact_lower_polynomial_regeneration':True,'base':{str(k):list(map(str,v)) for k,v in b.items()},'targets':{str(k):list(map(str,v)) for k,v in t.items()}},indent=2))
 else:accept()
