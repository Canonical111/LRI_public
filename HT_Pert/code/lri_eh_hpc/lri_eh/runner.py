from __future__ import annotations
import json,os,resource,time,traceback
from pathlib import Path
from .runtime import (claim,config,load_checkpoint,atomic_json,seal,validate_result,verify_seal,
                      environment,event,StopFlag,AcceptanceError,Preempted)


def paths(root,cutoff,degree):
    stem=f'vacuum_delta_L{cutoff}_d{degree}'
    root=Path(root)
    return {k:root/sub/(stem+ext) for k,sub,ext in (
        ('result','accepted','.json'),('checkpoint','checkpoints','.json'),('claim','claims','.lock'),
        ('attempts','attempts','.json'),('journal','events','.jsonl'))}


def run(cutoff,degree,output_dir,threads=4,memory_limit_gib=None,resume=False,max_attempts=3):
    """One solver item. Caller must not bypass acceptance when exporting/reusing."""
    if cutoff<4 or cutoff%2 or degree not in (4,5,6,7):raise ValueError('even cutoff>=4; degree=4,5,6,7')
    if threads<1 or max_attempts<1:raise ValueError('threads and max_attempts must be positive')
    if memory_limit_gib is not None and memory_limit_gib<=0:raise ValueError('positive memory budget required')
    # Distinct cutoffs parallelize across Slurm tasks/nodes; do not accidentally
    # run one identical solver per MPI rank with full arrays on every rank.
    for k in ('OMPI_COMM_WORLD_SIZE','PMI_SIZE','PMIX_SIZE'):
        if int(os.environ.get(k,'1'))>1:raise RuntimeError('Correction driver is one process per item; use a lane/job array, not mpirun')
    from numba import set_num_threads
    set_num_threads(threads)
    cfg=config(cutoff,degree);p=paths(output_dir,cutoff,degree)
    with claim(p['claim']):
        if p['result'].exists():
            if not resume:raise FileExistsError(p['result'])
            result=validate_result(json.loads(p['result'].read_text()),cfg)
            event(p['journal'],event='accepted_reuse');return result
        if p['checkpoint'].exists() and not resume:raise FileExistsError('Checkpoint exists; use --resume or a new directory')
        cp=load_checkpoint(p['checkpoint'],cfg) if resume else {}
        attempt=0
        if p['attempts'].exists():
            record=json.loads(p['attempts'].read_text());verify_seal(record)
            if record['config']!=cfg:raise AcceptanceError('Attempt journal source/config mismatch')
            attempt=record['count']
            if record.get('terminal') in ('validation_failure','exception'):
                raise AcceptanceError('Previous deterministic failure; inspect it and use a new reviewed directory')
        if attempt>=max_attempts:raise RuntimeError('Attempt budget exhausted; inspect events before explicitly increasing --max-attempts')
        attempt+=1
        attempt_obj=dict(config=cfg,count=attempt,terminal=None)
        atomic_json(p['attempts'],seal(attempt_obj))
        event(p['journal'],event='start',attempt=attempt,config=cfg,environment=environment())
        start=time.perf_counter()
        try:
            with StopFlag() as stop:
                def phase(name):
                    stop.check();event(p['journal'],event='phase',name=name,elapsed=time.perf_counter()-start)
                def save(state):
                    atomic_json(p['checkpoint'],seal(dict(config=cfg,state=state)))
                    stop.check()
                from .numerics import compute
                result=compute(cutoff,degree,memory_limit_gib,cp,save,phase)
                if config(cutoff,degree)!=cfg:raise AcceptanceError('Source/dependencies changed during calculation; refusing publication')
                result.update(config=cfg,source_sha256=cfg['source_sha256'],environment=environment(),
                              attempt=attempt,acceptance='passed',schema=cfg['schema'],
                              peakrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                result=seal(result);validate_result(result,cfg)
                stop.check();atomic_json(p['result'],result)
            attempt_obj['terminal']='success';atomic_json(p['attempts'],seal(attempt_obj))
            event(p['journal'],event='accepted',seconds=result['seconds'],payload_sha256=result['payload_sha256'])
            return result
        except Preempted as e:
            attempt_obj['terminal']='preempted';atomic_json(p['attempts'],seal(attempt_obj))
            event(p['journal'],event='preempted',message=str(e));raise
        except Exception as e:
            kind='validation_failure' if isinstance(e,AcceptanceError) else 'resource_failure' if isinstance(e,MemoryError) else 'exception'
            attempt_obj['terminal']=kind;atomic_json(p['attempts'],seal(attempt_obj))
            event(p['journal'],event=kind,message=str(e),traceback=traceback.format_exc());raise
