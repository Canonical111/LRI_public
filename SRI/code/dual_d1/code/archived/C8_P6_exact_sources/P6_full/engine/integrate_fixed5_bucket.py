"""One more exact ordered integration; sum rational endpoint terms before fibration."""
from group_before_fibration import *
def _run(i):
 source=ROOT/'P8_fixed4'/f'b{i:03d}.jsonl';sh=hashlib.sha256(source.read_bytes()).hexdigest()
 folder=ROOT/'P8_moving5'/f'b{i:03d}';folder.mkdir(parents=True,exist_ok=True);dest=folder/'moving.jsonl';rp=folder/'report.json'
 if dest.exists() and rp.exists():
  r=json.loads(rp.read_text());assert r['source_sha256']==sh and r['output_sha256']==hashlib.sha256(dest.read_bytes()).hexdigest();return r
 t=time.time();g,n=moving_stage([source],5,6);dump_moving(dest,g)
 r={'complete':True,'source_sha256':sh,'source':str(source),'input_rows':n,'moving_rows':len(g),'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'seconds':time.time()-t,'full_periods':True}
 rp.write_text(json.dumps(r,indent=2));return r
def run(i):
 import fcntl
 folder=ROOT/'P8_moving5'/f'b{i:03d}';folder.mkdir(parents=True,exist_ok=True)
 with (folder/'.lock').open('a') as f:
  fcntl.flock(f,fcntl.LOCK_EX)
  return _run(i)
if __name__=='__main__':print(json.dumps(run(int(sys.argv[1])),indent=2),flush=True)
