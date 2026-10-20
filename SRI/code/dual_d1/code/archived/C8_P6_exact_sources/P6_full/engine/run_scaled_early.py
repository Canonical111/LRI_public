from pathlib import Path
import concurrent.futures,subprocess,sys,json,os
r=Path(__file__).resolve().parent.parent
meta=json.loads((r/'SEQ6_v/manifest.json').read_text())
def run(rec):
 with (r/'logs'/f'SEQ6_early_{rec["block"]}.log').open('w') as f:
  subprocess.run([sys.executable,'-u',str(r/'engine/full_scaled_finite.py'),'--tag','SEQ6_v','--block',rec['block'],'--stop','3'],stdout=f,stderr=subprocess.STDOUT,check=True)
 return rec['block']
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as p:
 for name in p.map(run,meta['blocks']):print('EARLY_COMPLETE',name,flush=True)
