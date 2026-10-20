#!/usr/bin/env python3
"""Stage only one planned group's runtime and kernel pack on local scratch.

Optional: not needed for ordinary execution (which already reads only required
pack members). Copying a large pack is worthwhile only when amortized by work.
"""
from pathlib import Path
import argparse,shutil
from common import ROOT,load,checked
from production import verify_base,exe_for
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('destination',type=Path);p.add_argument('--index',type=int,required=True);a=p.parse_args()
m,im=verify_base(a.run.resolve());j=m['jobs'][a.index];cfg=load(a.run/'groups'/j['group']/'config.json');out=a.destination.resolve()
if out.exists():raise FileExistsError('Use an empty staging directory')
for d in ('bin','tools','inputs/packs'):(out/d).mkdir(parents=True,exist_ok=True)
for f in (ROOT/'tools').glob('*.py'):shutil.copy2(f,out/'tools'/f.name)
exe=exe_for(m['backend']);shutil.copy2(exe,out/'bin'/exe.name);checked(out/'bin'/exe.name,m['executable_sha256'])
for name in ('manifest.json','inventory.json','two_loop.json','gamma_d3_7.txt','primitive_reference.json'):
    shutil.copy2(ROOT/'inputs'/name,out/'inputs'/name)
    if name!='manifest.json':checked(out/'inputs'/name,im['sha256'][name])
rel=f'packs/{cfg["sector"]}_L{cfg["L"]}.pack';shutil.copy2(ROOT/'inputs'/rel,out/'inputs'/rel);checked(out/'inputs'/rel,im['sha256'][rel])
print(out)
