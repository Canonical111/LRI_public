#!/usr/bin/env python3
"""Read-only manifest status. Does not mistake job submission for acceptance."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lri_eh.runner import paths
from lri_eh.runtime import validate_result,verify_seal
ap=argparse.ArgumentParser();ap.add_argument('manifest',type=Path);a=ap.parse_args();m=json.loads(a.manifest.read_text())
rows=[]
for lane in m['lanes']:
 for L in lane['cutoffs']:
  p=paths(m['output_dir'],L,m['degree']);state='pending';detail=''
  try:
   if p['result'].exists():
    r=validate_result(json.loads(p['result'].read_text()))
    if r['source_sha256']!=m['source_sha256']:raise ValueError('Unexpected result source')
    state='accepted'
   elif p['attempts'].exists():
    x=json.loads(p['attempts'].read_text());verify_seal(x)
    state=x['terminal'] or 'running_or_interrupted';detail=f"attempts={x['count']}"
  except Exception as e:state='invalid';detail=str(e)
  rows.append(dict(cutoff=L,degree=m['degree'],state=state,detail=detail))
print(json.dumps(rows,indent=2))
print(f"Accepted {sum(x['state']=='accepted' for x in rows)}/{len(rows)}",file=sys.stderr)
