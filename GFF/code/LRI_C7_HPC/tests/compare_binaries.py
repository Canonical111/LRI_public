#!/usr/bin/env python3
"""Prove the kernels are bitwise unchanged against a baseline commit (acceptance A2).

Builds git BASELINE:src and the working-tree src with one toolchain command (-O3 -g), runs both on the
validate.py workloads plus thread/tile variants, and requires identical decimal text for every row value,
identical fallback counts and identical row identity. Output headers may differ only by the added "build" key.
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from workloads import files
import toolchain
ROWKEYS=['uid','replicate','graph','begin','end','total','quad_calls','mp_calls','value']
VOLATILE={'preparation_seconds','integration_seconds','profile','rows'} # timings; rows are compared separately.
ADDED={'build'} # the only header key the current source may add (PLAN section 3.3).

def sha(p:Path)->str:return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p:Path)->dict:return json.loads(p.read_text(),parse_float=str,parse_int=str) # exact decimal text, no rounding.
def git(*args)->str:return subprocess.run(['git','-C',str(ROOT),*args],stdout=subprocess.PIPE,check=True,universal_newlines=True).stdout.strip()

def compare(b:dict,c:dict)->dict:
    br={r['uid']:r for r in b['rows']};cr={r['uid']:r for r in c['rows']}
    if len(br)!=len(b['rows']) or len(cr)!=len(c['rows']):raise ValueError('duplicate uid in output')
    bad=sorted(set(br)^set(cr),key=int)+[u for u in sorted(set(br)&set(cr),key=int) if any(br[u].get(k)!=cr[u].get(k) for k in ROWKEYS)]
    keys={'only_baseline':sorted(set(b)-set(c)),'only_current':sorted(set(c)-set(b))}
    header=sorted(k for k in (set(b)&set(c))-VOLATILE if b[k]!=c[k])
    ok=not bad and not header and not keys['only_baseline'] and set(keys['only_current'])<=ADDED and len(br)>0
    return {'rows':len(cr),'differing_rows':len(bad),'first_differing_uids':bad[:10],'header_mismatches':header,'key_differences':keys,'passed':ok}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',default='c21b9e8');p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
    if out.exists() and any(out.iterdir()):raise FileExistsError('Use an empty or new output directory: '+str(out))
    try:commit=git('rev-parse','--verify',a.baseline+'^{commit}')
    except (OSError,subprocess.CalledProcessError):raise SystemExit(f'C7: {ROOT} is not a git checkout containing {a.baseline}; copy the package with its .git directory')
    for d in ('baseline','bin','runs','work'):(out/d).mkdir(parents=True,exist_ok=True)
    tar=subprocess.run(['git','-C',str(ROOT),'archive','--format=tar',commit,'src'],stdout=subprocess.PIPE,check=True).stdout
    subprocess.run(['tar','-x','-C',str(out/'baseline')],input=tar,check=True)
    exe={'baseline':out/'bin/c7_baseline','current':out/'bin/c7_current'};src={'baseline':out/'baseline/src/c7_integrate.cpp','current':ROOT/'src/c7_integrate.cpp'};builds={}
    for tag in exe:
        cmd=toolchain.compile_cmd([src[tag]],exe[tag],opt=['-O3','-g'])
        with (out/f'build_{tag}.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
        if r.returncode:raise SystemExit(f'C7: {tag} build failed; see {out}/build_{tag}.log')
        builds[tag]={'command':cmd,'sha256':sha(exe[tag]),'sources':{q.name:sha(q) for q in sorted(src[tag].parent.glob('*.[ch]pp'))}}
    inputs=ROOT/'reference/inputs';work=[] # (name, workload, L, mode, threads, degree, tile)
    for L in (5,6,7):
        work.append((f'qmc_L{L}',files(out/f'work/qmc{L}',inputs,L,'qmc',256,2,6),L,'qmc',1,3,128))
        wp=files(out/f'work/power{L}',inputs,L,'power',2,2,6)
        for N in (1,3,5,6):work.append((f'power_L{L}_N{N}',wp,L,'power',1,N,128))
    ws=files(out/'work/schedule',inputs,7,'qmc',256,2,6)
    for nt in (1,2,4):work.append((f'qmc_L7_schedule_t{nt}',ws,7,'qmc',nt,3,128))
    wt=files(out/'work/tiles',inputs,7,'power',2,2,4)
    for tile,nt in [(128,1),(1,1),(7,2),(512,4)]:work.append((f'power_L7_N3_tile{tile}_t{nt}',wt,7,'power',nt,3,tile))
    work.append(('power_L7_N6_tile7_t2',wt,7,'power',2,6,7))
    results=[];passed=True
    for name,w,L,mode,nt,N,tile in work:
        docs={}
        for tag in exe:
            dest=out/'runs'/f'{name}_{tag}.json' # the same command line as tests/validate.py newcmd().
            cmd=[exe[tag],'--mode',mode,'--inputs',inputs,'--L',L,'--tasks',w['tasks'],'--seed',41927510,'--rate','.8','--output',dest,'--threads',nt,'--tile',tile]+(['--net',w['net']] if mode=='qmc' else ['--degree',N])
            with dest.with_suffix('.log').open('w') as f:r=subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,OMP_NUM_THREADS=str(nt),OPENBLAS_NUM_THREADS='1'))
            if r.returncode:raise SystemExit(f'C7: {tag} run {name} failed with exit {r.returncode}; see {dest.with_suffix(".log")}')
            docs[tag]=load(dest)
        c=compare(docs['baseline'],docs['current']);c.update(name=name,mode=mode,L=L,degree=None if mode=='qmc' else N,threads=nt,tile=tile);results.append(c);passed&=c['passed']
        print('PASS' if c['passed'] else 'FAIL',name,'rows',c['rows'],'differing_rows',c['differing_rows'],*(['header',c['header_mismatches']] if c['header_mismatches'] else []),flush=True)
    report={'baseline':a.baseline,'baseline_commit':commit,'current_head':git('rev-parse','HEAD'),'current_src_dirty':bool(git('status','--porcelain','--','src')),'src_diff_stat':git('diff','--stat',commit,'--','src'),
            'compiler':toolchain.compiler_version(),'builds':builds,'inputs':str(inputs),'criterion':'identical decimal text of every value, quad_calls, mp_calls and uid/replicate/graph/begin/end/total per uid; header keys equal except timings and the added build key',
            'workloads':results,'total_rows':sum(r['rows'] for r in results),'total_differing_rows':sum(r['differing_rows'] for r in results),'passed':passed}
    (out/'compare.json').write_text(json.dumps(report,indent=2)+'\n')
    print(('ALL IDENTICAL: ' if passed else 'DIFFERENCES FOUND: ')+str(out/'compare.json'));sys.exit(0 if passed else 1)
if __name__=='__main__':main()
