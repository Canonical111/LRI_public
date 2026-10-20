#!/usr/bin/env python3
"""Build a separate validation input directory for the degree-7 checks; reference/inputs is never modified.

OUT (must not exist) receives copies, never links, of every reference/inputs file; the cw_L*_N*.txt files of
--extra (tools/regenerate_weights.py output); native x86 extended-precision .bin conversions of them for the
original programs (numpy.longdouble, i.e. strtold); and quad_replay_L7_N7.txt, the quad_replay_L7_N3.txt graph
selection. Every converted value is checked exactly: its stored 80-bit encoding must be the round-to-nearest-even
64-bit-significand value of the decimal string (rational arithmetic), cross-checked with mpmath. OUT is assembled
in a temporary sibling directory and renamed into place only after every check passed.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, sys
from fractions import Fraction
from pathlib import Path
import mpmath as mp
ROOT=Path(__file__).resolve().parents[1];BIAS=16383

def pow2(e:int)->Fraction:return Fraction(2**e) if e>=0 else Fraction(1,2**-e)
def binade(q:Fraction)->int:
    """e with 2^63 <= |q|/2^e < 2^64, so 2^e is one unit in the last place of a 64-bit significand."""
    q=abs(q);e=q.numerator.bit_length()-q.denominator.bit_length()-63
    while q>=2**64*pow2(e):e+=1
    while q<2**63*pow2(e):e-=1
    return e
def round64(q:Fraction)->Fraction:
    """Exact correctly rounded (nearest, ties to even) 64-bit-significand value; exponent range checked separately."""
    if q==0:return Fraction(0)
    e=binade(q);return round(q/pow2(e))*pow2(e) # Fraction.__round__ rounds half to even.
def ulps(x:Fraction,c:Fraction)->Fraction:return abs(x-c)/pow2(binade(c)) if c else (Fraction(0) if x==0 else Fraction(10**9))
def decode80(b:bytes)->Fraction:
    """Exact value of one x87 80-bit extended number (little endian: 64-bit significand, then sign+15-bit exponent)."""
    m=int.from_bytes(b[:8],'little');se=int.from_bytes(b[8:10],'little');e=se&0x7fff
    if e==0x7fff:raise ValueError('non-finite long double')
    if e and not m>>63:raise ValueError('unnormal long double')
    v=m*pow2((e or 1)-BIAS-63);return -v if se>>15 else v
def in_range(c:Fraction)->bool:return c==0 or pow2(1-BIAS)<=abs(c)<pow2(BIAS+1) # normal x87 range; weights never approach it.
def round64_mp(x):
    """Round an mpf to 64 significant bits, half to even (working precision must exceed 64 bits)."""
    if not x:return mp.mpf(0)
    m,e=mp.frexp(x);y=mp.ldexp(m,64);f=mp.floor(y);d=y-f
    if d>mp.mpf(.5) or (d==mp.mpf(.5) and int(f)%2):f+=1
    return mp.ldexp(f,e-64)
def parse_weights(p:Path)->tuple[int,int,list[str]]:
    m=re.fullmatch(r'cw_L(\d+)_N(\d+)\.txt',p.name)
    if not m:raise ValueError(f'{p}: not a cw_L*_N*.txt weight file')
    L,N=map(int,m.groups());tok=p.read_text().split()
    if len(tok)<2 or tok[0]!='C7WEIGHTS1' or not tok[1].isdigit() or int(tok[1])!=len(tok)-2:raise ValueError(f'{p}: bad C7WEIGHTS1 header or value count')
    if int(tok[1])!=(L-1)*(2*L+1)*8*(N+1):raise ValueError(f'{p}: {tok[1]} values, layout needs (L-1)(2L+1)*8*(N+1)={(L-1)*(2*L+1)*8*(N+1)}')
    return L,N,tok[2:]
def native_x87()->tuple[bool,str]:
    import numpy as np
    ok=np.dtype(np.longdouble).itemsize==16 and np.finfo(np.longdouble).nmant==63 and sys.byteorder=='little'
    ok=ok and np.array([1],dtype=np.longdouble).tobytes()[:10]==bytes.fromhex('0000000000000080ff3f')
    return ok,f'numpy longdouble itemsize {np.dtype(np.longdouble).itemsize}, nmant {np.finfo(np.longdouble).nmant}, byteorder {sys.byteorder}'
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def check_values(strs:list[str],blob:bytes,back)->dict:
    """Exact and mpmath rounding checks of stored 16-byte records against their decimal strings."""
    import numpy as np
    mp.mp.dps=150;worst=Fraction(0);exact_bad=mp_bad=0 # 150 digits: no double rounding for <=100-digit strings.
    for i,s in enumerate(strs):
        c=round64(Fraction(s));x=decode80(blob[16*i:16*i+10])
        if not in_range(c):raise ValueError(f'value {i} ({s}) outside the normal long-double range')
        u=ulps(x,c);worst=max(worst,u);exact_bad+=u!=0
        r=round64_mp(mp.mpf(s));mp_bad+=not (round64_mp(mp.mpf(np.format_float_scientific(back[i],unique=True)))==r==mp.mpf(x.numerator)/x.denominator)
    return {'values':len(strs),'max_ulp_error':str(worst),'exact_rounding_mismatches':int(exact_bad),'mpmath_rounding_mismatches':int(mp_bad)}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);p.add_argument('--extra',type=Path,required=True,help='directory holding cw_L{L}_N{N}.txt from tools/regenerate_weights.py');a=p.parse_args()
    import numpy as np
    ok,info=native_x87()
    if not ok:raise SystemExit('C7: the original programs read x86 80-bit extended .bin weights; run on x86-64 Linux ('+info+')')
    out=a.out.resolve();src=ROOT/'reference/inputs';extra=a.extra.resolve()
    if out.exists():raise FileExistsError(f'{out} exists; choose a new directory')
    if out==src or src in out.parents:raise ValueError('OUT must lie outside reference/inputs')
    txts=sorted(extra.glob('cw_L*_N*.txt'))
    if not txts:raise FileNotFoundError(f'no cw_L*_N*.txt in {extra}')
    out.parent.mkdir(parents=True,exist_ok=True);tmp=out.parent/f'.{out.name}.tmp{os.getpid()}';tmp.mkdir()
    try:
        copied=0
        for f in sorted(src.iterdir()):
            if f.is_dir():raise ValueError(f'unexpected directory {f}')
            shutil.copy2(f,tmp/f.name);copied+=1 # copy2 follows links: OUT holds real files only.
        created=[];conversions=[]
        for f in txts:
            if (tmp/f.name).exists():raise FileExistsError(f'{f.name} already in reference/inputs')
            shutil.copy2(f,tmp/f.name);created.append(f.name);L,N,strs=parse_weights(tmp/f.name)
            vals=np.array([np.longdouble(s) for s in strs],dtype=np.longdouble);b=tmp/f'cw_L{L}_N{N}.bin';new=not b.exists()
            if new:
                raw=vals.view(np.uint8).reshape(-1,16).copy();raw[:,10:]=0;raw.tofile(str(b));created.append(b.name) # zero padding: reproducible bytes.
            blob=b.read_bytes();back=np.fromfile(str(b),dtype=np.longdouble)
            if len(blob)!=16*len(strs) or back.shape!=vals.shape or not np.array_equal(back,vals):raise ValueError(f'{b.name}: read-back differs from the parsed decimals'+('' if new else ' (existing reference .bin)'))
            r=check_values(strs,blob,back);r.update(txt=f.name,bin=b.name,L=L,N=N,bin_created=new,numpy_readback_equal=True,source_sha256=sha(f))
            if r['exact_rounding_mismatches'] or r['mpmath_rounding_mismatches']:raise ValueError(f'{b.name}: values are not correctly rounded: {r}')
            conversions.append(r);print(('created ' if new else 'verified existing ')+b.name,r['values'],'values, max ulp error',r['max_ulp_error'],flush=True)
        q3=src/'quad_replay_L7_N3.txt';q7=tmp/'quad_replay_L7_N7.txt'
        if q7.exists():raise FileExistsError('quad_replay_L7_N7.txt already in reference/inputs')
        shutil.copy2(q3,q7);created.append(q7.name)
        if q7.read_bytes()!=q3.read_bytes():raise ValueError('quad replay copy differs')
        report={'schema':'c7-validation-inputs-1','reference_inputs':str(src),'extra':str(extra),'copied_reference_files':copied,
                'platform':{'python':sys.version.split()[0],'numpy':np.__version__,'mpmath':mp.__version__,'longdouble':info},
                'rule':'each .bin value is the round-to-nearest-even 64-bit-significand value of its decimal string (checked in exact rational arithmetic and with mpmath at 150 digits); record padding bytes are zero',
                'conversions':conversions,'quad_replay_L7_N7.txt':{'copied_from':q3.name,'identical':True,'sha256':sha(q7)},
                'created_files':{n:sha(tmp/n) for n in created},'all_files':{g.name:sha(g) for g in sorted(tmp.iterdir())},'passed':True}
        (tmp/'validation_inputs.json').write_text(json.dumps(report,indent=2)+'\n');os.rename(tmp,out)
    except BaseException:
        shutil.rmtree(tmp,ignore_errors=True);raise
    print('validation inputs:',out)
if __name__=='__main__':main()
