"""Verify a frozen request then exec the ordinary one-writer driver."""
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
from ht2d.hpc import digest,file_hash,source_hash
p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--index',type=int,required=True);a=p.parse_args()
m=json.loads(a.manifest.read_text());sig=m.pop('sha256',None)
if sig!=digest(m) or m.get('schema')!='ht2d-array-v1' or m['source_sha256']!=source_hash():raise ValueError('Manifest/source mismatch')
if not 0<=a.index<len(m['items']):raise IndexError('Array index outside the frozen manifest')
item=m['items'][a.index]
for path,h in item['inputs'].items():
 if file_hash(path)!=h:raise ValueError(f'Manifest input changed: {path}')
os.environ['HT2D_FROZEN_SOURCE']=m['source_sha256']
os.environ['HT2D_FROZEN_INPUTS']=json.dumps(item['inputs'],sort_keys=True)
argv=item['argv'];argv=argv if '--resume' in argv else argv+['--resume']
os.execv(sys.executable,[sys.executable,str(ROOT/'code/hpc_run.py'),*argv])
