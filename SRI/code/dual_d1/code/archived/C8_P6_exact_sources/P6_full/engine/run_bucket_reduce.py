from pathlib import Path
import json,subprocess,sys,concurrent.futures,os
ROOT=Path(__file__).resolve().parent.parent;folder=Path(sys.argv[1]);m=json.loads((folder/'partition.json').read_text())
def work(i):
 if not (folder/f'bucket{i:03}.report.json').is_file():
  env=os.environ.copy();env['OPENBLAS_NUM_THREADS']='1'
  with (ROOT/'logs'/f'bucket_reduce_{i:03}.log').open('a') as log:subprocess.run([sys.executable,'-u',str(ROOT/'engine/bucket_source_sum.py'),'reduce',str(folder),str(i)],stdout=log,stderr=subprocess.STDOUT,env=env,check=True)
 return i
with concurrent.futures.ThreadPoolExecutor(max_workers=int(os.environ.get('REDUCE_WORKERS','2'))) as pool:
 for f in concurrent.futures.as_completed([pool.submit(work,i) for i in range(m['buckets'])]):print('BUCKET_COMPLETE',f.result(),flush=True)
