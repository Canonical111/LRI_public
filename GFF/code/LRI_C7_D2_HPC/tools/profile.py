#!/usr/bin/env python3
"""Instrument the unchanged reference worker on the delivered matched workloads.

Only clocks are inserted. One thread is used so timer overhead is attributable.
This is profiling, not a new physical production campaign.
"""
from pathlib import Path
import argparse,json,subprocess
from common import ROOT,load,dump
from prepare_benchmarks import prepare_benchmarks
prepare_benchmarks()
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
ref=ROOT/'reference/LRI_C7_d2_progress/code'
s=(ref/'kernel.hpp').read_text().replace('#pragma once','#pragma once\n#include <omp.h>\nstatic thread_local double pt_ld=0,pt_q=0,pt_mp=0;')
s=s.replace('auto v=moderate?', 'double pstart=omp_get_wtime();auto v=moderate?').replace('ld ratio=absolute(v.first)','pt_ld+=omp_get_wtime()-pstart;ld ratio=absolute(v.first)')
s=s.replace('auto q=calculate_reference<Q>(g,lx,shift);','pstart=omp_get_wtime();auto q=calculate_reference<Q>(g,lx,shift);pt_q+=omp_get_wtime()-pstart;').replace('auto m=calculate_reference<MP>(g,lx,shift);','pstart=omp_get_wtime();auto m=calculate_reference<MP>(g,lx,shift);pt_mp+=omp_get_wtime()-pstart;')
(out/'kernel.hpp').write_text(s)
s=(ref/'c7d2_integrate.cpp').read_text().replace('double seconds=0;','double seconds=0,ldsec=0,qsec=0,mpsec=0;').replace('double t0=omp_get_wtime();','double t0=omp_get_wtime();pt_ld=pt_q=pt_mp=0;').replace('r.seconds=omp_get_wtime()-t0;','r.seconds=omp_get_wtime()-t0;r.ldsec=pt_ld;r.qsec=pt_q;r.mpsec=pt_mp;')
s=s.replace('std::cerr<<"completed "','double lds=0,qs=0,mps=0;for(auto&r:rows){lds+=r.ldsec;qs+=r.qsec;mps+=r.mpsec;}std::cerr<<"PROFILE "<<std::setprecision(15)<<seconds<<" "<<lds<<" "<<qs<<" "<<mps<<"\\n";std::cerr<<"completed "')
(out/'profile.cpp').write_text(s);exe=out/'profile'
subprocess.run(['g++','-O3','-std=c++17','-fopenmp','-ffp-contract=off','-fno-fast-math',str(out/'profile.cpp'),'-lquadmath','-o',str(exe)],check=True)
records=[]
for sector in ('free','power'):
 for L in (6,7):
  inp=ROOT/'reference'/('LRI_C7_d2_progress'if sector=='free'else'power_mass')/'inputs';b=ROOT/'benchmarks/fixtures';dest=out/f'{sector}_L{L}.json'
  cmd=list(map(str,[exe,inp,ROOT/'inputs/gamma_d2_7.txt',b/f'{sector}_L{L}.net',b/f'{sector}_L{L}.tasks',dest,5461981,0,.8,1,'compensated','-']))
  cp=subprocess.run(cmd,capture_output=True,text=True,check=True);(out/f'{sector}_L{L}.log').write_text(cp.stderr);v=list(map(float,next(l for l in cp.stderr.splitlines()if l.startswith('PROFILE ')).split()[1:]));d=load(dest)
  records.append(dict(sector=sector,L=L,integration_seconds=v[0],ordinary_kernel_seconds=v[1],quad_seconds=v[2],mp_seconds=v[3],quad_calls=sum(r['quad']for r in d['rows']),mp_calls=sum(r['mp']for r in d['rows']),samples=sum(r['end']-r['begin']for r in d['rows']),command=cmd))
dump(out/'profile_summary.json',dict(records=records,scope='Instrumented reference, selected expensive classes; one thread.'))
