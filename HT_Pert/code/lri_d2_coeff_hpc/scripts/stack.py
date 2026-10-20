#!/usr/bin/env python3
"""Print the numerical software stack as JSON; optionally check it.

--pins            require the tested versions (Python 3.11, numpy 2.3.5, scipy 1.17.0, numba 0.65.1, 80-bit long double)
--match RECEIPT   require the stack recorded in a passing validation receipt (same venv, versions and compiler)
Exit 3 on any mismatch.
"""
from pathlib import Path
import argparse,json,os,platform,subprocess,sys

PINS=dict(python='3.11',numpy='2.3.5',scipy='1.17.0',numba='0.65.1',longdouble_nmant=63,machine='x86_64')
MATCH=('python','prefix','numpy','scipy','numba','longdouble_nmant','machine','cxx','cxx_version')

def stack():
    import numpy,scipy,numba
    cxx=os.environ.get('CXX','c++')
    try:version=subprocess.run([cxx,'--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    except (OSError,subprocess.CalledProcessError,IndexError) as exc:version='unavailable: '+str(exc)
    return dict(python=platform.python_version(),executable=sys.executable,prefix=sys.prefix,numpy=numpy.__version__,
                scipy=scipy.__version__,numba=numba.__version__,longdouble_nmant=int(numpy.finfo(numpy.longdouble).nmant),
                machine=platform.machine(),cxx=cxx,cxx_version=version)

def pin_problems(s):
    out=[]
    if not s['python'].startswith(PINS['python']+'.'):out.append(f"python {s['python']} is not {PINS['python']}.x")
    for k in ('numpy','scipy','numba','longdouble_nmant','machine'):
        if s[k]!=PINS[k]:out.append(f'{k} {s[k]} != {PINS[k]}')
    return out

def match_problems(s,receipt):
    r=json.loads(Path(receipt).read_text())
    if r.get('kind')!='lri-coeff-validation-receipt-v1' or r.get('passed') is not True:return [f'{receipt} is not a passing validation receipt']
    return [f"{k}: {s[k]!r} != validated {r['stack'].get(k)!r}" for k in MATCH if s[k]!=r['stack'].get(k)]

def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--pins',action='store_true');p.add_argument('--match',type=Path);a=p.parse_args()
    s=stack();print(json.dumps(s,indent=1),flush=True)
    bad=(pin_problems(s) if a.pins else [])+(match_problems(s,a.match) if a.match else [])
    for x in bad:print('stack mismatch:',x,file=sys.stderr)
    return 3 if bad else 0
if __name__=='__main__':raise SystemExit(main())
