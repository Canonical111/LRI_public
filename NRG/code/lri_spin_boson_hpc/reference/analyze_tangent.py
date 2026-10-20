"""Target-free window audit of analytic flow responses.
Retain all windows and flags; no known CFT dimension enters their selection.
"""
from pathlib import Path
import json,numpy as np

def analyze(path,out=None):
    path=Path(path);d=json.loads(path.read_text());R=d['records'];n=len(R);lnL=np.log(d['config']['Lambda'])
    gap=np.array([r['odd_gap'] for r in R]);der=np.array([r['d_alpha_odd_gap'] for r in R]);lg=np.log(np.maximum(abs(der),1e-290))
    width=max(12,int(.13*n));windows=[]
    for start in range(max(8,int(.13*n)),int(.76*n)-width):
      ii=np.arange(start,start+width)
      if np.any(gap[ii]<=0) or np.any(~np.isfinite(lg[ii])):continue
      c=np.polyfit(ii,lg[ii],1);res=float(np.max(abs(lg[ii]-np.polyval(c,ii))))
      variation=float(np.ptp(gap[ii])/max(abs(np.mean(gap[ii])),1e-30))
      cg=np.polyfit(ii,np.log(gap[ii]),1)
      windows.append({'start':start,'stop':start+width,'Delta_E':float(1-c[0]/lnL),'y_t':float(c[0]/lnL),'log_response_residual':res,'gap_relative_variation':variation,
       'score':res+variation,'plateau_score':abs(cg[0])+variation/width})
    if not windows:raise RuntimeError('no windows')
    selected=min(windows,key=lambda r:r['score'])
    passed=[w for w in windows if w['gap_relative_variation']<.005 and w['log_response_residual']<.003]
    summary={'config':d['config'],'alpha':d['alpha'],'x':(1-d['config']['s'])/2,'selected':selected,
      'number_of_quality_windows':len(passed),'quality_window_range':([min(w['Delta_E'] for w in passed),max(w['Delta_E'] for w in passed)] if passed else None),
      'windows':windows,'scope':'finite-resolution scaling-window diagnostic, not a physical error interval'}
    if out:Path(out).write_text(json.dumps(summary,indent=2)+'\n')
    return summary
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('path');p.add_argument('--output');a=p.parse_args();r=analyze(a.path,a.output);print(json.dumps({k:v for k,v in r.items() if k!='windows'},indent=2))
