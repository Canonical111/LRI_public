"""Fresh independent graph-stratified MC/RQMC runs. Never overwrite results."""
import json,os,time,subprocess,argparse,struct
from pathlib import Path
import numpy as np
from scipy.stats import qmc
import scipy
W=Path(__file__).resolve().parents[1]
def graph_ids(path):
 it=iter(path.read_text().split());L=int(next(it));ng=int(next(it));rows=[]
 for _ in range(ng):
  idx=int(next(it));wa=float(next(it));wb=float(next(it));M=int(next(it));T=int(next(it));
  for _ in range(4*L+M):next(it)
  for _ in range(T):
   n=int(next(it))
   for _ in range(n+2*L):next(it)
  rows.append((idx,wa,wb,M,T))
 try:next(it);raise AssertionError('extra tokens')
 except StopIteration:pass
 return L,rows

def make_net(path,B,dim,bits,seed):
 rng=np.random.default_rng(seed);matrices=[]
 for i in range(B):
  engine=qmc.Sobol(d=dim,scramble=True,bits=bits,seed=int(rng.integers(1,2**32-1)))
  mat=engine._sv.copy()
  state=engine._shift.copy();raw=[]
  for n in range(16):
   if n:state^=mat[:,(n&-n).bit_length()-1]
   raw.append(state.copy())
  expected=engine.random_base2(4)
  assert np.max(np.abs(np.array(raw,dtype=np.float64)/2**bits-expected))==0
  matrices.append(mat.astype('<u8'))
 with path.open('wb')as f:f.write(struct.pack('<III',B,dim,bits));np.array(matrices).tofile(f)
 return {'scipy':scipy.__version__,'replicates':B,'dimensions':dim,'bits':bits,'matrix_seed':seed,'gray_code_comparisons':B*16*dim,'max_abs_reconstruction_error':0}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('tag');p.add_argument('--d',type=int,required=True);p.add_argument('--loops',default='3,4,5,6');p.add_argument('--replicates',type=int,default=16);p.add_argument('--budget',type=int,default=32768);p.add_argument('--seed',type=int,required=True);p.add_argument('--bits',type=int,default=52);p.add_argument('--mode',choices=['rqmc','mc'],default='rqmc');p.add_argument('--allocation',default=None);p.add_argument('--rate',default='0.8');p.add_argument('--encoding',choices=['original','single'],default='original');a=p.parse_args();manifest_path=W/f'records/{a.tag}_d{a.d}_manifest.json';manifest=json.load(open(manifest_path))if manifest_path.exists()else []
 for L in map(int,a.loops.split(',')):
  source=W/'baseline/lri_C6_d3_complete_update/inputs'/f'forest_L{L}.txt'
  rates=W/f'baseline/lri_C6_d3_complete_update/inputs/rates_L{L}_{a.rate}.txt' if a.d==3 else W/f'baseline/lri_C6_d2_complete_update/reproduction/mom_rates_{"c" if a.rate=="0.8" else "d"}{L}.txt'
  if a.d==2 and L==6: rates=W/f'inputs/d2_full_rates_{"c" if a.rate=="0.8" else "d"}6.txt'
  _,rows=graph_ids(source)
  if a.allocation:
   ai=json.load(open(W/f'inputs/{a.allocation}_d{a.d}_L{L}.json'));probs=np.array([ai['probabilities'][str(r[0])]for r in rows])
  else:probs=np.ones(len(rows))/len(rows)
  counts=np.maximum(4,2**np.rint(np.log2(np.maximum(4,a.budget*probs)))).astype(int)
  cf=W/f'inputs/{a.tag}_d{a.d}_L{L}_counts.txt';cf.write_text(str(len(rows))+'\n'+'\n'.join(f'{r[0]} {n}' for r,n in zip(rows,counts))+'\n')
  out=W/f'records/{a.tag}_d{a.d}_L{L}.json'
  if out.exists():raise RuntimeError('refusing overwrite '+str(out))
  nf=W/f'inputs/{a.tag}_d{a.d}_L{L}_net.bin';net_check=make_net(nf,a.replicates,2*L if a.encoding=='single'else 4*L-1,a.bits,a.seed+18743*L)
  cmd=[str(W/f'code/stratified_d{a.d}{"_single"if a.encoding=="single"else ""}'),str(source),str(rates),str(cf),str(a.seed+1279*L),str(nf),str(out),str(W/f'inputs/gamma_d{a.d}.txt'),a.mode]
  t=time.time()
  with open(W/f'logs/{a.tag}_d{a.d}_L{L}.log','w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
  row={'L':L,'dimension':a.d,'samples':int(sum(counts)*a.replicates),'replicates':a.replicates,'seconds':time.time()-t,'mode':a.mode,'command':cmd,'net_check':net_check,'allocation':a.allocation,'rate':a.rate,'sector_encoding':a.encoding};manifest.append(row)
  (W/f'records/{a.tag}_d{a.d}_manifest.json').write_text(json.dumps(manifest,indent=2));print(row['dimension'],L,row['samples'],row['seconds'],flush=True)
