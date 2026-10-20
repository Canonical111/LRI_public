#!/usr/bin/env python3
"""Portable verification of the saved exact C8 rational calculation.
Uses only the Python standard library. Raw reintegration is a separate replay.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,time
ROOT=Path(__file__).resolve().parent

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--skip-hashes',action='store_true');a=ap.parse_args()
 records=[];start=time.time();verify=ROOT/'verification/replay';verify.mkdir(parents=True,exist_ok=True)
 if not a.skip_hashes:
  m=json.loads((ROOT/'MANIFEST.json').read_text());files=m['files']
  for row in files:
   p=ROOT/row['path'];assert p.is_file(),str(p)
   assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256'],str(p)
  records.append({'check':'distributed_file_hashes','files':len(files),'status':'PASS'})
 work=ROOT/'workspace/R8_work';eng=work/'engine'
 commands=[('independent_lower_moment_tables','check_lower_tables_stdlib.py'),
           ('complete_tail_sources_and_divergences','finalize_tail.py'),
           ('complete_ninth_sources_endpoint_and_divergences','finalize_ninth.py'),
           ('six_low_insertion_beta_inputs','verify_extra_beta_inputs.py'),
           ('independent_full_fixed_point_Jacobian','assemble_C8_full_beta.py'),
           ('independent_direct_six_kink_volume','verify_direct_Z6.py'),
           ('post_calculation_trial_comparison','check_trial_rational_parts.py')]
 # Restore the archived output snapshots afterward, leaving replay logs separate.
 snapshots={p:p.read_bytes() for p in work.glob('*.json')}
 try:
  for name,script in commands:
   t=time.time();p=subprocess.run([sys.executable,str(eng/script)],cwd=eng,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
   (verify/(name+'.log')).write_text(p.stdout)
   records.append({'check':name,'returncode':p.returncode,'seconds':time.time()-t,'status':'PASS' if p.returncode==0 else 'FAIL'})
   assert p.returncode==0,(name,p.stdout[-4000:])
  got=json.loads((work/'Task_D_result.json').read_text());want=json.loads((ROOT/'result.json').read_text())
  assert got['C8_weight_zero']==want['C8_weight_zero']
  assert got['R9']==want['R9']
  records.append({'check':'result_matches_distributed_summary','status':'PASS','rational_C8':got['C8_weight_zero']})
 finally:
  for p,data in snapshots.items():p.write_bytes(data)
 summary={'status':'all_requested_saved_exact_checks_passed','checks':records,'seconds':time.time()-start,
          'scope':'saved exact source coverage, output sums, independently regenerated lower controls, and full-Jacobian algebra; not all raw reintegrations'}
 (verify/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
