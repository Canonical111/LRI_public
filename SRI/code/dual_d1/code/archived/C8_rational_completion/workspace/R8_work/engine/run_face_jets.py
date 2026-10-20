from pathlib import Path
import time,subprocess,sys,json,os
r=Path(__file__).resolve().parent.parent;k,d,n,f=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]);root=r/'tail_blocks'/f'{k}_{d}';logs=r/'tail_logs'/f'{k}{n}_{d}';m=json.loads((root/f'n{n}_face{f}_manifest.json').read_text())
for b in m['blocks']:
 name=b['id'];out=root/name
 while not (out/'result.json').exists():time.sleep(5)
 t=time.time()
 with (logs/(name+'_jets_extra.log')).open('w') as h:p=subprocess.run([sys.executable,str(r/'engine/tail_jets.py'),k,d,name],cwd=r/'engine',env=dict(os.environ,OPENBLAS_NUM_THREADS='1'),stdout=h,stderr=subprocess.STDOUT)
 print('EXTRA_JET',name,p.returncode,time.time()-t,flush=True);assert p.returncode==0
print('EXTRA_FACE_JETS_DONE',flush=True)
