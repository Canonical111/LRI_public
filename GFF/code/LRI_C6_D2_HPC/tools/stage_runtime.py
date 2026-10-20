#!/usr/bin/env python3
"""Copy a verified small runtime to node-local storage; leave campaign data shared."""
from pathlib import Path
import argparse,shutil
from common import ROOT,checked,digest,dump,load
p=argparse.ArgumentParser();p.add_argument('destination',type=Path);a=p.parse_args();dest=a.destination.resolve()
if dest.exists():raise FileExistsError('Use a new staging directory')
dest.mkdir(parents=True)
for sub in ('inputs','tools'):
    shutil.copytree(ROOT/sub,dest/sub,ignore=shutil.ignore_patterns('__pycache__'))
(dest/'bin').mkdir();shutil.copy2(ROOT/'bin/c6_integrate',dest/'bin/c6_integrate')
for name,h in load(dest/'inputs/manifest.json')['sha256'].items():checked(dest/'inputs'/name,h)
checked(dest/'bin/c6_integrate',digest(ROOT/'bin/c6_integrate'))
print(dest)
