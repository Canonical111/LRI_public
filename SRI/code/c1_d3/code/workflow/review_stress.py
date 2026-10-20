#!/usr/bin/env python3
"""Recompute sensitivity scenarios in isolated workspaces (no nominal receipt changes).
Gap scans reuse the packaged reference L40 numerical basis, explicitly.
Box scans regenerate input derivatives, denominator samples and the L40 basis.
All scenarios keep the original chosen integrated-objective allowance; their
sensitivity intervals are diagnostic, not independently certified alternate bounds.
"""
from __future__ import annotations
import argparse,json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
GAPS=[(8,7,1),(8,6.5,1),(7,7,1),(6.5,7,1),(8,6,1),(7,6,1),(6,6,1),(8,5.5,1),(6,5.5,1),(8,7,2),(8,7,3)]
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('mode',choices=['gaps','boxes']);ap.add_argument('--multipliers',type=float,nargs='+',default=[.5,.6,.7,.8,.9,1.5,2.,3.]);ap.add_argument('--iterations',type=int,default=10);ap.add_argument('--output',type=Path,default=None);args=ap.parse_args()
    out=(args.output or ROOT/'outputs/review_validation'/args.mode).resolve();out.mkdir(parents=True,exist_ok=True)
    cases=[dict(even_gap=g,odd_gap=o,padding=p,multiplier=1.) for g,o,p in GAPS] if args.mode=='gaps' else [dict(even_gap=8.,odd_gap=7.,padding=1.,multiplier=m) for m in args.multipliers]
    allresults=[]
    for case in cases:
        m=case['multiplier'];name=f"g{case['even_gap']:g}_{case['odd_gap']:g}_p{case['padding']:g}_m{m:g}";dest=out/name;dest.mkdir(exist_ok=True);start=time.time();steps=[]
        with tempfile.TemporaryDirectory(prefix='c1-review-stress-') as temp:
            work=Path(temp);inp=work/'inputs';shutil.copytree(ROOT/'data/inputs',inp)
            for group in ['c1_precision','c1_refinement']:
                shutil.copytree(ROOT/'code'/group,work/group,ignore=shutil.ignore_patterns('__pycache__'))
            for group,folder in [('precision','c1_precision'),('refinement','c1_refinement')]:
                for f in (ROOT/'outputs/reference'/group).iterdir():
                    if f.suffix in ['.json','.npz']:shutil.copy2(f,work/folder/f.name)
            if args.mode=='boxes':
                rows=json.loads((inp/'published_spectrum.json').read_text())
                for row in rows:
                    for key in ['Delta_error','f_error','h_error']:
                        if key in row:row[key]*=m
                (inp/'published_spectrum.json').write_text(json.dumps(rows))
                low=json.loads((inp/'low_inputs.json').read_text())
                for val in low['values'].values():val['quoted_error']*=m
                (inp/'low_inputs.json').write_text(json.dumps(low))
            env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',C1_INPUT_DIR=str(inp))
            def run(folder,script,*arguments):
                cmd=[sys.executable,'-u',str(work/folder/script),*map(str,arguments)];st=time.time()
                completed=subprocess.run(cmd,env=env,cwd=work/folder,capture_output=True,text=True)
                steps.append(dict(script=script,arguments=list(arguments),returncode=completed.returncode,elapsed_seconds=time.time()-st,stdout_tail=(completed.stdout+completed.stderr)[-1800:]))
                return completed
            if args.mode=='boxes':
                jobs=[('c1_precision','errors_and_crossing.py'),('c1_precision','complete_input_errors.py','global'),('c1_precision','complete_input_errors.py','box'),('c1_refinement','build_crossing.py',40)]
                for job in jobs:
                    rr=run(*job)
                    if rr.returncode:raise RuntimeError(rr.stderr)
            rr=run('c1_refinement','final_run.py',case['even_gap'],case['odd_gap'],case['padding'],args.iterations)
            prefix=f"final_{case['even_gap']:g}_{case['odd_gap']:g}_pad{case['padding']:g}"
            record=dict(**case,iterations=args.iterations,status='completed' if rr.returncode==0 else 'failed',steps=steps)
            if rr.returncode==0:
                summary=json.loads((work/'c1_refinement'/(prefix+'_summary.json')).read_text());record['interval']=summary['interval'];record['summary']=summary
                for f in (work/'c1_refinement').glob(prefix+'*'):
                    if f.suffix in ['.json','.npz']:shutil.copy2(f,dest/f.name)
            elif 'LP infeasible' in rr.stderr or 'Negative upper remainder' in rr.stderr or 'Negative odd bound' in rr.stderr:
                record['status']='infeasible';record['diagnostic_message']=rr.stderr[-1200:]
            else:raise RuntimeError(rr.stderr)
            if args.mode=='boxes':
                for rel in ['c1_precision/analysis_results.json','c1_precision/global_input_results.json','c1_precision/input_box_results.json','c1_refinement/basis_L40.json','c1_refinement/basis_L40.npz']:
                    f=work/rel;shutil.copy2(f,dest/f.name)
                for f in inp.iterdir():
                    if f.name in ['published_spectrum.json','low_inputs.json']:shutil.copy2(f,dest/('scaled_'+f.name))
            record['elapsed_seconds']=time.time()-start;(dest/'receipt.json').write_text(json.dumps(record,indent=2)+'\n');allresults.append(record)
            (out/'summary.json').write_text(json.dumps(dict(mode=args.mode,source='Fresh reruns by code/workflow/review_stress.py',gap_basis='outputs/reference/refinement/basis_L40.*' if args.mode=='gaps' else 'regenerated at scaled input errors',scope='Sensitivity diagnostics with chosen numerical allowances, not certified physical bounds',cases=allresults),indent=2)+'\n')
            print(name,record['status'],record.get('interval'),flush=True)
if __name__=='__main__':main()
