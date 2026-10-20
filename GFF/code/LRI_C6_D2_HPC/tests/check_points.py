#!/usr/bin/env python3
"""Compare optimized point kernel to independent high-precision Kirchhoff cofactors, by RELATIVE error.

The bridge returns long-double decimal strings, so the scaled (1e-80, 1e-130) configurations, whose values lie far
below the double range, are compared as values. Criterion: relative error <= 1e-9 for every check (set by the 1e-9
promotion threshold); a zero or sign-flipped value fails it, as demonstrated below.

One point is known NOT to meet it, and is the only permitted exception (KNOWN_UNRESOLVED): L6G160 with its scaled edge
variables at 1e-130. Its true value (4.7e-395) lies ~395 digits below its forest terms (A ~ 9), beyond the 300-digit
tier, whose result is rounding noise. For that point the test requires instead: level 2, measured cancellation depth
> 300 digits, |value| <= 1e-290 A, and a value identical to the ORIGINAL code's (reference/code/kernel.hpp, through
its own bridge) at the same point. Any other point failing the relative criterion, or a listed point that is not
encountered, fails the test.
"""
from pathlib import Path
import ctypes,json,math,subprocess,sys,tempfile,time
import mpmath as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'));from common import cxx_command,dump,load
B=ROOT/'reference/baseline_previous/baseline/lri_C6_d3_complete_update'
sys.path.insert(0,str(B/'vendor'));from mom_control_prepare import parse
TOL=mp.mpf('1e-9')
KNOWN_UNRESOLVED={('L6G160',130)}  # beyond the 300-digit tier; value must equal the original code's
ORIGINAL_BRIDGE='''#include "{kernel}"
#include <cstdio>
static vector<Graph> GR;
extern "C" int load_original(const char*k,const char*r){{GR=load(k,r);return int(GR.size());}}
extern "C" int eval_original(int id,const double*lx,int*level,char*out,int size){{for(auto&g:GR)if(g.id==id){{vector<ld>x(g.E);ld fac=0;for(int j=0;j<g.E;j++){{x[j]=lx[j];fac+=D/4.L*x[j];}}auto y=evaluate(g,x,fac);*level=y.level;return std::snprintf(out,size,"%.25Le",y.y/g.Z)<size?0:-2;}}return -1;}}
'''
BB=ROOT/'reference/baseline_previous'
def relerr(val,ref):return abs(val-ref)/abs(ref)

def run():
    records=[];t0=time.time();demo=None;unresolved=[];original=None
    with tempfile.TemporaryDirectory(prefix='c6_points_')as td:
        libpath=Path(td)/'bridge.so';subprocess.run(cxx_command([ROOT/'tests/bridge.cpp'],libpath,shared=True),check=True)
        lib=ctypes.CDLL(str(libpath));lib.load_single.argtypes=[ctypes.c_char_p]
        lib.eval_check.argtypes=[ctypes.c_int,ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int),ctypes.c_char_p,ctypes.c_int];lib.eval_check.restype=ctypes.c_int
        forests=load(B/'inputs/powerfree_forests.json');buf=ctypes.create_string_buffer(128)
        for L in range(3,7):
            _,gs=parse(B/f'inputs/forest_L{L}.txt');errors=[];levels={0:0,1:0,2:0};smallest=None
            for i,g in enumerate(gs):
                assert lib.load_single(str(ROOT/f'inputs/graphs/L{L}/G{g["id"]}.txt').encode())==g['id']
                configs=[0]+([80,130]if i in {0,len(gs)//2,len(gs)-1}else[])
                for scale in configs:
                    mp.mp.dps=70 if scale==0 else 650
                    lx=[math.log((3+(j*11+g['id'])%29)/32)for j in range(2*L)]
                    if scale:
                        for j in range(L):lx[j]-=scale*math.log(10)
                    x=[mp.exp(mp.mpf(v))for v in lx];S=sum(x);cache={}
                    def U(keep,edges):
                        key=tuple(keep)
                        if key in cache:return cache[key]
                        vs=sorted({v for pair in edges for v in pair});ind={v:j for j,v in enumerate(vs)};n=len(vs);a=mp.matrix(n)
                        for ei,(u,v)in zip(keep,edges):
                            u,v=ind[u],ind[v];z=1/x[ei];a[u,u]+=z;a[v,v]+=z;a[u,v]-=z;a[v,u]-=z
                        value=mp.det(a[:n-1,:n-1])*mp.fprod(x[j]for j in keep);cache[key]=value;return value
                    gid=f'L{L}G{g["id"]+1:03d}';ref=mp.mpf(0);A=mp.mpf(0)
                    for fs in forests[gid]:
                        den=mp.fprod(U(*block)for block in fs['blocks']if block[0]);term=sum(x[j]for j in fs['remaining_edges'])/(S*den);ref+=fs['sign']*term;A+=abs(term)
                    pre=mp.exp(mp.mpf('.5')*sum(map(mp.mpf,lx)));ref*=pre;A*=pre
                    a=(ctypes.c_double*len(lx))(*lx);lev=ctypes.c_int();rc=lib.eval_check(0,a,ctypes.byref(lev),buf,len(buf))
                    assert rc==0 and lev.value>=0,(gid,scale,rc)
                    val=mp.mpf(buf.value.decode());err=relerr(val,ref);assert ref!=0
                    if err<TOL:errors.append(err)
                    else:
                        depth=mp.log10(A/abs(ref))
                        assert (gid,scale)in KNOWN_UNRESOLVED,('relative criterion failed',gid,scale,mp.nstr(val,20),mp.nstr(ref,20),mp.nstr(err,5))
                        assert lev.value==2 and depth>300 and abs(val)<=mp.mpf('1e-290')*A,(gid,scale,lev.value,mp.nstr(depth,5))
                        if original is None:
                            src=Path(td)/'bridge_original.cpp';src.write_text(ORIGINAL_BRIDGE.format(kernel=ROOT/'reference/code/kernel.hpp'));olib=Path(td)/'bridge_original.so'
                            subprocess.run(cxx_command([src],olib,defines=['SPATIAL_D=2'],shared=True),check=True);original=ctypes.CDLL(str(olib))
                            original.load_original.argtypes=[ctypes.c_char_p,ctypes.c_char_p];original.eval_original.argtypes=[ctypes.c_int,ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int),ctypes.c_char_p,ctypes.c_int]
                        rate=BB/'inputs/d2_full_rates_c6.txt'if L==6 else BB/f'baseline/lri_C6_d2_complete_update/reproduction/mom_rates_c{L}.txt'
                        assert original.load_original(str(B/f'inputs/forest_L{L}.txt').encode(),str(rate).encode())>0
                        obuf=ctypes.create_string_buffer(128);olev=ctypes.c_int();assert original.eval_original(g['id'],a,ctypes.byref(olev),obuf,len(obuf))==0
                        oval=mp.mpf(obuf.value.decode())
                        assert olev.value==lev.value and oval==val,('new and original differ at a known unresolved point',gid,scale,mp.nstr(val,20),mp.nstr(oval,20))
                        unresolved.append({'graph':gid,'scale':scale,'level':lev.value,'reference':mp.nstr(ref,12),'value':mp.nstr(val,12),'original_code_value':mp.nstr(oval,12),'term_magnitude':mp.nstr(A,6),
                                           'cancellation_digits':mp.nstr(depth,5),'abs_error_over_term_magnitude':mp.nstr(abs(val-ref)/A,5)})
                    levels[lev.value]+=1
                    if scale and (smallest is None or abs(ref)<abs(smallest[1])):smallest=(gid,ref,val,scale)
                    if demo is None and scale:
                        # The metric is not vacuous: a zero or negated value of this tiny reference would fail.
                        assert relerr(-val,ref)>TOL and relerr(mp.mpf(0),ref)>TOL,'criterion would accept a negated or zero value'
                        demo={'graph':gid,'scale':scale,'reference':mp.nstr(ref,12),'relative_error_of_negated_value':mp.nstr(relerr(-val,ref),6),'relative_error_of_zero':mp.nstr(relerr(mp.mpf(0),ref),6)}
            records.append({'L':L,'graphs':len(gs),'checks':sum(levels.values()),'resolved_checks':len(errors),'max_relative_error_resolved':mp.nstr(max(errors),16),'precision_levels':levels,
                            'smallest_scaled_reference':smallest and {'graph':smallest[0],'scale':smallest[3],'reference':mp.nstr(smallest[1],12),'value':mp.nstr(smallest[2],12)}});print(records[-1],flush=True)
    missing=KNOWN_UNRESOLVED-{(u['graph'],u['scale'])for u in unresolved}
    assert not missing,('known unresolved points not encountered',missing)
    return {'status':'passed','reference':'Independent Kirchhoff cofactor determinant with 70 or 650 working digits, not shared monomial masks','metric':'relative error |value-ref|/|ref|','relative_tolerance':'1e-9',
            'strict_relative_criterion_met_by_all_points':False,'known_unresolved_points':unresolved,
            'known_unresolved_rule':'level 2, cancellation > 300 digits, |value| <= 1e-290 A, and value identical to the original code at the same point','nonvacuous_demonstration':demo,'records':records,'seconds':time.time()-t0}
if __name__=='__main__':
    x=run()
    if len(sys.argv)>1:dump(Path(sys.argv[1]),x)  # optional record; the shipped benchmarks/ evidence is never rewritten
    print(json.dumps(x,indent=2))
