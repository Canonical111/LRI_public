from pathlib import Path
import json,subprocess,concurrent.futures
R=Path('/mnt/data/P8_final_run/F3_six_kink_completion');logs=R/'F4_logs';logs.mkdir(exist_ok=True)
def work(pair):
 name,i=pair
 with (logs/f'{name}_inner{i:03d}.log').open('w') as f:subprocess.run(['python','-u','integrate_F4_lastinner.py',name,str(i)],cwd=R/'engine',stdout=f,stderr=subprocess.STDOUT,check=True)
 return pair
jobs=[]
for name in ['F4_Z8','F4_A9','F4_EA7']:
 nb=json.loads((R/name/'source_manifest.json').read_text())['buckets'];jobs.extend((name,i) for i in range(nb))
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for pair in pool.map(work,jobs):print('F4_INNER_COMPLETED',pair,flush=True)
