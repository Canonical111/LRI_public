from pathlib import Path
import subprocess,json,time,sys
ROOT=Path(__file__).resolve().parent
jobs=['n8_f2_b02','n8_f3_b01','n8_f3_b07']
report=[]
for b in jobs:
 start=time.time();p=subprocess.run([sys.executable,'prepare_stage3_fast.py',b],cwd=ROOT)
 row={'block':b,'returncode':p.returncode,'seconds':time.time()-start};report.append(row)
 (ROOT.parent/'missing_stage_preparation.json').write_text(json.dumps(report,indent=2))
 if p.returncode:raise RuntimeError(row)
 print('PREP_SEQUENCE_COMPLETED',b,flush=True)
