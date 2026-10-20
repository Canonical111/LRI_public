#!/usr/bin/env python3
"""Re-execute source calculations in temporary workspaces, preserving inputs."""
from __future__ import annotations
import argparse, json, os, platform, shutil, subprocess, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STAGES=ROOT/'code'/'stages'
CORE=[
 ('real_checks_45','C6_real_basis',['check.py','45']),
 ('real_checks_90','C6_real_basis',['check.py','90']),
 ('real_build','C6_real_basis',['build.py']),
 ('complete_smoke','C6_complete_interval',['certify_complete.py','smoke']),
 ('complete_release','C6_complete_interval',['certify_complete.py','release']),
 ('complete_refined','C6_complete_interval',['certify_complete.py','refined']),
 ('residual_intervals','C6_three_residual_sums_evaluation',['evaluate.py']),
]
EXACT=[
 ('wheel_exact','C6_central_binomial_wheel',['verify.py']),
 ('seventh_central_exact','C6_central_seventh',['verify.py']),
 ('cubic_exact','C6_primitive_cubic',['verify.py']),
 ('even_exact','C6_even_sector',['verify.py']),
 ('cyclotomic_exact','C6_cyclotomic',['verify.py']),
 ('flat_exact','C6_flat_harmonic',['verify.py']),
 ('linear_words','C6_linear_geometric',['word_certificate.py']),
 ('standard_even_exact','C6_standard_even',['verify.py']),
 ('standard_seventh_exact','C6_standard_seventh',['verify.py']),
 ('standard_primitive_exact','C6_standard_primitive',['verify.py']),
 ('sixth_exact','C6_sixth_MeijerG',['build_and_verify.py']),
 ('eighth_exact','C6_eighth_MeijerG',['build_and_verify.py']),
 ('lower_exact','C6_lower_MeijerG',['build_verify.py']),
 ('compact_primitive_exact','C6_compact_H',['build_verify.py']),
 ('single_wheel_exact','C6_single_wheel_H',['build_verify.py']),
 ('seventh_barnes_exact','C6_seventh_two_values',['build_and_verify.py']),
 ('unit_slope_exact','C6_seventh_unit_slopes',['build_and_verify.py']),
 ('spectral_exact','C6_primitive_Chebyshev',['verify.py']),
 ('primitive_seed_exact','C6_primitive_seed_relations',['verify.py']),
 ('polylog_audit','C6_polylog_basis_audit',['analysis.py']),
 ('eight_value_exact','C6_eight_value_alternative',['verify.py']),
]
NUMERICAL=[
 ('seventh_barnes','C6_seventh_unit_slopes',['numerical.py','40']),
 ('sixth_barnes','C6_sixth_MeijerG',['numerical.py','40']),
 ('eighth_barnes','C6_eighth_MeijerG',['numerical.py','40']),
]
def run_task(task,output,limit):
 name,stage,args=task;dest=output/name;dest.mkdir(parents=True,exist_ok=True)
 rec={'id':name,'source_stage':'code/stages/'+stage,'command':[sys.executable,*args],'status':'not_run'}
 start=time.monotonic()
 with tempfile.TemporaryDirectory(prefix='c6_reproduce_') as td:
  work=Path(td)/stage;shutil.copytree(STAGES/stage,work)
  before={str(p.relative_to(work)):p.read_bytes() for p in work.rglob('*') if p.is_file() and p.suffix in ('.json','.txt','.csv','.md')}
  env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',MPLBACKEND='Agg')
  try:
   proc=subprocess.run([sys.executable,*args],cwd=work,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=limit)
   rec.update(returncode=proc.returncode,status='passed' if proc.returncode==0 else 'failed')
   (dest/'stdout.txt').write_text(proc.stdout);(dest/'stderr.txt').write_text(proc.stderr)
  except subprocess.TimeoutExpired as exc:
   rec.update(status='timeout',returncode=None)
   for k,val in [('stdout',exc.stdout),('stderr',exc.stderr)]:
    if isinstance(val,bytes):val=val.decode(errors='replace')
    (dest/(k+'.txt')).write_text(val or '')
  generated=[]
  for p in work.rglob('*'):
   if p.is_file() and p.suffix in ('.json','.txt','.csv','.md'):
    rel=str(p.relative_to(work));data=p.read_bytes()
    if rel not in before or data!=before[rel]:
     q=dest/'generated'/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data);generated.append(str(q.relative_to(ROOT)))
  rec['generated_files']=generated
 rec['elapsed_seconds']=time.monotonic()-start
 (dest/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
 return rec

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--profile',choices=['core','exact','numerical','all'],default='core');ap.add_argument('--timeout',type=int,default=180);ap.add_argument('--only',nargs='*',help='Run only named tasks');ap.add_argument('--resume',action='store_true')
 args=ap.parse_args()
 if args.timeout<=0: ap.error('--timeout must be positive')
 if args.only:
  unknown=set(args.only)-{x[0] for x in CORE+EXACT+NUMERICAL}
  if unknown: ap.error('Unknown task identifiers: '+', '.join(sorted(unknown)))
 tasks=CORE if args.profile=='core' else EXACT if args.profile=='exact' else NUMERICAL if args.profile=='numerical' else CORE+EXACT+NUMERICAL
 tasks=[t for t in tasks if not args.only or t[0] in args.only]
 if not tasks: ap.error('No selected tasks belong to this profile')
 out=ROOT/'outputs'/'rerun';out.mkdir(parents=True,exist_ok=True)
 records=[]
 for task in tasks:
  previous=out/task[0]/'execution.json'
  if args.resume and previous.exists() and json.loads(previous.read_text()).get('status')=='passed':
   rec=json.loads(previous.read_text());print('KEEP',task[0],flush=True)
  else:
   print('RUN',task[0],flush=True);rec=run_task(task,out,args.timeout);print(rec['status'],round(rec['elapsed_seconds'],3),flush=True)
  records.append(rec)
 summary={'profile':args.profile,'environment':{'python':sys.version,'platform':platform.platform()},'tasks':records,'all_passed':all(x['status']=='passed' for x in records),'scope':'Re-execution of supplied analytic/numerical code; not a new independent physical graph calculation.'}
 (out/('summary_'+args.profile+'.json')).write_text(json.dumps(summary,indent=2)+'\n')
 return 0 if summary['all_passed'] else 1
if __name__=='__main__':raise SystemExit(main())
