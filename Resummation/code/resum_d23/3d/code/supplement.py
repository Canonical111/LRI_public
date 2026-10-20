#!/usr/bin/env python3
"""Strict b=0 Padé controls and an explicitly unmeasured C9 forecast."""
from calculate import *
curves=list(csv.DictReader((OUT/"curves.csv").open()))
newpoles=[]
for mode in MODES:
    for n in (7,8):
        values,records=pb(mode,n,b=0)
        newpoles.extend(records)
        if values is not None:
            for r,v in zip(curves,values): r[f"{mode}_PB{n}_b0"]=float(v)
# Conditional endpoint and independently quoted dimensional inputs.
baseline=cb("slope",8)
csr0=CSR
import calculate as cal
for tag,val in [("SR_low",SR["recommended_working_summary"]["interval"][0]),
                ("SR_high",SR["recommended_working_summary"]["interval"][1]),
                ("SR_midpoint",SR["recommended_working_summary"]["midpoint"]),
                ("SR_weak_low",SR["weaker_gap_sensitivity_interval"][0]),
                ("SR_weak_high",SR["weaker_gap_sensitivity_interval"][1])]:
    cal.CSR=mp.mpf(str(val))
    yy=cb("slope",8)
    for r,v in zip(curves,yy): r["slope_"+tag]=float(v)
cal.CSR=csr0
esr0=cal.ESR
cal.ESR=esr0+mp.mpf(P["E_SR_allowance"])
de=cb("slope",8)-baseline
cal.ESR=esr0
# Endpoint-location response is evaluated only on the common physical domain.
s0,e0=cal.S,cal.E
ds=[]
for sign in (-1,1):
    cal.S=s0+sign*mp.mpf(P["S_allowance"]);cal.E=3-4*cal.S
    xx=X[1:]
    assert np.min(xx)>float(cal.S)
    ds.append(cb("slope",8,x=xx)-baseline[1:])
cal.S,cal.E=s0,e0
for i,r in enumerate(curves):
    r["slope_E_input_allowance"]=float(abs(de[i]))
    r["slope_S_input_allowance"]=None if i==0 else float(max(abs(ds[0][i-1]),abs(ds[1][i-1])))
    r["slope_SR_lower"]=min(r["slope_SR_low"],r["slope_SR_high"])
    r["slope_SR_upper"]=max(r["slope_SR_low"],r["slope_SR_high"])
    r["slope_SR_allowance"]=max(abs(r["slope_SR_low"]-baseline[i]),abs(r["slope_SR_high"]-baseline[i]))
# Validate value, slope, and all original eight Taylor coefficients.
hh=mp.mpf("1e-6")
near=cb("slope",8,x=[float(s0),float(s0+hh),float(s0+2*hh)])
deriv=(-3*near[0]+4*near[1]-near[2])/(2*float(hh))
assert abs(near[0]-float(esr0))<1e-14
assert abs(deriv-float(csr0))<2e-8
CHECKS.append(dict(check="Endpoint right derivative",observed=float(deriv),target=float(csr0),error=float(abs(deriv-float(csr0)))))

forecast=[]
for mode in ("direct","slope"):
    n=8; cs=series(mode,n); s,power=epdata(mode,n+1)
    for method,b in [("CB",4),("PB",4),("PB",0)]:
        if method=="CB": hs=cb_back(pol(cs,b,0),b,0,A,n+1)
        else:
            choice,records=pade_candidates(mode,n,b)
            if choice is None: continue
            hs=rational_back(*choice,b,n+1)
        pred=hs[-1] if mode=="direct" else s[-1]+conv(hs,qp(power,n+1),n+1)[-1]
        forecast.append(dict(mode=mode,method=method,b=b,predicted_C9=float(pred),
                             status="unmeasured forecast, not an added input or error bound"))
writecsv("curves.csv",curves)
writecsv("key_points.csv",[curves[np.searchsorted(X,x)] for x in KEYX])
writecsv("C9_forecasts.csv",forecast)
(OUT/"pade_b0_poles.json").write_text(json.dumps(newpoles,indent=2))
(OUT/"supplement_validation.json").write_text(json.dumps(CHECKS,indent=2))
print("SUPPLEMENT PASSED",json.dumps(forecast),flush=True)
