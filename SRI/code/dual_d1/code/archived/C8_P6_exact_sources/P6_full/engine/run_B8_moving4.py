from pathlib import Path
import subprocess,sys,time,json,concurrent.futures
ROOT=Path(__file__).resolve().parent.parent

def work(i):
 while not (ROOT/'B8_stage3_buckets'/f'bucket{i:03}.report.json').exists():time.sleep(2)
 with (ROOT/'logs'/f'B8_moving4_{i:03}.log').open('w') as f:subprocess.run([sys.executable,str(ROOT/'engine/B8_stage4_moving.py'),str(i)],stdout=f,stderr=subprocess.STDOUT,check=True)
 return i
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for f in concurrent.futures.as_completed([pool.submit(work,i) for i in range(64)]):print('B8_MOVING4',f.result(),flush=True)
print('B8_ALL_MOVING4_COMPLETE',flush=True)
