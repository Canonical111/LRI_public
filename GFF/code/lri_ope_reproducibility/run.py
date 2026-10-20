#!/usr/bin/env python3
"""Reproduce the LRI bulk-one-point calculation without modifying source inputs.

Examples: python run.py quick; python run.py symbolic; python run.py numeric;
          python run.py integrals; python run.py masters; python run.py figures;
          python run.py note; python run.py all
Each legacy calculation is staged in a temporary working directory. Only named
final results/certificates are retained. No network is used, except optionally
by the saved HTML when a reader opens it to fetch original arXiv images.
"""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, os, shutil, subprocess, sys
import tempfile, time
from pathlib import Path
from typing import Iterable
ROOT=Path(__file__).resolve().parent

def environment():
    packages={}
    for p in ('mpmath','sympy','numpy','scipy','matplotlib'):
        try: packages[p]=importlib.metadata.version(p)
        except importlib.metadata.PackageNotFoundError: packages[p]='not installed'
    return {'python':sys.version.split()[0],'packages':packages}

def stage(name: str, where: Path, *, certificates: bool=False)->Path:
    work=where/name; work.mkdir(parents=True,exist_ok=True)
    for f in (ROOT/'code'/name).glob('*.py'): shutil.copy2(f,work/f.name)
    data=ROOT/'data'/name
    if data.exists():
        for f in data.glob('*.json'): shutil.copy2(f,work/f.name)
    if name=='bootstrap': shutil.copy2(data/'inputs_historical.json',work/'inputs.json')
    if certificates:
        for f in (ROOT/'data/reference/a6').glob('*.json'): shutil.copy2(f,work/f.name)
    return work

def execute(args: list[str], cwd: Path, log: list[dict], *, capture: str|None=None):
    start=time.monotonic();print('RUN', ' '.join(args),flush=True)
    env=dict(os.environ,PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1',MPLBACKEND='Agg',MPLCONFIGDIR=str(cwd/'.mpl_cache'))
    cp=subprocess.run(args,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    entry={'command':args,'working_directory_role':cwd.name,'returncode':cp.returncode,'seconds':round(time.monotonic()-start,3)}
    log.append(entry)
    if cp.returncode:
        print(cp.stdout[-20000:],file=sys.stderr)
        raise RuntimeError(f'Failed: {args}; exit {cp.returncode}')
    if capture: (cwd/capture).write_text(cp.stdout)
    print(f'  PASS ({entry["seconds"]:.2f} s)',flush=True)
    return cp.stdout

def retain(work:Path,out:Path,names:Iterable[str]):
    out.mkdir(parents=True,exist_ok=True)
    for n in names:
        f=work/n
        if not f.is_file(): raise FileNotFoundError(f'Expected output not produced: {n}')
        shutil.copy2(f,out/n)

def task_quick(tmp:Path,out:Path,log:list):
    w=stage('low_order',tmp)
    execute([sys.executable,'check_a_phi2.py','--json','low_order_checks.json'],w,log)
    retain(w,out/'verification',['low_order_checks.json'])
    w=stage('relations',tmp)
    text=execute([sys.executable,'relations.py','--verify'],w,log)
    (out/'verification/relations_symbolic.json').write_text(text)
    execute([sys.executable,'check_numeric.py'],w,log)
    retain(w,out/'verification',['numeric_checks.json'])
    execute([sys.executable,str(ROOT/'code/evaluate_project.py'),'--output-dir',str(out)],ROOT,log)
    w=stage('a6',tmp,certificates=True)
    execute([sys.executable,'verify_a6.py'],w,log)
    shutil.copy2(w/'verification_results.json',out/'verification/a6_stored_certificate_regression.json')

def task_symbolic(tmp:Path,out:Path,log:list):
    w=stage('a5',tmp)
    for name in ('enumerate_graphs.py','symbolic_kernels.py','symbolic_assembly.py'):
        execute([sys.executable,name],w,log)
    retain(w,out/'verification/a5_symbolic',['symbolic_kernels.json','symbolic_a5.json'])
    w=stage('a6',tmp)
    for name in ('enumerate_graphs.py','vertex_graphs.py','symbolic_engine.py','universal_assembly.py','collect_a6.py','verify_a6.py'):
        execute([sys.executable,name],w,log)
    retain(w,out/'verification/a6_symbolic',['symbolic_results.json','universal_assembly.json','collected_a6.json','verification_results.json'])
    # Inventories are reproducible inputs; compare exact decoded content.
    for f in list(w.glob('graphs_n*.json'))+list(w.glob('vertex_n*.json')):
        expected=ROOT/'data/a6'/f.name
        if json.loads(f.read_text())!=json.loads(expected.read_text()):
            raise AssertionError(f'Inventory mismatch: {f.name}')
    (out/'verification/a6_symbolic/inventory_check.json').write_text(json.dumps({'all_regenerated_inventories_match':True},indent=2)+'\n')

def task_numeric(tmp:Path,out:Path,log:list):
    w=stage('a6',tmp,certificates=True)
    # Prefer this run's fresh symbolic certificates; otherwise label their source.
    fresh=out/'verification/a6_symbolic'
    for n in ('symbolic_results.json','universal_assembly.json','collected_a6.json'):
        if (fresh/n).is_file(): shutil.copy2(fresh/n,w/n)
    execute([sys.executable,'verify_a6.py','--numeric','--dimension','1'],w,log)
    retain(w,out/'verification/a6_numeric',['verification_results.json'])

def task_integrals(tmp:Path,out:Path,log:list):
    w=stage('a4',tmp)
    execute([sys.executable,'symbolic_check.py'],w,log)
    execute([sys.executable,'verify_a4.py'],w,log)
    retain(w,out/'verification/a4_integrals',['verification_results.json'])
    w=stage('a5',tmp)
    execute([sys.executable,'verify_a5.py'],w,log)
    retain(w,out/'verification/a5_numeric',['verification_results.json'])

def task_masters(tmp:Path,out:Path,log:list):
    w=stage('a6',tmp)
    execute([sys.executable,'evaluate_fixed_dimensions.py'],w,log)
    retain(w,out/'verification/master_quadrature',['fixed_dimension_results.json','d2_inputs.json','d3_inputs.json'])

def task_figures(tmp:Path,out:Path,log:list):
    # Outputs are historical for exact reproducibility, plus a current-C6 sensitivity run.
    for version in ('historical','current'):
        w=stage('bootstrap',tmp/version)
        if version=='current':
            inp=json.loads((w/'inputs.json').read_text())
            cur=json.loads((ROOT/'data/thermal_current.json').read_text())
            for d in ('2','3'):inp['thermal_coefficients'][d]=cur['coefficients'][d][:7]
            inp['thermal_source']='2026-10-15 GFF note displayed table, C0..C6 (sensitivity update; OPE data unchanged)'
            (w/'inputs.json').write_text(json.dumps(inp,indent=2)+'\n')
        dest=out/'bootstrap'/version;dest.mkdir(parents=True,exist_ok=True)
        execute([sys.executable,'compare_sixth_order.py','--output-dir',str(dest)],w,log)
        shutil.copy2(w/'inputs.json',dest/'inputs_used.json')
        if version=='historical':
            for f in dest.glob('*.png'):shutil.copy2(f,out/'figures'/f.name)
    # Report the effect of the updated thermal input at fixed resummation prescription.
    old=json.loads((out/'bootstrap/historical/comparison_results.json').read_text())
    new=json.loads((out/'bootstrap/current/comparison_results.json').read_text())
    pairs=[]
    for a,b in zip(old['rows'],new['rows']):
        pairs.append({'d':a['d'],'label':a['label'],'epsilon':a['epsilon'],
                      'thermal_historical':a['thermal_BP42'],'thermal_current':b['thermal_BP42'],
                      'difference':b['thermal_BP42']-a['thermal_BP42']})
    (out/'bootstrap/thermal_input_sensitivity.json').write_text(json.dumps(pairs,indent=2)+'\n')

def task_note(tmp:Path,out:Path,log:list):
    if not shutil.which('latexmk'):raise RuntimeError('Install latexmk and a TeX distribution; see README.md.')
    w=tmp/'typeset'/'note';w.mkdir(parents=True)
    shutil.copy2(ROOT/'note/lri_ope_note.tex',w/'lri_ope_note.tex')
    # Standalone source compiles without figures; for the release include generated figures.
    fdir=w.parent/'results/figures';fdir.mkdir(parents=True)
    for f in (out/'figures').glob('*.png'):shutil.copy2(f,fdir/f.name)
    execute(['latexmk','-pdf','-interaction=nonstopmode','-halt-on-error','-file-line-error','lri_ope_note.tex'],w,log)
    shutil.copy2(w/'lri_ope_note.pdf',ROOT/'note/lri_ope_note.pdf')
    raw=(w/'lri_ope_note.log').read_text(errors='replace')
    summary={'compiled':True,'undefined_references':bool('There were undefined references' in raw),
             'overfull_boxes':[line for line in raw.splitlines() if 'Overfull' in line],
             'pages':next((line for line in raw.splitlines() if line.startswith('Output written on')),'')}
    (out/'verification/latex_build.json').write_text(json.dumps(summary,indent=2)+'\n')
    if summary['undefined_references']:raise RuntimeError('Unresolved references after latexmk.')

def task_manifest(out:Path):
    dest=ROOT/'MANIFEST.sha256'
    rows=[]
    for f in sorted(ROOT.rglob('*')):
        if f.is_file() and f!=dest and '__pycache__' not in f.parts and not any(p.startswith('.mpl') for p in f.parts):
            rows.append(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.relative_to(ROOT).as_posix())
    dest.write_text('\n'.join(rows)+'\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    choices=['quick','symbolic','numeric','integrals','masters','figures','note','all','manifest']
    parser.add_argument('tasks',nargs='+',choices=choices)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'results')
    args=parser.parse_args();out=args.output_dir.resolve()
    for p in ('verification','figures','bootstrap'):(out/p).mkdir(parents=True,exist_ok=True)
    tasks=args.tasks
    if 'all' in tasks: tasks=['quick','symbolic','numeric','integrals','masters','figures','note']
    for task in tasks:
        if task=='manifest':task_manifest(out);continue
        log=[];start=time.monotonic();status='passed';error=None
        try:
            with tempfile.TemporaryDirectory(prefix=f'lri_ope_{task}_') as td:
                globals()['task_'+task](Path(td),out,log)
        except Exception as exc:
            status='failed';error=str(exc);raise
        finally:
            report={'task':task,'status':status,'seconds':round(time.monotonic()-start,3),'environment':environment(),'commands':log,
                    'qualification':'Re-execution in a temporary directory. Internal identities and numerical residuals are not independent physical validation or truncation-error bounds.'}
            if error:report['error']=error
            (out/'verification'/f'run_{task}.json').write_text(json.dumps(report,indent=2)+'\n')
        print(f'TASK {task}: PASSED',flush=True)
if __name__=='__main__':main()
