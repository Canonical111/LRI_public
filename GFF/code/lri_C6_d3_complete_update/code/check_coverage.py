"""Verify all required power-target IDs, and every retained forest-kernel weight."""
import json,sys
from fractions import Fraction as F
from pathlib import Path
W=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(W/'vendor'))
from mom_control_prepare import parse
inv=json.load(open(W/'inputs/classified_inventory.json'))['loops']
audit=json.load(open(W/'records/power_ms_d3_shifted.json'))
byloop={r['L']:r for r in audit['loops']};rows=[]
for r in inv:
 L=r['loop'];graphs=r['graphs'];power=[g for g in graphs if g['power_subgraphs']]
 if L>=5:
  needed={g['id']for g in power if L!=6 or 3*F(g['weight2'])-F(g['weight4'])!=0}
  have={g['id']for g in byloop[L]['done']if g['power']}
  assert needed==have,(L,needed-have,have-needed)
 row={'L':L,'all_classes':len(graphs),'power_classes':len(power),'power_audited':sum(g['power']for g in byloop[L]['done'])}
 if L>=2:
  _,kernels=parse(W/f'inputs/forest_L{L}.txt');lookup={g['id']:g for g in graphs}
  for k in kernels:
   gid=f'L{L}G{k["id"]+1:03d}';g=lookup[gid]
   assert not g['power_subgraphs'];assert abs(k['wa']-float(F(g['weight4'])))<1e-14;assert abs(k['wb']-float(F(g['weight2'])))<1e-14
   assert k['edges']==sum(g['edges'],[])
  row['retained_finite_kernels']=len(kernels)
 if L==6:
  zeros=[g for g in power if 3*F(g['weight2'])==F(g['weight4'])]
  row['zero_target_power_classes']=len(zeros);row['zero_target_power_ids']=[g['id']for g in zeros]
 rows.append(row)
(W/'records/graph_coverage.json').write_text(json.dumps({'rows':rows,'all_checks_passed':True,'scope':'Graph inventory inherited from the d=2 full computation; dimension-specific coverage and retained kernel weights rechecked. This does not constitute an independently generated second six-loop inventory.'},indent=2));print([(r['L'],r['all_classes'],r['power_classes'],r['power_audited'])for r in rows])
