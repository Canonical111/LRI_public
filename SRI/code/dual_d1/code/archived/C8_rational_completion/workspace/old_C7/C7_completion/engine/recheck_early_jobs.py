"""Re-evaluate early new moments after the cached-shuffle immutability fix."""
from pathlib import Path
import subprocess,sys,time,json,os,re
ROOT=Path(__file__).resolve().parent;LOG=ROOT.parent/'logs'
# Wait for a worker slot, not for any missing numerical result.
pid=sys.argv[1] if len(sys.argv)>1 else ''
while pid and Path('/proc/'+pid).exists():
 try:
  if Path('/proc/'+pid+'/stat').read_text().split()[2]=='Z':break
 except FileNotFoundError:break
 time.sleep(2)
from hyperlog_core import K,addto,clean
snapshot=ROOT/'pre_fix_raw_snapshots';snapshot.mkdir(exist_ok=True)
def rd(data):
 out={}
 for w,l,c in json.loads(data):addto(out,(tuple(w),tuple(l)),K.from_expr(c))
 return clean(out)
records=[]
for tag in ['EQ2_dd','Q2_dd','Q2_vdd','Z2_vdd','A3_dd','A3_vdd','A3_vvd','A3_vvv','EA3_vd','EA3_vv','EZ4_v','Q4_dd','EQ4_d']:
 file=ROOT/(tag+'_negative.json');old=file.read_bytes() if file.exists() else None
 if old is not None:(snapshot/file.name).write_bytes(old)
 k,n,d=re.fullmatch(r'(EA|EQ|EZ|A|Q|Z)(\d+)_(\w+)',tag).groups()
 print('RECHECK',tag,flush=True);start=time.time()
 with (LOG/(tag+'_cachefixed.log')).open('w') as f:
  cp=subprocess.run([sys.executable,'run_moment.py',n,k,d],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','LRI_COMBINE_EARLY':'1'})
 rec={'tag':tag,'returncode':cp.returncode,'seconds':time.time()-start}
 if cp.returncode==0 and old is not None:
  aa=rd(old);bb=rd(file.read_bytes());df=clean({key:aa.get(key,K.zero)-bb.get(key,K.zero) for key in aa.keys()|bb.keys()})
  rec.update({'exact_agreement_with_early_run':not df,'difference_terms':len(df)})
 records.append(rec);(ROOT/'cachefix_rechecks.json').write_text(json.dumps(records,indent=2))
 print('RESULT',rec,flush=True)
 if cp.returncode:break
