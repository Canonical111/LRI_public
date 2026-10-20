from fibration_defect import *
base=Path('/mnt/data/P8_final_run/rational_stages/C8_rational_completion/workspace/R8_work/finite_lower/EZ6_base');dest=ROOT/'F4_defects_EZ6';dest.mkdir(exist_ok=True)
for idx in range(2,5):
 total={};records=[]
 for src in sorted(base.glob(f'b*/stage{idx-1}.jsonl')):
  ans,rec=defect_stage(src,idx,6);records.append(rec)
  for k,c in ans.items():addto(total,k,c)
 assert idx==4 or not clean(total),(idx,len(clean(total)))
 dump(dest/f'defect_stage{idx}.jsonl',total);(dest/f'report{idx}.json').write_text(json.dumps({'complete_zero_defect':not bool(clean(total)),'input_records':records},indent=2));print('EZ6_DEFECT_ZERO',idx,flush=True)
folder=ROOT/'F4_EZ6';folder.mkdir(exist_ok=True);out={};records=[]
for src in sorted(base.glob('b*/stage4.jsonl')):
 rec={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'rows':sum(1 for _ in src.open())};records.append(rec)
 for line in src.open():
  ww,ll,ct=json.loads(line)
  if isinstance(ll,int):assert ll==0;ll=[]
  key=(tuple(tuple(rm.parseK(a) for a in w) for w in ww),tuple(ll));addto(out,key,rm.parseK(ct))
for key,c in load(dest/'defect_stage4.jsonl'):addto(out,key,c)
out=clean(out);dump(folder/'fixed_b000.jsonl',out)
(folder/'source_manifest.json').write_text(json.dumps({'n':6,'dimensionless_endpoint_offset':5,'kappa':0,'interval_factor':False,'buckets':1,'source_blocks':6,'sources':records,'full_constant_status':'nonzero stage-four coalescence defect restored exactly; restore 2 log(8/15)*Z6_finite'},indent=2));print('EZ6_SOURCE',len(out),flush=True)
