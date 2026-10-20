"""Linear response of the joint-lens calibrated C8 (selection on C6+C7, full grid, hi=92) to dC8 continuation members
(exactly linear at fixed selection: dC8 enters only the order-8 fit). Members: verifier's continuation (all kept) and
delta-v1 hi72 floor-level curves; deviations relative to the floor-mean central at L=74..92."""
import os, json, pickle, numpy as np
os.environ['NREAL']='0'
import jmc
from myjoint2 import fit2
from mytabs import floor_curves
jmc.build(); L=jmc.L; W=jmc.W; T=jmc.TABS; Ls=list(L.astype(int))
REF={6:14331.68703277,7:-322550.}
R=pickle.load(open('../out/jmc_all.pkl','rb')); CFG=R['cfg']
Lp=list(range(74,93,2)); ip=[Ls.index(l) for l in Lp]
fm=np.array([T['fmean'][i,8]-jmc.raw[i,8] for i in ip])
my=json.load(open('../out/mycont_dC678.json'))['8']['members']
MY=np.array([m['pred'][:len(Lp)] for m in my if m['kept']])-fm
Lv,P,fl=floor_curves(8); FL=np.array([[P[j,Lv.index(l)] for l in Lp] for j in np.where(fl)[0]])-fm
ALL=np.array([[P[j,Lv.index(l)] for l in Lp] for j in range(len(P))])-fm
print('n members: mine %d, delta floor %d, delta all-kept %d'%(len(MY),len(FL),len(ALL)))
print('dev at 92: mine std %.1e, floor std %.1e, all std %.1e'%(MY[:,-1].std(),FL[:,-1].std(),ALL[:,-1].std()))
for wt in ('w','u'):
    rows=[r for r in R['res'] if r[0]=='fmean' and r[1]==wt]
    sel=[]
    for (t,w_,ci,lims,e8,r8,st8,d8,el,dl) in rows:
        if st8<=1000 and e8<=1.125e-7 and d8>=4 and abs(lims[2]/REF[6]-1)<=1e-4 and abs(lims[3]-REF[7])<=82: sel.append((ci,lims[4]))
    C8=np.array([c for _,c in sel]); G=np.zeros((len(sel),len(Lp)))
    for a,(ci,_) in enumerate(sel):
        low,lo,b,mode,sh,gap=CFG[ci]
        o=fit2(L,T['fmean'],lo,92,b,mode,sh,gap,hi_low=118 if low=='th118' else None,wrel=W,weighted=(wt=='w'))
        assert abs(o[8]['lim']-C8[a])<1e-6*abs(C8[a])
        for q,i in enumerate(o[8]['idx']):
            if Ls[i] in Lp: G[a,Lp.index(Ls[i])]=o[8]['p0'][q]
    base=np.median(C8)
    for name,M in (('mine',MY),('delta floor',FL),('delta all-kept',ALL)):
        sh=np.array([np.median(C8+G@d)-base for d in M])
        per=np.abs(G@M.T)  # per-config per-member
        print('wt=%s n_sel=%d %-14s sel67-median shift: std %4.0f p16 %+5.0f p84 %+5.0f min %+6.0f max %+6.0f | per-fit |dC8| median %.0f'%(wt,len(sel),name,sh.std(),np.percentile(sh,16),np.percentile(sh,84),sh.min(),sh.max(),np.median(per)))
    print('   per-config gain sum|p0| over 74..92: median %.2e max %.2e'%(np.median(np.abs(G).sum(1)),np.abs(G).sum(1).max()))

# detail for the weighted case: shift distribution and member shapes
wt='w'
rows=[r for r in R['res'] if r[0]=='fmean' and r[1]==wt]
sel=[(ci,lims[4]) for (t,w_,ci,lims,e8,r8,st8,d8,el,dl) in rows if st8<=1000 and e8<=1.125e-7 and d8>=4 and abs(lims[2]/REF[6]-1)<=1e-4 and abs(lims[3]-REF[7])<=82]
C8=np.array([c for _,c in sel]); G=np.zeros((len(sel),len(Lp)))
for a,(ci,_) in enumerate(sel):
    low,lo,b,mode,sh_,gap=CFG[ci]
    o=fit2(L,T['fmean'],lo,92,b,mode,sh_,gap,hi_low=118 if low=='th118' else None,wrel=W,weighted=True)
    for q,i in enumerate(o[8]['idx']):
        if Ls[i] in Lp: G[a,Lp.index(Ls[i])]=o[8]['p0'][q]
base=np.median(C8)
sh=np.array([np.median(C8+G@d)-base for d in MY])
print('mine members: median shift %+.0f, frac |shift|>500: %.2f, frac shift<-300 %.2f'%(np.median(sh),np.mean(np.abs(sh)>500),np.mean(sh<-300)))
keptm=[m for m in my if m['kept']]
order=np.argsort(sh)
print('median-config response row G (per unit dC8 at L):', ' '.join('%d:%+.1e'%(l,g) for l,g in zip(Lp,np.median(G,axis=0))))
for q in (0,int(0.05*len(sh)),int(0.16*len(sh)),int(0.5*len(sh)),int(0.84*len(sh)),len(sh)-1):
    i=order[q]; m=keptm[i]
    print('  q=%.2f shift %+6.0f %s lo=%d chi %.2f dev(L=74,76,80,86,92): %s'%(q/len(sh),sh[i],m['name'],m['lo'],m['chi'],' '.join('%+.1e'%MY[i][Lp.index(l)] for l in (74,76,80,86,92))))
fs=np.array([np.median(C8+G@d)-base for d in FL])
print('delta floor members dev at 74,76,80,86,92 (std):',' '.join('%.1e'%FL[:,Lp.index(l)].std() for l in (74,76,80,86,92)),' mine std:',' '.join('%.1e'%MY[:,Lp.index(l)].std() for l in (74,76,80,86,92)))
# robust: mine members restricted to chi<=1.2 (tighter)
for cmax in (1.0,1.2,1.5):
    idx=[i for i,m in enumerate(keptm) if m['chi']<=cmax]
    s2=sh[idx]; print('  mine chi<=%.1f n=%d: shift median %+.0f p16 %+.0f p84 %+.0f'%(cmax,len(idx),np.median(s2),np.percentile(s2,16),np.percentile(s2,84)))
