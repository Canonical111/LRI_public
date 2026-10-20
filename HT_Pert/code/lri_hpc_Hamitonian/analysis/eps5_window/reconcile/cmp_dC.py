import json, numpy as np
S='<TMP>/scratchpad/eps5'
A=json.load(open(S+'/A/dC_table.json')); B=json.load(open(S+'/B/dC5_table.json'))
At={int(k):v for k,v in A['table'].items()}; Bt={r['L']:r for r in B}
print('A Ls', min(At), max(At), len(At), ' B Ls', min(Bt), max(Bt), len(Bt))
print('Lv (A measured windows up to)', A['Lv'])
common=sorted(set(At)&set(Bt))
print(' L    dC5 A              dC5 B             diff      | g2D diff  | g3W: A(g2D3W-g2D) vs B | dC4 Dconn diff | meas')
mx={}
for L in common:
    a=At[L]; b=Bt[L]
    d5=a['Dconn']['dC5']-b['dC5_Dconn']
    dg=a['g2D']['dC5']-b['dC5_g2D']
    dw=(a['g2D3W']['dC5']-a['g2D']['dC5'])-b['dC5_g3W']
    d4=a['Dconn']['dC4']-b['dC4_Dconn']
    d4g=a['g2D']['dC4']-b['dC4_g2D']
    # rows: A's Dconn - g2D3W vs B rows4+rows5
    dr=(a['Dconn']['dC5']-a['g2D3W']['dC5'])-(b['dC5_rows4']+b['dC5_rows5'])
    meas=a['Dconn']['window_measured']
    for k,v in [('d5',d5),('dg',dg),('dw',dw),('d4',d4),('d4g',d4g),('dr',dr)]:
        key=(k,meas); mx[key]=max(mx.get(key,0),abs(v))
    print(f"{L:4d} {a['Dconn']['dC5']:.13f} {b['dC5_Dconn']:.13f} {d5:+.2e} | {dg:+.2e} | {dw:+.2e} | {d4:+.2e} {d4g:+.2e} | {int(meas)}")
print(mx)
