import os, sys, itertools, numpy as np
os.environ['NREAL']='0'
import jmc
from myjoint2 import fit2
jmc.build(); L=jmc.L; W=jmc.W; T=jmc.TABS
REF={6:14331.68703277,7:-322550.}
wt=sys.argv[1]; modes=sys.argv[2].split(',')
PRE=('A','B','C','Dj','D','E','F')
cfg=list(itertools.product((40,50,60,70),PRE,modes,(-2.,0.,2.),('orig','ext','wf')))
names=['fmean','mine','my6_p16','my6_p84','my7_p16','my7_p84']
R={}
for t in names:
    R[t]=np.array([[fit2(L,T[t],lo,118,b,m,sh,g,wrel=W,weighted=(wt=='w'),maxorder=7)[n]['lim'] for n in (6,7)] for lo,b,m,sh,g in cfg])
f=R['fmean']
print('wt',wt,'modes',modes,'n',len(cfg),': fmean C6 miss med %+.2f, C7 miss med %+.1f'%(np.median(f[:,0]-REF[6]),np.median(f[:,1]-REF[7])))
for t in names[1:]:
    d=R[t]-f
    print('  %-8s - fmean: dC6 med %+.3f [16-84 %+.3f,%+.3f] |max| %.2f ; dC7 med %+.1f [%+.1f,%+.1f] |max| %.0f'%(t,np.median(d[:,0]),np.percentile(d[:,0],16),np.percentile(d[:,0],84),np.abs(d[:,0]).max(),np.median(d[:,1]),np.percentile(d[:,1],16),np.percentile(d[:,1],84),np.abs(d[:,1]).max()))
