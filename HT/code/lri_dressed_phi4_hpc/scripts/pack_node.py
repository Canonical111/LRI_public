#!/usr/bin/env python3
"""Node-packing launcher: run many independent pack items on one exclusive node.

Several launchers (one per node job) may share one campaign directory; items are taken
under cross-node generation leases (lri_dressed.lease). Each item is one CLI process in
its own process group with explicit numerical options. Shutdown: USR1/TERM stops new
launches and forwards USR1 (children checkpoint at the next Newton boundary, exit 75); at
end-ESCALATE the remaining groups get TERM, then KILL after TERM_GRACE. An item lease is
released only after its child has been reaped.

Outcome of a child: rc 0 with validated result envelopes covering the item: done; rc 75
interrupted; rc 73 claimed elsewhere (pending); death by a signal THIS launcher sent during
escalation: interrupted; anything else: failed. A failed item is retried only while its
recorded attempts are below --max-attempts (default 1: no retry), re-checked under its lease.
Completion records are bound to the item's numerical digest and the result checksums, and
are re-validated before an item is skipped.

Campaign layout: manifest.json, results/ (CLI output), items/{leases,done,failed}/,
logs/items/<item>.<job>.log, logs/launcher.<job>.jsonl, MAINTENANCE (blocks launching).
"""
import argparse,json,math,os,signal,subprocess,sys,time
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_dressed.io import digest,source_fingerprint,release_fingerprint,runtime,read_envelope,atomic_json
from lri_dressed.lease import Lease,Claimed,slurm_job_alive
from lri_dressed.pack import check_item,command,completion,completion_valid,results_from_log,result_stamp

STOP=False


def request_stop(signum,frame):
    global STOP
    STOP=True


def load_manifest(campaign):
    m=json.loads((campaign/'manifest.json').read_text());s=m.pop('sha256',None)
    if s!=digest(m):raise ValueError('Manifest checksum failed')
    if m.get('schema')!='lri-dressed-pack-v1':raise ValueError(f"pack_node.py runs only lri-dressed-pack-v1 manifests, not {m.get('schema')!r}")
    if m['release_sha256']!=release_fingerprint() or m['source_sha256']!=source_fingerprint():
        raise ValueError('Manifest belongs to a different release/source revision')
    for item in m['items']:check_item(item)
    if len({i['id'] for i in m['items']})!=len(m['items']):raise ValueError('Duplicate item ids')
    return m


def check_receipt(path):
    r=read_envelope(path,'validation')['payload']
    if r.get('passed') is not True or r.get('release_sha256')!=release_fingerprint() or r.get('source_sha256')!=source_fingerprint() \
       or r.get('runtime')!=runtime():
        raise ValueError('Missing or stale release/source/dependency validation receipt')


SHUTDOWN_SIGNALS={signal.SIGUSR1,signal.SIGTERM,signal.SIGINT}


def block_shutdown_signals():
    """Child pre-exec: keep USR1/TERM/INT pending until the CLI has installed its handlers."""
    signal.pthread_sigmask(signal.SIG_BLOCK,SHUTDOWN_SIGNALS)


def slurm_end_epoch():
    job=os.environ.get('SLURM_JOB_ID')
    if not job:return None
    try:
        p=subprocess.run(['squeue','-h','-j',job,'-o','%e'],capture_output=True,text=True,timeout=60)
        return datetime.strptime(p.stdout.strip(),'%Y-%m-%dT%H:%M:%S').timestamp()
    except (OSError,ValueError,subprocess.TimeoutExpired):return None


def node_resources(a):
    cores=a.cores or int(os.environ.get('SLURM_CPUS_ON_NODE') or os.cpu_count())
    if a.mem_gib:mem=a.mem_gib
    elif os.environ.get('SLURM_MEM_PER_NODE'):mem=.9*int(os.environ['SLURM_MEM_PER_NODE'])/1024
    else:
        total=[int(l.split()[1]) for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemTotal:')][0]
        mem=.9*total/2**20
    return max(1,cores-a.reserve_cores),mem


class Launcher:
    def __init__(self,a):
        self.a=a;self.campaign=Path(a.campaign).resolve();self.manifest=load_manifest(self.campaign);check_receipt(a.receipt)
        self.job=os.environ.get('SLURM_JOB_ID','local');self.host=os.uname().nodename
        self.dirs={k:self.campaign/'items'/k for k in ('leases','done','failed')}
        for d in list(self.dirs.values())+[self.campaign/'results',self.campaign/'logs/items']:d.mkdir(parents=True,exist_ok=True)
        self.events=self.campaign/'logs'/f'launcher.{self.job}.{os.getpid()}.jsonl'
        self.cores,self.mem=node_resources(a)
        self.end=a.end_epoch or slurm_end_epoch()
        self.slurm=lambda job,restart=None:slurm_job_alive(job,restart=restart,timeout=a.squeue_timeout)
        self.running={};self.backoff={};self.escalated=set();self.forwarded=False
        self.items={i['id']:i for i in self.manifest['items']};self.source=self.manifest['source_sha256']
        self.verdicts={};self.failed_here=set();self.dirs['superseded']=self.dirs['failed']/'superseded'
        self.dirs['superseded'].mkdir(parents=True,exist_ok=True)

    def log(self,event,**kw):
        with open(self.events,'a') as f:f.write(json.dumps({'time':time.time(),'event':event,'job':self.job,'host':self.host,**kw})+'\n')

    def maintenance(self):return (self.campaign/'MAINTENANCE').exists()

    def done_valid(self,iid):
        """Validated completion, cached on the marker AND the referenced result files (mtime, size)."""
        p=self.dirs['done']/f'{iid}.json'
        try:st=p.stat();record=json.loads(p.read_text())
        except FileNotFoundError:return False
        except (OSError,ValueError):record={}
        key=(st.st_mtime_ns,st.st_size,result_stamp(record))
        if self.verdicts.get(iid,(None,))[0]!=key:
            try:ok=completion_valid(self.items[iid],record,self.source)
            except (OSError,ValueError):ok=False
            if not ok:self.log('stale_done_marker',item=iid)
            self.verdicts[iid]=(key,ok)
        return self.verdicts[iid][1]

    def attempts(self,iid):
        try:return int(json.loads((self.dirs['failed']/f'{iid}.json').read_text()).get('attempts',1))
        except FileNotFoundError:return 0
        except (OSError,ValueError):return 10**6

    def eligible(self,iid):
        return not self.done_valid(iid) and iid not in self.failed_here and self.attempts(iid)<self.a.max_attempts

    def outstanding(self):
        return [i for iid,i in self.items.items() if iid not in self.running and self.eligible(iid)]

    def remaining(self):return None if self.end is None else self.end-time.time()-self.a.escalate_before

    def fits(self,item,cores,mem):
        if item['threads']>cores or item['mem_gib']>mem:return False
        rem=self.remaining()
        return rem is None or 1.5*item['est_seconds']<=rem

    def stopping(self):return STOP or self.forwarded or self.maintenance()

    def launch(self,item):
        if self.stopping():return False
        lease=Lease(self.dirs['leases']/item['id'],slurm=self.slurm)
        try:lease.acquire()
        except Claimed as exc:
            self.backoff[item['id']]=time.time()+self.a.claim_backoff;self.log('held_elsewhere',item=item['id'],detail=str(exc)[:300]);return False
        # Re-check under the lease: another node may have completed or failed it since selection.
        self.verdicts.pop(item['id'],None)
        if self.stopping() or not self.eligible(item['id']):
            lease.release();return False
        log=self.campaign/'logs/items'/f"{item['id']}.{self.job}.log"
        env=dict(os.environ,NUMBA_NUM_THREADS=str(item['threads']),OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1',
                 LRI_MAINTENANCE_MARKER=str(self.campaign/'MAINTENANCE'),PYTHONPATH=str(ROOT/'src')+os.pathsep+os.environ.get('PYTHONPATH',''))
        fh=open(log,'a');offset=fh.tell();cmd=command(item,self.campaign/'results')
        proc=subprocess.Popen(cmd,stdout=fh,stderr=subprocess.STDOUT,env=env,start_new_session=True,cwd=self.campaign,
                              preexec_fn=block_shutdown_signals)
        self.running[item['id']]={'proc':proc,'item':item,'lease':lease,'start':time.time(),'sent':[],'log':log,'fh':fh,'offset':offset}
        self.log('launch',item=item['id'],pid=proc.pid,threads=item['threads'],mem_gib=item['mem_gib'],log=str(log));return True

    def signal_group(self,rec,sig):
        try:os.killpg(rec['proc'].pid,sig);rec['sent'].append(int(sig))
        except ProcessLookupError:pass

    def reap(self):
        for iid,rec in list(self.running.items()):
            rc=rec['proc'].poll()
            if rc is None:continue
            rec['fh'].close();wall=time.time()-rec['start'];sent=rec['sent']
            info={'item':iid,'returncode':rc,'wall_seconds':wall,'job':self.job,'host':self.host,'log':str(rec['log']),'signals_sent':sent}
            try:text=rec['log'].read_text()[rec['offset']:]
            except OSError:text=''
            outcome=None
            if rc==0:
                try:
                    atomic_json(self.dirs['done']/f'{iid}.json',dict(info,**completion(rec['item'],results_from_log(text),self.source)))
                    outcome='done';self.supersede_failure(iid)
                except (OSError,ValueError) as exc:info['error']=f'completion check: {exc}'[:2000]
            elif rc==75 or (rc<0 and -rc in sent and -rc in (signal.SIGTERM,signal.SIGKILL)):
                outcome='interrupted'
            elif rc==73:
                outcome='claimed';self.backoff[iid]=time.time()+self.a.claim_backoff
            if outcome is None:
                n=self.attempts(iid)+1;self.failed_here.add(iid)
                atomic_json(self.dirs['failed']/f'{iid}.json',dict(info,attempts=n,log_tail=text[-4000:]));outcome='failed'
            self.verdicts.pop(iid,None)
            rec['lease'].release()        # only after the child has been reaped
            del self.running[iid];self.log(outcome,**info)

    def supersede_failure(self,iid):
        p=self.dirs['failed']/f'{iid}.json'
        if p.exists():os.replace(p,self.dirs['superseded']/f'{iid}.{int(time.time())}.json')

    def escalate(self):
        rem=None if self.end is None else self.end-time.time()
        if (STOP or (rem is not None and rem<=self.a.escalate_before)) and not self.forwarded:
            for rec in self.running.values():self.signal_group(rec,signal.SIGUSR1)
            self.forwarded=True;self.log('forward_usr1',children=list(self.running))
        if rem is None:return
        for iid,rec in self.running.items():
            if rem<=self.a.escalate_before and signal.SIGTERM not in rec['sent']:
                self.signal_group(rec,signal.SIGTERM);rec['term_time']=time.time();self.log('escalate_term',item=iid)
            elif 'term_time' in rec and time.time()-rec['term_time']>=self.a.term_grace and signal.SIGKILL not in rec['sent']:
                self.signal_group(rec,signal.SIGKILL);self.log('escalate_kill',item=iid)

    def warmup(self):
        tmp=self.campaign/'logs'/f'warmup.{self.job}.{os.getpid()}'
        cmd=[sys.executable,'-m','lri_dressed','run','--bath-cut','4','--nz','4','--osc','32','--deltas','.24','--output-dir',str(tmp),'--window','vacuum']
        p=subprocess.run(cmd,capture_output=True,text=True,env=dict(os.environ,NUMBA_NUM_THREADS='1'))
        self.log('warmup',returncode=p.returncode,stderr=p.stderr[-500:])

    def run(self):
        self.log('start',cores=self.cores,mem_gib=self.mem,end_epoch=self.end,items=len(self.items))
        if not self.a.no_warmup:self.warmup()
        while True:
            self.reap();self.escalate()
            if not self.stopping():
                used_c=sum(r['item']['threads'] for r in self.running.values());used_m=sum(r['item']['mem_gib'] for r in self.running.values())
                now=time.time();deadline=now+self.a.pass_seconds
                for item in sorted(self.outstanding(),key=lambda i:-i['est_seconds']*i['threads']):
                    # Bounded pass: shutdown, reaping and escalation are never starved by lease lookups.
                    if self.stopping() or time.time()>deadline:break
                    if self.backoff.get(item['id'],0)>now:continue
                    if self.fits(item,self.cores-used_c,self.mem-used_m) and self.launch(item):
                        used_c+=item['threads'];used_m+=item['mem_gib']
                    self.reap();self.escalate()
            if not self.running:
                if self.stopping():break
                now=time.time();pending=self.outstanding()
                waiting=[i for i in pending if self.backoff.get(i['id'],0)>now]
                launchable=[i for i in pending if self.backoff.get(i['id'],0)<=now and self.fits(i,self.cores,self.mem)]
                if not launchable and not (waiting and self.a.wait_for_others):break
            time.sleep(self.a.poll)
        left=[i['id'] for i in self.outstanding()]
        self.log('exit',stopped=STOP,maintenance=self.maintenance(),outstanding=len(left))
        print(json.dumps({'job':self.job,'outstanding':len(left),'stopped':STOP}),flush=True)
        return 0


def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--campaign',required=True);ap.add_argument('--receipt',required=True)
    ap.add_argument('--cores',type=int);ap.add_argument('--mem-gib',type=float);ap.add_argument('--reserve-cores',type=int,default=1)
    ap.add_argument('--end-epoch',type=float,help='override the Slurm end time (epoch seconds)')
    ap.add_argument('--squeue-timeout',type=float,default=15.)
    ap.add_argument('--escalate-before',type=float,default=120.);ap.add_argument('--term-grace',type=float,default=30.)
    ap.add_argument('--claim-backoff',type=float,default=120.);ap.add_argument('--poll',type=float,default=2.)
    ap.add_argument('--max-attempts',type=int,default=1,help='retry a failed item while its recorded attempts are below this')
    ap.add_argument('--pass-seconds',type=float,default=15.,help='time budget of one scheduling pass')
    ap.add_argument('--no-warmup',action='store_true')
    ap.add_argument('--wait-for-others',action='store_true',help='keep polling while other nodes hold the remaining items')
    a=ap.parse_args()
    for sig in (signal.SIGUSR1,signal.SIGTERM,signal.SIGINT):signal.signal(sig,request_stop)
    return Launcher(a).run()

if __name__=='__main__':sys.exit(main())
