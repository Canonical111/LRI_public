"""Dimensionless boundary log jets and restoration of the physical scale.

Only negative powers are needed. At such powers the final rational
functional is determined by the large-variable jet, with no unknown period
constant. Explicit powers of log(epsilon) are restored analytically.
"""
from pathlib import Path
from fractions import Fraction as Q
from math import factorial
from functools import lru_cache
import json,os,hashlib,time,argparse
os.environ.setdefault('R6_ACCEL','1');os.environ.setdefault('R6_NATIVE','1')
import boundary_residue as br
import moving_terminal as mt
import terminal_projection as tp
from hyperlog_core import e,GEN,K
ROOT=Path(__file__).resolve().parent.parent
POWERS=(-2,-1);MAXLOG=8
DEMANDS=tuple((p,m) for p in POWERS for m in range(MAXLOG+1))

def direct_file(path):
    start=time.time();items=br.rr.load(path);total=[Q(0)]*len(DEMANDS)
    for (words,logs),c in items:
        assert not logs and not any(words[:-1])
        w=tuple((Q(0),tp.field_letter(a,4,e)) for a in words[-1])
        v=mt.apply_field(c,mt.canon((w,)),5,4,DEMANDS)
        total=[a+b for a,b in zip(total,v)]
    mt.clear();br.rr.clear()
    return {'source':path.name,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'rows':len(items),'demands':DEMANDS,'values':list(map(str,total)),
        'seconds':time.time()-start,'method':'dimensionless final-variable functional from complete stage3 expression'}

def batch_file(path):
    import finish_boundaries as fb
    fb.DEMANDS=DEMANDS
    src=path.with_suffix('.stage2.jsonl') if path.name.startswith(('f2_','f3_')) else path
    if not src.exists():raise FileNotFoundError(src)
    start=time.time();items=br.rr.load(src)
    values,count=fb.integrate_last_two(items)
    dest=path.with_suffix('.logjets.json')
    result={'source':src.name,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),
        'rows':len(items),'demands':DEMANDS,'values':list(map(str,values)),
        'terminal_terms':count,'seconds':time.time()-start}
    dest.write_text(json.dumps(result,indent=2));mt.clear();fb.aword.cache_clear();br.rr.clear()
    return result

def pad(a):return list(a)+[Q(0)]*(MAXLOG+1-len(a))
def padd(a,b):return [x+y for x,y in zip(pad(a),pad(b))]
def scale(a,c):return [c*x for x in pad(a)]
def shift(a,n):return ([Q(0)]*n+pad(a))[:MAXLOG+1]
def deriv(a):return [i*a[i] for i in range(1,len(a))]+[Q(0)]
def inverse_euler(a,p):
    out=[Q(0)]*(MAXLOG+1);r=pad(a)
    for j in range(MAXLOG+1):
        out=padd(out,scale(r,-Q((-1)**j,p**(j+1))))
        r=deriv(r)
    return out

def restore(B):
    """B dictionaries hold dimensionless full sums, keyed by insertions."""
    out={}
    for p in POWERS:
        base=B['base'][p];v=B['v'][p];d=B['d'][p];vv=B['vv'][p];mixed=B['vd'][p]
        one=padd(padd(v,vv),scale(d,-6))
        two=padd(scale(base,-3),scale(v,-9))
        result=padd(padd(mixed,shift(one,1)),padd(shift(two,2),shift(scale(base,18),3)))
        out[p]={'B':result,'M':inverse_euler(result,p)}
    return out

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--controls',action='store_true');parser.add_argument('--file');a=parser.parse_args()
    if a.controls:
        out=[]
        for kind in ('base','v','d','vv'):
            for face in (1,2,3):
                path=ROOT/'boundary'/f'B6_{kind}_f{face}_stage3.jsonl'
                if not path.exists():continue
                d=direct_file(path);out.append(d);print(kind,face,d['values'],flush=True)
        (ROOT/'boundary_control_logjets.json').write_text(json.dumps(out,indent=2))
    elif a.file:
        print(json.dumps(batch_file(Path(a.file)),indent=2))
