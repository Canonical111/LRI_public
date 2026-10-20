"""Exact bookkeeping of all seven-loop target classes and lower-loop kernels."""
from pathlib import Path
import json
W=Path(__file__).resolve().parents[1];old=W.parent/'LRI_C7_d2_progress'
rows=[];partition={'zero_channel_weight':0,'zero_mixed_forest_kernel_at_nonzero_weight':0,'retained_primitive':0,'retained_powerfree_nonprimitive':0,'new_power_containing':0}
for L in range(3,8):
 p=json.load(open(W/f'inputs/L{L}/inventory.json'));f=json.load(open(old/f'inputs/L{L}/inventory.json'));assert len(p)==len(f)
 cc=dict(loop=L,classes=len(p),power_classes=0,new_nonzero_kernels=0,new_sampled_classes=0,new_zero_kernels=0)
 allrows=[]
 for a,b in zip(p,f):
  assert a['id']==b['id'] and a['key']==b['key'] and a['denominator']==b['denominator'] and a['mass_numerator']==b['mass_numerator']
  if a['power_subgraphs']:
   cc['power_classes']+=1
   if a['status']=='finite-kernel':cc['new_nonzero_kernels']+=1
   if a['status']=='exact-zero-kernel':cc['new_zero_kernels']+=1
   if a['status']=='finite-kernel' and (L<7 or a['mass_numerator']!=4):cc['new_sampled_classes']+=1
  if L==7:
   if a['mass_numerator']==4:c='zero_channel_weight'
   elif a['power_subgraphs']:
    c='new_power_containing'if a['status']=='finite-kernel'else'zero_mixed_forest_kernel_at_nonzero_weight'
   elif b['status']!='finite-kernel':c='zero_mixed_forest_kernel_at_nonzero_weight'
   elif b['primitive']:c='retained_primitive'
   else:c='retained_powerfree_nonprimitive'
   partition[c]+=1;allrows.append(dict(id=a['id'],category=c,denominator=a['denominator'],mass_numerator=a['mass_numerator'],power_subgraphs=a['power_subgraphs']))
 rows.append(cc)
 if L==7:detail=allrows
assert sum(partition.values())==3986
out=dict(status='passed',loops=rows,seventh_order_partition=partition,total_classes=3986,definitions='zero-channel exclusions apply only to the seventh-order simple-pole target. All lower-loop coupling/mass jets are retained separately.',seven_loop_classes=detail)
(W/'verification/full_graph_coverage.json').write_text(json.dumps(out,indent=2));print(rows);print(partition)
