import sys, numpy as np
from myjoint import tables, old_table
L,raw,T,D=tables()
To=old_table(L,raw)
sys.path.insert(0,'<TMP>/scratchpad/dconn_refit72/joint/code')
import os
os.environ['DCONN_OLD_CORRECTED']='<PROJECT>/lri_1d_coefficient_flow_review/step1_dconn_refit/delta/out/delta_v1_corrected.json'
import data as JD
J=JD.load(with_perts=False)
assert np.array_equal(J['L'],L)
def cmp(a,b,name):
    m=np.isfinite(a)|np.isfinite(b)
    assert np.array_equal(np.isfinite(a)[m],np.isfinite(b)[m]), name+' nan pattern'
    mm=np.isfinite(a)&np.isfinite(b)
    d=np.abs(a-b); d[~mm]=0
    rel=d/np.maximum(1,np.abs(np.nan_to_num(a)))
    k=np.unravel_index(np.argmax(rel),rel.shape)
    print('%-28s max rel diff %.2e at L=%d k=%d (abs %.2e)'%(name,rel.max(),L[k[0]],k[1],d[k]))
cmp(T['fmean'],J['dconn'],'mine fmean vs joint dconn')
cmp(raw,J['raw'],'raw')
cmp(T['median'],J['dconn_med'],'mine median vs joint med')
# s46 joint vs mine: mine = fmean table with 46..72 replaced by floor-mean curve
# old
VF='<PROJECT>/lri_1d_coefficient_flow_review/step1_dconn_refit/joint/out' 
import glob; print(glob.glob('<PROJECT>/lri_1d_coefficient_flow_review/step1_dconn_refit/*/out/variants_full*'))
