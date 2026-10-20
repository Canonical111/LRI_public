"""Dump all dens_v1 results (density basis, consistent window) as JSON rows to stdout."""
import json,glob,os
R="<SCRATCH>/lri_dressed/campaigns"
out=[]
for c in ("dens16_lo","dens16_mid","dens16_hi8","dens16_hi16","dens24_ctl"):
    for f in sorted(glob.glob(f"{R}/{c}/results/N*.json")):
        d=json.load(open(f));p=d.get("payload",d)
        out.append(dict(campaign=c,path=f,sha256=d.get("sha256"),N=p["bath_cut"],nz=p["nz_per_parity"],delta=p["delta"],
            Delta_thermal=p["Delta_thermal"],even_gaps=p.get("even_gaps"),odd_gaps=p.get("odd_gaps"),theta=p.get("theta"),
            tuning_residual=p.get("tuning_residual"),seconds=p.get("seconds"),threads=p.get("execution",{}).get("threads"),
            peak_rss_mib=p.get("execution",{}).get("peak_rss_mib"),host_campaign=c))
print(json.dumps(out))
