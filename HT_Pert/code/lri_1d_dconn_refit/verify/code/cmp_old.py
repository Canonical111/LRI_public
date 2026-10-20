import sys, numpy as np
from myjoint import tables, old_table
L,raw,T,D=tables()
To=old_table(L,raw)
sys.path.insert(0,'<TMP>/scratchpad/dconn_refit72/joint/code')
import data as JD
A='<PROJECT>/lri_1d_coefficient_flow_review/step1_dconn_refit/'
J=JD.load(A+'delta/out/delta_v1_corrected.json',A+'joint/out/variants_full.json',with_perts=False)
a,b=To,J['dconn']
m=np.isfinite(a)&np.isfinite(b)
print('nan pattern equal',np.array_equal(np.isfinite(a),np.isfinite(b)))
d=np.where(m,np.abs(a-b),0); print('old table max abs diff',d.max(), 'by k',d.max(axis=0))
# difference new - old at selected L
for k in (6,7,8):
    print('dC%d new(fmean)-old(fmean v1) at L=46,60,72,74,92,118:'%k,' '.join('%+.2e'%(T['fmean'][list(L).index(l),k]-To[list(L).index(l),k]) if np.isfinite(T['fmean'][list(L).index(l),k]) else '-' for l in (46,60,72,74,92,118)))
np.save('../out/tab_old.npy',To)
