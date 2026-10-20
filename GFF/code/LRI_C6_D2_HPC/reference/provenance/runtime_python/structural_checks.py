from pathlib import Path
import json,sys
import numpy as np
W=Path(__file__).resolve().parents[1]
B=Path('/mnt/data/c6_method_work/lri_C6_precision_update')
rows=[]
# Exact measure change on each piece: sums of endpoint increments telescope.
for path in sorted((W/'inputs').glob('grid_d*_top*.txt')):
    tokens=path.read_text().split();ng,nd,nb=map(int,tokens[:3]);i=3;maxerr=0;naxis=0;endpoint=0
    x,w=np.polynomial.legendre.leggauss(4);x=(x+1)/2;w=w/2
    for _ in range(ng):
        idx=int(tokens[i]);i+=1
        for j in range(nd):
            v=np.array(list(map(float,tokens[i:i+nb+1])));i+=nb+1
            endpoint=max(endpoint,abs(v[0]),abs(v[-1]-1))
            assert abs(v[0])<1e-14 and abs(v[-1]-1)<1e-14 and np.all(np.diff(v)>0)
            for k in range(6):
                val=sum(width*sum(w*(a+width*x)**k)for a,width in zip(v[:-1],np.diff(v)))
                maxerr=max(maxerr,abs(val-1/(k+1)))
            naxis+=1
    assert i==len(tokens)
    rows.append({'file':path.name,'axes':naxis,'positive_widths':True,'max_endpoint_roundoff':float(endpoint),'polynomial_moment_orders':list(range(6)),'max_measure_change_error':maxerr})
# A diagnostic for the potential of linear known-C3,C4,C5 controls: not applied.
controls={}
old=json.load(open(B/'verification/precision_results.json'))
for d,j in old.items():
    cov=np.array(j['coefficient_covariance'])[3:7,3:7]
    reduced=cov[3,3]-cov[3,:3]@np.linalg.solve(cov[:3,:3],cov[:3,3])
    controls[d]={'predicted_se_ratio_for_covariance_optimal_linear_control':float((reduced/cov[3,3])**.5),'status':'Covariance diagnostic only; controls not fitted or applied to the reported estimate; estimated covariance gives no universal bound.'}
(W/'verification/structural_checks.json').write_text(json.dumps({'maps':rows,'linear_control_diagnostic':controls},indent=2))
print(rows);print(controls)
