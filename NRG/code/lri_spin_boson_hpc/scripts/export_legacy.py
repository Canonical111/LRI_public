"""Gated exports readable by prior analyze_tangent.py; not resumable checkpoints.

Destination folder: the item ID for campaign records (<root>/<id>/gNNNN/result.json,
generation kept in provenance), else the record's parent folder name. Every record
and destination is checked before anything is written. A destination holds the
components of exactly one record: an identical export is skipped, a different one
needs --replace, which also removes components the new record does not have.
Exports are never written inside a campaign root.
"""
from pathlib import Path
import argparse,json,os,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from lri_spin import Config
from lri_spin.io import read_record,source_hash,_atomic
from lri_spin.validation import validate_result
from lri_spin.campaign import campaign_of,GEN_RE,refuse_campaign_destination,OwnershipError
COMPONENTS=('critical.json','tangent.json','flow.json')
p=argparse.ArgumentParser();p.add_argument('records',nargs='+');p.add_argument('--output-dir',required=True);p.add_argument('--allow-other-source',action='store_true')
p.add_argument('--replace',action='store_true',help='replace an existing export made from a different record');a=p.parse_args()
try:refuse_campaign_destination(a.output_dir)
except OwnershipError as exc:raise SystemExit(f'Refusing: {exc}')

def destination(path):
    source=Path(path).resolve();found=campaign_of(source)
    if found:
        _,rel=found
        if len(rel)==3 and GEN_RE.fullmatch(rel[1]) and rel[2]=='result.json':
            return rel[0],{'campaign_item':rel[0],'generation':int(GEN_RE.fullmatch(rel[1]).group(1))}
    return source.parent.name,{}

def refuse(msg):raise SystemExit(f'Refusing: {msg}')

def check_dest(dest):
 """The destination must stay a plain folder outside every campaign root."""
 if dest.is_symlink():refuse(f'{dest} is a symlink')
 if dest.exists() and not dest.is_dir():refuse(f'{dest} exists and is not a directory')
 for f in COMPONENTS:
  if (dest/f).is_symlink():refuse(f'{dest/f} is a symlink')
 try:refuse_campaign_destination(dest.resolve())
 except OwnershipError as exc:refuse(exc)

def existing_state(dest,env,components):
 """'skip' for an identical export, else the existing component files (refused without --replace)."""
 existing={f:dest/f for f in COMPONENTS if (dest/f).exists()}
 shas=set()
 for f,t in existing.items():
  try:shas.add(json.loads(t.read_text()).get('_record_sha256'))
  except ValueError:shas.add(None)
 if existing and shas=={env['sha256']} and set(existing)=={k+'.json' for k in components}:return 'skip'
 if existing and not a.replace:refuse(f'{dest} holds an export of a different record; use --replace')
 return existing

outdir=Path(a.output_dir)
targets=[destination(p) for p in a.records]
canon=[str((outdir/t[0]).resolve()) for t in targets]
if len(canon)!=len(set(canon)):
 raise ValueError('Duplicate destination folder names; export separately to distinct output roots')
plans=[]
for path,(name,extra) in zip(a.records,targets):
 source=Path(path);env=json.loads(source.read_text());r=read_record(path)
 if env['identity']['source_sha256']!=source_hash() and not a.allow_other_source:raise ValueError('Different solver source')
 components={'critical':r['critical_flow'],'tangent':r['tangent']} if 'critical_flow' in r and 'tangent' in r else {'critical':r['critical_flow']} if 'critical_flow' in r else {'tangent' if 'tangent' in r['method'] else 'flow':r}
 for key,v in components.items():
  validate_result(v,Config(**v['config']),tangent=key=='tangent',observers=v.get('observers',True))
 dest=outdir/name;check_dest(dest)
 if existing_state(dest,env,components)=='skip':print('Unchanged:',dest);continue
 plans.append((dest,env,components,extra))
if not plans:raise SystemExit(0)
# Serialize against other exporters, on any BeeGFS client: an O_EXCL lock file per
# destination (fails closed; a stale lock from a crashed export is removed by hand).
outdir.mkdir(parents=True,exist_ok=True);locks=[]
try:
 for dest,*_ in sorted(plans,key=lambda t:t[0].name):
  lock=outdir/f'.{dest.name}.export.lock'
  try:fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
  except FileExistsError:refuse(f'another export to {dest} is in progress (or {lock} is stale: delete it if no export runs)')
  os.write(fd,f'{os.uname().nodename} {os.getpid()}\n'.encode());os.close(fd);locks.append(lock)
 # Everything is checked again under the locks before the first write.
 work=[]
 for dest,env,components,extra in plans:
  check_dest(dest);state=existing_state(dest,env,components)
  if state=='skip':print('Unchanged:',dest);continue
  work.append((dest,env,components,extra,state))
 for dest,env,components,extra,existing in work:
  dest.mkdir(parents=True,exist_ok=True)
  for key,v in components.items():
   v=dict(v);v['_provenance']={**env['identity'],**extra};v['_record_sha256']=env['sha256']
   _atomic(dest/(key+'.json'),lambda f:f.write(json.dumps(v,indent=2,allow_nan=False).encode()+b'\n'))
  for f,t in existing.items():
   if f[:-5] not in components:os.unlink(t)
finally:
 for lock in locks:
  try:os.unlink(lock)
  except FileNotFoundError:pass
print('Analysis exports saved; do not use them as HPC result/checkpoint records')
