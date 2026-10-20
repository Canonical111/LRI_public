"""Collect complete stage-five sources in deterministic hash buckets."""
from pathlib import Path
import json,hashlib,sys,time
root=Path(__file__).resolve().parent.parent
nb=64;dest=root/'P8_moving5_sum';dest.mkdir(exist_ok=True)
files=[(dest/f'b{i:03d}.tsv.tmp').open('w') for i in range(nb)]
records=[];nr=0
for i in range(256):
 folder=root/'P8_moving5'/f'b{i:03d}';fp=folder/'moving.jsonl';rp=folder/'report.json'
 if not rp.exists():raise RuntimeError(('missing bucket',i))
 r=json.loads(rp.read_text());assert r['complete'] and r['output_sha256']==hashlib.sha256(fp.read_bytes()).hexdigest()
 records.append({'file':str(fp),'sha256':r['output_sha256']})
 for line in fp.open():
  w,tail,ll,c=json.loads(line);key=json.dumps([w,tail,ll],separators=(',',':'));idx=int.from_bytes(hashlib.blake2b(key.encode(),digest_size=8).digest(),'little')%nb
  files[idx].write(key+'\t'+c+'\n');nr+=1
for f in files:f.close()
for i in range(nb):(dest/f'b{i:03d}.tsv.tmp').rename(dest/f'b{i:03d}.tsv')
(dest/'manifest.json').write_text(json.dumps({'complete':True,'source_buckets':256,'input_rows':nr,'sources':records,'sum_buckets':nb},indent=2));print('COLLECTED',nr,flush=True)
