#!/usr/bin/env python3
"""R3b `dd` (Stage 4c; PLAN A-FLAG-4): Mac-runnable checks of src/numerics/dd.hpp. No kernel build (the kernel needs
binary128): only the header's stage 1 (the double-double arithmetic, which needs nothing but IEEE doubles and fma) is
compiled, with the host's C++ compiler and -ffp-contract=off, and compared with mpmath. The cluster-side accuracy test
(tests/dd_accuracy.cpp, 120-digit reference, the x86-64 build with -mavx2 -mfma) and the F-gates run on Expanse.

  constants   LN2_1 (ln 2 truncated to 42 significant bits), LN2_2, LN2_3 (|ln 2 - sum| < 2^-150), INV_LN2 and the
              1/k! table (hi = RN(1/k!), lo = RN(1/k! - hi)) re-derived from mpmath at 600 bits
  exp_mpmath  exp_dd on 4,000 arguments (|a| <= 300 uniform with random tails, -650 <= a <= 700, small, next to (k + 1/2) ln 2,
              specials) against mpmath: relative error <= 40 u^2 (u^2 = 2^-106); the largest is reported
  ops_exact   add, add_d, mul, mul_d, div, div_d on 3,000 random operand pairs (both signs, cancellations) against exact
              rationals: bounds 3, 2, 6, 2, 11, 4 u^2; two_sum, fast_two_sum and two_prod exact
  sum         sum_positive on positive addends (n = 1 .. 601; the 4-lane path from n = 8): relative error <= (7.5 n + 1)
              u^2 for n < 8, <= (7.5 n + 29) u^2 for n >= 8
  guards      the parameters are fixed: overriding C8_DD_RATIO, C8_DD_CASCADE_LOW, C8_DD_ROUTING or C8_DD_GUARD without
              -DC8_DD_DEVELOPMENT is a compile error, invalid routing/guard values too; params() prints valid JSON
              members with the defaults (1e-20, cascade, 1e-23, products guard, development false)
  make        `make -n gmp NUMERICS=dd` puts -mavx2 -mfma (NX_FLAGS_dd) before the required flags; no default command and
              no other profile has them
  structure   stage 2: every guard failure goes to nx::quad_tier; the ratio failure to nx::quad_tier at or above
              C8_DD_CASCADE_LOW only with C8_DD_ROUTING 1, else nx::mp_tier; an accepted value sets lev 1 and nx::DD
  scripts     the dd development job scripts: bash syntax, #SBATCH account/partition/--mem/-t/--no-requeue/job names
              c8d2-s4c-dd-*, logs under $C8_DATA/logs; the driver admits (h7_admit.py, agent share) before its sbatch
Usage: python3 -B tests/test_dd_profile.py [--output FILE] [--only NAME,...]   (needs mpmath; a C++ compiler for the
compiled checks, which are skipped, and said so, without one)"""
from __future__ import annotations
import argparse,json,math,os,platform,random,re,shlex,shutil,subprocess,sys,tempfile
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DD=ROOT/'src/numerics/dd.hpp';DEV=ROOT/'benchmarks/expanse_2026-10-c8/stage4c/dev_dd/scripts'
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,'status':'passed',**info});print('PASS',name,json.dumps(info)if info else'',flush=True)
def skip(name,why):RESULTS.append({'test':name,'status':'skipped','why':why});print('SKIP',name,why,flush=True)
U2=F(1,2**106)
def hexf(name:str)->float:return float.fromhex(re.search(rf'\b{name} = (-?0x[0-9a-fp.+-]+)',DD.read_text()).group(1))
def cxx()->str|None:
    for c in (os.environ.get('CXX'),'c++','clang++','g++'):
        if c and shutil.which(c):return c
    return None
# the profile's own fma flags on an x86-64 host (dd.hpp refuses x86-64 without them); an arm64 host always has fma
ARCH=['-mavx2','-mfma']if platform.machine().lower()in('x86_64','amd64')else[]
def compile_run(src:str,args=(),defines=())->subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory()as td:
        p=Path(td)/'t.cpp';p.write_text(src);exe=Path(td)/'t'
        cp=subprocess.run([cxx(),'-std=c++17','-O2',*ARCH,'-ffp-contract=off','-fno-fast-math',*defines,str(p),'-o',str(exe)],capture_output=True,text=True,timeout=300)
        if cp.returncode:return cp
        return subprocess.run([str(exe),*args],capture_output=True,text=True,timeout=300)
HEAD='#define C8_NUMERICS\n#define C8_NUMERICS_DD\n#define C8_NX_STAGE 1\n#include "'+str(DD)+'"\n#include <cstdio>\n#include <iostream>\nusing namespace nx::dd;\n'

def test_constants():
    import mpmath as mp
    mp.mp.prec=600
    def fr(x):m,e=mp.mpf(x).man_exp;return F(int(m))*F(2)**int(e)
    ln2=fr(mp.log(2));u=F(1,2**42);L1=F(int(ln2/u))*u
    assert F(hexf('LN2_1'))==L1 and (F(hexf('LN2_1'))/u).denominator==1
    assert hexf('LN2_2')==float(ln2-L1) and hexf('LN2_3')==float(ln2-L1-F(hexf('LN2_2')))
    assert abs(ln2-L1-F(hexf('LN2_2'))-F(hexf('LN2_3')))<F(1,2**150)
    assert hexf('INV_LN2')==float(1/ln2)
    body=DD.read_text().split('INV_FACT[12] = {',1)[1].split('};',1)[0]
    pairs=re.findall(r'\{(-?0x[0-9a-fp.+-]+|0\.0), (-?0x[0-9a-fp.+-]+|0\.0)\}',body);assert len(pairs)==12,pairs
    for k,(h,l) in enumerate(pairs):
        q=F(1,math.factorial(k));H=float.fromhex(h)if h!='0.0'else 0.0;Lo=float.fromhex(l)if l!='0.0'else 0.0
        assert H==float(q)and Lo==float(q-F(H)),(k,h,l)
        assert abs(q-F(H)-F(Lo))<=q*F(1,2**106),k
    ok('constants')

def test_exp_mpmath():
    if not cxx():return skip('exp_mpmath','no C++ compiler')
    import mpmath as mp
    mp.mp.prec=420;rng=random.Random(5)
    args=[0.0,2**-1074,-2**-1074,1e-300,300.0,-300.0,700.0,-650.0,math.log(2)/2,-math.log(2)/2]
    for i in range(4000):
        kind=i%5
        if kind==0:a=rng.uniform(-300,300)
        elif kind==1:a=rng.uniform(-650,700)
        elif kind==2:a=rng.choice((-1,1))*10**rng.uniform(-30,-3)
        else:k=rng.randint(-433,433);a=(k+(0.5 if kind==3 else 0))*math.log(2)+rng.choice((-1,1))*10**rng.uniform(-17,-9)
        args.append(a)
    tails=[0.0]*10+[rng.uniform(-.5,.5)*(math.ulp(a)if a else 0)for a in args[10:]]
    src=HEAD+'int main(){double h,l;while(std::scanf("%la %la",&h,&l)==2){DW e=exp_dd(fast_two_sum(h,l));std::printf("%a %a\\n",e.h,e.l);}}\n'
    with tempfile.TemporaryDirectory()as td:
        p=Path(td)/'t.cpp';p.write_text(src);exe=Path(td)/'t'
        cp=subprocess.run([cxx(),'-std=c++17','-O2',*ARCH,'-ffp-contract=off','-fno-fast-math',str(p),'-o',str(exe)],capture_output=True,text=True,timeout=300);assert cp.returncode==0,cp.stderr[-2000:]
        cp=subprocess.run([str(exe)],input=''.join(f'{a.hex()} {t.hex()}\n'for a,t in zip(args,tails)),capture_output=True,text=True,timeout=300);assert cp.returncode==0
    worst=0.0;u2=mp.mpf(2)**-106
    for (a,t),line in zip(zip(args,tails),cp.stdout.split('\n')):
        h,l=(float.fromhex(x)for x in line.split())
        s=mp.mpf(a)+mp.mpf(t)
        # the normalized argument fast_two_sum(a, t) is exactly a + t
        ref=mp.exp(s);e=float(abs(mp.mpf(h)+mp.mpf(l)-ref)/ref/u2);worst=max(worst,e)
        assert e<=40,(a,t,e)
    ok('exp_mpmath',points=len(args),max_relative_error_u2=round(worst,3))

def test_ops_exact():
    if not cxx():return skip('ops_exact','no C++ compiler')
    rng=random.Random(11)
    def dd(rng):
        h=rng.choice((-1,1))*10**rng.uniform(-30,30);return h,rng.uniform(-.5,.5)*math.ulp(h)
    rows=[]
    for i in range(3000):
        xh,xl=dd(rng);yh,yl=dd(rng)
        if i%4==0:yh=-xh*(1+rng.choice((-1,1))*10**rng.uniform(-16,-1));yl=rng.uniform(-.5,.5)*math.ulp(yh)
        if i%8==1:yh,yl=-xh,-xl*rng.uniform(0,2)
        d=rng.choice((-1,1))*10**rng.uniform(-30,30);rows.append((xh,xl,yh,yl,d))
    src=HEAD+r'''int main(){double a,b,c,e,d;while(std::scanf("%la %la %la %la %la",&a,&b,&c,&e,&d)==5){DW x=fast_two_sum(a,b),y=fast_two_sum(c,e);
DW r[9]={x,y,add(x,y),add_d(x,d),mul(x,y),mul_d(x,d),div(x,y),div_d(x,d),two_prod(a,d)};DW s=two_sum(a,d);
for(auto&z:r)std::printf("%a %a ",z.h,z.l);std::printf("%a %a\n",s.h,s.l);}}'''+'\n'
    with tempfile.TemporaryDirectory()as td:
        p=Path(td)/'t.cpp';p.write_text(src);exe=Path(td)/'t'
        cp=subprocess.run([cxx(),'-std=c++17','-O2',*ARCH,'-ffp-contract=off','-fno-fast-math',str(p),'-o',str(exe)],capture_output=True,text=True,timeout=300);assert cp.returncode==0,cp.stderr[-2000:]
        cp=subprocess.run([str(exe)],input=''.join(' '.join(v.hex()for v in r)+'\n'for r in rows),capture_output=True,text=True,timeout=300);assert cp.returncode==0
    worst={k:F(0)for k in('add','add_d','mul','mul_d','div','div_d')};bound={'add':3,'add_d':2,'mul':6,'mul_d':2,'div':11,'div_d':4}
    for r,line in zip(rows,cp.stdout.split('\n')):
        v=[float.fromhex(z)for z in line.split()];P=lambda i:F(v[2*i])+F(v[2*i+1])
        X,Y,D=P(0),P(1),F(r[4])
        assert P(8)==F(r[0])*D and F(v[18])+F(v[19])==F(r[0])+D   # two_prod, two_sum exact
        for i,(k,ref)in enumerate((('add',X+Y),('add_d',X+D),('mul',X*Y),('mul_d',X*D),('div',X/Y if Y else None),('div_d',X/D)),start=2):
            if ref is None:continue
            e=abs(P(i)-ref)/abs(ref)/U2 if ref else(F(0)if P(i)==0 else F(10**9))
            worst[k]=max(worst[k],e);assert e<=bound[k],(k,r,float(e))
    ok('ops_exact',cases=len(rows),max_u2={k:round(float(v),3)for k,v in worst.items()})

def test_sum():
    if not cxx():return skip('sum','no C++ compiler')
    rng=random.Random(3);cases=[]
    for n in (1,2,7,8,9,11,17,35,64,200,601):
        for prof in range(3):
            P=[]
            for k in range(n):
                h=rng.uniform(0,1)if prof==0 else(10**rng.uniform(-10,0)if prof==1 else math.ldexp(rng.uniform(1,2),-(k%60)))
                P.append((h,rng.uniform(-.5,.5)*math.ulp(h)))
            s0=(0.0,0.0)if prof==0 else(lambda h:(h,rng.uniform(-.5,.5)*math.ulp(h)))(rng.uniform(0,10))
            cases.append((s0,P))
    src=HEAD+r'''#include <vector>
int main(){int n;while(std::scanf("%d",&n)==1){double h,l;std::scanf("%la %la",&h,&l);DW s=fast_two_sum(h,l);std::vector<DW>P(n);std::vector<int>idx(n);
for(int k=0;k<n;++k){std::scanf("%la %la",&h,&l);P[k]=fast_two_sum(h,l);idx[k]=k;}double hi=s.h,lo=s.l;sum_positive(hi,lo,P.data(),idx.data(),0,n);std::printf("%a %a\n",hi,lo);}}'''+'\n'
    inp=''.join(f'{len(P)} {s0[0].hex()} {s0[1].hex()} '+' '.join(f'{h.hex()} {l.hex()}'for h,l in P)+'\n'for s0,P in cases)
    with tempfile.TemporaryDirectory()as td:
        p=Path(td)/'t.cpp';p.write_text(src);exe=Path(td)/'t'
        cp=subprocess.run([cxx(),'-std=c++17','-O2',*ARCH,'-ffp-contract=off','-fno-fast-math',str(p),'-o',str(exe)],capture_output=True,text=True,timeout=300);assert cp.returncode==0,cp.stderr[-2000:]
        cp=subprocess.run([str(exe)],input=inp,capture_output=True,text=True,timeout=300);assert cp.returncode==0
    worst=0.0
    for (s0,P),line in zip(cases,cp.stdout.split('\n')):
        h,l=(float.fromhex(z)for z in line.split());ref=F(s0[0])+F(s0[1])+sum(F(a)+F(b)for a,b in P)
        e=abs(F(h)+F(l)-ref)/ref/U2;n=len(P);assert e<=F(15,2)*n+(1 if n<8 else 29),(n,float(e));worst=max(worst,float(e)/n)
        assert abs(l)<=math.ulp(h)/2   # normalized on return
    ok('sum',cases=len(cases),max_u2_per_addend=round(worst,4))

def test_guards():
    if not cxx():return skip('guards','no C++ compiler')
    src=HEAD+'int main(){params(std::cout);std::cout<<"\\n";}\n'
    cp=compile_run(src);assert cp.returncode==0,cp.stderr[-2000:]
    p=json.loads('{'+cp.stdout.strip()+'}')
    assert p['dd_ratio']=='1e-20'and p['routing']=='cascade'and p['cascade_low']=='1e-23'and p['range']==300 and p['guard']=='products'and p['development']is False,p
    for d in (['-DC8_DD_RATIO=1e-21'],['-DC8_DD_CASCADE_LOW=1e-22'],['-DC8_DD_ROUTING=0'],['-DC8_DD_GUARD=1']):
        cp=compile_run(src,defines=d);assert cp.returncode!=0 and 'parameters are fixed'in cp.stderr,(d,cp.stderr[-500:])
        cp=compile_run(src,defines=[*d,'-DC8_DD_DEVELOPMENT']);assert cp.returncode==0 and json.loads('{'+cp.stdout.strip()+'}')['development']is True,(d,cp.stderr[-500:])
    cp=compile_run(src,defines=['-DC8_DD_DEVELOPMENT','-DC8_DD_ROUTING=0']);assert json.loads('{'+cp.stdout.strip()+'}')['routing']=='direct'
    cp=compile_run(src,defines=['-DC8_DD_PHASE_TIMERS']);assert cp.returncode!=0 and 'development build'in cp.stderr,cp.stderr[-500:]
    for d in (['-DC8_DD_ROUTING=2'],['-DC8_DD_GUARD=3']):
        cp=compile_run(src,defines=[*d,'-DC8_DD_DEVELOPMENT']);assert cp.returncode!=0,d
    ok('guards')

def test_make():
    env={k:v for k,v in os.environ.items()if k not in('CPPFLAGS','CXXFLAGS','LDFLAGS','LDLIBS','OPTFLAGS','NUMERICS','GMP_PREFIX')}
    def dry(*a):
        cp=subprocess.run(['make','-n','-B','-C',str(ROOT),'CXX=g++',*a],capture_output=True,text=True,env=env,timeout=120);assert cp.returncode==0,cp.stderr[-500:]
        return [shlex.split(l)for l in cp.stdout.splitlines()if l.startswith('g++ ')]
    dd=[c for c in dry('gmp','NUMERICS=dd')if '-o'in c];assert len(dd)==1 and dd[0][-1]=='bin/c8d2_gmp_dd',dd
    c=dd[0];i=c.index('-mavx2');assert c[i:i+2]==['-mavx2','-mfma']and i<c.index('-std=c++17')<c.index('-ffp-contract=off')<c.index('-fno-fast-math')<c.index('-DC8_USE_GMP')
    for args in (('gmp',),('decimal',),('gmp','NUMERICS=mp256'),('gmp','NUMERICS=exp1')):
        for c in dry(*args):assert '-mavx2'not in c and '-mfma'not in c,(args,c)
    for c in dry('gmp','NUMERICS=exp1,dd'):
        if '-o'in c:assert c.count('-mavx2')==1 and c[-1]=='bin/c8d2_gmp_dd+exp1'
    ok('make')

def test_structure():
    t=DD.read_text();s2=t.split('#elif C8_NX_STAGE == 2',1)[1]
    impl=re.search(r'inline void tier_impl\(.*?\n\}',s2,re.S).group(0)
    assert 'if (r != ACCEPT) { trace = {r, 0.0}; quad_tier(g, lx, shift, f, lev); return; }'in impl
    assert 'f = to_ld(div(v.val, v.S)); lev = 1; last_tier = nx::DD;'in impl
    assert re.search(r'#if C8_DD_ROUTING\n\s*if \(!\(av < C8_DD_CASCADE_LOW \* v.err\)\) \{ trace = \{RATIO_QUAD, ratio\}; quad_tier\(g, lx, shift, f, lev\); return; \}\n#endif\n\s*trace = \{RATIO_MP, ratio\}; lev = 1; mp_tier\(g, lx, shift, f, lev\);',impl)
    assert 'if (!(av < C8_DD_RATIO * v.err))'in impl   # the binary128 test's form: fail iff |v| < ratio x err
    ev=re.search(r'inline int evaluate_dd\(.*?\n\}',s2,re.S).group(0)
    assert 'fabsl(lx[j] - shift / g.L) > RANGE) return GUARD_RANGE;'in ev and 'constexpr long double RANGE = 300;'in s2
    assert 'constexpr double TINY = 0x1p-900, BIG = 0x1p900;'in s2 and '(p.h >= TINY) & (p.h <= BIG)'in ev
    assert 'std::isfinite(val.h) && std::isfinite(val.l) && std::isfinite(err)'in ev
    ok('structure')

def test_scripts():
    sl={p.name:p.read_text()for p in DEV.glob('*.slurm')};assert sorted(sl)==['dd_dev.slurm','dd_speed.slurm'],sorted(sl)
    for n,t in sl.items():
        assert subprocess.run(['bash','-n',str(DEV/n)]).returncode==0,n
        hdr=[l for l in t.splitlines()if l.startswith('#SBATCH')]
        assert any('-A yun124'in l for l in hdr)and any('--mem='in l for l in hdr)and any(' -t 'in l for l in hdr)and any('--no-requeue'in l for l in hdr),n
        assert any(re.search(r'-J c8d2-s4c-dd-',l)for l in hdr)and any('-o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out'in l for l in hdr),n
        assert 'source "$HOME/c8d2/env_expanse.sh"'in t
    assert '-p shared'in sl['dd_dev.slurm']and '--exclusive'in sl['dd_speed.slurm']and '-t 00:30:00'in sl['dd_speed.slurm']
    d=(DEV/'submit_dd.sh').read_text();assert subprocess.run(['bash','-n',str(DEV/'submit_dd.sh')]).returncode==0
    assert d.count('sbatch --parsable')==1 and d.index('admit "$name" "$part" 1')<d.index('sbatch --parsable')and 'h7_admit.py'in d and 'PFX=c8d2-s4c-$TAGN-'in d and 'TAGN=dd'in d
    assert "ssh -O check expanse 2>&1 | grep -q 'Master running'"in d
    assert subprocess.run([sys.executable,'-c',f'import ast;ast.parse(open({str(DEV/"dd_dev.py")!r}).read())']).returncode==0
    ok('scripts')

TESTS={'constants':test_constants,'exp_mpmath':test_exp_mpmath,'ops_exact':test_ops_exact,'sum':test_sum,'guards':test_guards,'make':test_make,
       'structure':test_structure,'scripts':test_scripts}
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);ap.add_argument('--output',type=Path);ap.add_argument('--only')
    a=ap.parse_args();sel=a.only.split(',')if a.only else list(TESTS);failed=[]
    for n in sel:
        try:TESTS[n]()
        except Exception as e:
            import traceback;traceback.print_exc();failed.append(n);RESULTS.append({'test':n,'status':'failed','error':f'{type(e).__name__}: {e}'})
    rec={'passed':not failed,'tests':len(sel),'failed':failed,'results':RESULTS,'compiler':cxx()}
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps({k:rec[k]for k in('passed','tests','failed')}));sys.exit(0 if not failed else 1)
