from pathlib import Path
import sys,subprocess,os,time,json
ROOT=Path(__file__).resolve().parent;LOG=ROOT.parent/'logs'
n,kind,der,waitpid=sys.argv[1:5];tags=list(map(int,sys.argv[5:]))
while Path('/proc/'+waitpid).exists():
 try:
  if Path('/proc/'+waitpid+'/stat').read_text().split()[2]=='Z':break
 except FileNotFoundError:break
 time.sleep(2)
records=[]
for sector in tags:
 tag=f'{kind}{n}_{der}_sector{sector}'
 print('START',tag,flush=True);start=time.time()
 with (LOG/(tag+'_canonical.log')).open('w') as f:
  cp=subprocess.run([sys.executable,'run_moment.py',n,kind,der],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','LRI_SECTOR':str(sector),'LRI_COMBINE_EARLY':'1'})
 records.append({'tag':tag,'returncode':cp.returncode,'seconds':time.time()-start})
 (ROOT/(f'{kind}{n}_{der}_sector_status.json')).write_text(json.dumps(records,indent=2))
 print('DONE',records[-1],flush=True)
 if cp.returncode:break
