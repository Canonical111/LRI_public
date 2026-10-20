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
forecast=[]
for mode in ("direct","curvature"):
    n=8; cs=series(mode,n); s,power=epdata(mode,n+1)
    for method,b in [("CB",3.5),("PB",3.5),("PB",0)]:
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
