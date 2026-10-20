import json, numpy as np
from mytabs import get
from myload import SCR
A='<PROJECT>/lri_1d_coefficient_flow_review/step1_dconn_refit/delta/out/'
def medoid_table(corr, var, L, raw, pick=None):
    d=json.load(open(corr)); V=json.load(open(var))
    Ls=[int(x) for x in L]
    T=raw.copy(); info={}
    seq=d['sequences']
    for k in range(9):
        for r in seq['C%d'%k]:
            i=Ls.index(r['L']); T[i,k]=r['raw']+r['dC']
    for k in (6,7,8):
        rows={r['L']:r for r in seq['C%d'%k]}
        b=V['dC%d'%k]; P=np.array(b['pred'])
        Lm=[l for l in b['L'] if l in rows and not rows[l]['exact']]
        idx=[b['L'].index(l) for l in Lm]
        cen=np.array([rows[l]['dC'] for l in Lm]); unc=np.array([rows[l]['dC_unc'] for l in Lm])
        dist=np.sqrt(np.mean(((P[:,idx]-cen)/unc)**2,axis=1))
        i0=int(np.argmin(dist)) if pick is None else pick[k]
        info[k]=i0
        for a,l in enumerate(Lm):
            T[Ls.index(l),k]=rows[l]['raw']+P[i0,idx[a]]
    return T,info
if __name__=='__main__':
    L,raw,T=get()
    To,info=medoid_table(A+'delta_v1_corrected.json',A+'delta_v1_variants.json',L,raw)
    print('old medoid members',info)
    Tn,infon=medoid_table(SCR+'/delta/out/delta_v1_hi72_corrected.json',SCR+'/delta/out/delta_v1_hi72_variants.json',L,raw)
    print('new MI-rule medoid members',infon)
    Tf,_=medoid_table(SCR+'/delta/out/delta_v1_hi72_corrected.json',SCR+'/delta/out/delta_v1_hi72_variants.json',L,raw,pick={6:53,7:74,8:79})
    m=np.isfinite(Tf)
    print('floor-medoid (53,74,79) vs smooth-table fmedoid: max abs diff',np.nanmax(np.abs(Tf-T['fmedoid'])))
    # compare with the delta stage floormedoid corrected file
    d=json.load(open(SCR+'/delta/out/delta_v1_hi72_floormedoid_corrected.json'))
    Ls=[int(x) for x in L]; mx=0
    for k in range(9):
        for r in d['sequences']['C%d'%k]:
            mx=max(mx,abs(r['corrected']-Tf[Ls.index(r['L']),k])); assert abs(r['raw']+r['dC']-r['corrected'])<=1e-9*max(1,abs(r['corrected']))
    print('floormedoid file vs mine max abs',mx)
    np.savez('../out/mitabs.npz',old=To,mimed=Tn,fmed=Tf)
