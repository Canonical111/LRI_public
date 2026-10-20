import json
S='<TMP>/scratchpad/eps5'
M={(r['lo'],r['variant']):r for r in json.load(open(S+'/reconcile/refit_rc.json'))['rows']}
A={(r['lo'],r['variant'].replace('+free_exp','+free_exp')):r for r in json.load(open(S+'/A/refit_c5.json'))['rows']}
B={(r['lo'],r['variant'].replace('+free_exponents','+free_exp')):r for r in json.load(open(S+'/B/refit/refit5_hi118.json'))['rows']}
mxA={};mxB={}
for key,m in M.items():
    if key in A:
        a=A[key]
        for mk,ak in [('Dconn_full','Dconn_full'),('Dconn_MS','Dconn_MS'),('raw','raw'),('g2D_MS','g2D_MS'),('g2D3W_MS','g2D3W_MS')]:
            d=abs(m[mk]['C5']-a[ak][1]); mxA[mk]=max(mxA.get(mk,(0,)),(d,key))
            d4=abs(m[mk]['C4']-a[ak][0]); mxA[mk+'_C4']=max(mxA.get(mk+'_C4',(0,)),(d4,key))
    if key in B:
        b=B[key]
        for mk,bk in [('Dconn_MS','Dconn'),('raw','raw'),('g2D_MS','pkg'),('Dconn_full','Dconn(no log subtraction)')]:
            d=abs(m[mk]['C5']-b[bk]['5']); mxB[mk]=max(mxB.get(mk,(0,)),(d,key))
            d4=abs(m[mk]['C4']-b[bk]['4']); mxB[mk+'_C4']=max(mxB.get(mk+'_C4',(0,)),(d4,key))
print('mine vs A refit (max abs diff, worst key):'); [print('  ',k,v) for k,v in mxA.items()]
print('mine vs B refit:'); [print('  ',k,v) for k,v in mxB.items()]
print('--- per-class max diffs (Dconn_full / Dconn_MS C5), and intercept gain of C5 fit')
for cls in ('pre','post','extra'):
    da=[(abs(M[k]['Dconn_full']['C5']-A[k]['Dconn_full'][1]),k) for k in M if k in A and M[k]['cls']==cls]
    db=[(abs(M[k]['Dconn_MS']['C5']-B[k]['Dconn']['5']),k) for k in M if k in B and M[k]['cls']==cls]
    print(cls,'vs A',max(da) if da else None,' vs B',max(db) if db else None)
for k in sorted(M):
    if k[0]==60: print(k, 'gain5=%.2e cond5=%.1e'%(M[k]['Dconn_full']['gain5'],M[k]['Dconn_full']['cond5']))
