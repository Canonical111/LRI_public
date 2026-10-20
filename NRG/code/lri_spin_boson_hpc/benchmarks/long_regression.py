"""Full-depth replay at archived alphas. Do not infer continuum accuracy."""
from pathlib import Path
import argparse,json,sys,time
import numpy as np
root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root/'src'),str(root/'reference')]
from lri_spin import Config,run,run_tangent
from lri_spin.io import source_hash
from lri_spin.validation import audit_tangent,validate_result
from nrg import run as ref_flow
from nrg_tangent import run_tangent as ref_tangent
p=argparse.ArgumentParser();p.add_argument('--quick',action='store_true');p.add_argument('--output',default=str(root/'benchmarks'/'LONG_REGRESSION.json'));a=p.parse_args()
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lri_spin.campaign import refuse_campaign_destination
refuse_campaign_destination(a.output)   # never write benchmark output into campaign state
cases=[(.8,48,65,.43977045457263714),(.98,64,105,1.0806597653161139),(.52,64,65,.12784352652132314)]
if a.quick:cases=cases[:1]
results=[]
for s,k,n,alpha in cases:
 c=Config(s=s,Lambda=3.,keep=k,nb=10,nsites=n)
 entry={'config':c.asdict(),'alpha':alpha,'comparisons':{}}
 for kind,f,ref in [('flow',run,ref_flow),('tangent',run_tangent,ref_tangent)]:
  old=ref(alpha,c);new=f(alpha,c);validate_result(new,c,tangent=kind=='tangent')
  spec=obs=tan=abs_tan=0.;exact=True
  for o,v in zip(old['records'],new['records']):
   for key in ['odd_gap','even_levels','odd_levels']:
    x=np.asarray(o[key]);y=np.asarray(v[key]);spec=max(spec,float(np.max(abs(x-y))));exact&=bool(np.array_equal(x,y))
   for key in ['log_spin_scale_correlation','log_thermal_scale_correlation']:
    obs=max(obs,abs(o[key]-v[key]))
   if kind=='tangent':
    dif=abs(o['d_alpha_odd_gap']-v['d_alpha_odd_gap']);abs_tan=max(abs_tan,dif);tan=max(tan,dif/max(1,abs(o['d_alpha_odd_gap'])))
  assert spec<1e-8 and obs<1e-8 and tan<2e-10,(s,kind,spec,obs,tan)
  out={'spectra_max_absolute':spec,'observers_max_absolute':obs,'bitwise_spectra':exact,'tangent_max_scaled':tan,'tangent_max_absolute':abs_tan}
  if kind=='tangent':
   eo=audit_tangent(old);en=audit_tangent(new)
   out.update(reference_selected=eo['selected'],optimized_selected=en['selected'],
              delta_E_difference=en['selected']['Delta_E']-eo['selected']['Delta_E'])
  entry['comparisons'][kind]=out
  print(s,kind,out,flush=True)
 results.append(entry)
 Path(a.output).write_text(json.dumps({'source_sha256':source_hash(),'completed_cases':results},indent=2)+'\n')
