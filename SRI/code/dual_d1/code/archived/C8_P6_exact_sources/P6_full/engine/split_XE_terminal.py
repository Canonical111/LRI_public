"""Restart final two integrations on a verified disjoint source partition."""
from pathlib import Path
import os,sys,time,json,hashlib,signal,subprocess,concurrent.futures
ROOT=Path(__file__).resolve().parent.parent
source=ROOT/'SEQ6_combined/b00/stage4.jsonl'
while not source.is_file():time.sleep(.5)
# Stop only the specific old serial continuation, after its atomic stage is saved.
try:
 cmd=Path('/proc/2574/cmdline').read_bytes()
 if b'full_scaled_finite.py' in cmd and b'SEQ6_combined' in cmd:os.kill(2574,signal.SIGTERM)
except (FileNotFoundError,ProcessLookupError):pass
out=ROOT/'XE_terminal';out.mkdir(exist_ok=True)
meta=json.loads((ROOT/'SEQ6_combined/manifest.json').read_text());rows=source.read_text().splitlines(keepends=True);records=[];size=2000
for start in range(0,len(rows),size):
 name=f'b{start//size:03}';p=out/name/'stage4.jsonl';p.parent.mkdir(exist_ok=True);text=''.join(rows[start:start+size]);p.write_text(text)
 records.append({'block':name,'start':start,'end':min(start+size,len(rows)),'rows':len(rows[start:start+size]),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
meta.update({'starting_stage':4,'blocks':records,'whole_source':str(source),'whole_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_rows':len(rows),'disjoint_contiguous_ranges':True})
(out/'manifest.json').write_text(json.dumps(meta,indent=2));print('XE_SPLIT',len(rows),len(records),flush=True)
def run(rec):
 b=rec['block'];env=os.environ.copy();env['OPENBLAS_NUM_THREADS']='1'
 with (ROOT/'logs'/f'XE_terminal_{b}.log').open('a') as log:
  subprocess.run([sys.executable,'-u',str(ROOT/'engine/full_scaled_finite.py'),'--tag','XE_terminal','--block',b],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 return b
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for f in concurrent.futures.as_completed([pool.submit(run,r) for r in records]):print('XE_TERMINAL_COMPLETE',f.result(),flush=True)
