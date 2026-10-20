import task_memory_gate
_start_guard=task_memory_gate.acquire()
from grouped_endpoint_projection import *
task_memory_gate.release(_start_guard)
p=Path(sys.argv[1]);source=p/'moving.jsonl';digest=hashlib.sha256(source.read_bytes()).hexdigest();dest=p/'growth_stage5.jsonl';rp=p/'growth_stage5_report.json'
if dest.exists() and rp.exists():
 r=json.loads(rp.read_text());assert r['input_sha256']==digest and r['output_sha256']==hashlib.sha256(dest.read_bytes()).hexdigest();sys.exit(0)
g={}
for line in source.open():
 a,b,ll,c=json.loads(line);g[(tuple(rm.parseK(x) for x in a),tuple(rm.parseK(x) for x in b),tuple(ll))]=rm.parseK(c)
n=len(g);st=time.time();out=fibrate_group(g);dump(dest,out)
r={'complete':True,'input_rows':n,'input_sha256':digest,'output_rows':len(out),'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'seconds':time.time()-st,'all_periods_retained':True};rp.write_text(json.dumps(r,indent=2));print('FIBRATION_FINISHED',p.name,r,flush=True)
