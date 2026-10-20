import pickle, sys, numpy as np, json
REF={6:14331.68703277,7:-322550.}
Z=pickle.load(open(sys.argv[1],'rb'))
CFG=Z['cfg']
mode=np.array([c[3] for c in CFG]); lo=np.array([c[1] for c in CFG])
tabs={}
for (t,wt,ci,lims,erms8,rms8,stat8,dof8,ermsl,dofl) in Z['res']:
    tabs.setdefault((t,wt),{})[ci]=(lims,erms8,stat8,dof8)
def est(t,wt):
    d=tabs[(t,wt)]; idx=np.array(sorted(d))
    C=np.array([d[i][0] for i in idx]); e8=np.array([d[i][1] for i in idx]); st=np.array([d[i][2] for i in idx]); dof=np.array([d[i][3] for i in idx])
    md=mode[idx]
    base=(st<=1000)&(e8<=1.125e-7)&(dof>=4)
    c6,c7,c8=C[:,2],C[:,3],C[:,4]
    s67=base&(np.abs(c6/REF[6]-1)<=1e-4)&(np.abs(c7-REF[7])<=82)
    s7=base&(np.abs(c7-REF[7])<=82)
    near=(st<=1000)&(dof>=4)&(e8*np.sqrt((dof+0.)/1)>=0)  # placeholder
    def reg(m,cols):
        X=np.column_stack([np.ones(m.sum())]+[c[m] for c in cols]); b,*_=np.linalg.lstsq(X,c8[m],rcond=None); return b[0]
    d6=c6/REF[6]-1; d7=c7/REF[7]-1
    fx=base&(md=='fixed')
    out=dict(n=int(base.sum()),unc=np.median(c8[base]),fixed=np.median(c8[fx]),free=np.median(c8[base&(md=='free')]),FL=np.median(c8[base&np.isin(md,('FL','FL5'))]),
             n67=int(s67.sum()),sel67=np.median(c8[s67]) if s67.any() else np.nan,sel7=np.median(c8[s7]),reg7=reg(base,[d7]),reg67=reg(base,[d6,d7]),
             sel67fx=np.median(c8[s67&(md=='fixed')]) if (s67&(md=='fixed')).any() else np.nan)
    out['med4']=np.median([out['sel67'],out['sel7'],out['reg7'],out['reg67']])
    return out
names=sorted({t for t,_ in tabs})
R={}
for t in names:
    for wt in ('u','w'):
        if (t,wt) in tabs: R[(t,wt)]=est(t,wt)
keys=('n','unc','fixed','free','FL','n67','sel67','sel67fx','sel7','reg7','reg67','med4')
for wt in ('u','w'):
    print('== weighting',wt)
    for t in names:
        r=R[(t,wt)]; print('  %-9s '%t+' '.join('%s %.0f'%(k,r[k]) for k in keys))
    # noise realizations relative to s46
    nz=[t for t in names if t.startswith('noise')]
    if nz:
        b=R[('s46',wt)]
        for k in ('unc','fixed','free','FL','sel67','sel7','reg7','reg67','med4'):
            d=np.array([R[(t,wt)][k]-b[k] for t in nz])
            act=R[('fmean',wt)][k]-b[k]
            print('   noise MC %-6s shift vs s46: mean %+6.0f std %5.0f [min %+6.0f max %+6.0f] | actual(fmean)-s46 %+6.0f'%(k,d.mean(),d.std(),d.min(),d.max(),act))
    for t in ('mine','my6_p16','my6_p84','my7_p16','my7_p84','my8_p16','my8_p84'):
        if (t,wt) in R:
            print('   %-8s - fmean: '%t+' '.join('%s %+.0f'%(k,R[(t,wt)][k]-R[('fmean',wt)][k]) for k in ('unc','fixed','sel67','sel7','reg7','reg67','med4')))
pickle.dump(R,open(sys.argv[1].replace('.pkl','_summary.pkl'),'wb'))
