# Stand-in for bin/c8d2_decimal and bin/c8d2_gmp in orchestration tests (tests/unit_orchestration.py, test_pipeline.py,
# merge_scale.py); never a physics result. Same command line, --describe and output schema as src/c8d2_integrate.cpp
# at order 8 (task header 'C8D2TASKS1 <order> <L> <nt>', K = order - L, rows 2(K+1) wide, the class-B tail fields,
# the @FILE rate form with exact coverage and a per-row rate echo); the backend follows the file name. Per-point values
# are deterministic functions of (seed, replicate, graph, point), so chunked and unchunked executions agree.
# Under a rate map (@FILE) the integrand keeps its mean but has twice the per-point variance and costs 1.5x per point
# (A-FLAG-6: a new map changes variance and cost, not the mean).
# C8_FAKE_LOG=file appends one JSON line per invocation (executable path and sha256, arguments, pid); C8_FAKE_FAIL=1
# fails like a native error; C8_FAKE_SLEEP=seconds sleeps before computing; C8_FAKE_HEAVY=g1,g2 gives those graphs a
# Pareto(2) per-point tail (xi = 1/2); C8_FAKE_SECONDS=x scales the reported seconds; C8_FAKE_B3=1 makes campaign b
# (scalar rate above .85) cost 3x per point. C8_FAKE_IGNORE_TERM=1 ignores SIGTERM from before the C8_FAKE_LOG line on (a native
# worker that does not stop in time: the lane's kill fallback, F7).
# Opt-in numerics (Stage 4c): a copy named c8d2_gmp_<profile> reports numerics <profile> (C8_FAKE_NUMERICS overrides
# it), and C8_FAKE_PROFILE_DELTA=x adds x times the point's own value to every point value of such a copy (a stand-in
# numerics change for tests/numerics_flags.py's unit tests); the exact copies ignore it. Such a copy's --describe has
# numerics_params: {"stub":true} per profile without a delta (the Stage-4c stub headers), {"delta":"x"} with one;
# C8_FAKE_DEVELOPMENT=1 adds "development":true to each (a measurement variant such as dd's -DC8_DD_DEVELOPMENT builds).
import hashlib,json,math,os,re,struct,sys
exe=os.path.abspath(sys.argv[0]);gmp='gmp'in os.path.basename(exe)
_prof=re.fullmatch(r'c8d2_gmp_((?:dd|mp256|exp1)(?:\+(?:dd|mp256|exp1))*)',os.path.basename(exe))
NUMERICS=os.environ.get('C8_FAKE_NUMERICS')or(_prof.group(1)if _prof else'exact')
DELTA=float(os.environ.get('C8_FAKE_PROFILE_DELTA','0'))if _prof else 0.
if sys.argv[1:]==['--describe']:
    print(json.dumps({'schema':'c8-d2-build-1','dimension':2,'orders':[7,8],'lmax':8,'kmax':6,'emax':16,'dimmax':31,'numerics':NUMERICS,
                      'diagnostic':os.environ.get('C8_FAKE_DIAGNOSTIC')=='1','tail_top':16,'compiler':'fake','long_double_bits':64,'mp_backend':'gmp350'if gmp else'decimal300',
                      'mp_digits10':350 if gmp else 300,'mp_max_digits10':372 if gmp else 328,'openmp':201511,
                      **({'numerics_params':{p:{**({'delta':repr(DELTA)}if DELTA else{'stub':True}),**({'development':True}if os.environ.get('C8_FAKE_DEVELOPMENT')=='1'else{})}
                                             for p in NUMERICS.split('+')}}if _prof else{})}));sys.exit(0)
a=sys.argv[1:]
if len(a)!=11:print('graphs_root gamma net tasks output seed layout rate threads sum_mode grid_or_dash',file=sys.stderr);sys.exit(1)
root,gamma,net,tasks,out,seed,layout,rate,threads,mode,grid=a
if os.environ.get('C8_FAKE_IGNORE_TERM'):import signal;signal.signal(signal.SIGTERM,signal.SIG_IGN)
if os.environ.get('C8_FAKE_LOG'):
    with open(os.environ['C8_FAKE_LOG'],'a')as f:f.write(json.dumps({'executable':exe,'sha256':hashlib.sha256(open(exe,'rb').read()).hexdigest(),'args':a,'pid':os.getpid()})+'\n')
if os.environ.get('C8_FAKE_FAIL'):print('forced native failure (C8_FAKE_FAIL)',file=sys.stderr);sys.exit(2)
if os.environ.get('C8_FAKE_SLEEP'):import time;time.sleep(float(os.environ['C8_FAKE_SLEEP']))
B,dim,bits=struct.unpack('<III',open(net,'rb').read(12))
lines=open(tasks).read().split('\n');head=lines[0].split()
if len(head)!=4 or head[0]!='C8D2TASKS1':print('invalid task header: expected C8D2TASKS1 <order> <L> <nt>',file=sys.stderr);sys.exit(2)
order,L,nt=map(int,head[1:]);K=order-L
if order not in(7,8)or not 2<=L<=order:print('bad order or L',file=sys.stderr);sys.exit(2)
if dim!=4*L-1:print('bad net header',file=sys.stderr);sys.exit(2)
open(gamma).close()
rows_in=[tuple(map(int,ln.split()))for ln in lines[1:1+nt]]
graphs={r[2]for r in rows_in};rate_of=None
if rate.startswith('@'):
    rate_of={}
    for n,ln in enumerate(open(rate[1:]).read().splitlines(),1):
        f=ln.split()
        if len(f)!=2 or not f[0].isdigit():print(f'rate file line {n}: expected exactly graph rate',file=sys.stderr);sys.exit(2)
        g=int(f[0])
        if g in rate_of:print(f'rate file: duplicate graph {g}',file=sys.stderr);sys.exit(2)
        try:x=float(f[1])
        except ValueError:x=-1
        if not 0<x<=1:print(f'invalid rate for graph {g}',file=sys.stderr);sys.exit(2)
        rate_of[g]=f[1]
    if set(rate_of)!=graphs:print('rate file does not cover exactly the graphs of the task file',file=sys.stderr);sys.exit(2)
heavy={int(x)for x in os.environ.get('C8_FAKE_HEAVY','').split(',')if x.strip()}
scale=float(os.environ.get('C8_FAKE_SECONDS','1'))*(1.5 if rate_of is not None else 1.)*(3. if os.environ.get('C8_FAKE_B3')and rate_of is None and float(rate)>.85 else 1.)
amp=math.sqrt(2.)if rate_of is not None else 1.
rows=[]
for uid,rep,g,b,e,t in rows_in:
    if rep>=B or not os.path.exists(f'{root}/L{L}/G{g}.txt'):print('bad task',file=sys.stderr);sys.exit(2)
    v=[0.0]*(2*(K+1));base=1e-3*((g%7)+1);sig=1e-3*((g%5)+1);top=[];tsum=0.;arg=b;best=-1.
    for i in range(b,e):
        hb=hashlib.sha256(f'{seed}|{rep}|{g}|{i}'.encode()).digest();h=int.from_bytes(hb[:8],'little')/2**64;h2=(int.from_bytes(hb[8:16],'little')+1)/2**64
        x=base+amp*sig*(h-.5);x+=DELTA*x
        tv=abs(x)if g not in heavy else h2**-0.5
        for j in range(K+1):v[j]+=x*(j+1)/t;v[K+1+j]+=x*(j+1)/(6*t)
        tsum+=tv
        if tv>best:best=tv;arg=i
        top.append(tv)
    top=sorted(top,reverse=True)[:16]
    r={'uid':uid,'rep':rep,'graph':g,'begin':b,'end':e,'total':t,'quad':0,'mp':0,'seconds':scale*1e-6*(e-b)*((g%3)+1),'max_abs':'1','values':[repr(x)for x in v],
       'tail_top':[repr(x)for x in top],'tail_sum':repr(tsum),'tail_argmax':arg}
    if rate_of is not None:r['rate']=rate_of[g]
    rows.append(r)
json.dump({'schema':'c8-d2-hpc-native-1','order':order,'L':L,'seed':int(seed),'layout':int(layout),'bits':bits,'rate':'file'if rate_of is not None else rate,'sum_mode':mode,
           'long_double_bits':64,'mp_backend':'gmp350'if gmp else'decimal300','mp_digits10':350 if gmp else 300,'numerics':NUMERICS,
           'threads':int(threads),'load_seconds':0.0,'integration_seconds':scale*1e-6*sum(r[4]-r[3]for r in rows_in)/max(1,int(threads))+1e-9,
           'graphs_loaded':len(graphs),'max_rss_kb':1024,'max_rss_source':'fake','rows':rows},open(out,'w'))
