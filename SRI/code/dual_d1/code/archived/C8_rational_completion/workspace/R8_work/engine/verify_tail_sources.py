"""Rebuild all tail boundary sources from the defining kernels, exactly."""
from hyperlog_core import *
import tail_boundary as t
from pathlib import Path
import json,time,hashlib
st=time.time();records=[]
for kind,n in [('Z',6),('A',7)]:
 t.configure(kind,'d')
 for face in range(1,n//2+1):
  factors,ins,N,ids=t.setup(n,face);blocks=t.tb.pp_factored(factors)
  # Exact algebraic check of the complete first partial-fraction decomposition.
  raw=K.one
  for fac,power in factors:raw*=fac**power
  decomposed=K.zero
  for typ,a,p,c in blocks:decomposed+=c*(GEN[1]**p if typ=='poly' else (GEN[1]-a)**(-p))
  assert not raw-decomposed,(kind,n,face)
  manifest=json.loads((t.OUT/f'n{n}_face{face}_manifest.json').read_text())
  assert len(blocks)==len(manifest['blocks'])
  total=0
  for b,meta in zip(blocks,manifest['blocks']):
   src=t.OUT/meta['id']/'stage1.jsonl';fresh=t.tb.first_block(b,ins,N);saved=dict(t.tb.br.rr.load(src))
   assert fresh==saved,(kind,n,face,meta['id']);total+=len(saved)
   assert hashlib.sha256(src.read_bytes()).hexdigest()==meta['source_sha256']
  records.append({'kind':kind,'n':n,'face':face,'blocks':len(blocks),'source_terms':total,'kernel_partial_fractions_exact':True,'every_source_coefficient_exact':True})
  print('SOURCE_FACE_PASS',kind,n,face,total,time.time()-st,flush=True)
r={'status':'all_defining_source_coefficients_rebuilt_exactly','faces':records,'seconds':time.time()-st}
(t.ROOT/'source_regeneration_check.json').write_text(json.dumps(r,indent=2));print('SOURCE_REGEN_PASS',flush=True)
