#!/usr/bin/env python3
"""Probe the semantics the campaign relies on, on the production file system (one node):
atomic_save/read round trip (int keys), directory fsync, O_EXCL exclusivity, owner files
refused to a second process and free after release, flock refused to a second process."""
import argparse,json,os,platform,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_c8 import io

def fstype(path):
    best=('',None)
    try:
        for line in Path('/proc/mounts').read_text().splitlines():
            mnt,typ=line.split()[1:3]
            if (str(path)+'/').startswith(mnt.rstrip('/')+'/') and len(mnt)>len(best[0]):best=(mnt,typ)
    except OSError:pass
    return {'mount':best[0],'type':best[1]}

def second(code):
    return subprocess.run([sys.executable,'-c','import sys;sys.path.insert(0,%r)\nfrom lri_c8 import io\n'%str(ROOT/'src')+code]).returncode

ap=argparse.ArgumentParser();ap.add_argument('dir',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args()
d=a.dir/f'probe_{platform.node()}_{os.getpid()}';d.mkdir(parents=True,exist_ok=True)
r={'dir':str(d),'host':platform.node(),**fstype(d.resolve())}
io.atomic_save(d/'probe.json',{8:1,10:2});r['atomic_roundtrip']=io.read(d/'probe.json')=={'8':1,'10':2}
fd=os.open(d,os.O_RDONLY)
try:os.fsync(fd);r['dir_fsync']='ok'
except OSError as e:r['dir_fsync']=f'errno {e.errno} ({e.strerror})'
finally:os.close(fd)
x=d/'excl';os.close(os.open(x,os.O_CREAT|os.O_EXCL|os.O_WRONLY))
try:os.close(os.open(x,os.O_CREAT|os.O_EXCL|os.O_WRONLY));r['o_excl']=False
except FileExistsError:r['o_excl']=True
owner=d/'lane.owner'
token=io.acquire_owner(owner)
r['owner_second_refused']=second('try:\n io.acquire_owner(%r)\nexcept io.ClaimBusy:sys.exit(3)\n'%str(owner))==3
io.release_owner(owner,token);r['owner_released']=not owner.exists()
r['owner_after_release']=second('io.acquire_owner(%r)\n'%str(owner))==0
lock=d/'item.lock'
with io.claim(lock):r['flock_second_refused_same_node']=second('try:\n with io.claim(%r):pass\nexcept io.ClaimBusy:sys.exit(3)\n'%str(lock))==3
r['pass']=all(r[k] is True for k in ('atomic_roundtrip','o_excl','owner_second_refused','owner_released','owner_after_release','flock_second_refused_same_node'))
print(json.dumps(r,indent=1))
if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=1)+'\n')
raise SystemExit(0 if r['pass'] else 1)
