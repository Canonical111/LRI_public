from pathlib import Path
import sys,subprocess,time,os,json
ROOT=Path(__file__).resolve().parent;LOG=ROOT.parent/'logs'
pid=sys.argv[1]
while Path('/proc/'+pid).exists():
 try:
  if Path('/proc/'+pid+'/stat').read_text().split()[2]=='Z':break
 except FileNotFoundError:break
 time.sleep(2)
records=[]
for n,k,der in [(3,'EA','v'),(4,'EQ','v'),(5,'EA','base'),(6,'Q','v'),(7,'A','base')]:
 tag=f'{k}{n}_{der}';t=time.time()
 print('START CONTROL',tag,flush=True)
 with (LOG/(tag+'_control.log')).open('w') as f:
  cp=subprocess.run([sys.executable,'run_moment.py',str(n),k,der],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','LRI_COMBINE_EARLY':'1'})
  if cp.returncode==0:cp=subprocess.run([sys.executable,'check_backend.py',tag],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 records.append({'tag':tag,'returncode':cp.returncode,'seconds':time.time()-t})
 (ROOT/'baseline_control_status.json').write_text(json.dumps(records,indent=2))
 print('DONE CONTROL',records[-1],flush=True)
 if cp.returncode:break
