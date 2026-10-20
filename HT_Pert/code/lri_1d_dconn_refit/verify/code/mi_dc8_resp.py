import json, pickle, numpy as np
from flint import arb
from mylsq import solve
from mymi import TAILSETS, WF, REF, eser, analyze
from myjoint import C2X, C3X
from mytabs import get, floor_curves
L,raw,T=get(); Ls=[int(x) for x in L]
M=np.load('../out/mitabs.npz'); Tf=M['fmed']
F=pickle.load(open('../out/mi_fmed_hi92.pkl','rb')); a=analyze(F)
cal=a['C8']['cal']; per={k:(c8,cc) for k,c8,cc in a['C8']['per']}
Lp=list(range(74,93,2))
def p0_row(key):
    tn,lead,lo=key; terms=dict(TAILSETS)[tn]
    Lw=[l for l in Ls if lo<=l<=92]
    cols=[[] for _ in range(3+len(terms))]; S=[]
    lims={2:C2X,3:C3X,4:arb(REF[4]),5:arb(REF[5]),6:arb(REF[6]),7:arb(REF[7])}
    w={j:WF[j] for j in range(1,6)}
    for l in Lw:
        i=Ls.index(l); la=arb(l); z=la.log(); e=eser(z,w,6)
        s=arb(float(Tf[i,8]))+sum((e[j]*(arb(float(Tf[i,8-j]))-lims[8-j]) for j in range(1,7)),arb(0)); S.append(s)
        b=(arb(float(Tf[i,2]))-C2X) if lead=='T2' else la**arb(-0.5)
        cols[0].append(arb(1)); cols[1].append(b); cols[2].append(b*z)
        for t,(p,j) in enumerate(terms): cols[3+t].append(la**arb(-p)*z**j)
    r=solve(cols,S,want_pinv0=True)
    assert abs(float(r['coef'][0].mid())-per[key][0])<1e-6*abs(per[key][0])
    g=np.zeros(len(Lp))
    for q,l in enumerate(Lw):
        if l in Lp: g[Lp.index(l)]=r['p0'][q]
    return g
G=np.array([p0_row(k) for k in cal]); c8=np.array([per[k][0] for k in cal]); fac=np.array([per[k][1]/per[k][0] for k in cal])
ip=[Ls.index(l) for l in Lp]; cen=np.array([Tf[i,8]-raw[i,8] for i in ip])   # floor-medoid central
my=json.load(open('../out/mycont_dC678.json'))['8']['members']
MY=np.array([m['pred'][:len(Lp)] for m in my if m['kept']])-cen
Lv,P,fl=floor_curves(8); FL=np.array([[P[j,Lv.index(l)] for l in Lp] for j in np.where(fl)[0]])-cen
for name,Mm in (('mine',MY),('delta floor',FL)):
    su=np.array([np.median(c8+G@d)-np.median(c8) for d in Mm]); sc=np.array([np.median((c8+G@d)*fac)-np.median(c8*fac) for d in Mm])
    print('MI fixed-selection (n=%d) %-12s uncal shift median %+.0f p16 %+.0f p84 %+.0f [min %+.0f max %+.0f] | cal median %+.0f p16 %+.0f p84 %+.0f [min %+.0f max %+.0f]'%(len(cal),name,np.median(su),np.percentile(su,16),np.percentile(su,84),su.min(),su.max(),np.median(sc),np.percentile(sc,16),np.percentile(sc,84),sc.min(),sc.max()))
