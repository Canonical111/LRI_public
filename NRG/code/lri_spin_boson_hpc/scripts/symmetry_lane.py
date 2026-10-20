"""Packed lane: run one submission's items concurrently on one exclusive node.

Started with exec from cluster/symmetry/lane.sbatch, so Slurm's B:USR1 reaches
this process. A child starts only while the running threads and memory
reservations plus its own fit the node. Children are never signalled: a stop
request creates this execution's STOP file, which every child checks before it
starts work and after every NRG site and bisection step (checkpoint, exit 75).
A restarted execution (SLURM_RESTART_COUNT > 0) launches nothing (exit 79):
recovery goes through `symmetry_submit.py resubmit` with a new generation.
"""
import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
RESTART_EXIT=79
FINISHED_OK={0,73,75,76}


def restart_count():
    try:return int(os.environ.get('SLURM_RESTART_COUNT') or 0)
    except ValueError:return 1


class Lane:
    poll=.2

    def __init__(self,spec,logs,cores=None,mem_gib=None,headroom_gib=8.,python=sys.executable):
        from lri_spin.manifest import load_manifest,reservation_gib,contained
        from lri_spin.campaign import is_campaign_root
        self.spec=json.loads(Path(spec).read_text())
        self.campaign=Path(self.spec['campaign'])
        if not is_campaign_root(self.campaign):raise SystemExit(f'{self.campaign} is not a campaign root')
        # Validated before anything is written: unsafe IDs never reach the filesystem.
        # Admission and every child use the submitted snapshot, verified by hash.
        if not (self.spec.get('manifest_sha256') and self.spec.get('receipt_sha256')):
            raise SystemExit('Lane spec lacks snapshot hashes; resubmit with the current submitter')
        manifest=load_manifest(self.spec['manifest'],self.campaign,sha256=self.spec['manifest_sha256'])
        self.manifest_items=manifest['items']
        self.items=[]
        for entry in self.spec['items']:
            item=self.manifest_items[entry['index']]
            if item['id']!=entry['id']:raise SystemExit(f'Lane spec item {entry["id"]} does not match manifest index {entry["index"]}')
            self.items.append({**entry,'folder':contained(self.campaign,item['id']),
                'threads':item['config'].get('threads',1),'reservation':reservation_gib(item)})
        self.cores=int(cores or os.environ.get('SLURM_CPUS_ON_NODE') or os.cpu_count())
        mem=mem_gib if mem_gib is not None else (int(os.environ['SLURM_MEM_PER_NODE'])/1024 if os.environ.get('SLURM_MEM_PER_NODE') else None)
        if mem is None:raise SystemExit('Memory budget unknown: set --mem-gib or run under Slurm with --mem')
        self.mem=float(mem)-float(headroom_gib)
        job=os.environ.get('SLURM_JOB_ID') or f'local-{uuid.uuid4().hex[:12]}'
        self.execdir=Path(logs)/f'{job}.r{restart_count()}'
        self.stopfile=self.execdir/'STOP'
        self.python=python
        self.stop=False
        self.running={}
        self.results={}

    def event(self,**e):
        e['time']=time.time()
        with open(self.execdir/'events.jsonl','a') as f:
            f.write(json.dumps(e,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())

    def request_stop(self,signum=None,frame=None):
        self.stop=True
        try:
            with open(self.stopfile,'a'):pass
        except OSError:pass

    def owner_ok(self,entry):
        from lri_spin.campaign import read_owner,OwnershipError
        try:return read_owner(entry['folder'])['token']==entry['token']
        except OwnershipError:return False

    def child_env(self,entry):
        env=os.environ.copy();t=str(entry['threads'])
        env.update(LRI_SPIN_OWNER_TOKEN=entry['token'],LRI_SPIN_STOP_FILE=str(self.stopfile),
                   LRI_SPIN_MANIFEST_SHA256=self.spec['manifest_sha256'],LRI_SPIN_RECEIPT_SHA256=self.spec['receipt_sha256'],
                   OPENBLAS_NUM_THREADS=t,MKL_NUM_THREADS=t,OMP_NUM_THREADS=t,SLURM_CPUS_PER_TASK=t,
                   PYTHONPATH=os.pathsep.join([str(ROOT/'src')]+([env['PYTHONPATH']] if env.get('PYTHONPATH') else [])))
        return env

    def command(self,entry):
        return [self.python,'-m','lri_spin','item','--manifest',self.spec['manifest'],
                '--validation-receipt',self.spec['receipt'],'--index',str(entry['index']),
                '--output-dir',str(self.campaign),'--resume']

    def spawn(self,entry):
        log=open(self.execdir/f'{entry["id"]}.log','ab')
        try:return subprocess.Popen(self.command(entry),env=self.child_env(entry),stdout=log,stderr=subprocess.STDOUT)
        finally:log.close()

    def used(self):
        return (sum(e['threads'] for e,_,_ in self.running.values()),
                sum(e['reservation'] for e,_,_ in self.running.values()))

    def fits(self,entry):
        threads,mem=self.used()
        return threads+entry['threads']<=self.cores and mem+entry['reservation']<=self.mem

    def start_ready(self,pending):
        for entry in list(pending):
            if self.stop:return
            if not self.fits(entry):continue
            pending.remove(entry)
            if not self.owner_ok(entry):
                self.results[entry['id']]=76;self.event(event='skip',id=entry['id'],reason='owner token changed')
                continue
            proc=self.spawn(entry)
            self.running[proc.pid]=(entry,proc,time.monotonic())
            self.event(event='start',id=entry['id'],index=entry['index'],pid=proc.pid,token=entry['token'],
                       threads=entry['threads'],reservation_gib=entry['reservation'],
                       threads_in_use=self.used()[0],reserved_gib_in_use=self.used()[1])

    def reap(self):
        for pid,(entry,proc,t0) in list(self.running.items()):
            done,status,usage=os.wait4(pid,os.WNOHANG)
            if done==0:continue
            rc=os.waitstatus_to_exitcode(status);proc.returncode=rc
            del self.running[pid];self.results[entry['id']]=rc
            self.event(event='end',id=entry['id'],rc=rc,peak_rss_kib=usage.ru_maxrss,seconds=time.monotonic()-t0)

    def node_record(self):
        """CPU and runtime of this execution, written before any comparison (heterogeneous-node diagnosis)."""
        from lri_spin import Config
        from lri_spin.io import identity
        try:lscpu=subprocess.run(['lscpu'],capture_output=True,text=True,timeout=30).stdout
        except (OSError,subprocess.SubprocessError):lscpu=None
        info={'host':os.uname().nodename,'runtime':identity(Config(),None,'receipt')['runtime'],'lscpu':lscpu}
        (self.execdir/'node.json').write_text(json.dumps(info,indent=2)+'\n')
        return info

    def check_receipt(self,actual):
        # Each child repeats this check; failing here first gives one clear message.
        from lri_spin.io import read_record,source_hash
        blob=Path(self.spec['receipt']).read_bytes()
        if hashlib.sha256(blob).hexdigest()!=self.spec['receipt_sha256']:raise SystemExit('Receipt snapshot differs from its submitted hash')
        r=read_record(self.spec['receipt'])
        if not r.get('passed') or r.get('source_sha256')!=source_hash():raise SystemExit('Receipt is not for this solver source')
        if r.get('runtime')!=actual:
            raise SystemExit('Receipt runtime differs from this node; validate on this node type.\n'
                             f'expected {json.dumps(r.get("runtime"),sort_keys=True)}\nactual   {json.dumps(actual,sort_keys=True)}')

    def run(self):
        for entry in self.items:
            if entry['threads']>self.cores or entry['reservation']>self.mem:
                raise SystemExit(f'{entry["id"]} cannot fit this node (threads {entry["threads"]}, {entry["reservation"]:.1f} GiB)')
        self.execdir.mkdir(parents=True,exist_ok=True)
        self.check_receipt(self.node_record()['runtime'])
        if self.stopfile.exists():
            print('Stop file already present; launching nothing',file=sys.stderr);return 75
        previous={s:signal.signal(s,self.request_stop) for s in (signal.SIGUSR1,signal.SIGTERM,signal.SIGINT)}
        try:
            self.event(event='lane',host=os.uname().nodename,cores=self.cores,mem_budget_gib=self.mem,
                       items=[e['id'] for e in self.items],restart=restart_count())
            pending=sorted(self.items,key=lambda e:(-e['threads'],-e['reservation'],e['index']))
            while True:
                if not self.stop:self.start_ready(pending)
                self.reap()
                if not self.running and (self.stop or not pending):break
                if not self.running and pending and not any(self.fits(e) for e in pending):
                    raise RuntimeError('No pending item fits an idle node')
                time.sleep(self.poll)
            for entry in pending:self.results.setdefault(entry['id'],None)
            failed=sorted(k for k,v in self.results.items() if v is not None and v not in FINISHED_OK)
            interrupted=sorted(k for k,v in self.results.items() if v is None or v==75)
            self.event(event='lane_end',failed=failed,interrupted=interrupted,stop=self.stop,results=self.results)
            if failed:print('Failed items:',failed,file=sys.stderr);return 1
            if interrupted:return 75
            return 0
        finally:
            for s,h in previous.items():signal.signal(s,h)


def main(argv=None):
    if restart_count()>0:
        # Same job id, possibly a surviving old execution: never write.
        print(f'Refusing restarted execution (SLURM_RESTART_COUNT={os.environ.get("SLURM_RESTART_COUNT")}); use symmetry_submit.py resubmit',file=sys.stderr)
        return RESTART_EXIT
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',required=True);p.add_argument('--logs',required=True)
    p.add_argument('--cores',type=int);p.add_argument('--mem-gib',type=float);p.add_argument('--headroom-gib',type=float,default=8.)
    a=p.parse_args(argv)
    try:lane=Lane(a.spec,a.logs,a.cores,a.mem_gib,a.headroom_gib)
    except ValueError as exc:raise SystemExit(f'Invalid lane input: {exc}')
    return lane.run()


if __name__=='__main__':
    raise SystemExit(main())
