"""Fresh randomized sampling of the exact two-loop finite RG Taylor vector.
Independent of production; constant conservative Hepp exponents differ from
production exponents. Reference coefficients are the retained hypergeometric
master evaluation, not fitted targets.
"""
from pathlib import Path
import json,subprocess,time
import numpy as np
from run_precision import W,make_net
from analysis import base_module
if __name__=='__main__':
 out=[]
 for d in (2,3):
  for enc in ('original','single'):
   stem=f'two_loop_control_d{d}_{enc}';kernel=W/'baseline/lri_C6_d3_complete_update/inputs/forest_L2.txt'
   rf=W/f'inputs/{stem}_rates.txt';rf.write_text('1\n1 16\n'+' '.join(['0']+['0.4']*14+['1'])+'\n')
   cf=W/f'inputs/{stem}_counts.txt';cf.write_text('1\n1 65536\n')
   nf=W/f'inputs/{stem}_net.bin';seed=1724631+d*7079+(213 if enc=='single'else 0)
   nc=make_net(nf,32,4 if enc=='single'else 7,60 if enc=='single'else 52,seed)
   path=W/f'records/{stem}.json'
   if path.exists():raise RuntimeError('Refusing overwrite '+str(path))
   cmd=[str(W/f'code/stratified_d{d}{"_single"if enc=="single"else""}'),str(kernel),str(rf),str(cf),str(seed+1011),str(nf),str(path),str(W/f'inputs/gamma_d{d}.txt'),'rqmc']
   t=time.time()
   with (W/f'logs/{stem}.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
   a=np.array(json.load(open(path))['batches']);mu=a.mean(0);se=a.std(0,ddof=1)/np.sqrt(len(a));b=base_module(d).B2;ref=np.r_[b,b/6]
   row={'dimension':d,'ordering_encoding':enc,'samples':len(a)*65536,'seconds':time.time()-t,'estimate':mu.tolist(),'standard_error':se.tolist(),'exact_master_reference':ref.tolist(),'pulls':((mu-ref)/se).tolist(),'net_check':nc,'production_input':False,'reference_used_as_fit':False};out.append(row);print(d,enc,((mu-ref)/se),flush=True)
 (W/'verification/two_loop_sampling_checks.json').write_text(json.dumps(out,indent=2))
