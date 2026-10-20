from jan import *
T=ld('o8')
def base(ds,hi,low=None):
    m=(T['ds']==ds)&(T['hi']==hi)&(T['stat8']<=1000)&(T['lo']>=24)&(T['erms8']<=1.125e-7)&(T['dof8']>=4)
    if low: m&=(T['low']==low)
    return m
def sel67(m): return m&(np.abs(T['C6']/REF[6]-1)<=1e-4)&(np.abs(T['C7']+322550)<=82)
def reg(m,cols):
    y=T['C8'][m]; X=np.column_stack([np.ones(m.sum())]+[c[m] for c in cols]); b,*_=np.linalg.lstsq(X,y,rcond=None); return b[0]
d6=T['C6']/REF[6]-1; d7=T['C7']/REF[7]-1
for hi in (72,92):
  for low in ('same','th118'):
    for ds in ('raw','dconn','dconn_w','dconn_s46','dconn_old'):
        m=base(ds,hi,low); s=sel67(m); s7=m&(np.abs(T['C7']+322550)<=82)
        print(' hi=%d low=%-5s %-9s n=%4d unc %.0f | sel67 n=%3d %.0f | sel7 %.0f | reg d7 %.0f d6d7 %.0f'%(hi,low,ds,m.sum(),np.median(T['C8'][m]),s.sum(),np.median(T['C8'][s]) if s.sum() else np.nan,np.median(T['C8'][s7]),reg(m,[d7]),reg(m,[d6,d7])))
