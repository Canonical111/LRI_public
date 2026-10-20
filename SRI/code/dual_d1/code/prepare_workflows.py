#!/usr/bin/env python3
"""Recreate portable original layouts from de-duplicated archived code/data.
Only this generated workspace is mutable. The distributed input bytes stay fixed.
"""
from __future__ import annotations
import argparse,hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GROUPS={
 'baseline':['LRI_1d_complete','D3_analytic_proof','C6_closed_form','LRI_thermal_closed_form'],
 'c7':['C7_completion','C7_closed_form_proof'],
 'c7-proof':['C7_closed_form_proof'],
 'c8-rational':['C8_rational_completion','R6_Task_A_completion','R8_Task_B_completion'],
 'f1':['F1b_completion','F1c_completion'],
 'f2-f3':['F2_F3_delivery','F3_six_kink_completion','F2_work','F2_resume'],
 'c8-full':['C8_full_numerical_completion'],
 'c8-candidate':['C8_zeta_candidate'],
 'p6-source':['C8_P6_exact_sources'],
 'p8-source':['P8_final_run','F3_P8_checkpoint','F3_six_kink_completion','C8_rational_completion','C7_completion','F1c_completion','F2_F3_delivery','C8_full_work'],
 'conjectures':['LRI_all_order_trials','LRI_new_general_formula','LRI_Gamma_exclusion','LRI_alternative_models','LRI_conjecture_audit'],
}
def prepare(group:str, destination:Path|None=None,rebase:bool=False)->Path:
 if group!='all' and group not in GROUPS:raise ValueError('Unknown workflow '+group)
 dest=(destination or ROOT/'work').resolve();dest.mkdir(parents=True,exist_ok=True)
 records=json.loads((ROOT/'reproduction/layout.json').read_text())['files']
 prefixes=GROUPS.get(group,[]); selected=[r for r in records if group=='all' or r['path'].split('/')[0] in prefixes]
 count=0
 for rec in selected:
  rel=Path(rec['path'])
  if rel.is_absolute() or '..' in rel.parts:raise ValueError('Unsafe virtual path')
  source=ROOT/rec['stored'];target=dest/rel
  if not source.is_file():raise FileNotFoundError(source)
  target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():
   if hashlib.sha256(source.read_bytes()).hexdigest()!=rec['sha256']:raise ValueError('Corrupt stored input '+str(source))
   shutil.copy2(source,target);count+=1
  # Path repair is explicit, applied only to generated copies of program text.
  if rebase and target.suffix=='.py':
   text=target.read_text();new=text.replace('/mnt/data/',dest.as_posix()+'/')
   if new!=text:target.write_text(new)
 report={'workflow':group,'root':str(dest),'paths_selected':len(selected),'new_copies':count,'scratch_paths_rebased':rebase,'warning':'Some regenerable ordered stages are intentionally omitted. See reproduction/omitted_files.json and documentation/REPRODUCTION.md. Stage manifests describe original snapshots, not the curated distribution.'}
 (dest/f'PREPARED_{group}.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2),flush=True);return dest
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workflow',choices=['all',*GROUPS],default='c8-candidate');p.add_argument('--destination',type=Path);p.add_argument('--rebase-scratch',action='store_true');a=p.parse_args();prepare(a.workflow,a.destination,a.rebase_scratch)
