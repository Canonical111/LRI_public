from driver import *
# Baseline allocation is supplied from an earlier independent pilot, not this benchmark.
for d in (2,3):
 _,rows=graph_ids(B/'baseline/lri_C6_d3_complete_update/inputs/forest_L6.txt')
 pp=json.load(open(B/f'inputs/production_d3_L6.json'))['probabilities']
 c=np.maximum(64,2**np.rint(np.log2(np.array([pp[str(r[0])] for r in rows])*65536))).astype(int)
 cases=[('ref',0,1,False,'rqmc',True),('base',0,1,False,'rqmc',False),('radial',1,1,False,'rqmc',False),('single',2,1,False,'rqmc',False),('smooth6',1,.75,False,'rqmc',False),('smooth5',1,.625,False,'rqmc',False),('rate1',1,1.25,False,'rqmc',False),('anti',1,1,True,'rqmc',False),('mc',1,1,False,'mc',False)]
 for name,lay,rate,anti,method,ref in cases:
  if (W/f'records/pilot_{name}_d{d}_L6.json').exists():continue
  run('pilot_'+name,d,6,c//2 if anti else c,16,8134917+31*d,lay,rate,anti,method,ref)
