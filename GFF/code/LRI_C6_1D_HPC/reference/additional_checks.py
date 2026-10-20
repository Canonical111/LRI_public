from pathlib import Path
import json, hashlib
import numpy as np
import mpmath as mp
R=Path(__file__).resolve().parent
mp.mp.dps=70
read=lambda f:json.loads((R/f).read_text(),parse_float=str)
out={}
for nv in [6,7]:
 ne=nv*(nv-1)//2;data=np.memmap(R/f'graphs{nv}.bin',dtype=np.int32,mode='r').reshape(-1,ne+2)
 A=data[:,ne].astype(np.int64);B=data[:,ne+1].astype(np.int64);H=3*B-A
 out[f'graphs{nv}']={'number':len(A),'zero_H':int((H==0).sum()),'positive_H':int((H>0).sum()),'negative_H':int((H<0).sum()),'integer_scale':1728,'sum_scaled_A':int(A.sum()),'sum_scaled_B':int(B.sum()),'sum_scaled_H':int(H.sum())}
d=read('assembly_lower6.json')
out['lower_order_degree_controls']={}
for cut in ['maxgap','span']:
 out['lower_order_degree_controls'][cut]={f'N{a}_minus_N{b}':mp.nstr(mp.mpf(d[f'{cut}_{a}']['C6_lower'])-mp.mpf(d[f'{cut}_{b}']['C6_lower']),40)for a,b in [(22,16),(28,22)]}
J12=read('full_J_L5_N12_0_10000.json')['values'];J16=read('full_J_L5_N16_0_10000.json')['values'];out['J5']={}
for c,cut in enumerate(['maxgap','span']):
 out['J5'][cut]={'N12':str(J12[6*c+5]),'N16':str(J16[6*c+5]),'C6_shift_N16_minus_N12':mp.nstr(mp.mpf(4)/243*(mp.mpf(J16[6*c+5])-mp.mpf(J12[6*c+5])),40)}
out['five_loop_reproduction']={}
for c,cut in enumerate(['maxgap','span']):
 vals=read('full_H_L5_N16_0_10000.json')['values'][c*5:(c+1)*5]
 corr=read(f'lri_numerical_resolution/verification/records/combined5_{cut}_24.json')
 # discover retained field
 out['five_loop_reproduction'][cut]={'new_H5':vals,'retained_N24':corr}
# The light stratum has at most one meromorphic axis, so H's eps^-6 through eps^-3 are zero.
full=np.array(read('full_H_L6_N6_0_10000.json')['values'],dtype=np.longdouble)
hard=np.array(read('full_H_hard_L6_N6_0_10000.json')['values'],dtype=np.longdouble)
out['light_stratum_abs_higher_poles']=list(map(float,(full-hard)[[0,1,2,3,6,7,8,9]]))
# All sampled tails can be audited directly; no tail fit is an input here.
(R/'additional_checks.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
