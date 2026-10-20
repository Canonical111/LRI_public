from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import subprocess,os,sys,json,time
root=Path(__file__).resolve().parent.parent
kind=sys.argv[1];deriv=sys.argv[2];n=int(sys.argv[3]);jobs=int(sys.argv[4]) if len(sys.argv)>4 else 2
out=root/'tail_blocks'/f'{kind}_{deriv}';logs=root/'tail_logs'/f'{kind}{n}_{deriv}';names=[b['id'] for p in sorted(out.glob(f'n{n}_face*_manifest.json')) for b in json.loads(p.read_text())['blocks']]
def run(name):
    while not (out/name/'result.json').exists():time.sleep(2)
    if (out/name/'full_boundary_jets.json').exists():return name,0,'reused'
    with (logs/f'{name}_jets.log').open('w') as f:
        st=time.time();p=subprocess.run([sys.executable,str(root/'engine/tail_jets.py'),kind,deriv,name],stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,OPENBLAS_NUM_THREADS='1'))
    return name,p.returncode,time.time()-st
print('JET_QUEUE',kind,n,len(names),flush=True)
with ThreadPoolExecutor(max_workers=jobs) as pool:
 for f in as_completed([pool.submit(run,name) for name in names]):print(f.result(),flush=True)
assert all((out/name/'full_boundary_jets.json').exists() for name in names)
print('ALL_JETS_DONE',flush=True)
