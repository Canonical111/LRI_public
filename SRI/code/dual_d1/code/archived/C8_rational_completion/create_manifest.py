"""Hash the distribution, excluding only disposable/platform-specific outputs."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent

def included(p):
 rel=p.relative_to(ROOT)
 if rel.as_posix()=='MANIFEST.json':return False
 if '__pycache__' in rel.parts or p.suffix in ['.pyc','.so','.lock','.tmp']:return False
 if len(rel.parts)>=2 and rel.parts[0]=='verification' and rel.parts[1] in ['replay','raw_replay']:return False
 return p.is_file()

def main():
 rows=[]
 for p in sorted(ROOT.rglob('*')):
  if not included(p):continue
  h=hashlib.sha256()
  with p.open('rb') as f:
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
  rows.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':h.hexdigest()})
 d={'algorithm':'sha256','scope':'all distributed files except MANIFEST.json and disposable replay/native build outputs','files':rows,'total_bytes':sum(v['bytes'] for v in rows),'file_count':len(rows)}
 (ROOT/'MANIFEST.json').write_text(json.dumps(d,indent=2));print(json.dumps({'file_count':len(rows),'total_bytes':d['total_bytes']}))
if __name__=='__main__':main()
