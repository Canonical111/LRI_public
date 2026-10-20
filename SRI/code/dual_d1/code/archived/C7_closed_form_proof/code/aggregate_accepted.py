#!/usr/bin/env python3
"""Reassemble the complete weight-six certificate from all accepted stage rows."""
from pathlib import Path
from fractions import Fraction
import argparse,json,hashlib,time

def main():
 root=Path(__file__).resolve().parent.parent
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=root/'verification/reassembled.w6.certificate.txt');args=p.parse_args()
 manifest=json.loads((root/'accepted_stages/aggregation_manifest.json').read_text());co={};count=0;start=time.perf_counter()
 for item in manifest['source_files']:
  file=root/'accepted_stages'/item['file']
  if hashlib.sha256(file.read_bytes()).hexdigest()!=item['sha256']:raise RuntimeError('Source hash mismatch: '+str(file))
  rows=0
  for line in file.read_text().splitlines():
   q,key=line.split(' ',1);co[key]=co.get(key,0)+Fraction(q);rows+=1
   if not co[key]:del co[key]
  if rows!=item['rows']:raise RuntimeError('Source row-count mismatch')
  count+=rows
 with args.output.open('w') as f:
  for key,q in sorted(co.items()):f.write(f'{q} {key}\n')
 sha=hashlib.sha256(args.output.read_bytes()).hexdigest()
 if sha!=manifest['certificate_sha256']:raise RuntimeError('Aggregated certificate differs')
 result={'status':'PASS','source_rows':count,'aggregated_rows':len(co),'certificate_sha256':sha,'seconds':time.perf_counter()-start}
 (root/'verification/aggregation_report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
