"""Freeze independent point requests; does not submit or fit a curve.

For branch-sensitive points supply an explicit adjacent-cutoff seed. Separate
arrays may be chained with afterok dependencies. Outputs never share a writer.
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
from ht2d.hpc import atomic_json,digest,file_hash,source_hash
p=argparse.ArgumentParser();p.add_argument('--request-list',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
# Input is a list of argv arrays, e.g. [["--L","12","--x",".25",...]].
requests=json.loads(a.request_list.read_text());items=[];outputs=set()
if not isinstance(requests,list) or not requests:raise ValueError('At least one argv request is required')
from ht2d.hpc import parser
for argv in requests:
 args=parser().parse_args(argv)
 output=str(args.output.resolve())
 if output in outputs:raise ValueError('Duplicate output in manifest')
 outputs.add(output)
 # Normalize both --path VALUE and --path=VALUE, resolving repeated path
 # options exactly as argparse did. No relative path depends on the job cwd.
 normalized=[];i=0;pathflags={'--basis','--seed','--output'}
 while i<len(argv):
  arg=argv[i];flag=arg.split('=',1)[0]
  if flag in pathflags:
   i+=1 if '=' in arg else 2
  else:
   normalized.append(arg);i+=1
 for flag in sorted(pathflags):
  val=getattr(args,flag[2:])
  if val is not None:normalized.extend([flag,str(val.resolve())])
 files={str(p.resolve()):file_hash(p) for p in (args.basis,args.seed) if p is not None}
 items.append({'argv':normalized,'inputs':files,'output':output})
manifest={'schema':'ht2d-array-v1','source_sha256':source_hash(),'items':items}
manifest['sha256']=digest(manifest)
if a.output.exists():raise FileExistsError(a.output)
atomic_json(a.output,manifest);print(f'{len(items)} items; submit --array=0-{len(items)-1} with a site-specific concurrency limit')
