from driver import *
import os
orig=W/'inputs/grid_d2_top11.txt';t=orig.read_text().split();ng,nd,nb=map(int,t[:3]);i=3
for _ in range(ng):
 i+=1
 for j in range(nd):t[i]='0';t[i+nb]='1';i+=nb+1
snap=W/'inputs/grid_d2_top11_snapped.txt';snap.write_text(' '.join(t)+'\n')
counts=json.load(open(W/'inputs/benchmark_counts.json'))
for tag,path in [('endpoint_original',orig),('endpoint_snapped',snap)]:
 os.environ['GRID_FILE']=str(path);os.environ.pop('PREFIX_STRATA',None);os.environ.pop('TRAIN_HIST',None)
 run(tag,2,6,counts,16,314691473,0,1,False,'rqmc',False,60)
a=json.load(open(W/'records/endpoint_original_d2_L6.json'));b=json.load(open(W/'records/endpoint_snapped_d2_L6.json'))
x=np.array(a['graph_batches']);y=np.array(b['graph_batches']);diff=(np.array(a['batches'])-np.array(b['batches']))@np.array([-1.,3.])/2187
out={'N':a['N'],'identical_seed':a['seed']==b['seed'],'max_normalized_graph_batch_difference':float(np.max(abs(x-y)/(1+abs(x)))),'C6_component_mean_difference':float(diff.mean()),'max_abs_C6_component_replicate_difference':float(max(abs(diff))),'scope':'Same-point floating normalization replay; not an interval bound.'}
(W/'verification/grid_endpoint_replay.json').write_text(json.dumps(out,indent=2));print(out)
