# Stand-in for bin/c6_integrate in orchestration tests (tests/unit_orchestration.py); never a physics result.
# Same command line and output schema as src/c6_integrate.cpp. Per-point values are deterministic functions of
# (seed, replicate, graph, point), so chunked and unchunked executions agree.
# C6_FAKE_LOG=file appends one JSON line per invocation; C6_FAKE_FAIL=1 fails like a native error.
import hashlib,json,os,struct,sys
a=sys.argv[1:]
if len(a)!=11:print('graphs_root gamma net tasks output seed layout rate threads sum_mode grid_or_dash',file=sys.stderr);sys.exit(1)
root,gamma,net,tasks,out,seed,layout,rate,threads,mode,grid=a
if os.environ.get('C6_FAKE_LOG'):
    with open(os.environ['C6_FAKE_LOG'],'a')as f:f.write(json.dumps({'executable':os.path.abspath(sys.argv[0]),'args':a})+'\n')
if os.environ.get('C6_FAKE_FAIL'):print('forced native failure (C6_FAKE_FAIL)',file=sys.stderr);sys.exit(2)
B,dim,bits=struct.unpack('<III',open(net,'rb').read(12))
lines=open(tasks).read().split('\n');magic,L,nt=lines[0].split();L=int(L);K=6-L;rows=[];graphs=set()
if magic!='C6TASKS3D1':sys.exit('invalid task header')
for i in (gamma,)+((grid,)if grid!='-'else()):open(i).close()
for ln in lines[1:1+int(nt)]:
    uid,rep,g,b,e,t=map(int,ln.split())
    if rep>=B or not os.path.exists(f'{root}/L{L}/G{g}.txt'):sys.exit('bad task')
    graphs.add(g);v=[0.0]*(2*(K+1))
    for i in range(b,e):
        h=int.from_bytes(hashlib.sha256(f'{seed}|{rep}|{g}|{i}'.encode()).digest()[:8],'little')/2**64
        for j in range(K+1):v[j]+=(h+j)/t;v[K+1+j]+=(h*h-j)/t
    rows.append({'uid':uid,'rep':rep,'graph':g,'begin':b,'end':e,'total':t,'quad':0,'mp':0,'seconds':0.0,'max_abs':'1','values':[repr(x)for x in v]})
json.dump({'schema':'c6-d3-native-1','dimension':3,'L':L,'seed':int(seed),'layout':int(layout),'bits':bits,'rate':rate,'sum_mode':mode,'long_double_bits':64,'threads':int(threads),'load_seconds':0.0,'integration_seconds':0.0,'graphs_loaded':len(graphs),'rows':rows},open(out,'w'))
