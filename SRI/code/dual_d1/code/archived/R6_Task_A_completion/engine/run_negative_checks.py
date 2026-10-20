from pathlib import Path
import os,json,time
from concurrent.futures import ProcessPoolExecutor,as_completed
import multiprocessing as mp
from negative_moments import worker,ROOT

def main():
    manifest=json.loads((ROOT/'boundary_batches/manifest.json').read_text());st=time.time();done=0
    with ProcessPoolExecutor(max_workers=int(os.environ.get("R6_NEG_WORKERS","2")),mp_context=mp.get_context('fork')) as pool:
        futures=[pool.submit(worker,r) for r in manifest]
        for f in as_completed(futures):
            f.result();done+=1
            if done%20==0:print('NEG_PROGRESS',done,'/',len(manifest),'seconds',time.time()-st,flush=True)
    print('NEGATIVE_MOMENTS_COMPLETE',done,flush=True)
if __name__=='__main__':main()
