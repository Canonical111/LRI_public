#!/usr/bin/env python3
"""Stage 4b #4's proof (= C62d's R3a; PLAN "Performance plan", #4: "quad_differential.cpp: >= 10^9 random pairs per
operation over P1's exponent ranges plus edge lists, bitwise against libgcc"): src/quadfast.hpp's binary128 add, sub and
mul are bit for bit libgcc's __addtf3, __subtf3 and __multf3. Port of LRI_C8_D2_HPC@14d7347 tests/quad_differential.py
(sha256 821e22cd...) to the d=3 names, fixtures and tools; the per-stream count is gated as well (>= 2^30 pairs per
operation and stream at the default 2^32 per operation). Linux x86-64 only (needs __float128); build first with
`make quaddiff`.

  python3 -B tests/quad_differential.py --output FILE [--pairs N] [--threads T] [--seed S] [--scratch DIR]
                                         [--no-ranges] [--ranges-blocks B1,B2,...] [--ranges-graphs G] [--ranges-points P]
                                         [--ubsan-pairs N] [--min-pairs N] [--min-stream-pairs N]

1. Ranges (unless --no-ranges): bin/c8d3_quad_ranges on the first G graphs (default 16) of each fixture block of
   benchmarks/fixtures8 (default: heavy and random, free and power, L8 and L7), P uniform points per graph (default 256)
   through the d=3 kernel.hpp's own sample() at the fixtures' rate: every binary128 +, - and * of calculate_shared<Q>
   (d=3: the products, the segment sums, the numerators, U*sqrt(U), the term sums, the shift path) is observed (operand classes, exponent ranges and histograms, alignment distances, cancellation depths, fast-path share).
   The graphs are staged from the pinned packs and checked against their inventory sha256 (tools/benchkit.py).
2. Kernel windows: the observed biased-exponent range of the normal operands of add/sub and of mul, widened by 512 on
   each side (a factor 2^512) and clipped to the normal range; with --no-ranges the whole normal range.
3. The differential test bin/c8d3_quad_differential: N random pairs per operation (default 2^32, at least --min-pairs,
   default 10^9) over four streams per operation (kernel windows, full range, cancellation or product ties, uniform bit
   patterns) plus the edge lists, each compared with libgcc through volatile operands; then the injection self-test
   (every 4099th fast result corrupted: each operation must report mismatches) and an ASan+UBSan build of the same
   program on --ubsan-pairs pairs per operation (default 2^22) with every edge list.
Gates: zero mismatches in the random streams and the edge lists of every operation (and in the sanitizer run, which
must exit 0), at least --min-pairs random pairs per operation and --min-stream-pairs (default 2^30) in every stream of
every operation, the injection detected for every operation. The JSON
record (with the executables' sha256 and build lines, the commands, the ranges, the windows and the environment) goes
to --output; exit 1 when a gate fails.
"""
from __future__ import annotations
import argparse,concurrent.futures,json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from common import STRICT_CXXFLAGS,digest,dump,host_info,load,utc

BIAS=16383;EMAXN=0x7FFE;WIDEN=512
DIFF=ROOT/'bin'/'c8d3_quad_differential';RANGES=ROOT/'bin'/'c8d3_quad_ranges'
BLOCKS='heavy_free_L8,heavy_power_L8,random_free_L8,random_power_L8,random_free_L7,random_power_L7'
SAN_FLAGS=['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address,undefined','-fno-sanitize-recover=all']

def environment_record()->dict:
    import platform
    cxx=os.environ.get('CXX','g++')
    try:ver=subprocess.run([cxx,'--version'],capture_output=True,text=True,timeout=60).stdout.splitlines()[0]
    except (OSError,subprocess.SubprocessError,IndexError):ver=None
    return {'host':host_info(),'platform':platform.platform(),'python':platform.python_version(),'cxx':cxx,'cxx_version':ver,
            'omp':{k:v for k,v in os.environ.items()if k.startswith('OMP_')},'slurm_job':os.environ.get('SLURM_JOB_ID')}

def log(msg:str)->None:print(f'[{time.strftime("%H:%M:%S")}] {msg}',flush=True)

def exe_record(p:Path)->dict:
    b=p.with_name(p.name+'.build.txt')
    return {'path':str(p.relative_to(ROOT)),'sha256':digest(p),'build':b.read_text().splitlines()if b.exists()else None}

def run_json(cmd:list,timeout:float,env=None)->tuple[dict,float,str]:
    t0=time.time();cp=subprocess.run([str(c)for c in cmd],capture_output=True,text=True,timeout=timeout,env=env)
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
        rec,sec,_=run_json(cmd,timeout=7200)
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

def main()->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--pairs',type=int,default=1<<32);p.add_argument('--min-pairs',type=int,default=10**9);p.add_argument('--min-stream-pairs',type=int,default=1<<30)
    p.add_argument('--threads',type=int,default=len(os.sched_getaffinity(0))if hasattr(os,'sched_getaffinity')else(os.cpu_count()or 1))
    p.add_argument('--seed',type=int,default=20261004);p.add_argument('--scratch',type=Path)
    p.add_argument('--no-ranges',action='store_true');p.add_argument('--ranges-blocks',default=BLOCKS);p.add_argument('--ranges-graphs',type=int,default=16)
    p.add_argument('--ranges-points',type=int,default=256);p.add_argument('--ranges-order',choices=('block','id'),default='block')
    p.add_argument('--ubsan-pairs',type=int,default=1<<22);p.add_argument('--inject',type=int,default=4099)
    a=p.parse_args()
    if a.output.exists():raise SystemExit(f'{a.output} exists; give a new path')
    need=[DIFF]+([]if a.no_ranges else[RANGES])
    missing=[str(x)for x in need if not x.exists()]
    if missing:raise SystemExit(f'missing {", ".join(missing)}: run `make quaddiff` first')
    t0=time.time();base=Path(a.scratch or os.environ.get('SLURM_TMPDIR')or tempfile.gettempdir());base.mkdir(parents=True,exist_ok=True)
    scratch=Path(tempfile.mkdtemp(prefix='c8d3_quaddiff_',dir=base));rec={'schema':'c8-d3-quad-differential-record-1','utc':utc(),
        'executables':{'differential':exe_record(DIFF),**({}if a.no_ranges else{'ranges':exe_record(RANGES)})},'arguments':{k:str(v)for k,v in vars(a).items()}}
    try:
        if a.no_ranges:rr={};wa=wm={'observed':None,'window':[1,EMAXN]}
        else:
            log('ranges');rr=ranges(a,scratch);wa=window(rr,('add','sub'));wm=window(rr,('mul',))
        rec['ranges']={'blocks':rr,'summary':summarize(rr)if rr else None,'add_sub_window':wa,'mul_window':wm,'widen':WIDEN}
        log(f'windows add/sub {wa} mul {wm}')
        cmd=[DIFF,'--pairs',a.pairs,'--seed',a.seed,'--threads',a.threads,'--kernel-add',f'{wa["window"][0]}:{wa["window"][1]}','--kernel-mul',f'{wm["window"][0]}:{wm["window"][1]}','--bench']
        log('differential: '+' '.join(map(str,cmd)));d,sec,_=run_json(cmd,timeout=36000);rec['differential']={'command':[str(c)for c in cmd],'seconds':round(sec,2),'result':d}
        log(f'differential done in {sec:.0f} s')
        icmd=[DIFF,'--pairs',1<<22,'--seed',a.seed+1,'--threads',a.threads,'--inject',a.inject,'--no-edges'];inj,sec,_=run_json(icmd,timeout=3600)
        rec['inject']={'command':[str(c)for c in icmd],'seconds':round(sec,2),'mismatches':{op:v['mismatches']for op,v in inj['random'].items()},
                       'pairs':{op:v['pairs']for op,v in inj['random'].items()}}
        san=scratch/'c8d3_quad_differential_san';cxx=os.environ.get('CXX','g++')
        bcmd=[cxx,*SAN_FLAGS,*STRICT_CXXFLAGS,str(ROOT/'tests/quad_differential.cpp'),'-o',str(san)]
        log('sanitizer build');subprocess.run(bcmd,check=True,timeout=1800)
        scmd=[san,'--pairs',a.ubsan_pairs,'--seed',a.seed+2,'--threads',a.threads,'--kernel-add',f'{wa["window"][0]}:{wa["window"][1]}','--kernel-mul',f'{wm["window"][0]}:{wm["window"][1]}']
        senv={**os.environ,'UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1','ASAN_OPTIONS':'halt_on_error=1'}
        sd,sec,serr=run_json(scmd,timeout=36000,env=senv)
        rec['sanitizer']={'build':[str(c)for c in bcmd],'command':[str(c)for c in scmd],'seconds':round(sec,2),'stderr_tail':serr,
                          'random':{op:{k:v[k]for k in('pairs','fast','mismatches')}for op,v in sd['random'].items()},
                          'edges':{op:{k:v[k]for k in('pairs','fast','mismatches')}for op,v in sd['edges'].items()}}
    finally:
        shutil.rmtree(scratch,ignore_errors=True)
    R=rec['differential']['result'];ops=('add','sub','mul')
    gates={
        'random_pairs_per_op_at_least_min':all(R['random'][op]['pairs']>=a.min_pairs for op in ops),
        'random_pairs_per_stream_at_least_min':all(v['pairs']>=a.min_stream_pairs for op in ops for v in R['random'][op]['streams'].values()),
        'random_zero_mismatches':all(R['random'][op]['mismatches']==0 for op in ops),
        'edges_zero_mismatches':all(R['edges'][op]['mismatches']==0 for op in ops)and all(R['edges'][op]['pairs']>0 for op in ops),
        'first_mismatches_empty':R['first_mismatches']==[],
        'inject_detected_every_op':all(rec['inject']['mismatches'][op]>0 for op in ops),
        'sanitizer_zero_mismatches':all(rec['sanitizer']['random'][op]['mismatches']==0 and rec['sanitizer']['edges'][op]['mismatches']==0 for op in ops)}
    rec['summary']={op:{'random_pairs':R['random'][op]['pairs'],'random_fast':R['random'][op]['fast'],'random_mismatches':R['random'][op]['mismatches'],
                        'edge_pairs':R['edges'][op]['pairs'],'edge_fast':R['edges'][op]['fast'],'edge_mismatches':R['edges'][op]['mismatches'],
                        'edge_categories':{k:v['pairs']for k,v in R['edges'][op]['categories'].items()}}for op in ops}
    rec['gates']=gates;rec['status']='passed'if all(gates.values())else'failed';rec['wall_seconds']=round(time.time()-t0,1);rec['environment']=environment_record()
    dump(a.output,rec);print(json.dumps({'status':rec['status'],'gates':gates,'summary':rec['summary'],'bench':R.get('bench')},indent=1))
    return 0 if rec['status']=='passed'else 1

if __name__=='__main__':sys.exit(main())
