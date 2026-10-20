import json, sys, numpy as np
d=json.load(open(sys.argv[1]))
EX=-731.13947662454; EX4=45.42488010356
pre=['A','B','C','D','E','F']
for lo in (40,50,60,70):
    rows=[r for r in d['rows'] if r['lo']==lo]
    def rng(names, key, k='5'):
        v=[r[key][k] for r in rows if r['variant'] in names]
        return min(v), max(v)
    allv=[r['variant'] for r in rows]
    post=[v for v in allv if v not in pre]
    for key in ('raw','pkg','pkg+sh4+g3W','Dconn','Dconn(no log subtraction)'):
        a=rng(pre,key); b=rng(post,key)
        E=[r[key]['5'] for r in rows if r['variant']=='E'][0]; A=[r[key]['5'] for r in rows if r['variant']=='A'][0]
        print(f"lo={lo} {key:26s} E={E:.4f} (miss {E-EX:+.4f}) A={A:.4f} | pre-reg A-F [{a[0]:.4f},{a[1]:.4f}] miss [{a[0]-EX:+.3f},{a[1]-EX:+.3f}] | post-hoc [{b[0]:.4f},{b[1]:.4f}] miss [{b[0]-EX:+.3f},{b[1]-EX:+.3f}]")
    a=rng(pre,'Dconn','4'); print(f'   C4 Dconn pre-reg [{a[0]:.5f},{a[1]:.5f}] miss [{a[0]-EX4:+.4f},{a[1]-EX4:+.4f}]')
    for v in ('A+free_exponents','B+free_exponents','D+free_exponents','E+L^-0.5,zL^-0.5','D+L^-0.75','A+z^j/L'):
        r=[x for x in rows if x['variant']==v][0]
        print(f"     {v:20s} Dconn C5={r['Dconn']['5']:.4f} (miss {r['Dconn']['5']-EX:+.4f}) raw {r['raw']['5']:.4f} pkg+g3W {r['pkg+sh4+g3W']['5']:.4f} res5 {r['Dconn']['res5']:.1e}")
c=d['corrections']
for L in ('60','96','116','118'):
    x=c[L]; print(L, {k: x[k] for k in ('dC4_complete','dC5_complete','dC5g','dC5g3','rows5','B5','B5spread')})
