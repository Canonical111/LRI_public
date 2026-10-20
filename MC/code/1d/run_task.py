#!/usr/bin/env python3
"""Run/resume one immutable task. exec() lets Slurm signals reach the C++ runner."""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ENGINES={'v1':'bin/lri_mc','1d':'bin/lri_mc_1d'}   # per-task 'engine' (default v1 for every campaign prepared before 2026-09-19)

def command(campaign: Path, task_id: int, measurements: int | None = None,
            checkpoint_seconds: float = 600, max_seconds: float = 0) -> list[str]:
    campaign=campaign.resolve()
    manifest=json.loads((campaign/'manifest.json').read_text())
    if not 0<=task_id<len(manifest['tasks']): raise ValueError('task index outside manifest')
    t=manifest['tasks'][task_id]; engine=t.get('engine','v1')
    if engine not in ENGINES: raise ValueError(f'unknown engine {engine!r} in task {task_id}')
    binary=ROOT/ENGINES[engine]
    if not binary.is_file(): raise FileNotFoundError(f'run make first ({binary.name} missing)')
    coupling=campaign/t['coupling_file']; directory=campaign/t['directory']
    if hashlib.sha256(coupling.read_bytes()).hexdigest()!=t['coupling_sha256']:
        raise ValueError('coupling checksum mismatch')
    signature=hashlib.sha256(binary.read_bytes()).hexdigest()
    provenance=directory/'binary.sha256'
    if provenance.exists() and provenance.read_text().strip()!=signature:
        raise ValueError('binary changed; resume with the original binary/standard library or start a new campaign')
    if not provenance.exists(): provenance.write_text(signature+'\n')
    target=measurements or t['measurements']
    status_path=directory/'status.json'
    if measurements is None and status_path.exists():
        target=max(target,json.loads(status_path.read_text())['measurements_target'])
    common=['--beta',repr(t['beta']),'--measurements',str(target),'--warmup',str(t['warmup']),'--seed',str(t['seed']),
            '--init',t['initialization'],'--out',str(directory),'--checkpoint-seconds',str(checkpoint_seconds),'--max-seconds',str(max_seconds)]
    if engine=='v1':
        return [str(binary),'--n',str(t['N']),'--couplings',str(coupling)]+common
    # '1d': the backbone sampler builds the exact periodic kernel from s internally; the coupling file stays as the Hamiltonian record
    # (its hash is verified above). Basic 4-column record = the v1 record (K_active, m2, m4, m2_sample).
    return [str(binary),'--dim','1','--length',str(t['N']),'--s',repr(float(t['s'])),'--sampler','backbone','--record','basic',
            '--core-radius',str(t.get('core_radius',256)),'--near-radius',str(t.get('near_radius',1)),'--batch',str(t.get('batch',0))]+common

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('campaign',type=Path);p.add_argument('--task',type=int,required=True)
    p.add_argument('--measurements',type=int,help='extend to this total count; never add duplicate samples')
    p.add_argument('--checkpoint-seconds',type=float,default=600)
    p.add_argument('--max-seconds',type=float,default=0)
    a=p.parse_args()
    if a.measurements is not None and a.measurements<1: p.error('measurements must be positive')
    cmd=command(a.campaign,a.task,a.measurements,a.checkpoint_seconds,a.max_seconds)
    print('Executing:', ' '.join(cmd),flush=True);os.execv(cmd[0],cmd)
if __name__=='__main__':main()
