#!/usr/bin/env python3
"""Run one frozen basis-training job after a new-release validation receipt.

The CLI process owns the output claim/lease and checkpoint. Exit codes 73/75
retain their original meaning. Seed files are provenance only: the accepted
scalar theta was frozen into the request, never an eigenvector or a window.
"""
import argparse,json,os,signal,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_dressed.io import digest,source_fingerprint,release_fingerprint,runtime,read_envelope


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True);p.add_argument('--index',type=int,required=True);p.add_argument('--receipt',required=True)
    a=p.parse_args();row=json.loads(Path(a.manifest).read_text());sha=row.pop('sha256',None)
    if sha!=digest(row) or row.get('schema')!='lri-dressed-basis-training-v1':raise ValueError('Training manifest checksum/schema failure')
    if row.get('source_sha256')!=source_fingerprint() or row.get('release_sha256')!=release_fingerprint() or row.get('runtime')!=runtime():
        raise ValueError('Stale training manifest: release/source/runtime mismatch')
    receipt=read_envelope(a.receipt,'validation')['payload']
    if receipt.get('passed') is not True or receipt.get('source_sha256')!=source_fingerprint() or receipt.get('release_sha256')!=release_fingerprint() or receipt.get('runtime')!=runtime():
        raise ValueError('Missing or stale validation receipt')
    if not 0<=a.index<len(row['jobs']):raise ValueError('Training job index out of range')
    job=row['jobs'][a.index];cfg=job['config']
    if cfg['source_sha256']!=source_fingerprint() or cfg['runtime']!=runtime():raise ValueError('Training config source/runtime mismatch')
    if cfg.get('window')!='vacuum' or cfg.get('window_mode')!='consistent' or cfg.get('zero_scale')!=1.:
        raise ValueError('Unsupported training physics')
    from types import SimpleNamespace
    from lri_dressed.basis_training import train_configuration
    options=dict(cfg,backend=cfg['resolved_backend'])
    checked=train_configuration(SimpleNamespace(**options))
    checked['initial_theta']=list(map(float,cfg['initial_theta']))
    if checked!=cfg:raise ValueError('Training manifest contains unsupported or changed numerical fields')
    if not Path(job['output']).is_absolute():raise ValueError('Training output path must be absolute')
    cmd=[sys.executable,'-m','lri_dressed','train-basis','--output',job['output'],'--resume',
         '--threads',str(job['threads']),'--memory-limit-gib',str(job['memory_limit_gib'])]
    for key in ('bath_cut','delta','teacher_nz','keep','osc','basis_tol','teacher_tol','max_sweeps','eig_tol',
                'residual_tol','tuning_tol','ncv','maxiter','max_eig_iter','window_tol','window_maxiter'):
        cmd+=['--'+key.replace('_','-'),str(cfg[key])]
    cmd+=['--backend',cfg['resolved_backend'],'--guess',*map(repr,cfg['initial_theta'])]
    os.environ['PYTHONPATH']=str(ROOT/'src')+os.pathsep+os.environ.get('PYTHONPATH','')
    os.environ['NUMBA_NUM_THREADS']=str(job['threads'])
    for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):os.environ[key]='1'
    signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGUSR1,signal.SIGTERM,signal.SIGINT})
    os.execv(sys.executable,cmd)
if __name__=='__main__':main()
