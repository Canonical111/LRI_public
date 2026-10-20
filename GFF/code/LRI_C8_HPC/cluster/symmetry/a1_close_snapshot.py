#!/usr/bin/env python3
"""Amendment A2 (docs/EXTENSION_A2.md): immutable record of the A1 wave at its close. Run after every A1 lane job has
ended, before any A1-close combination. The A1 INCLUSION SET keeps A1's own rule (a planned batch is complete when
all its planned checkpoints are present, as lane8.py finalize decides; done markers are not required, so a batch whose
last done marker was cut off after its final checkpoint is still included) and attributes the checkpoints to a wave by
CLAIMS: a lane worker runs an element only after publishing an attempt file claims/<element>.<n> in its own queue, so
an element with no claim in queue_a2 was never run by A2. queue_a2 is published only after this snapshot (submit_a2.sh
close), and its existence (or that of its staging directory) stops this script, so in the intended order no A2 claim
exists yet; the claim checks remain as a defence. A batch is in the A1 inclusion set when its checkpoints are
complete and no element of it has a claim in queue_a2. Barrier: if any batch has claims in BOTH queues (only b10 can,
once A2 workers reach it, more than a day after the A1 close), attribution by claims is no longer possible and the
script stops without writing. Integrity checks: every A1-queue done marker must name an A1 lane job; a batch with A1
done markers on every element but incomplete checkpoints stops the script. Also recorded per batch: checkpoints
present/planned, claimed and done counts in both queues, A1 merge state and the production.json digest; and the A1
lane jobs' final states. Outputs, no-clobber:
  results/C8_A1_close/a1_close_snapshot.json
  runs/ext1/extension_A1close.json   extension.json with the planned extension batches restricted to the A1 inclusion
                                     set, bound to the snapshot by its sha256
Restartable: if the snapshot exists, it is validated (schema, extension.json digest) and only a missing derived file is
rebuilt from the saved inclusion set; an existing derived file is verified against it. Live checkpoints are never
rescanned for an existing snapshot. Read-only otherwise: no queue marker is created, archived or removed."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
W=Path('/mnt/beegfs/zzheng1/c8_hpc');R=W/'runs/ext1';OUT=W/'results/C8_A1_close'
sys.path.insert(0,str(W/'code/15a110e/tools'))
import lane8
TERMINAL={'COMPLETED','CANCELLED','FAILED','TIMEOUT','NODE_FAIL','BOOT_FAIL','DEADLINE','OUT_OF_MEMORY','REVOKED','PREEMPTED'}

def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def listed(d:Path)->set:return {f for f in os.listdir(d) if '.tmp.' not in f} if d.is_dir() else set()

def claimed(d:Path)->set:
    """Element keys with at least one published attempt file <element>.<n> in a queue's claims directory."""
    return {f.rsplit('.',1)[0] for f in listed(d)}

def derive(ext:dict,rec:dict,snap:Path)->dict:
    return {**ext,'amendment':f'docs/EXTENSION_A2.md: A1-close inclusion set derived from extension.json (sha256 {rec["extension_json_sha256"]}); snapshot {snap} sha256 {sha(snap)}',
            'extension':[x for x in ext['extension'] if x['label'] in rec['a1_inclusion_set']]}

def finish(ext:dict,snap:Path,derived:Path)->None:
    """Publish (or verify) the derived file from the saved snapshot only."""
    rec=json.loads(snap.read_text())
    if rec.get('schema')!='c8-a1-close-1':sys.exit('snapshot: unexpected schema')
    if rec['extension_json_sha256']!=sha(R/'extension.json'):sys.exit('extension.json changed since the snapshot')
    want=derive(ext,rec,snap)
    if derived.exists():
        if json.loads(derived.read_text())!=want:sys.exit('derived extension file differs from the snapshot')
    elif not lane8.publish(derived,want):sys.exit('derived extension file appeared concurrently')
    print(json.dumps({'snapshot':str(snap),'snapshot_sha256':sha(snap),'derived':str(derived),'a1_inclusion_set':rec['a1_inclusion_set'],
                      'unmerged_in_set':[x['label'] for x in rec['batches'] if x['label'] in rec['a1_inclusion_set'] and not x['merged_A1_queue']],
                      'fractions':{x['label']:x['completed_fraction'] for x in rec['batches']}},indent=1))

def main()->None:
    snap=OUT/'a1_close_snapshot.json';derived=R/'extension_A1close.json'
    ext=json.loads((R/'extension.json').read_text())
    if snap.exists():finish(ext,snap,derived);return
    if derived.exists():sys.exit('derived extension file exists without a snapshot: inspect')
    if (R/'queue_a2').exists() or (R/'queue_a2.staging').exists():sys.exit('A2 queue (or its staging directory) exists before the A1-close snapshot: inspect')
    jobs=[l.strip() for f in ('lane_jobs_longq.txt','lane_jobs_defq.txt','lane_jobs_preq.txt') for l in (R/f).read_text().split('\n') if l.strip()]
    q=lane8.squeue_jobs()
    if q is None:sys.exit('squeue failed: cannot confirm that the A1 lane jobs have ended')
    live=[f'{j} {st}' for j,n,st in q if j in jobs and st not in TERMINAL]
    if live:sys.exit('A1 lane jobs not ended: '+'; '.join(live))
    r=subprocess.run(['sacct','-X','-n','-P','-j',','.join(jobs),'-o','JobID,State,Start,End,Elapsed','-S','2026-10-10','-E','now'],capture_output=True,text=True,timeout=120)
    if r.returncode:sys.exit('sacct failed: '+r.stderr.strip())
    acct={t[0]:{'state':t[1],'start':t[2],'end':t[3],'elapsed':t[4]} for t in (l.split('|') for l in r.stdout.split('\n') if l.strip())}
    missing=[j for j in jobs if j not in acct];unended=[j for j in jobs if j in acct and acct[j]['state'].split()[0] not in TERMINAL]
    if missing or unended:sys.exit(f'A1 lane jobs without a terminal accounting state: missing {missing}, not ended {unended}')
    Q=lane8.Queue(R/'queue');Q2=R/'queue_a2';scan=[]
    for x in ext['extension']: # pass 1: checkpoints (and A1 merge state) of every batch
        lab=x['label'];b=(R/x['path']).resolve();complete,have,need=lane8.checkpoints_complete(b)
        prod=json.loads((b/'production.json').read_text())
        merged=(Q.q/'merge'/(lab+'.ok')).exists() and all((b/c/'merged'/'audit.json').is_file() for c in prod['campaigns'])
        scan.append((x,b,complete,have,need,merged))
    # pass 2, AFTER every checkpoint was observed: claims and done markers. A worker publishes its claim before it writes
    # any checkpoint of the element, and claims are only ever added while lanes run, so every checkpoint seen in pass 1
    # that an A2 worker wrote has its claim in this listing.
    done=Q.done();done2=listed(Q2/'done');claims1=claimed(Q.q/'claims');claims2=claimed(Q2/'claims');rows=[]
    for x,b,complete,have,need,merged in scan:
        lab=x['label'];ks=Q.batches[lab]['elements'] if lab in Q.batches else []
        a1=[k for k in ks if k in done];foreign=[]
        for k in a1:
            d=lane8.readj(Q.q/'done'/k)
            if not d or str(d.get('job')) not in jobs:foreign.append(k)
        if foreign:sys.exit(f'{lab}: done markers in the A1 queue not attributed to an A1 lane job: {foreign[:5]}')
        if bool(ks) and len(a1)==len(ks) and not complete:sys.exit(f'{lab}: every element done under A1 but checkpoints incomplete ({have}/{need}): inspect')
        c1=sum(k in claims1 for k in ks);c2=sum(k in claims2 for k in ks)
        if c1 and c2:sys.exit(f'{lab}: elements claimed in both queues ({c1} A1, {c2} A2): attribution by claims impossible (snapshot too late?): inspect')
        rows.append({'label':lab,'seed':int(x['seed']),'path':x['path'],'production_sha256':sha(b/'production.json'),
                     'complete_under_A1':complete and c2==0,'checkpoints_complete_now':complete,'checkpoints_present':have,'checkpoints_planned':need,
                     'completed_fraction':round(have/need,6),'claimed_elements_A1_queue':c1,'claimed_elements_A2_queue':c2,
                     'done_elements_A1_queue':len(a1),'done_elements_A2_queue':sum(k in done2 for k in ks),
                     'elements':len(ks),'merged_A1_queue':merged})
    rec={'schema':'c8-a1-close-1','amendment':'docs/EXTENSION_A2.md','time':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
         'deadline':json.loads((R/'queue'/'deadline.json').read_text()),'stop_marker':(R/'queue'/'STOP').exists(),
         'a1_lane_jobs':{j:acct[j] for j in jobs},'extension_json_sha256':sha(R/'extension.json'),'batches':rows,
         'a1_inclusion_set':[x['label'] for x in rows if x['complete_under_A1']],
         'note':'inclusion: complete checkpoints (A1 rule) and no claim in queue_a2; checkpoint counts and fractions of batches claimed in queue_a2 include A2 work up to this time'}
    OUT.mkdir(parents=True,exist_ok=True)
    if not lane8.publish(snap,rec):sys.exit('snapshot appeared concurrently')
    finish(ext,snap,derived)

if __name__=='__main__':main()
