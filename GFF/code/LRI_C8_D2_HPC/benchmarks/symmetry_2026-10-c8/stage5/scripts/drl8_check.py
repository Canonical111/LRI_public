import json,sys,glob,os
run,saved,out=sys.argv[1:4]
SCI=('uid','rep','graph','begin','end','total','values','quad','mp','max_abs','tail_top','tail_sum','tail_argmax')
old=json.load(open(glob.glob(saved+'/s000001_p000000.json')[0]));new=json.load(open(run+'/groups/a_free_L7/checkpoints/s000001_p000000.json'))
ro,rn=old['native']['rows'],new['native']['rows']
sci_equal=len(ro)==len(rn) and all(all(a.get(k)==b.get(k) for k in SCI) for a,b in zip(ro,rn))
recomputed=old['native'].get('integration_seconds')!=new['native'].get('integration_seconds') or old['runtime']['fingerprint']!=new['runtime']['fingerprint']
res={'index':17,'checkpoint':'groups/a_free_L7/checkpoints/s000001_p000000.json','rows':len(rn),'scientific_fields_equal':sci_equal,
     'recomputed (new integration time or fingerprint)':recomputed,'old_job':(old['runtime']['fingerprint'].get('slurm')or{}).get('SLURM_JOB_ID'),'new_job':(new['runtime']['fingerprint'].get('slurm')or{}).get('SLURM_JOB_ID')}
mb={}
for d in sorted(os.listdir(saved+'/merged')):
    a=json.load(open(f'{saved}/merged/{d}/merged.json'));b=json.load(open(f'{run}/groups/{d}/merged.json'))
    mb[d]=json.dumps(a['batches'],sort_keys=True)==json.dumps(b['batches'],sort_keys=True)
res['merged_batches_equal']=mb;res['all_24_batches_equal']=len(mb)==24 and all(mb.values())
inv=[json.loads(l) for l in open(run+'/lanes/done_invalidated.jsonl')]
res['done_invalidated']=inv;res['names_index_17']=any(x['index']==17 for x in inv)
json.dump(res,open(out,'w'),indent=1);print(json.dumps({k:v for k,v in res.items() if k!='merged_batches_equal'}))
