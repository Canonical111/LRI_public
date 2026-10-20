from pathlib import Path
import json,subprocess,os,sys
r=Path(__file__).resolve().parent.parent
for face in [4,3]:
 tag=f'B8_v_f{face}';records=json.loads((r/tag/'manifest.json').read_text())['blocks']
 for item in reversed(records):
  b=item['block'];folder=r/tag/b
  if (folder/'stage3.jsonl').exists():continue
  env=os.environ.copy();env['OPENBLAS_NUM_THREADS']='1'
  with (r/'logs'/f'{tag}_{b}_reverse.log').open('a') as log:
   subprocess.run([sys.executable,'-u',str(r/'engine/full_boundary.py'),'--tag',tag,'--block',b,'--stop','3'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  print('REVERSE_EARLY_DONE',tag,b,flush=True)
