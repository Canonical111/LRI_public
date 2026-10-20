from pathlib import Path
import json,subprocess,os,time
root=Path('/mnt/data/P8_final_run/F3_six_kink_completion');env=os.environ.copy();env['OPENBLAS_NUM_THREADS']='1'
for target in ['F4_Z8','F4_EA7','F4_A9']:
 while not(root/target/'source_manifest.json').exists():time.sleep(2)
 n=json.loads((root/target/'source_manifest.json').read_text())['buckets'];logs=root/target/'logs';logs.mkdir(exist_ok=True)
 for i in range(n):
  with (logs/f'collapse_{i:03d}.log').open('w') as f:
   subprocess.run(['python','-u',str(root/'engine/collapse_F4_bucket.py'),target,str(i)],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
  print('F4_COLLAPSED',target,i,flush=True)
