from jan import *
T=ld('o8')
def base(ds,hi,crit='w'):
    rms=T['erms8'] if crit=='w' else T['rms8']
    return (T['ds']==ds)&(T['hi']==hi)&(T['stat8']<=1000)&(T['lo']>=24)&(rms<=1.125e-7)&(T['dof8']>=4)
def sel67(m,c7=-322550.):
    s=m&(np.abs(T['C6']/REF[6]-1)<=1e-4)&(np.abs(T['C7']-c7)<=82)
    return s
print('== C8 calibrated: full grid, prior criterion (whitened rms for dconn/dconn_w), sel on C6+C7')
for hi in (92,80,72,70):
    for ds in ('raw','dconn','dconn_w','dconn_s46','dconn_old'):
        for crit in (('w','p') if ds=='dconn' else ('w',)):
            m=base(ds,hi,crit); s1=sel67(m)
            s7=m&(np.abs(T['C7']+322550)<=82)
            print(' hi=%d %-9s crit=%s base n=%5d  unc med %.0f | sel67 n=%3d med %.0f | sel7 n=%3d med %.0f'%(hi,ds,crit,m.sum(),np.median(T['C8'][m]) if m.sum() else np.nan,s1.sum(),np.median(T['C8'][s1]) if s1.sum() else np.nan,s7.sum(),np.median(T['C8'][s7]) if s7.sum() else np.nan))
print('== uncalibrated family medians, hi=92 prior criterion')
for ds in ('dconn','dconn_w','dconn_s46','dconn_old'):
    m=base(ds,92)
    out=[]
    for name,mm in (('fixed',T['mode']=='fixed'),('free',T['mode']=='free'),('FL',np.isin(T['mode'],('FL','FL5')))):
        out.append('%s %.0f (n=%d)'%(name,np.median(T['C8'][m&mm]),(m&mm).sum()))
    print(' %-9s all %.0f (n=%d) | '%(ds,np.median(T['C8'][m]),m.sum())+' | '.join(out))
print('== paired same-config C8 change new - old (hi=92), all configs and by mode')
def key(m): return {(T['lo'][i],T['base'][i],T['mode'][i],T['sh'][i],T['gap'][i],T['low'][i]):i for i in np.where(m)[0]}
ko=key((T['ds']=='dconn_old')&(T['hi']==92))
for new in ('dconn','dconn_w','dconn_s46'):
    kn=key((T['ds']==new)&(T['hi']==92))
    for mode in ('fixed','free','FL','FL5'):
        for low in ('same','th118'):
            cc=[c for c in kn if c in ko and c[2]==mode and c[5]==low and c[0]>=24]
            d=np.array([T['C8'][kn[c]]-T['C8'][ko[c]] for c in cc])
            print(' %-9s %-5s %-5s n=%4d dC8 med %+.0f [16-84 %+.0f,%+.0f]'%(new,mode,low,len(cc),np.median(d),np.percentile(d,16),np.percentile(d,84)))
