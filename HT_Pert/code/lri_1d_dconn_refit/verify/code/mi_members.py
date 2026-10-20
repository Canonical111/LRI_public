import os, numpy as np
os.environ['NREAL']='0'
import jmc
from mymi import run_family, analyze
jmc.build()
L=jmc.L
# MI uses floor-medoid beyond 72 as primary; my member tables are built on my central ('mine'); compare mine vs members
base=analyze(run_family(L,jmc.TABS['mine'],92))
print('mine  C8 uncal %.0f cal %.0f ncal %d | C6 cal %.2f C7 cal %.0f'%(base['C8']['uncal'],base['C8']['calib'],base['C8']['ncal'],base['C6']['calib'],base['C7']['calib']))
for t in ('my6_p16','my6_p84','my7_p16','my7_p84','my8_p16','my8_p84'):
    a=analyze(run_family(L,jmc.TABS[t],92))
    print('%-8s C8 uncal %+.0f cal %+.0f ncal %d | C6 cal %+.3f C7 cal %+.1f (vs mine)'%(t,a['C8']['uncal']-base['C8']['uncal'],a['C8']['calib']-base['C8']['calib'],a['C8']['ncal'],a['C6']['calib']-base['C6']['calib'],a['C7']['calib']-base['C7']['calib']))
