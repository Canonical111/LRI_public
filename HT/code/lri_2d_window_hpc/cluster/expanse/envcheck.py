"""Environment identity of the running interpreter (F6).

env_id = first 16 hex digits of sha256 over the Python version and the sorted
name==version list of every installed distribution. Uses only the standard library.

Usage: python envcheck.py                 print env_id and the package list (JSON)
       python envcheck.py --expect ID     exit 74 unless the running env has this id
"""
from __future__ import annotations
import argparse,hashlib,json,platform,sys
from importlib import metadata


def packages():
    seen={}
    for d in metadata.distributions():
        name=(d.metadata.get('Name') or '').lower().replace('_','-')
        if name:seen[name]=d.version
    return sorted(f'{k}=={v}' for k,v in seen.items())


def identity():
    pk=packages();text='\n'.join([platform.python_implementation(),platform.python_version(),*pk])
    return {'env_id':hashlib.sha256(text.encode()).hexdigest()[:16],'python':platform.python_version(),
            'prefix':sys.prefix,'packages':pk}


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--expect')
    a=ap.parse_args(argv);ident=identity()
    if a.expect is not None:
        if ident['env_id']!=a.expect:
            print(f"envcheck: environment {ident['env_id']} != expected {a.expect}",file=sys.stderr);return 74
        print(f"envcheck: ok {ident['env_id']}");return 0
    print(json.dumps(ident,indent=1));return 0


if __name__=='__main__':raise SystemExit(main())
