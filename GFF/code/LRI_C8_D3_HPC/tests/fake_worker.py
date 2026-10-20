# Stand-in for bin/c8d3_gmp (and bin/c8d3_decimal) in the orchestration tests; NEVER a physics result (PLAN F).
# Same command line, --describe and output schema as src/c8d3_integrate.cpp (PLAN C.2, C.3):
#   graphs gamma net tasks output seed layout rate threads sum_mode grid [--mp-check on|off|stride16]
# Task files: 'C8D3TASKS1 <order> <L> <nt>' (order 7 or 8, K = order - L) or 'C7D3TASKS1 <L> <nt>' (read as order 7).
# Every point's contribution is divided by the task's `total`, as c7d3_integrate.cpp:56, so chunked and unchunked
# executions agree and a prefix [0, P) of rows sums to P/total of the prefix mean (A-DES-8).
# Integrands (C8_FAKE_INTEGRAND): hash (default; a splitmix64 hash of seed, replicate, graph, point), const, step:P (1 below
# point P, 0 from P on), ramp (jets as const, |t| = point index + 1). t = v_0 * jac is the class-B tail quantity.
# Seconds per row (the fake cost): C8_FAKE_SPP (seconds per point, default 0.001) or C8_FAKE_SPP_FILE, a JSON map from
# '<rate>:<L>:<graph>' or '<L>:<graph>' to seconds per point (campaign a has rate .8, b .7).
# C8_FAKE_HEAVY='<L>:<graph>,...': those graphs get a Pareto(1.5) tail |t| = u^(-2/3) (the screen and confirmation tests).
# C8_FAKE_FAST=1: one hash per row instead of per point (long design-batch tests; the class-B fields stay well formed).
# C8_FAKE_LOG=file appends one JSON line per invocation; C8_FAKE_FAIL=1 fails like a native error (C8_FAKE_FAIL=graph:G
# only for blocks holding graph G); C8_FAKE_SLEEP=seconds sleeps per invocation (lane tests); C8_FAKE_IGNORE_TERM=1 ignores
# SIGTERM from before the C8_FAKE_LOG line on (a native worker that does not stop in time: the lane's kill fallback, F7).
# C8_FAKE_OMP_EFF=e (default 1): integration_seconds = the sum of the row seconds / (threads x e), so the per-block OpenMP
# efficiency of tools/thru_report.py is e (tests/thru_report_test.py).
import hashlib,json,os,struct,sys,time
a=sys.argv[1:]
BACKEND=('decimal300',300)if 'decimal'in os.path.basename(sys.argv[0])else('gmp350',350)
DESCRIBE={'schema':'c8-d3-build-1','dimension':3,'orders':[7,8],'lmax':8,'kmax':6,'numerics':'exact','diagnostic':False,'boost':'1_77','compiler':'fake',
          'long_double_bits':64,'mp_backend':BACKEND[0],'mp_digits10':BACKEND[1],'mp_max_digits10':BACKEND[1]+22,'openmp':201511,
          'gmp':{'applicable':BACKEND[0]=='gmp350','header_version':'6.2.1','runtime_version':'6.2.1','library':'/fake/libgmp.so.10'}if BACKEND[0]=='gmp350'else{'applicable':False},
          'libraries':[],'tail_top':16,'fake':True}
if a==['--describe']:print(json.dumps(DESCRIBE));sys.exit(0)
# C8_FAKE_RUNTIME_GMP_LIBRARY: the runs (not --describe) report another loaded libgmp (tests/integration_3a.py, A-KER-3).
RUNTIME_GMP=dict(DESCRIBE['gmp'],library=os.environ['C8_FAKE_RUNTIME_GMP_LIBRARY'])if os.environ.get('C8_FAKE_RUNTIME_GMP_LIBRARY')and DESCRIBE['gmp']['applicable']else DESCRIBE['gmp']
mode='off'
if len(a)==13 and a[11]=='--mp-check':mode=a[12];a=a[:11]
if len(a)!=11 or mode not in('on','off','stride16'):print('graphs_root gamma net tasks output seed layout rate threads sum_mode grid_or_dash [--mp-check on|off|stride16]',file=sys.stderr);sys.exit(1)
root,gamma,net,tasks,out,seed,layout,rate,threads,smode,grid=a
if os.environ.get('C8_FAKE_IGNORE_TERM'):import signal;signal.signal(signal.SIGTERM,signal.SIG_IGN)
if os.environ.get('C8_FAKE_LOG'):
    with open(os.environ['C8_FAKE_LOG'],'a')as f:f.write(json.dumps({'executable':os.path.abspath(sys.argv[0]),'args':sys.argv[1:],'pid':os.getpid()})+'\n')
fail=os.environ.get('C8_FAKE_FAIL')
if os.environ.get('C8_FAKE_SLEEP'):time.sleep(float(os.environ['C8_FAKE_SLEEP']))
B,dim,bits=struct.unpack('<III',open(net,'rb').read(12))
lines=open(tasks).read().split('\n');head=lines[0].split()
if head[0]=='C8D3TASKS1'and len(head)==4:order,L,nt=int(head[1]),int(head[2]),int(head[3])
elif head[0]=='C7D3TASKS1'and len(head)==3:order,L,nt=7,int(head[1]),int(head[2])
else:print(f'{tasks}: invalid task header',file=sys.stderr);sys.exit(2)
if order not in(7,8)or not 2<=L<=order:print(f'{tasks}: order {order} or L {L} out of range',file=sys.stderr);sys.exit(2)
rows_g=[l for l in open(gamma).read().split('\n')if l.strip()]
if len(rows_g)!=order-1:print(f'{gamma}: {len(rows_g)} gamma rows, order {order} needs {order-1} (label check)',file=sys.stderr);sys.exit(2)
K=order-L;integrand=os.environ.get('C8_FAKE_INTEGRAND','hash');heavy={tuple(map(int,x.split(':')))for x in os.environ.get('C8_FAKE_HEAVY','').split(',')if x}
spp_map=json.load(open(os.environ['C8_FAKE_SPP_FILE']))if os.environ.get('C8_FAKE_SPP_FILE')else{}
spp_default=float(os.environ.get('C8_FAKE_SPP','0.001'))
def spp(g):return float(spp_map.get(f'{rate}:{L}:{g}',spp_map.get(f'{L}:{g}',spp_default)))
M64=(1<<64)-1
def mix(*xs):
    z=0x9E3779B97F4A7C15
    for x in xs:
        z=(z^(x&M64))*0xBF58476D1CE4E5B9&M64;z=(z^(z>>31))*0x94D049BB133111EB&M64;z^=z>>29
    return z/2**64
rows=[];graphs=set()
for ln in lines[1:1+nt]:
    uid,rep,g,b,e,t=map(int,ln.split())
    if rep>=B or not os.path.exists(f'{root}/L{L}/G{g}.txt'):print(f'bad task {uid}: replicate or graph file',file=sys.stderr);sys.exit(2)
    if fail and (fail=='1'or fail==f'graph:{g}'):print('forced native failure (C8_FAKE_FAIL)',file=sys.stderr);sys.exit(2)
    graphs.add(g);v=[0.0]*(2*(K+1));ts=[];quad=mp=nond=nonm=0;checked=0;hist=[0]*18;mmin=None;alarm=0
    if os.environ.get('C8_FAKE_FAST')=='1':
        h=mix(int(seed),rep,g,b,e);n=e-b
        for j in range(K+1):v[j]=1e-4*(h-.5+j)*n/t;v[K+1+j]=1e-4*(h*h-j)*n/t
        ts=[(1.0-k/64,b+k)for k in range(min(16,n))]
        rows.append({'uid':uid,'rep':rep,'graph':g,'begin':b,'end':e,'total':t,'quad':0,'mp':0,'seconds':spp(g)*n,'max_abs':'1.0','values':[repr(x)for x in v],
                     'tail_top':[repr(p[0])for p in ts],'tail_sum':repr(sum(p[0]for p in ts)+0.5*(n-len(ts))),'tail_argmax':b,'nondirect':0,'nonmoderate':0,
                     'mp_checked':0,'mp_hist':[0]*18,'mp_min_log10':None,'mp_alarm':0})
        continue
    for i in range(b,e):
        h=mix(int(seed),rep,g,i)
        if integrand=='hash':
            base=h-.5;tv=abs(base)+1e-3*(h*h)
            for j in range(K+1):v[j]+=1e-4*(h-.5+j)/t;v[K+1+j]+=1e-4*(h*h-j)/t
        else:
            if integrand=='const'or integrand=='ramp':x=1.0
            elif integrand.startswith('step:'):x=1.0 if i<int(integrand[5:])else 0.0
            else:print(f'unknown C8_FAKE_INTEGRAND {integrand}',file=sys.stderr);sys.exit(2)
            for j in range(K+1):v[j]+=(j+1)*1e-4*x/t;v[K+1+j]+=(j+2)*1e-4*x/t
            tv=float(i+1)if integrand=='ramp'else x
        if (L,g)in heavy:tv=max(h,1e-12)**(-2/3)
        ts.append((tv,i))
        if h<0.1:
            quad+=1
            if h<0.01:
                mp+=1
                if mode=='on'or (mode=='stride16'and i%16==0):
                    checked+=1;lg=-25-int(h*4000);mmin=lg if mmin is None else min(mmin,lg);hist[min(17,max(0,(-lg)//20))]+=1
                    if lg<-320:alarm+=1
        if h>0.97:nond+=1
        if h<0.02:nonm+=1
    ts.sort(key=lambda p:(-p[0],p[1]));top=ts[:16]
    rows.append({'uid':uid,'rep':rep,'graph':g,'begin':b,'end':e,'total':t,'quad':quad,'mp':mp,'seconds':spp(g)*(e-b),'max_abs':repr(max(p[0]for p in ts)),
                 'values':[repr(x)for x in v],'tail_top':[repr(p[0])for p in top],'tail_sum':repr(sum(p[0]for p in ts)),'tail_argmax':top[0][1],
                 'nondirect':nond,'nonmoderate':nonm,'mp_checked':checked,'mp_hist':hist,'mp_min_log10':mmin,'mp_alarm':alarm})
if mode=='off':   # like the native worker (c8d3_integrate.cpp: the MP self-check fields only under on or stride16, C.3)
    for r in rows:
        for k in ('mp_checked','mp_hist','mp_min_log10','mp_alarm'):r.pop(k)
json.dump({'schema':'c8-d3-hpc-native-1','order':order,'L':L,'seed':int(seed),'layout':int(layout),'bits':bits,'rate':rate,'sum_mode':smode,'long_double_bits':64,
           'mp_backend':BACKEND[0],'mp_digits10':BACKEND[1],'numerics':'exact','mp_check':mode,'threads':int(threads),'load_seconds':0.0,
           'integration_seconds':sum(r['seconds']for r in rows)/max(1,int(threads))/float(os.environ.get('C8_FAKE_OMP_EFF','1')),'graphs_loaded':len(graphs),'max_rss_kb':1024,'gmp':RUNTIME_GMP,'libraries':[],'rows':rows},open(out,'w'))
