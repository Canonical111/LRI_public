from pathlib import Path
import json,subprocess,sys,time
ROOT=Path(__file__).resolve().parent;LOG=ROOT.parent/'logs'
while True:
 p=ROOT/'Q8_base_sector_status.json'
 if p.exists():
  r=json.loads(p.read_text())
  if len(r)==4 and all(x['returncode']==0 for x in r):break
  if any(x['returncode'] for x in r):raise RuntimeError(r)
 time.sleep(3)
for args,name in [(['merge_raw_sectors.py','8','Q','base'],'Q8_merge_raw.log')]:
 with (LOG/name).open('w') as f:subprocess.run([sys.executable]+args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
print('Q8 EXACT RAW COMPLETE',flush=True)
