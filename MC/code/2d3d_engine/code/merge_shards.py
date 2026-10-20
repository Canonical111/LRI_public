#!/usr/bin/env python3
"""Merge completed disjoint copies of ONE global campaign; never double-count chains.

Input directories must already be mounted/copied locally. No remote transfer is
performed. By default chains are symlinked; --copy creates a portable data copy.
"""
import argparse,hashlib,json,shutil
from pathlib import Path

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--sources',type=Path,nargs='+',required=True);p.add_argument('--copy',action='store_true');a=p.parse_args()
 mfs=[json.loads((p/'manifest.json').read_text()) for p in a.sources];base=mfs[0]
 if any(m['campaign_id']!=base['campaign_id'] or m['tasks']!=base['tasks'] for m in mfs):p.error('inputs must be identical global manifests, not independently regenerated campaigns')
 if a.out.exists():p.error('output exists; refusing to overwrite')
 chosen={};duplicates=[]
 for source in a.sources:
  for t in base['tasks']:
   dr=source/t['directory']
   if not (dr/'DONE.json').exists():continue
   z=json.loads((dr/'DONE.json').read_text());raw=dr/'samples.bin';size=z['measurements_done']*z.get('record_columns',4)*8
   if raw.stat().st_size!=size:raise ValueError(f'inconsistent raw size: {dr}')
   if t['id'] in chosen:
    old=chosen[t['id']]
    if digest(old/'samples.bin')!=digest(raw):raise ValueError(f'task {t["id"]} has two DIFFERENT completed trajectories; resolve explicitly')
    duplicates.append({'task':t['id'],'duplicate_source':str(dr)});continue
   chosen[t['id']]=dr.resolve()
 a.out.mkdir(parents=True);(a.out/'manifest.json').write_text(json.dumps(base,indent=2)+'\n')
 for tid,dr in chosen.items():
  target=a.out/base['tasks'][tid]['directory'];target.parent.mkdir(exist_ok=True,parents=True)
  if a.copy:shutil.copytree(dr,target)
  else:target.symlink_to(dr,target_is_directory=True)
 # Restore tiny kernel files only for optional table-based samplers.
 for t in base['tasks']:
  if t.get('coupling_sha256'):
   target=a.out/t['couplings']
   if not target.exists():
    source=next((p/t['couplings'] for p in a.sources if (p/t['couplings']).exists()),None)
    if source is None:raise ValueError('required table kernel missing')
    target.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(source,target)
 audit={'campaign_id':base['campaign_id'],'complete_unique_chains':len(chosen),'deduplicated_identical_chains':duplicates,
        'missing_task_ids':[t['id'] for t in base['tasks'] if t['id'] not in chosen]}
 (a.out/'merge_audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
