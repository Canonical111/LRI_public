#!/usr/bin/env python3
"""Locate a retained historical input/program by filename or path fragment."""
from pathlib import Path
import argparse,json
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('query');p.add_argument('--limit',type=int,default=30);a=p.parse_args()
rows=json.loads((ROOT/'reproduction/layout.json').read_text())['files'];hits=[r for r in rows if a.query.lower() in r['path'].lower()]
for r in hits[:a.limit]:print(r['path']+'\n  -> '+r['stored'])
print(f'{len(hits)} matching logical paths; {min(len(hits),a.limit)} displayed.')
