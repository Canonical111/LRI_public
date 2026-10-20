"""Audit new whole-model coefficients, frozen forecasts, and all polynomial probes.
This does not interpret fitted parameters as analytic tail amplitudes.
"""
from pathlib import Path
import csv,json,hashlib,math,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def save(name,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (ROOT/'results'/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def main():
    old=json.loads((ROOT/'inputs/scheme_data.json').read_text());rows=[];data={};rawerrors=[];lowererrors=[];replayerrors=[]
    for p in sorted((ROOT/'results/new_coefficients').glob('*_L*_d8.json'),key=lambda p:int(p.stem.split('_L')[1].split('_')[0])):
        a=json.loads(p.read_text());L=a['cutoff'];scheme=a['scheme']
        if scheme=='dconn':data[L]=a
        row=dict(Lambda=L,scheme=scheme,**{f'C{k}':v for k,v in enumerate(a['C'])},seconds=a['seconds'],basis_dimension=a['basis_dimension'],stored_wavefunction_entries=a['stored_wavefunction_entries'],maxrss_MiB=a['maxrss_kib']/1024,source=str(p.relative_to(ROOT)))
        for k in [4,5,6,7,8]:
            if str(L) in old['raw'] and str(k) in old['raw'][str(L)]:row[f'dconn_minus_raw_C{k}']=a['C'][k]-float(old['raw'][str(L)][str(k)]) if scheme=='dconn' else ''
        rows.append(row)
        if str(L) in old[scheme]:
            for k,v in old[scheme][str(L)].items():
                if int(k)>8:continue
                err=abs(a['C'][int(k)]-float(v));scaled=err/max(1,abs(float(v)))
                if scheme=='raw':rawerrors.append(scaled)
                elif int(k)<=5:lowererrors.append(err)
                else:replayerrors.append(scaled)
    save('whole_model_coefficients.csv',rows)
    steps=[]
    for L in sorted(data):
        if L-2 in data:
            steps.append(dict(Lambda=L,**{f'dC{k}':data[L]['C'][k]-data[L-2]['C'][k] for k in [4,5,6,7,8]}))
    save('full_shell_increments.csv',steps)
    controls=[]
    for p in (ROOT/'results/new_coefficients').glob('dconn_L*_d7.json'):
        a=json.loads(p.read_text());L=a['cutoff'];b=data[L]
        diff=max(abs(np.array(a['C'])-np.array(b['C'][:8]))/np.maximum(1,abs(np.array(b['C'][:8]))))
        controls.append(dict(Lambda=L,degree7_vs_degree8_scaled_error=float(diff)))
    save('support_order_checks.csv',controls)
    if rawerrors:assert max(rawerrors)<1e-10
    assert max(lowererrors)<2e-9,(max(lowererrors))
    assert max(replayerrors,default=0)<1e-10
    assert all(c['degree7_vs_degree8_scaled_error']<1e-10 for c in controls)
    p=ROOT/'results/frozen_forecasts.json';assert hashlib.sha256(p.read_bytes()).hexdigest()==(ROOT/'results/forecast_sha256.txt').read_text().split()[0]
    forecast=[]
    with (ROOT/'results/forecast_validation.csv').open() as f:
        for r in csv.DictReader(f):forecast.append(r)
    endpoints=[r for r in forecast if int(r['cutoff'])==max(data)];save('forecast_at_largest_cutoff.csv',endpoints)
    # A sign test for the CONDITIONAL highest homogeneous logarithm only.
    # It is not a theorem that that monomial controls the whole model at these cutoffs.
    sign=[]
    for n in [6,7,8]:
        d=n-2;turn=math.exp(2*d);L=max(data);ell=math.log(L)
        pref=-40/(81*math.sqrt(math.pi))*(-3.5)**d/math.factorial(d)
        derivative=pref*L**(-1.5)*ell**(d-1)*(d-.5*ell)
        actual=data[L]['C'][n]-data[L-2]['C'][n]
        sign.append(dict(order=n,degree=d,conditional_turning_cutoff=turn,conditional_highest_log_slope_at_last=derivative,actual_last_increment=actual,signs_agree=bool(derivative*actual>0),scope='Conditional highest-log-only model; lower log coefficients and subleading powers were not asserted absent.'))
    save('highest_log_only_sign_test.csv',sign)
    out=dict(complete_degree8_cutoffs=sorted(data),new_C8_cutoffs=[L for L in sorted(data) if L>24],new_C6_C7_cutoffs=[L for L in sorted(data) if L>28],max_raw_scaled_difference=max(rawerrors,default=0),max_corrected_C2_to_C5_absolute_difference=max(lowererrors,default=0),max_existing_corrected_high_order_scaled_difference=max(replayerrors,default=0),support_order_checks=controls,all_forecasts_frozen_before_new_high_coefficients=True,forecast_records=len(forecast),number_of_derived_complete_C6_C7_C8_asymptotic_polynomials=0,scope='All finite-coefficient contributions are included. This report does not claim the uncomputed asymptotic limit or its leading amplitudes.')
    (ROOT/'results/SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));return out
if __name__=='__main__':main()
