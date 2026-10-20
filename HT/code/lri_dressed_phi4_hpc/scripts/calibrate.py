#!/usr/bin/env python3
"""Measure wall time and peak RSS of single-delta tuning solves through the real CLI.

Each spec runs `python -m lri_dressed run` in its own process (fresh output directory, seeded
from --seed-dir), up to --concurrent at once so that packed-node contention is included.
Writes calibration.json, which make_campaign.py --pack reads for per-item threads/memory/time.
"""
import argparse,itertools,json,os,subprocess,sys,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_dressed.io import atomic_json,read_envelope,source_fingerprint,release_fingerprint,runtime


def run(spec,a):
    N,backend,threads,window,delta=spec;win,mode=(window.split(':')+[None])[:2] if window!='none' else ('none',None)
    basis=a.basis_entries.get(delta)
    sid=f'N{N}_{backend}_t{threads}_{window.replace(":","-")}_x{delta:.8f}';sid+=('_basis'+basis[1]['sha256'][:12] if basis else '');out=Path(a.workdir)/sid
    cmd=[sys.executable,'-m','lri_dressed','run','--bath-cut',str(N),'--nz',str(a.nz),'--osc',str(a.osc),'--backend',backend,
         '--deltas',repr(delta),'--threads',str(threads),'--output-dir',str(out),'--seed-dir',a.seed_dir,'--window',win]
    if mode:cmd+=['--window-mode',mode]
    if basis:cmd+=['--local-basis',basis[0],'--local-basis-sha256',basis[1]['sha256']]
    env=dict(os.environ,NUMBA_NUM_THREADS=str(threads),OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1')
    t=time.perf_counter();p=subprocess.run(cmd,env=env,capture_output=True,text=True);wall=time.perf_counter()-t
    rec={'bath_cut':N,'nz':a.nz,'osc':a.osc,'backend':backend,'window':win,'window_mode':mode,'threads':threads,'delta':delta,
         'seconds':wall,'returncode':p.returncode}
    if basis:rec['local_basis_sha256']=basis[1]['sha256']
    if p.returncode==0:
        res=read_envelope(next(out.glob('*.json')),'result')['payload']
        rec.update(solve_seconds=res['seconds'],peak_rss_gib=res['execution']['peak_rss_mib']/1024,
            spectral_evaluations=res['spectral_evaluations'],matvec_count=res['matvec_count'],dimension=res['dimension'],
            Delta_thermal=res['Delta_thermal'],window_seconds=(res.get('window_correction') or {}).get('cumulative_seconds'))
    else:rec['stderr_tail']=p.stderr[-1500:]
    print(json.dumps({k:rec.get(k) for k in ('bath_cut','backend','threads','window','window_mode','delta','seconds','peak_rss_gib','returncode')}),flush=True)
    return rec


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cuts',type=int,nargs='+',required=True);ap.add_argument('--backends',nargs='+',default=['auto'])
    ap.add_argument('--threads',type=int,nargs='+',default=[1]);ap.add_argument('--windows',nargs='+',default=['none'])
    ap.add_argument('--deltas',type=float,nargs='+',default=[.1]);ap.add_argument('--nz',type=int,default=24);ap.add_argument('--osc',type=int,default=192)
    ap.add_argument('--basis-index');ap.add_argument('--seed-dir',default=str(ROOT/'inputs'));ap.add_argument('--concurrent',type=int,default=1)
    ap.add_argument('--workdir',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    a.basis_entries={}
    if a.basis_index:
        from lri_dressed.local_basis import read_basis_index,for_configuration
        a.basis_entries=read_basis_index(a.basis_index)
        if a.windows!=['vacuum:consistent']:raise ValueError('Density calibration uses --windows vacuum:consistent')
        for d in a.deltas:
            if d not in a.basis_entries:raise ValueError(f'No basis at delta {d}')
            for_configuration(a.basis_entries[d][1],delta=d,nz=a.nz,osc=a.osc,window='vacuum',window_mode='consistent')
    specs=[]
    for N,b,t,w,d in itertools.product(a.cuts,a.backends,a.threads,a.windows,a.deltas):
        specs.append((N,('tensor' if N<=18 else 'ladder') if b=='auto' else b,t,w,d))
    specs.sort(key=lambda s:-s[0])
    with ThreadPoolExecutor(a.concurrent) as ex:records=list(ex.map(lambda s:run(s,a),specs))
    atomic_json(a.output,{'schema':'lri-dressed-calibration-v1','host':os.uname().nodename,'concurrent':a.concurrent,
        'release_sha256':release_fingerprint(),'source_sha256':source_fingerprint(),'runtime':runtime(),
        'records':[r for r in records if r['returncode']==0],'failures':[r for r in records if r['returncode']!=0]})
    raise SystemExit(1 if any(r['returncode'] for r in records) else 0)

if __name__=='__main__':main()
