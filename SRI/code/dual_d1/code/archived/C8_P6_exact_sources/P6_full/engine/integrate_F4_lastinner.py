from group_before_fibration import *
import fcntl
name=sys.argv[1];i=int(sys.argv[2]);folder=ROOT/name;src=folder/f'fixed_b{i:03d}.jsonl';dest=folder/f'moving_b{i:03d}.jsonl';rp=folder/f'moving_b{i:03d}.report.json';sh=hashlib.sha256(src.read_bytes()).hexdigest()
with (folder/f'.moving_b{i:03d}.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 if dest.exists() and rp.exists():
  r0=json.loads(rp.read_text());assert r0['source_sha256']==sh and r0['output_sha256']==hashlib.sha256(dest.read_bytes()).hexdigest()
 else:
  start=time.time();g,n=moving_stage([src],5,6);dump_moving(dest,g)
  rp.write_text(json.dumps({'complete':True,'source':str(src),'source_sha256':sh,'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'input_rows':n,'moving_rows':len(g),'seconds':time.time()-start},indent=2));print('F4_INNER_DONE',name,i,n,len(g),flush=True)
