import subprocess,sys,os,json,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
root=Path(__file__).resolve().parent.parent
kind=sys.argv[1];deriv=sys.argv[2];n=int(sys.argv[3]);workers=int(sys.argv[4]) if len(sys.argv)>4 else 2
eng=root/'engine';out=root/'tail_blocks'/f'{kind}_{deriv}';logs=root/'tail_logs'/f'{kind}{n}_{deriv}';logs.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
for face in range(1,(n-1+1)//2+1):
    mf=out/f'n{n}_face{face}_manifest.json'
    if not mf.exists():
        with (logs/f'source_f{face}.log').open('w') as f:
            subprocess.run([sys.executable,str(eng/'tail_boundary.py'),'--kind',kind,'--deriv',deriv,'--n',str(n),'--face',str(face),'--sources'],stdout=f,stderr=subprocess.STDOUT,check=True,env=env,cwd=eng)
names=[b['id'] for p in sorted(out.glob(f'n{n}_face*_manifest.json')) for b in json.loads(p.read_text())['blocks']]
def run(name):
    if (out/name/'result.json').exists():return name,0,'reused'
    with (logs/f'{name}.log').open('w') as f:
        st=time.time();r=subprocess.run([sys.executable,str(eng/'tail_boundary.py'),'--kind',kind,'--deriv',deriv,'--block',name],stdout=f,stderr=subprocess.STDOUT,env=env,cwd=eng)
    return name,r.returncode,time.time()-st
print('QUEUE',kind,n,deriv,len(names),flush=True)
results=[]
with ThreadPoolExecutor(max_workers=workers) as e:
    for fut in as_completed([e.submit(run,name) for name in names]):
        value=fut.result();results.append(value);print('FINISHED',value,flush=True)
assert all(code==0 for _,code,_ in results), 'At least one integral block failed'
assert all((out/name/'result.json').exists() for name in names), 'Incomplete block coverage'
print('DONE',flush=True)
