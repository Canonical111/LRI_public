import subprocess,sys,json,os,concurrent.futures
from pathlib import Path
root=Path(__file__).resolve().parent.parent
records=[]
for face in range(1,5):
 tag=f'B8_v_f{face}';meta=json.loads((root/tag/'manifest.json').read_text())
 records.extend((tag,r) for r in meta['blocks'])
# Pole blocks remain separate and source hashes determine coverage.
def work(row):
 tag,r=row;name=r['block'];env=os.environ.copy();env['OPENBLAS_NUM_THREADS']='1'
 with (root/'logs'/f'{tag}_{name}.log').open('a') as f:
  subprocess.run([sys.executable,'-u',str(root/'engine/full_boundary.py'),'--tag',tag,'--block',name,'--stop','3'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 return tag,name
with concurrent.futures.ThreadPoolExecutor(max_workers=int(os.environ.get('B8_WORKERS','1'))) as pool:
 for x in pool.map(work,records):print('STAGE3_COMPLETE',x,flush=True)
