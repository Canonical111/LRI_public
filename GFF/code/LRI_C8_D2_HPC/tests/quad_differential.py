#!/usr/bin/env python3
"""R3a proof (PLAN "Performance plan", R3a; Stage 4b): src/quadfast.hpp's binary128 add, sub and mul are bit for bit
libgcc's __addtf3, __subtf3 and __multf3. Linux x86-64 only (needs __float128); build first with `make quaddiff`.

  python3 -B tests/quad_differential.py --output FILE [--pairs N] [--threads T] [--seed S] [--scratch DIR]
                                         [--no-ranges] [--ranges-blocks B1,B2,...] [--ranges-graphs G] [--ranges-points P]
                                         [--ubsan-pairs N]
  python3 -B tests/quad_differential.py --check RECORD

1. Ranges (unless --no-ranges): bin/c8d2_quad_ranges on the first G graphs (default 16) of each fixture block of
   benchmarks/fixtures8 (default: heavy and random, free and power, L8 and L7), P uniform points per graph (default 256)
   through kernel.hpp's own sample() at the fixtures' rate: every binary128 +, - and * of calculate_shared<Q> is
   observed (operand classes, exponent ranges and histograms, alignment distances, cancellation depths, fast-path share).
   The graphs are staged from the pinned packs and checked against their inventory sha256 (tools/benchkit.py).
2. Kernel windows: the observed biased-exponent range of the normal operands of add/sub and of mul, widened by 512 on
   each side (a factor 2^512) and clipped to the normal range; with --no-ranges the whole normal range.
3. The differential test bin/c8d2_quad_differential: N random pairs per operation (default 2^32) over four streams per
   operation (kernel windows, full range, cancellation or product ties, uniform bit patterns) plus the edge lists, each
   compared with libgcc through volatile operands; then the injection self-test (every 4099th fast result corrupted:
   each operation must report mismatches) and an ASan+UBSan build of the same program on --ubsan-pairs pairs per
   operation (default 2^22) with every edge list.
Gates (correctness): zero mismatches in the random streams and the edge lists of every operation (and in the sanitizer
run, which must exit 0), the injection detected for every operation. Coverage (the size and scope of the run, W1): at
least MIN_PAIRS = 10^9 random pairs per operation (PLAN R3a; a fixed constant), and the rest below. The JSON record
(with the executables' sha256 and build lines, the commands, the ranges, the windows and the environment) goes to
--output.
W1 (Stage-6 fix round 4, S6A4-01): the acceptance threshold is no longer the caller's (--min-pairs is gone), and
"status":"passed" (R3a acceptance evidence) needs every gate AND the complete coverage that coverage() recomputes from
the record itself: the ranges measured on the six default blocks (>= 16 graphs x 256 points each, block order) and the
kernel windows of the differential run equal to the windows those ranges give; per operation >= MIN_PAIRS random pairs
over all four streams (each non-empty, summing to the total), every edge category non-empty, no mismatch, no first
mismatch; the injection run of INJECT_PAIRS pairs detected for every operation; the sanitizer run on >= MIN_UBSAN_PAIRS
random pairs per operation and on every edge pair. A run whose gates pass with less (--pairs, --ubsan-pairs,
--no-ranges or a ranges subset) is labelled "development run (...)" naming what it lacks. Exit 0: acceptance evidence;
1: a gate failed; 3: a development run. A consumer checks a record with `--check RECORD` (exit 0 only for a record that
says "passed" and whose recomputed coverage is complete) or coverage(record).
"""
from __future__ import annotations
import argparse,concurrent.futures,json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from common import REQUIRED_CXXFLAGS,digest,dump,environment_record,load,omp_child_env,utc

BIAS=16383;EMAXN=0x7FFE;WIDEN=512
MIN_PAIRS=10**9           # PLAN R3a: >= 10^9 random pairs per operation (W1: fixed, not an option)
MIN_UBSAN_PAIRS=1<<22     # the sanitizer run's default pairs per operation
INJECT_PAIRS=1<<22        # the injection self-test's pairs per operation
RANGES_GRAPHS,RANGES_POINTS=16,256  # the ranges' graphs per block and points per graph
OPS=('add','sub','mul')
STREAMS={'add':('kernel','full','cancel','bits'),'sub':('kernel','full','cancel','bits'),'mul':('kernel','full','ties','bits')}
EDGE_CATEGORIES={'add':('specials','align','cancel','carry','boundary','zeros'),'sub':('specials','align','cancel','carry','boundary','zeros'),
                 'mul':('specials','mul_ties','mul_boundary','mul_carry')}
SCHEMA='c8-d2-quad-differential-record-1'
DIFF=ROOT/'bin'/'c8d2_quad_differential';RANGES=ROOT/'bin'/'c8d2_quad_ranges'
BLOCKS='heavy_free_L8,heavy_power_L8,random_free_L8,random_power_L8,random_free_L7,random_power_L7'
SAN_FLAGS=['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address,undefined','-fno-sanitize-recover=all']

def log(msg:str)->None:print(f'[{time.strftime("%H:%M:%S")}] {msg}',flush=True)

def exe_record(p:Path)->dict:
    b=p.with_name(p.name+'.build.txt')
    return {'path':str(p.relative_to(ROOT)),'sha256':digest(p),'build':b.read_text().splitlines()if b.exists()else None}

def run_json(cmd:list,timeout:float,threads:int,env=None)->tuple[dict,float,str]:
    """Run a tool of `threads` OpenMP threads and parse its JSON stdout. R1 (Stage-6 residual): in common.omp_child_env
    (no inherited OMP_*, GOMP_*, KMP_*: an inherited OMP_THREAD_LIMIT=1 would run the threads serially and slow the
    --bench timing), unbound (the ranges jobs run concurrently on one affinity mask)."""
    t0=time.time();cp=subprocess.run([str(c)for c in cmd],capture_output=True,text=True,timeout=timeout,env=omp_child_env(threads,env,bind=False))
    if cp.returncode:raise RuntimeError(f'{cmd[0]} exited {cp.returncode}: {cp.stderr[-2000:]}')
    return json.loads(cp.stdout),time.time()-t0,cp.stderr[-2000:]

def ranges(a,scratch:Path)->dict:
    import benchkit as bk
    m=bk.load_fixtures();I=m['_inputs'];inv=load(I.where('inventory.json'));rate=m['native']['rate'];out={}
    jobs=[]
    for name in a.ranges_blocks.split(','):
        b=bk.block_of(m,name);ids=sorted(b['graphs'])[:a.ranges_graphs]if a.ranges_order=='id'else list(b['graphs'])[:a.ranges_graphs]
        g=scratch/'graphs'/name;st=bk.stage_graphs(I,inv,b['sector'],b['L'],ids,g)
        jobs.append((name,b,ids,g,st))
    per=max(1,a.threads//max(1,len(jobs)))
    def one(j):
        name,b,ids,g,st=j
        cmd=[RANGES,g,b['L'],rate,a.ranges_points,a.seed,per,*ids]
        rec,sec,_=run_json(cmd,timeout=7200,threads=per)
        return name,{'sector':b['sector'],'L':b['L'],'graphs':ids,'staging':st,'seconds':round(sec,2),'threads':per,
                     'command':[str(c)for c in cmd[:7]]+['<ids>'],'result':rec}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs))as pool:
        for name,r in pool.map(one,jobs):out[name]=r;log(f'ranges {name}: {r["result"]["points"]} points, {r["result"]["quad_points"]} binary128, {r["seconds"]} s')
    return out

def window(rr:dict,ops)->dict:
    lo=min((r['result']['ops'][op]['operand_exponent_min']for r in rr.values()for op in ops if r['result']['ops'][op]['n']),default=None)
    hi=max((r['result']['ops'][op]['operand_exponent_max']for r in rr.values()for op in ops if r['result']['ops'][op]['n']),default=None)
    if lo is None or lo<1:return {'observed':None,'window':[1,EMAXN]}
    return {'observed':[lo,hi],'observed_unbiased':[lo-BIAS,hi-BIAS],'window':[max(1,lo-WIDEN),min(EMAXN,hi+WIDEN)]}

def summarize(rr:dict)->dict:
    s={}
    for name,r in rr.items():
        res=r['result'];row={'points':res['points'],'quad_points':res['quad_points'],'mp_points':res['mp_points']}
        for op,v in res['ops'].items():
            n=max(1,v['n']);d=v.get('exponent_difference_hist',{});dn=max(1,sum(d.values()))
            row[op]={'n':v['n'],'fast_fraction':v['fast']/n,'zero_operand':v['zero_operand'],'subnormal_operand':v['subnormal_operand'],'inf_nan_operand':v['inf_nan_operand'],
                     'operand_exponent':[v['operand_exponent_min']-BIAS,v['operand_exponent_max']-BIAS]if v['n']and v['operand_exponent_min']>0 else None,
                     'result_exponent':[v['result_exponent_min']-BIAS,v['result_exponent_max']-BIAS]if v['n']and v['result_exponent_min']>0 else None}
            if op!='mul':
                row[op].update(effective_sub_fraction=v['effective_sub']/n,d_le_3=sum(c for k,c in d.items()if int(k)<=3)/dn,
                               d_le_127=sum(c for k,c in d.items()if int(k)<=127)/dn,d_max_bin=max((int(k)for k in d),default=None),
                               cancellation_shift_max=max((int(k)for k in v.get('cancellation_shift_hist',{})),default=None))
        s[name]=row
    return s

def _n(x)->int|None:
    return x if isinstance(x,int)and not isinstance(x,bool)else None

def coverage(rec:dict)->dict:
    """W1 (Stage-6 fix round 4, S6A4-01): whether a quad_differential record is R3a acceptance evidence, recomputed from
    the record (never from its arguments or its own gates). complete only with: the schema; ranges measured on the six
    default blocks (BLOCKS), each with >= RANGES_GRAPHS graphs and >= RANGES_POINTS points per graph, in block order;
    the add/sub and mul windows recomputed from those ranges (window()) equal to the recorded ones and to the kernel
    windows the differential run used; per operation >= MIN_PAIRS random pairs, the four streams of STREAMS each
    non-empty and summing to the total, zero mismatches, every edge category of EDGE_CATEGORIES non-empty with zero
    mismatches, no first mismatch; the injection run of >= INJECT_PAIRS pairs per operation detected for each; the
    sanitizer run with >= MIN_UBSAN_PAIRS random pairs per operation, every edge pair of the differential run, zero
    mismatches. {'complete': bool, 'why': [...]}."""
    why=[];rec=rec if isinstance(rec,dict)else{}
    if rec.get('schema')!=SCHEMA:why.append(f'schema {rec.get("schema")!r}, not {SCHEMA}')
    rg=rec.get('ranges')if isinstance(rec.get('ranges'),dict)else{};blocks=rg.get('blocks')if isinstance(rg.get('blocks'),dict)else{}
    want=BLOCKS.split(',')
    if sorted(blocks)!=sorted(want):why.append(f'ranges on blocks {sorted(blocks)}, not the six default blocks {want} (--no-ranges or --ranges-blocks)')
    order=(rec.get('arguments')or{}).get('ranges_order','block')
    if order!='block':why.append(f'ranges order {order!r}, not block')
    for name in want:
        b=blocks.get(name)
        if not isinstance(b,dict):continue
        res=b.get('result')if isinstance(b.get('result'),dict)else{};g=len(b.get('graphs')or[]);ppg=_n(res.get('points_per_graph'))
        if g<RANGES_GRAPHS:why.append(f'ranges {name}: {g} graphs, below {RANGES_GRAPHS}')
        if ppg is None or ppg<RANGES_POINTS:why.append(f'ranges {name}: {ppg!r} points per graph, below {RANGES_POINTS}')
        elif _n(res.get('points'))!=g*ppg:why.append(f'ranges {name}: {res.get("points")!r} points, not {g} graphs x {ppg}')
    R=((rec.get('differential')or{}).get('result'))if isinstance(rec.get('differential'),dict)else None
    R=R if isinstance(R,dict)else{}
    if blocks and sorted(blocks)==sorted(want):
        try:
            wa,wm=window(blocks,('add','sub')),window(blocks,('mul',))
            for label,w,key,kkey in (('add/sub',wa,'add_sub_window','kernel_add_window'),('mul',wm,'mul_window','kernel_mul_window')):
                if (rg.get(key)or{}).get('window')!=w['window']:why.append(f'the recorded {label} window {(rg.get(key)or{}).get("window")!r} is not the one its ranges give, {w["window"]}')
                if R.get(kkey)!=w['window']:why.append(f'the differential run used the {label} kernel window {R.get(kkey)!r}, not the ranges\' {w["window"]}')
                if w['observed']is None:why.append(f'no normal {label} operand observed in the ranges')
        except (KeyError,TypeError,ValueError)as e:why.append(f'the ranges cannot be read ({type(e).__name__}: {e})')
    rnd=R.get('random')if isinstance(R.get('random'),dict)else{};edg=R.get('edges')if isinstance(R.get('edges'),dict)else{}
    for op in OPS:
        x=rnd.get(op)if isinstance(rnd.get(op),dict)else{};p=_n(x.get('pairs'))
        if p is None or p<MIN_PAIRS:why.append(f'{op}: {p!r} random pairs, below MIN_PAIRS = {MIN_PAIRS}')
        if x.get('mismatches')!=0:why.append(f'{op}: {x.get("mismatches")!r} random mismatches')
        st=x.get('streams')if isinstance(x.get('streams'),dict)else{}
        if sorted(st)!=sorted(STREAMS[op]):why.append(f'{op}: streams {sorted(st)}, not {list(STREAMS[op])}')
        elif any((_n((st[k]or{}).get('pairs'))or 0)<=0 or (st[k]or{}).get('mismatches')!=0 for k in st)or sum(_n(st[k].get('pairs'))or 0 for k in st)!=p:
            why.append(f'{op}: a random stream is empty, mismatches, or the streams do not sum to the {p!r} pairs')
        e=edg.get(op)if isinstance(edg.get(op),dict)else{};cats=e.get('categories')if isinstance(e.get('categories'),dict)else{}
        if sorted(cats)!=sorted(EDGE_CATEGORIES[op]):why.append(f'{op}: edge categories {sorted(cats)}, not {list(EDGE_CATEGORIES[op])}')
        elif any((_n((cats[k]or{}).get('pairs'))or 0)<=0 for k in cats):why.append(f'{op}: an empty edge category')
        if (_n(e.get('pairs'))or 0)<=0 or e.get('mismatches')!=0:why.append(f'{op}: edge pairs {e.get("pairs")!r}, mismatches {e.get("mismatches")!r}')
    if R.get('first_mismatches')!=[]:why.append(f'first_mismatches {str(R.get("first_mismatches"))[:120]}')
    inj=rec.get('inject')if isinstance(rec.get('inject'),dict)else{}
    for op in OPS:
        if (_n((inj.get('pairs')or{}).get(op))or 0)<INJECT_PAIRS:why.append(f'{op}: injection run of {(inj.get("pairs")or{}).get(op)!r} pairs, below {INJECT_PAIRS}')
        if (_n((inj.get('mismatches')or{}).get(op))or 0)<=0:why.append(f'{op}: the injected corruption was not detected')
    san=rec.get('sanitizer')if isinstance(rec.get('sanitizer'),dict)else{}
    for op in OPS:
        sr=(san.get('random')or{}).get(op)or{};se=(san.get('edges')or{}).get(op)or{}
        if (_n(sr.get('pairs'))or 0)<MIN_UBSAN_PAIRS:why.append(f'{op}: sanitizer run on {sr.get("pairs")!r} random pairs, below {MIN_UBSAN_PAIRS}')
        if se.get('pairs')!=(edg.get(op)or{}).get('pairs'):why.append(f'{op}: sanitizer run on {se.get("pairs")!r} edge pairs, not every edge pair ({(edg.get(op)or{}).get("pairs")!r})')
        if sr.get('mismatches')!=0 or se.get('mismatches')!=0:why.append(f'{op}: sanitizer mismatches {sr.get("mismatches")!r}/{se.get("mismatches")!r}')
    return {'complete':not why,'why':why}

def check(path:Path)->int:
    """--check: 0 for a record that says "passed" and whose recomputed coverage is complete, 1 otherwise."""
    rec=json.loads(Path(path).read_text());cov=coverage(rec);good=rec.get('status')=='passed'and cov['complete']
    print(json.dumps({'record':str(path),'status':rec.get('status'),'acceptance':good,'coverage':cov},indent=1));return 0 if good else 1

def main()->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--output',type=Path);p.add_argument('--pairs',type=int,default=1<<32,help=f'random pairs per operation (acceptance needs at least MIN_PAIRS = {MIN_PAIRS})')
    p.add_argument('--check',type=Path,metavar='RECORD',help='check an existing record: exit 0 only for acceptance evidence (W1)')
    p.add_argument('--threads',type=int,default=len(os.sched_getaffinity(0))if hasattr(os,'sched_getaffinity')else(os.cpu_count()or 1))
    p.add_argument('--seed',type=int,default=20261004);p.add_argument('--scratch',type=Path)
    p.add_argument('--no-ranges',action='store_true');p.add_argument('--ranges-blocks',default=BLOCKS);p.add_argument('--ranges-graphs',type=int,default=16)
    p.add_argument('--ranges-points',type=int,default=256);p.add_argument('--ranges-order',choices=('block','id'),default='block')
    p.add_argument('--ubsan-pairs',type=int,default=MIN_UBSAN_PAIRS);p.add_argument('--inject',type=int,default=4099)
    a=p.parse_args()
    if a.check:return check(a.check)
    if a.output is None:p.error('--output is required (or --check RECORD)')
    if a.output.exists():raise SystemExit(f'{a.output} exists; give a new path')
    need=[DIFF]+([]if a.no_ranges else[RANGES])
    missing=[str(x)for x in need if not x.exists()]
    if missing:raise SystemExit(f'missing {", ".join(missing)}: run `make quaddiff` first')
    t0=time.time();base=Path(a.scratch or os.environ.get('SLURM_TMPDIR')or tempfile.gettempdir());base.mkdir(parents=True,exist_ok=True)
    scratch=Path(tempfile.mkdtemp(prefix='c8d2_quaddiff_',dir=base));rec={'schema':'c8-d2-quad-differential-record-1','utc':utc(),
        'executables':{'differential':exe_record(DIFF),**({}if a.no_ranges else{'ranges':exe_record(RANGES)})},'arguments':{k:str(v)for k,v in vars(a).items()}}
    try:
        if a.no_ranges:rr={};wa=wm={'observed':None,'window':[1,EMAXN]}
        else:
            log('ranges');rr=ranges(a,scratch);wa=window(rr,('add','sub'));wm=window(rr,('mul',))
        rec['ranges']={'blocks':rr,'summary':summarize(rr)if rr else None,'add_sub_window':wa,'mul_window':wm,'widen':WIDEN}
        log(f'windows add/sub {wa} mul {wm}')
        cmd=[DIFF,'--pairs',a.pairs,'--seed',a.seed,'--threads',a.threads,'--kernel-add',f'{wa["window"][0]}:{wa["window"][1]}','--kernel-mul',f'{wm["window"][0]}:{wm["window"][1]}','--bench']
        log('differential: '+' '.join(map(str,cmd)));d,sec,_=run_json(cmd,timeout=36000,threads=a.threads);rec['differential']={'command':[str(c)for c in cmd],'seconds':round(sec,2),'result':d}
        log(f'differential done in {sec:.0f} s')
        icmd=[DIFF,'--pairs',INJECT_PAIRS,'--seed',a.seed+1,'--threads',a.threads,'--inject',a.inject,'--no-edges'];inj,sec,_=run_json(icmd,timeout=3600,threads=a.threads)
        rec['inject']={'command':[str(c)for c in icmd],'seconds':round(sec,2),'mismatches':{op:v['mismatches']for op,v in inj['random'].items()},
                       'pairs':{op:v['pairs']for op,v in inj['random'].items()}}
        san=scratch/'c8d2_quad_differential_san';cxx=os.environ.get('CXX','g++')
        bcmd=[cxx,*SAN_FLAGS,*REQUIRED_CXXFLAGS,str(ROOT/'tests/quad_differential.cpp'),'-o',str(san)]
        log('sanitizer build');subprocess.run(bcmd,check=True,timeout=1800)
        scmd=[san,'--pairs',a.ubsan_pairs,'--seed',a.seed+2,'--threads',a.threads,'--kernel-add',f'{wa["window"][0]}:{wa["window"][1]}','--kernel-mul',f'{wm["window"][0]}:{wm["window"][1]}']
        senv={**os.environ,'UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1','ASAN_OPTIONS':'halt_on_error=1'}
        sd,sec,serr=run_json(scmd,timeout=36000,threads=a.threads,env=senv)
        rec['sanitizer']={'build':[str(c)for c in bcmd],'command':[str(c)for c in scmd],'seconds':round(sec,2),'stderr_tail':serr,
                          'random':{op:{k:v[k]for k in('pairs','fast','mismatches')}for op,v in sd['random'].items()},
                          'edges':{op:{k:v[k]for k in('pairs','fast','mismatches')}for op,v in sd['edges'].items()}}
    finally:
        shutil.rmtree(scratch,ignore_errors=True)
    R=rec['differential']['result'];ops=OPS
    gates={  # correctness; the size of the run (MIN_PAIRS and the rest) is coverage's (W1)
        'random_zero_mismatches':all(R['random'][op]['mismatches']==0 for op in ops),
        'edges_zero_mismatches':all(R['edges'][op]['mismatches']==0 for op in ops)and all(R['edges'][op]['pairs']>0 for op in ops),
        'first_mismatches_empty':R['first_mismatches']==[],
        'inject_detected_every_op':all(rec['inject']['mismatches'][op]>0 for op in ops),
        'sanitizer_zero_mismatches':all(rec['sanitizer']['random'][op]['mismatches']==0 and rec['sanitizer']['edges'][op]['mismatches']==0 for op in ops)}
    rec['summary']={op:{'random_pairs':R['random'][op]['pairs'],'random_fast':R['random'][op]['fast'],'random_mismatches':R['random'][op]['mismatches'],
                        'edge_pairs':R['edges'][op]['pairs'],'edge_fast':R['edges'][op]['fast'],'edge_mismatches':R['edges'][op]['mismatches'],
                        'edge_categories':{k:v['pairs']for k,v in R['edges'][op]['categories'].items()}}for op in ops}
    rec['gates']=gates;rec['min_pairs']=MIN_PAIRS;rec['wall_seconds']=round(time.time()-t0,1);rec['environment']=environment_record()
    rec['coverage']=coverage(json.loads(json.dumps(rec,default=str)))  # W1: judged on the record as written
    rec['status']=('failed'if not all(gates.values())else'passed'if rec['coverage']['complete']
                   else'development run ('+'; '.join(rec['coverage']['why'])[:500]+')')
    dump(a.output,rec);print(json.dumps({'status':rec['status'],'gates':gates,'coverage':rec['coverage'],'summary':rec['summary'],'bench':R.get('bench')},indent=1))
    return 0 if rec['status']=='passed'else 1 if rec['status']=='failed'else 3

if __name__=='__main__':sys.exit(main())
