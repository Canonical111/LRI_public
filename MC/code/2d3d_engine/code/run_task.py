#!/usr/bin/env python3
"""Run/resume one immutable task. exec() lets Slurm signals reach the C++ runner."""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def command(campaign: Path, task_id: int, measurements: int | None = None,
            checkpoint_seconds: float = 600, max_seconds: float = 0) -> list[str]:
    campaign=campaign.resolve()
    manifest=json.loads((campaign/'manifest.json').read_text())
    if not 0<=task_id<len(manifest['tasks']): raise ValueError('task index outside manifest')
    t=manifest['tasks'][task_id]; binary=ROOT/'bin'/('lri_mt' if t.get('rng','xoshiro')=='mt' else 'lri_mc')
    if not binary.is_file(): raise FileNotFoundError('run make first')
    coupling=campaign/t['couplings']; directory=campaign/t['directory']
    if t.get('coupling_sha256') and hashlib.sha256(coupling.read_bytes()).hexdigest()!=t['coupling_sha256']:
        raise ValueError('coupling checksum mismatch')
    signature=hashlib.sha256(binary.read_bytes()).hexdigest()
    provenance=directory/'binary.sha256'
    if provenance.exists() and provenance.read_text().strip()!=signature:
        raise ValueError('binary changed; resume with the original binary/standard library or start a new campaign')
    if not provenance.exists(): provenance.write_text(signature+'\n')
    target=measurements if measurements is not None else t['measurements']
    status_path=directory/'status.json'
    if measurements is None and status_path.exists():
        target=max(target,json.loads(status_path.read_text())['measurements_target'])
    return [str(binary),'--dim',str(t['d']),'--length',str(t['L']),'--beta',repr(t['beta']),
        '--couplings',str(coupling),'--s',str(t['s']),'--sampler',t.get('sampler','hybrid'),
        '--record',t.get('record','extended'),'--core-radius',str(t.get('core_radius',16)),
        '--near-radius',str(t.get('near_radius',1)),'--nn-extra',str(t.get('nn_extra',0)),'--measurements',str(target),
        '--warmup',str(t['warmup']),'--seed',str(t['seed']),'--init',t['initialization'],
        '--out',str(directory),'--checkpoint-seconds',str(checkpoint_seconds),'--max-seconds',str(max_seconds)]

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
