from jan import *
T=ld('o8')
for ds in ('dconn','dconn_w','dconn_s46','dconn_old'):
    for stat in (True,False):
        m=(T['ds']==ds)&(T['hi']==92)&(T['lo']>=24)&(T['erms8']<=1.125e-7)&(T['dof8']>=4)
        if stat: m&=(T['stat8']<=1000)
        s=m&(np.abs(T['C6']/REF[6]-1)<=1e-4)&(np.abs(T['C7']+322550)<=82)
        print(ds,'stat cut' if stat else 'no stat ','base n',m.sum(),'sel67 n',s.sum(),'med %.0f'%np.median(T['C8'][s]),' unc med %.0f'%np.median(T['C8'][m]))
