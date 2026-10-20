#!/usr/bin/env python3
"""Run the packaged calculations without modifying preserved input data.

Examples (run from the package root):
  python scripts/run.py validate
  python scripts/run.py analyze
  python scripts/run.py certify
  python scripts/run.py demo
  python scripts/run.py hamiltonian --work-dir work/main -- --cutoff 256 --order 1 --lam .1
  python scripts/run.py continuum -- run --records <merged index> --aux-dir <c2aux dir> --output <dir>

A temporary working directory is used unless --work-dir is specified. This
stages the original flat-layout code and data, exports results, and then removes
caches. Large Hamiltonian runs should use a persistent --work-dir to reuse grids.
No calculation requires network access after dependencies are installed.
"""
from __future__ import annotations
import argparse, contextlib, datetime, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def hash_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def stage_hamiltonian(work:Path,data:bool=False)->None:
    work.mkdir(parents=True,exist_ok=True)
    for p in (ROOT/'code/hamiltonian').glob('*.py'):shutil.copy2(p,work/p.name)
    if data:
        for group in ['raw','auxiliary']:
            for p in (ROOT/'data/hamiltonian'/group).glob('*.json'):shutil.copy2(p,work/p.name)

class Runner:
    def __init__(self,work:Path,out:Path):
        self.work,self.out=work,out;self.jobs=[]
        self.env=dict(os.environ,OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',MPLBACKEND='Agg',MPLCONFIGDIR=str(work/'.matplotlib'))
    def call(self,name:str,*args:str,cwd:Path|None=None,capture:str|None=None)->None:
        wd=cwd or self.work
        argv=[sys.executable,str(wd/name),*map(str,args)]
        print('RUN',name,*args,flush=True)
        if capture is None:
            subprocess.run(argv,cwd=wd,env=self.env,check=True)
        else:
            result=subprocess.run(argv,cwd=wd,env=self.env,check=True,text=True,stdout=subprocess.PIPE)
            # Captured report must be valid JSON before it is exported.
            json.loads(result.stdout)
            (wd/capture).write_text(result.stdout)
            print(result.stdout,end='',flush=True)
        self.jobs.append(dict(script=name,arguments=list(map(str,args)),status='passed'))
    def export(self,names:list[str],source:Path|None=None)->None:
        self.out.mkdir(parents=True,exist_ok=True);src=source or self.work
        for pattern in names:
            for p in src.glob(pattern):
                if p.is_file():shutil.copy2(p,self.out/p.name)
    def finish(self)->None:
        self.out.mkdir(parents=True,exist_ok=True)
        files={p.name:hash_file(p) for p in sorted(self.out.iterdir()) if p.is_file() and p.name!='run_receipt.json'}
        receipt=dict(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),python=sys.version,jobs=self.jobs,outputs_sha256=files,
                     scope='Only listed jobs were rerun; a saved-data analysis is not a full recomputation of the large spectral grids.')
        (self.out/'run_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print('OUTPUTS',self.out,flush=True)

def analyze(r:Runner)->None:
    r.call('bundle_helpers.py','refresh-large')
    r.call('tail_transseries_fit.py')
    r.call('analyze_extended.py')
    r.call('final_analysis.py')
    r.call('bundle_helpers.py','coupling')
    r.call('bundle_helpers.py','tables')
    r.export(['FINAL_NUMERICAL_RESULTS.json','tail_transseries_fits.json','extended_analysis.json','coupling_scheme_recheck.json','*.csv'])

def collect_run(work:Path,row:dict)->None:
    """Convert a new solver record to the names consumed by saved-data analysis."""
    from importlib.util import spec_from_file_location,module_from_spec
    sys.path.insert(0,str(work))
    try:
        from analyze_fine import analyze as af
        from analyze_sequences import fits
        k=row['order'];lam=row['lam'];N=row['N'];a=af(row)
        if N==128 and k==3 and lam==.5:
            target=work/'large_lambda_k3_a0.5.json';obj=dict(data=row,analysis=a,tail_fits=fits(a['sequence']))
        else:
            prefix='extended' if N==384 else 'fine';target=work/f'{prefix}_k{k}_a{lam}.json';obj=row
        target.write_text(json.dumps(obj,indent=2)+'\n')
    finally:sys.path.pop(0)

def full_hamiltonian(r:Runner)->None:
    plan=json.loads((ROOT/'data/hamiltonian/run_plan.json').read_text())
    tails=[]
    for job in plan['jobs']:
        argv=['--cutoff',str(job['cutoff']),'--order',str(job['order']),'--lam',*map(str,job['lambda']),
              '--mixed-cutoff','4096','--collapsed-cutoff',str(job['collapsed_cutoff']),
              '--oversample',str(job['oversample']),'--radius-cost',str(job['radius_cost']),
              '--workers',str(job.get('workers',1)),'--output-prefix','fresh']
        r.call('reproduce.py',*argv)
        for lam in job['lambda']:
            p=r.work/f"fresh_k{job['order']}_a{lam}_N{job['cutoff']}.json"
            collect_run(r.work,json.loads(p.read_text()))
            q=p.with_name(p.stem+'_analysis.json');a=json.loads(q.read_text());t=a['leading_tail']
            if job['cutoff']==384:(r.work/f"leading_N384_k{job['order']}_a{lam}.json").write_text(json.dumps(t,indent=2)+'\n')
            else:tails.append(t)
    (r.work/'exact_leading_tail.json').write_text(json.dumps(tails,indent=2)+'\n')
    analyze(r)
    r.export(['fine_k*.json','extended_k*.json','large_lambda_k*.json','leading_N384_*.json','exact_leading_tail.json'])

def execute(a,extra:list[str])->None:
    out=(a.output or ROOT/'outputs'/a.command).resolve()
    ctx=contextlib.nullcontext(a.work_dir.resolve()) if a.work_dir else tempfile.TemporaryDirectory(prefix='lri_c2_')
    with ctx as d:
        work=Path(d);work.mkdir(parents=True,exist_ok=True);r=Runner(work,out)
        if a.command in ['validate','analyze','analyze-recorded','second-order','demo','hamiltonian','full-hamiltonian']:
            stage_hamiltonian(work,data=a.command in ['analyze','analyze-recorded'])
            if a.command=='validate':
                r.call('validate.py');r.export(['validation_results.json','checks_results.json','finite_shell_check.json','mixed_sequence_checks.json','lowmemory_checks.json'])
            elif a.command=='analyze':analyze(r)
            elif a.command=='analyze-recorded':
                # Reproduce the originally recorded model ensemble, which had
                # no transseries-fit entry for order 3, lambda .35 and used
                # the documented raw-tail fallback for that single point.
                for name in ['tail_transseries_fits.json','extended_analysis.json']:
                    shutil.copy2(ROOT/'data/hamiltonian/reference'/name,work/name)
                r.call('final_analysis.py')
                r.call('bundle_helpers.py','tables')
                r.export(['FINAL_NUMERICAL_RESULTS.json','*.csv'])
            elif a.command=='second-order':
                r.call('second_order.py',capture='second_order_results.json');r.call('slope_check.py');r.call('beta_improved.py');r.call('bundle_helpers.py','magnetic')
                r.export(['second_order_results.json','slope_check.json','beta_improved.json','magnetic_calibration_improved.json'])
            elif a.command in ['demo','hamiltonian']:
                argv=extra or ['--cutoff','24','--order','1','--lam','0.25','--mixed-cutoff','64','--collapsed-cutoff','4000']
                r.call('reproduce.py',*argv);r.export(['*_k*_a*_N*.json','fast_coeff*.json','parallel_coeff*.json'])
            else:full_hamiltonian(r)
        elif a.command in ['certify','formula-checks']:
            for group in ['numerical','elliptic','physical']:
                dst=work/group;dst.mkdir(exist_ok=True)
                for p in (ROOT/'code/formula_checks'/group).glob('*.py'):shutil.copy2(p,dst/p.name)
            if a.command=='certify':
                r.call('certify_c2.py',*extra,cwd=work/'numerical');r.export(['certified_result*.json'],work/'numerical')
            else:
                for name in ['identity_audit.py','complex_moment_check.py','complex_moment_general_check.py']:r.call(name,cwd=work/'elliptic')
                for n in [96,192,384]:r.call('continued_period_check.py',str(n),cwd=work/'elliptic')
                r.call('local_physics_checks.py',cwd=work/'physical')
                r.export(['*.json'],work/'elliptic');r.export(['*.json'],work/'physical')
        elif a.command=='legacy-checks':
            for p in (ROOT/'code/legacy_hamiltonian').glob('*.py'):shutil.copy2(p,work/p.name)
            r.call('checks.py');r.call('second_order.py',capture='second_order_results.json');r.export(['checks_results.json','second_order_results.json'])
        elif a.command=='original-study':
            shutil.copytree(ROOT/'code/original_study',work/'code',dirs_exist_ok=True)
            shutil.copytree(ROOT/'data/original_study',work/'inputs',dirs_exist_ok=True)
            shutil.copytree(ROOT/'reference/original_study',work/'note',dirs_exist_ok=True)
            # The manuscript inventory check expects the original README and source map.
            for name in ['README.md','requirements.txt','DEPENDENCIES.json','MANIFEST.json']:
                src=ROOT/'reference/original_study'/name
                if src.exists():shutil.copy2(src,work/name)
            (work/'provenance').mkdir(exist_ok=True)
            src=ROOT/'provenance/original_study_source_map.json'
            if src.exists():shutil.copy2(src,work/'provenance/source_map.json')
            r.call('reproduce.py',cwd=work/'code')
            if out.exists():shutil.rmtree(out)
            shutil.copytree(work/'outputs',out,ignore=shutil.ignore_patterns('logs','.matplotlib','__pycache__'))
        r.finish()

def main()->None:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('command',choices=['validate','analyze','analyze-recorded','certify','formula-checks','second-order','demo','hamiltonian','full-hamiltonian','original-study','legacy-checks','continuum'])
    p.add_argument('--work-dir',type=Path,help='Persistent scratch directory; useful for large array reuse.')
    p.add_argument('--output',type=Path,help='Output directory; default outputs/<command>.')
    a,extra=p.parse_known_args();extra=extra[1:] if extra[:1]==['--'] else extra
    if a.command=='continuum':
        # Arbitrary-N continuum analysis (code/continuum, PLAN_ANALYSIS rev 4). Every argument after
        # `--` goes to its driver unchanged; the other commands are not affected.
        if a.work_dir or a.output:p.error('continuum: pass the driver arguments after --, e.g. continuum -- run --output DIR ...')
        sys.exit(subprocess.run([sys.executable,str(ROOT/'code/continuum/continuum_driver.py'),*extra],cwd=ROOT).returncode)
    if extra and a.command not in ['hamiltonian','demo','certify']:p.error('Extra arguments are only accepted by hamiltonian, demo, or certify.')
    try:execute(a,extra)
    except (subprocess.CalledProcessError,OSError,ValueError) as e:
        print(f'ERROR: {e}',file=sys.stderr);sys.exit(1)
if __name__=='__main__':main()
