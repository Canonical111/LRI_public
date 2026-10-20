#!/usr/bin/env python3
"""Profile the archived numerical formulas, one thread, without editing evidence."""
from pathlib import Path
import argparse,json,os,struct,subprocess,sys,tempfile
from common import ROOT,cxx_command,dump
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
if out.exists():raise FileExistsError('Use a new profiling directory')
out.mkdir(parents=True)
s=(ROOT/'reference/code/kernel.hpp').read_text()
s=s.replace('using namespace std;','using namespace std;\nstatic thread_local double tld=0,tq=0,tmp=0; static thread_local uint64_t nq=0,nmp=0;')
s=s.replace('ld ratio=abs(v.first)','tld+=omp_get_wtime()-t0;\nld ratio=abs(v.first)')
s=s.replace('bool moderate=true;','double t0=omp_get_wtime();bool moderate=true;')
s=s.replace('auto q=calculate<Q>(g,logx,shift);','double tq0=omp_get_wtime();auto q=calculate<Q>(g,logx,shift);tq+=omp_get_wtime()-tq0;++nq;')
s=s.replace('auto m=calculate<MP>(g,logx,shift);','double tm0=omp_get_wtime();auto m=calculate<MP>(g,logx,shift);tmp+=omp_get_wtime()-tm0;++nmp;')
(out/'kernel.hpp').write_text(s)
s=(ROOT/'reference/code/experiment.cpp').read_text().replace('num_threads(4)','num_threads(1)')
s=s.replace('double elapsed=omp_get_wtime()-start;','double elapsed=omp_get_wtime()-start; cerr<<setprecision(15)<<"PROFILE "<<elapsed<<" "<<tld<<" "<<tq<<" "<<tmp<<" "<<nq<<" "<<nmp<<"\\n";')
(out/'experiment.cpp').write_text(s)
subprocess.run(cxx_command([out/'experiment.cpp'],out/'profile',defines=['SPATIAL_D=2']),check=True)
R=ROOT/'reference';B=R/'baseline_previous';records=[]
for L in range(3,7):
    raw=json.loads((R/f'records/new_b_d2_L{L}.json').read_text());counts=[256 if n else 0 for n in raw['counts_per_replicate']]
    cf=out/f'counts_L{L}.txt';cf.write_text(str(len(counts))+'\n'+''.join(f'{i} {n}\n'for i,n in zip(raw['graph_ids'],counts)))
    b=(R/f'inputs/new_b_d2_L{L}_net.bin').read_bytes();_,dd,bits=struct.unpack('<III',b[:12]);nf=out/f'net_L{L}.bin';nf.write_bytes(struct.pack('<III',2,dd,bits)+b[12:12+2*dd*bits*8])
    rate=B/'inputs/d2_full_rates_c6.txt'if L==6 else B/f'baseline/lri_C6_d2_complete_update/reproduction/mom_rates_c{L}.txt'
    cmd=[out/'profile',B/f'baseline/lri_C6_d3_complete_update/inputs/forest_L{L}.txt',rate,cf,1298972000,nf,out/f'results_L{L}.json',B/'inputs/gamma_d2.txt','rqmc',0,0,1]
    cp=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,check=True);(out/f'profile_L{L}.log').write_text(cp.stderr)
    values=next(line.split()[1:]for line in cp.stderr.splitlines()if line.startswith('PROFILE '))
    records.append(dict(zip(['integration_seconds','ordinary_kernel_seconds','quad_seconds','mp_seconds','quad_calls','mp_calls'],map(float,values)))|{'L':L,'samples':sum(counts)*2})
dump(out/'profile_summary.json',{'records':records,'scope':'Instrumented original formulas, not a precision production calculation.'})
