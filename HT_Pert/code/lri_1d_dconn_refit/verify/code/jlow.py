from jan import *
T=ld('o7')
PRE=('A','B','C','Dj','D','E','F')
print('== fixed pre-registered bases, o7 hi=118, lo 40..70, all shifts & gaps: C6 / C7 misses')
for ds in ('raw','dconn','dconn_w','dconn_s46','dconn_old'):
    m=(T['ds']==ds)&(T['hi']==118)&(T['lo']>=40)&(T['lo']<=70)&(T['mode']=='fixed')&np.isin(T['base'],PRE)
    print(' %-10s C6 %s | C7 %s'%(ds,s(T['miss6'][m]),s(T['miss7'][m])))
print('== E and Dj at lo=60, hi=118, sh 0, ext, fixed')
for ds in ('dconn','dconn_w','dconn_s46','dconn_old'):
    out=[]
    for b in ('E','Dj'):
        m=(T['ds']==ds)&(T['hi']==118)&(T['lo']==60)&(T['mode']=='fixed')&(T['base']==b)&(T['sh']==0)&(T['gap']=='ext')
        i=np.where(m)[0][0]; out.append('%s C6 %+.3f C7 %+.1f'%(b,T['miss6'][i],T['miss7'][i]))
    print(' %-10s'%ds,' | '.join(out))
print('== paired same-config change, new - old (o7 hi=118, lo 40..70), by mode: dC6, dC7')
def key(m): return {(T['lo'][i],T['base'][i],T['mode'][i],T['sh'][i],T['gap'][i]):i for i in np.where(m)[0]}
for new in ('dconn','dconn_w','dconn_s46'):
    for hi in (118,92):
        kn=key((T['ds']==new)&(T['hi']==hi)&(T['lo']>=40)&(T['lo']<=70)); ko=key((T['ds']=='dconn_old')&(T['hi']==hi)&(T['lo']>=40)&(T['lo']<=70))
        for mode in ('fixed','FL','FL5','free'):
            cc=[c for c in kn if c in ko and c[2]==mode]
            d6=np.array([T['C6'][kn[c]]-T['C6'][ko[c]] for c in cc]); d7=np.array([T['C7'][kn[c]]-T['C7'][ko[c]] for c in cc])
            print(' %-9s hi=%d %-5s n=%d  dC6 med %+.3f [%+.3f,%+.3f]  dC7 med %+.1f [%+.1f,%+.1f]'%(new,hi,mode,len(cc),np.median(d6),np.percentile(d6,16),np.percentile(d6,84),np.median(d7),np.percentile(d7,16),np.percentile(d7,84)))
