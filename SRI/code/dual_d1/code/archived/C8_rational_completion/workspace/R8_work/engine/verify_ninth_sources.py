"""Rebuild each defining ninth-group boundary source in a separate process.
The exact finite-size kernels and integrations are unchanged. Process isolation
bounds the otherwise cumulative symbolic-cache memory footprint.
"""
from pathlib import Path
import json,subprocess,sys,time,os
ROOT=Path(__file__).resolve().parent.parent

def one(kind,n,face):
 import tail_boundary as t
 import hashlib
 st=time.time();t.configure(kind,'base')
 factors,ins,N,ids=t.setup(n,face);blocks=t.tb.pp_factored(factors)
 manifest=json.loads((t.OUT/f'n{n}_face{face}_manifest.json').read_text())
 assert len(blocks)==len(manifest['blocks'])
 total=0
 for block,meta in zip(blocks,manifest['blocks']):
  src=t.OUT/meta['id']/'stage1.jsonl';fresh=t.tb.first_block(block,ins,N);saved=dict(t.tb.br.rr.load(src))
  assert fresh==saved,(kind,n,face,meta['id']);total+=len(saved)
  assert hashlib.sha256(src.read_bytes()).hexdigest()==meta['source_sha256']
  del fresh,saved;t.tb.br.rr.clear()
  print('SOURCE_BLOCK_PASS',kind,n,face,meta['id'],flush=True)
 r={'kind':kind,'n':n,'face':face,'blocks':len(blocks),'source_terms':total,
  'every_source_coefficient_exact':True,
  'scope':'direct regeneration of every first-stage source from the factored kernel; full expanded multivariate kernel denominator not recombined in this checker',
  'seconds':time.time()-st}
 dest=ROOT/'source_replay_faces';dest.mkdir(exist_ok=True)
 (dest/f'{kind}{n}_f{face}.json').write_text(json.dumps(r,indent=2))

def main():
 if len(sys.argv)>1:
  assert len(sys.argv)==5 and sys.argv[1]=='--one'
  one(sys.argv[2],int(sys.argv[3]),int(sys.argv[4]));return
 start=time.time();records=[];out=ROOT/'source_replay_faces';out.mkdir(exist_ok=True)
 for kind,n in [('Z',8),('A',9)]:
  for face in range(1,n//2+1):
   with (out/f'{kind}{n}_f{face}.log').open('w') as log:
    subprocess.run([sys.executable,__file__,'--one',kind,str(n),str(face)],stdout=log,stderr=subprocess.STDOUT,check=True,env=dict(os.environ,OPENBLAS_NUM_THREADS='1'))
   d=json.loads((out/f'{kind}{n}_f{face}.json').read_text());assert d['every_source_coefficient_exact'];records.append(d)
   print('SOURCE_FACE_PASS',kind,n,face,d['blocks'],time.time()-start,flush=True)
 r={'status':'all_defining_source_coefficients_rebuilt_exactly','faces':records,'seconds':time.time()-start,
    'source_blocks':sum(d['blocks'] for d in records),'scope':'source regeneration rather than reintegration of every later ordered stage'}
 assert r['source_blocks']==81
 (ROOT/'ninth_source_regeneration_check.json').write_text(json.dumps(r,indent=2));print('NINTH_SOURCE_REPLAY_PASS',flush=True)
if __name__=='__main__':main()
