import json,shutil,subprocess,sys,tempfile,hashlib
from pathlib import Path
ROOT=Path(sys.argv[1]);old=sys.argv[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory() as tmp:
    r=Path(tmp)/'pkg';(r/'tools').mkdir(parents=True);shutil.copy2(old,r/'tools/verify_delivery.py')
    (r/'results').mkdir();rec=r/'results/C8_test_result.json';d=json.loads((ROOT/'tests/fixtures/verify_result_cross_machine/smoke1-20261005.json').read_text())
    d['test_partial'].pop('gates');rec.write_text(json.dumps(d))
    g=lambda *a:subprocess.run(['git','-C',str(r),*a],capture_output=True,text=True,check=True);g('init','-q');g('add','-A')
    w=subprocess.run([sys.executable,str(r/'tools/verify_delivery.py'),'--write'],capture_output=True,text=True);print('write',w.returncode)
    v=subprocess.run([sys.executable,str(r/'tools/verify_delivery.py'),'--strict'],capture_output=True,text=True);print('strict',v.returncode,json.loads(v.stdout)['status'])
