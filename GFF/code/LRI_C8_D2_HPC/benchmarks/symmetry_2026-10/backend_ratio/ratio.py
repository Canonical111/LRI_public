import json,sys
E,W=sys.argv[1],sys.argv[2]
g=json.load(open(E+"/calibration_gmp_<NODE>.json"));d=json.load(open(E+"/calibration_decimal.json"))
print("gmp backend",g["backend"],"decimal backend",d["backend"])
prod=json.load(open(W+"/final2/tools/calibration.json"))["backends"]["gmp"]
out={}
for s in ("free","power"):
  for L in ("3","4","5","6","7"):
    gr=g["rows"][s][L];dr=d["rows"][s][L];pr=prod[s][L]
    a=gr["seconds_per_proxy_unit"];b=dr["seconds_per_proxy_unit"];p=pr["seconds_per_proxy_unit"]
    out[s+L]=dict(gmp_<NODE>=a,decimal_<NODE>=b,gmp_production=p,decimal_over_gmp_same_hw=b/a,gmp_<NODE>_over_production=a/p,tasks=gr["tasks"],task_seconds=round(gr["task_seconds"],1))
    print("%-5s L%s gmp(7543) %.4e dec(7543) %.4e dec/gmp %5.3f gmp7543/prod %5.3f tasks %d task_s %.0f"%(s,L,a,b,b/a,a/p,gr["tasks"],gr["task_seconds"]))
json.dump(dict(job=567730,host="<NODE>",cpu="AMD EPYC 7543",plan_seed=6948572463051812907,note="same plan, seed and jobs as decimal drill 5 (567667, <NODE>, EPYC 7543)",rows=out),open(E+"/backend_ratio_same_hw.json","w"),indent=1)
