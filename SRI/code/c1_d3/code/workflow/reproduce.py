#!/usr/bin/env python3
"""Reproduce C1 in a temporary workspace and collect final data.
full --from-scratch regenerates everything without archived numerical seeds.
Other profiles may explicitly use bundled reference numerical dependencies.
"""
from __future__ import annotations
import argparse,hashlib,json,os,platform,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',choices=['smoke','central','legacy','refinement','validation','full']);p.add_argument('--from-scratch',action='store_true');p.add_argument('--output',type=Path,default=None);p.add_argument('--keep-workspace',action='store_true');a=p.parse_args()
 selected=a.output if a.output is not None else ROOT/'outputs'/('reproduced' if a.profile=='full' else a.profile+'_run')
 out=selected.resolve();out.mkdir(parents=True,exist_ok=True);t=time.time()
 receipt=dict(profile=a.profile,from_scratch=a.from_scratch,python=sys.version,platform=platform.platform(),cached_dependencies=[],steps=[],status='running')
 env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',C1_INPUT_DIR=str(ROOT/'data/inputs'))
 work=Path(tempfile.mkdtemp(prefix='ising-c1-'));groups={'precision':work/'c1_precision','refinement':work/'c1_refinement'}
 def record():(out/'run_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 try:
  for g,folder in groups.items():
   (out/g).mkdir(exist_ok=True);shutil.copytree(ROOT/'code'/folder.name,folder,ignore=shutil.ignore_patterns('__pycache__'))
   if not a.from_scratch:
    for f in (ROOT/'outputs/reference'/g).glob('*'):
     if f.suffix in ['.json','.npz']:shutil.copy2(f,folder/f.name);receipt['cached_dependencies'].append(dict(path=str(f.relative_to(ROOT)),sha256=sha(f)))
  def run(g,script,*args):
   folder=groups[g];cmd=[sys.executable,'-u',str(folder/script),*map(str,args)];print('RUN',g,script,*args,flush=True)
   before={f.name:sha(f) for f in folder.iterdir() if f.suffix in ['.json','.npz']};st=time.time()
   r=subprocess.run(cmd,cwd=folder,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);print(r.stdout,flush=True);created=[]
   for f in folder.iterdir():
    if f.suffix not in ['.json','.npz'] or f.name.startswith('checkpoint_'):continue
    if f.name not in before or sha(f)!=before[f.name]:shutil.copy2(f,out/g/f.name);created.append(f.name)
   receipt['steps'].append(dict(group=g,script=script,arguments=list(args),returncode=r.returncode,elapsed_seconds=time.time()-st,generated_files=created,stdout_tail=r.stdout[-1200:]));record()
   if r.returncode:raise RuntimeError(f'{script} failed; see {out}/run_receipt.json')
  central=a.profile in ['central','full'] or a.from_scratch and a.profile in ['refinement','legacy','validation']
  if a.profile=='smoke':run('precision','run_diagnostics.py','--quick')
  if central:
   run('precision','run_diagnostics.py');run('precision','errors_and_crossing.py');run('precision','complete_input_errors.py','global');run('precision','complete_input_errors.py','box')
  if a.profile in ['legacy','full']:
   for s in ['compute_tail_scenarios.py','finalize_results.py','tail_validation.py','alternative_domain.py','validate_cap.py']:run('precision',s)
  if a.from_scratch and a.profile in ['refinement','validation','full']:
   for n in ([32,40,48] if a.profile in ['validation','full'] else [40]):run('refinement','build_crossing.py',n)
  if a.profile in ['refinement','full'] or a.from_scratch and a.profile=='validation':
   for pars in [(8,7,1,10),(8,7,2,8),(6,6,1,8)]:run('refinement','final_run.py',*pars)
  if a.profile in ['validation','full']:
   run('refinement','check_nonlinear.py');run('refinement','validate_refinement.py','objective');run('refinement','validate_refinement.py','radial');run('refinement','run_numerical_checks.py');run('refinement','cap_tail_check.py')
  receipt.update(status='passed',elapsed_seconds=time.time()-t);record();print('All requested computations passed:',out/'run_receipt.json',flush=True)
 except Exception as exc:receipt.update(status='failed',error=str(exc));record();raise
 finally:
  if a.keep_workspace:receipt['workspace']=str(work);record()
  else:shutil.rmtree(work,ignore_errors=True)
if __name__=='__main__':main()
