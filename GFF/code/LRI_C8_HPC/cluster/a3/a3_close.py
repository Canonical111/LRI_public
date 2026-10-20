#!/usr/bin/env python3
"""Amendment A3 (docs/EXTENSION_A3.md), symmetry: guards and bookkeeping of the closing job (a3_close.slurm).

  begin          every invocation, in this order: the close lock runs/ext1/A3_CLOSE.lock is published no-clobber (an
                 existing lock, from an earlier close attempt, stops the job: inspect, and remove it by hand only after
                 that job has ended); then squeue answers and lists no unfinished c8x- job except this one (c8x-stop
                 excepted, as in lane8); then no transfer is registered (runs/ext1_a3_import/.incoming.*); then no stop
                 marker, admitted publication or published result; then the A1-close snapshot records b12-b14
                 untouched by A1 workers (this covers an early export); then queue_a2 is complete (all 996 elements
                 done, b10 and b11 merged) and b12-b14 are staged
  verify LABEL   before any installation: the staged copy passes a3_tree.py check-import and production8.py merge
                 (which, all campaigns being audited, only re-validates them), then the receipt
                 runs/ext1/A3_verified_<label>.json bound to the manifest digest is published. On a rerun after an
                 interrupted install (some campaign directories already moved), the receipt with the same manifest
                 digest is required instead, and the installed result is verified after the install
  batches        after finalize and install: every one of b5-b14 has all planned checkpoints and every campaign merged
                 (b12-b14: the installed tree equals its manifest); prints the ten extension batch paths
  end            the private combination results/C8_final_A3.pending is the closed K=14 result; writes A3_close.json
                 there; then publication: the marker runs/ext1/A3_PUBLISH is published no-clobber, the symmetry stop
                 marker runs/ext1/A3_STOP must be absent, and the directory is renamed to results/C8_final_A3
  stop           (login node; the first step of a user stop) publishes runs/ext1/A3_STOP no-clobber, then reports the stop
                 acknowledged only if A3_PUBLISH is absent: with the two markers published before each one checks the
                 other, either the stop is acknowledged and no close publishes, or publication was admitted first and
                 the stop is reported as too late for the result
"""
from __future__ import annotations
import json, os, subprocess, sys, time
from pathlib import Path
W=Path('/mnt/beegfs/zzheng1/c8_hpc');R=W/'runs'/'ext1';I=W/'runs'/'ext1_a3_import';T=W/'code'/'15a110e'
sys.path.insert(0,str(T/'tools'));sys.path.insert(0,str(Path(__file__).resolve().parent))
import lane8, a3_tree # noqa: E402
A3L=('b12','b13','b14');SYM=('b5','b6','b7','b8','b9','b10','b11')
TERMINAL={'COMPLETED','CANCELLED','FAILED','TIMEOUT','NODE_FAIL','BOOT_FAIL','DEADLINE','OUT_OF_MEMORY','REVOKED'} # as lane8: every other state (held, requeued, preempted) may still run
LOCK=R/'A3_CLOSE.lock';SSTOP=R/'A3_STOP';PUB=R/'A3_PUBLISH'
PENDING=W/'results'/'C8_final_A3.pending';FINAL=W/'results'/'C8_final_A3'

def die(m):print('A3 close:',m,file=sys.stderr);sys.exit(64)
def now():return time.strftime('%Y-%m-%dT%H:%M:%S%z')
def man(l):return I/f'{l}.expanse_manifest.txt'

def begin()->None:
    if os.environ.get('SLURM_JOB_NAME')!='c8x-finalize' or not os.environ.get('SLURM_JOB_ID'):die('runs only inside the A3 close job (c8x-finalize)')
    if not lane8.publish(LOCK,{'job':os.environ['SLURM_JOB_ID'],'time':now()}):
        die(f'{LOCK} exists ({LOCK.read_text().strip()}): an earlier close attempt; inspect, remove it after that job ended, resubmit')
    jobs=lane8.squeue_jobs();mine=os.environ['SLURM_JOB_ID']
    if jobs is None:die('squeue failed: cannot confirm that no other C8 job runs')
    busy=[f'{j} {n} {st}' for j,n,st in jobs if n.startswith('c8x-') and n!='c8x-stop' and st not in TERMINAL and j!=mine]
    if busy:die('other C8 jobs exist: '+'; '.join(busy))
    inc=sorted(p.name for p in I.glob('.incoming.*')) if I.is_dir() else []
    if inc:die(f'transfers or unstaging registered (in flight or interrupted): {inc}')
    stops=[str(p) for p in (SSTOP,R/'A2_CANCEL',R/'queue_a2'/'STOP') if p.exists()]
    if stops:die(f'stop markers exist: {stops}: a stopped close needs its own reviewed procedure')
    if PUB.exists() or FINAL.exists():die('an A3 result was already admitted for publication or published')
    snap=W/'results'/'C8_A1_close'/'a1_close_snapshot.json' # the A1 record must show b12-b14 untouched by A1 workers
    rec=lane8.readj(snap)
    if not rec or rec.get('schema')!='c8-a1-close-1':die('A1-close snapshot missing or unreadable')
    rows={x['label']:x for x in rec['batches']}
    for l in A3L:
        x=rows.get(l)
        if not x or any(x[k]!=0 for k in ('checkpoints_present','claimed_elements_A1_queue','claimed_elements_A2_queue','done_elements_A1_queue','done_elements_A2_queue')):
            die(f'{l}: the A1-close snapshot does not record it untouched ({x}): its Expanse copy cannot be used (new decision)')
    Q=lane8.Queue(R/'queue_a2');d=Q.done();miss=[Q.key(e) for e in Q.order if Q.key(e) not in d]
    ok=[l for l in ('b10','b11') if (Q.q/'merge'/(l+'.ok')).exists()]
    if miss or ok!=['b10','b11'] or sorted(Q.batches)!=['b10','b11']:die(f'queue_a2 not complete: {len(miss)} elements not done, merged {ok}')
    for l in A3L:
        if not (man(l).is_file() and (I/l).is_dir()):die(f'{l}: not staged')
    print('begin ok')

def installed_any(l)->bool:return any((R/l/c/s).exists() for c in a3_tree.campaigns(R/l) for s in ('checkpoints','merged'))

def verify(l:str,c8_root:str,scratch:str)->None:
    rp=R/f'A3_verified_{l}.json';ms=a3_tree.sha(man(l))
    if installed_any(l): # rerun after an interrupted install: only a receipt from the attempt that verified it admits it
        rc=json.loads(rp.read_text()) if rp.is_file() else None
        if not rc or rc.get('manifest_sha256')!=ms:die(f'{l}: partly installed without a verification receipt for this manifest')
        a3_tree.check_import(R/l,I/l,man(l));print(f'{l}: partly installed, receipt {rp.name} matches');return
    a3_tree.check_import(R/l,I/l,man(l))
    r=subprocess.run([sys.executable,str(Path(c8_root)/'tools'/'production8.py'),'merge',str(I/l),'--scratch',scratch])
    if r.returncode:die(f'{l}: staged copy fails validation (production8.py merge rc {r.returncode})')
    if rp.exists():
        if json.loads(rp.read_text()).get('manifest_sha256')!=ms:die(f'{rp} exists for another manifest')
    elif not lane8.publish(rp,{'label':l,'manifest_sha256':ms,'job':os.environ.get('SLURM_JOB_ID'),'time':now()}):die(f'{rp} appeared concurrently')
    print(f'{l}: staged copy verified')

def batches()->None:
    out=[]
    for l in SYM+A3L:
        b=R/l;ok,have,need=lane8.checkpoints_complete(b)
        if not ok:die(f'{l}: {have}/{need} checkpoints: a complete close needs every planned checkpoint of b5-b14')
        if not all((b/c/'merged'/'audit.json').is_file() for c in a3_tree.campaigns(b)):die(f'{l}: not merged')
        if l in A3L and a3_tree.tree(b)!=a3_tree.read_manifest(man(l)):die(f'{l}: installed tree differs from its manifest')
        out.append(str(b))
    print(' '.join(out))

def end(paths:list)->None:
    f=json.loads((PENDING/'C8_final.json').read_text());x=f.get('extension') or {}
    if f.get('batches',{}).get('count')!=14 or f.get('final') is not True or x.get('closed') is not True or x.get('omitted_incomplete') or sorted(x.get('included_extension',[]))!=sorted(SYM+A3L):
        die(f'combination is not the closed K=14 result: count {f.get("batches",{}).get("count")}, final {f.get("final")}, extension {x.get("included_extension")}')
    doc={'schema':'c8-a3-close-1','time':now(),'job':os.environ.get('SLURM_JOB_ID'),'combined_extension_batches':[Path(p).name for p in paths],
         'vendor':{**{f'b{i}':'AMD EPYC 7742 (Expanse)' for i in (1,2,3,4,12,13,14)},**{l:'Intel Xeon Gold 6148 (symmetry)' for l in SYM}}}
    cp=PENDING/'A3_close.json';key=lambda d:{k:d.get(k) for k in ('schema','combined_extension_batches','vendor')}
    if not lane8.publish(cp,doc): # atomic no-clobber (temporary file, fsync, link); an earlier attempt's record must agree
        old=lane8.readj(cp)
        if not old or key(old)!=key(doc):die(f'{cp} exists and differs from this close (or is unreadable): inspect')
    if not lane8.publish(PUB,{'job':os.environ.get('SLURM_JOB_ID'),'time':now()}):die(f'{PUB} exists: publication admitted earlier; inspect')
    if SSTOP.exists():die(f'stop acknowledged ({SSTOP}) before publication: the result stays private in {PENDING}')
    os.rename(PENDING,FINAL) # FINAL cannot exist: begin checked it, and only this step creates it
    print('published',FINAL);print(json.dumps(doc,indent=1))

def stop()->None:
    if os.environ.get('SLURM_JOB_ID'):die('run from the login node')
    if not lane8.publish(SSTOP,{'time':now(),'by':os.environ.get('USER')}):die(f'{SSTOP} exists')
    if PUB.exists():print(f'stop NOT acknowledged for the result: publication was admitted first ({PUB.read_text().strip()})');sys.exit(1)
    print('stop acknowledged: no A3 close will publish a result; continue with the stop procedure (A2 markers, Expanse stop, scancel)')

if __name__=='__main__':
    a=sys.argv[1:]
    if a[0]=='begin':begin()
    elif a[0]=='verify':verify(a[1],a[2],a[3])
    elif a[0]=='batches':batches()
    elif a[0]=='end':end(a[1:])
    elif a[0]=='stop':stop()
    else:die('usage: begin | verify LABEL C8_ROOT SCRATCH | batches | end PATHS... | stop')
