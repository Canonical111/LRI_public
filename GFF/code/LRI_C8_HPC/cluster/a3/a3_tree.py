#!/usr/bin/env python3
"""Amendment A3 (docs/EXTENSION_A3.md): file-tree checks for running the planned batches b12-b14 on Expanse.

  manifest DIR [--out FILE | --digest]   sha256 and relative path of every file under DIR, sorted by path ("<sha>  <rel>");
                                   --digest prints only the sha256 of that text (exit nonzero on any failure)
  gate [--early]                   symmetry, before export: the A1-close snapshot exists and records b12-b14 untouched,
                                   queue_a2 holds exactly b10 and b11, and b12-b14 still have no checkpoint, no merged
                                   output and no claim in either queue. --early (before the A1 close): the snapshot and
                                   queue_a2 do not exist yet, b12-b14 are untouched and unclaimed, the A1 queue has no
                                   failure record, and a lower bound on the time the A1 lanes need to reach b12 by
                                   computing (see early_bound) exceeds the time left to the A1 deadline. This is a
                                   speculative start, not an exclusion guarantee (fast failures could advance A1
                                   faster): the A1-close snapshot decides afterwards, see docs/EXTENSION_A3.md
  check-expanse DIR                Expanse, before submission: a planned, untouched A3 batch (label and seed of the
                                   amendment, no checkpoints/ or merged/ directory)
  check-import PLANNED IMPORT MANIFEST     symmetry: IMPORT (an Expanse batch copied back) equals the Expanse
                                   manifest, every planned file is unchanged, and the only additions are
                                   <campaign>/checkpoints/<file> and <campaign>/merged/<file>, with every campaign merged
  unstage LABEL                    symmetry, login node, before the close only: withdraw a staged copy that failed its
                                   checks (for example a damaged transfer) so that it can be imported again: moves runs/ext1_a3_import/<label>
                                   and its manifest to runs/ext1_a3_import/withdrawn/<label>.<k>/ (renames) and archives a
                                   verification receipt of it, if any; refuses once the close lock or a transfer
                                   registration exists, or if any part of the batch is installed in runs/ext1
  install PLANNED IMPORT MANIFEST  symmetry, inside the A3 close job only: check, then move each campaign's checkpoints/
                                   and merged/ from IMPORT into PLANNED (renames on one filesystem); restartable; the
                                   installed tree must then equal the Expanse manifest file for file
Exit status nonzero (with a message) on any failed check.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys, tempfile, time
from pathlib import Path

W=Path('/mnt/beegfs/zzheng1/c8_hpc');R=W/'runs'/'ext1'
A3={'b12':80840012,'b13':80840013,'b14':80840014} # labels and seeds of the A3 batches (runs/ext1/extension.json)
ADDED=re.compile(r'([^/]+)/(checkpoints|merged)/[^/]+') # run and merge output only (no quarantine on Expanse under A3)

def sha(p:Path)->str:
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def tree(d:Path)->dict:
    """{relative path: sha256} of every file under d. Fails on any traversal error, on a root that is not a real
    directory, and on any entry that is neither a real directory nor a regular file (symlinks included)."""
    import stat
    if d.is_symlink() or not d.is_dir():raise SystemExit(f'not a directory: {d}')
    d=d.resolve();out={}
    def err(e):raise SystemExit(f'cannot read {getattr(e,"filename",d)}: {e}')
    for root,dirs,files in os.walk(d,onerror=err):
        for n in dirs+files:
            p=Path(root)/n;st=os.lstat(p)
            if stat.S_ISDIR(st.st_mode):continue
            if not stat.S_ISREG(st.st_mode):raise SystemExit(f'not a regular file or directory: {p}')
        dirs.sort()
        for f in files:out[str((Path(root)/f).relative_to(d))]=sha(Path(root)/f)
    return dict(sorted(out.items()))

def text(m:dict)->str:return ''.join(f'{h}  {k}\n' for k,h in m.items())

def read_manifest(p:Path)->dict:
    m={}
    for line in p.read_text().splitlines():
        h,k=line.split('  ',1)
        if not re.fullmatch(r'[0-9a-f]{64}',h) or k in m:raise SystemExit(f'malformed manifest line in {p}: {line!r}')
        m[k]=h
    if list(m)!=sorted(m):raise SystemExit(f'manifest {p} is not sorted by path')
    return m

def campaigns(d:Path)->list:return json.loads((d/'production.json').read_text())['campaigns']

def planned_only(d:Path,lab:str)->None:
    prod=json.loads((d/'production.json').read_text())
    if (prod.get('label') or d.name)!=lab or int(prod['seed'])!=A3[lab] or d.name!=lab:raise SystemExit(f'{d}: not the A3 batch {lab} (seed {A3[lab]})')
    touched=[str(d/c/s) for c in prod['campaigns'] for s in ('checkpoints','merged') if os.path.lexists(d/c/s)]
    if touched:raise SystemExit(f'{d}: already has run or merge output: {touched[:3]}')

def early_bound()->dict:
    """Lower bound on the time before any A1 worker can claim a b12 element. A1 workers claim strictly in queue order,
    so every unclaimed element before the first b12 element must be claimed first; when the first b12 element is claimed,
    at most W of them are still running, so the others have finished. Bound: (sum of their predicted costs minus the W
    largest) / (W * SPEED), with W = 2 workers per A1 lane job ever submitted and SPEED = 2 (a symmetry worker measured
    1.3-1.6 times faster than the cost unit, 16 EPYC cores; A1 smoke replay)."""
    Q=R/'queue';o=json.loads((Q/'order.json').read_text())['elements']
    cl={f.rsplit('.',1)[0] for f in os.listdir(Q/'claims')}
    jobs=[l for f in ('lane_jobs_longq.txt','lane_jobs_defq.txt','lane_jobs_preq.txt') for l in (R/f).read_text().split() if l.strip().isdigit()]
    W_=2*len(jobs);SPEED=2.0;dl=json.loads((Q/'deadline.json').read_text())['epoch']
    first=next(i for i,e in enumerate(o) if e['label']=='b12')
    pre=sorted(float(e['cost']) for e in o[:first] if '%s_%04d'%(e['label'],int(e['index'])) not in cl)
    tmin=(sum(pre)-sum(pre[-W_:]))/(W_*SPEED) if len(pre)>W_ else 0.0
    return {'unclaimed_before_b12':len(pre),'workers_assumed':W_,'speed_assumed':SPEED,'min_seconds_to_reach_b12':round(tmin),
            'seconds_to_deadline':round(dl-time.time()),'pass':tmin>dl-time.time()}

def gate(a)->None:
    snap=W/'results'/'C8_A1_close'/'a1_close_snapshot.json'
    ext={x['label']:x for x in json.loads((R/'extension.json').read_text())['extension']}
    if a.early:
        if snap.exists() or (R/'queue_a2').exists() or (R/'queue_a2.staging').exists():raise SystemExit('the A1 close has happened or is under way: use the normal gate')
        b=early_bound()
        if not b['pass']:raise SystemExit(f'early gate: A1 lanes could reach b12 before their deadline: {b}')
        f=os.listdir(R/'queue'/'failed')
        if f:raise SystemExit(f'early gate: the A1 queue has failure records ({f[:3]}): wait for the A1-close snapshot')
        rows=None
    else:
        if not snap.is_file():raise SystemExit('A1-close snapshot not published: export not allowed yet (or use --early before the A1 close)')
        rec=json.loads(snap.read_text())
        if rec.get('schema')!='c8-a1-close-1':raise SystemExit('unexpected snapshot schema')
        rows={x['label']:x for x in rec['batches']}
        order=json.loads((R/'queue_a2'/'order.json').read_text())['elements']
        if sorted({e['label'] for e in order})!=['b10','b11'] or len(order)!=996:raise SystemExit('queue_a2 is not exactly b10 and b11 (996 elements)')
    for lab,seed in A3.items():
        if rows is not None:
            x=rows.get(lab)
            if not x or any(x[k]!=0 for k in ('checkpoints_present','claimed_elements_A1_queue','claimed_elements_A2_queue','done_elements_A1_queue','done_elements_A2_queue')):
                raise SystemExit(f'{lab}: the A1-close snapshot does not record it untouched: {x}')
        if int(ext[lab]['seed'])!=seed or ext[lab]['path']!=lab:raise SystemExit(f'{lab}: extension.json entry differs from A3')
        d=R/lab;planned_only(d,lab)
        if rows is not None and sha(d/'production.json')!=rows[lab]['production_sha256']:raise SystemExit(f'{lab}: production.json changed since the snapshot')
        for q in ('queue','queue_a2'):
            c=[f for f in os.listdir(R/q/'claims') if f.startswith(lab+'_')] if (R/q/'claims').is_dir() else []
            if c:raise SystemExit(f'{lab}: claims in {q}: {c[:3]}')
    print(json.dumps({'gate':'pass','mode':'early' if a.early else 'snapshot','snapshot_sha256':None if a.early else sha(snap),'batches':sorted(A3),
                      'production_sha256':{l:sha(R/l/'production.json') for l in A3}}))

def check_import(planned:Path,imp:Path,man:Path,quiet=False)->tuple:
    """Return (E, P, I) after checking the union of the planned tree and the import against the Expanse manifest E.
    Valid states: fresh (PLANNED untouched, IMPORT complete) and partially or fully installed (each campaign's
    checkpoints/ and merged/ wholly in one of the two trees)."""
    lab=planned.name;E=read_manifest(man);P=tree(planned);I=tree(imp) if imp.exists() else {}
    if imp.exists() and imp.name!=lab:raise SystemExit('import and planned batch names differ')
    cs=set(campaigns(planned))
    prod=json.loads((planned/'production.json').read_text())
    if (prod.get('label') or lab)!=lab or int(prod['seed'])!=A3.get(lab,-1):raise SystemExit(f'{planned}: not an A3 batch')
    base={k:h for k,h in E.items() if not ADDED.fullmatch(k)}  # the planned files, as Expanse holds them
    added={k:h for k,h in E.items() if ADDED.fullmatch(k)}
    bad=[k for k in added if ADDED.fullmatch(k).group(1) not in cs]
    if bad:raise SystemExit(f'{lab}: Expanse added files outside the campaigns: {bad[:3]}')
    pb={k:h for k,h in P.items() if not ADDED.fullmatch(k)}
    if pb!=base:raise SystemExit(f'{lab}: planned files differ between symmetry and the Expanse manifest ({len(set(pb)^set(base))} paths differ)')
    for c in cs:
        if f'{c}/merged/audit.json' not in added:raise SystemExit(f'{lab}: campaign {c} not merged on Expanse')
    for k,h in I.items():
        if E.get(k)!=h:raise SystemExit(f'{lab}: import file {k} not in the Expanse manifest or different')
    for k,h in P.items():
        if E.get(k)!=h:raise SystemExit(f'{lab}: planned-tree file {k} not in the Expanse manifest or different')
    for k in added: # every added file in exactly one tree; each campaign subdirectory wholly in one tree
        if (k in P)==(k in I):raise SystemExit(f'{lab}: {k} is in {"both trees" if k in P else "neither tree"}')
    for c in cs:
        for s in ('checkpoints','merged'):
            ks=[k for k in added if k.startswith(f'{c}/{s}/')]
            if len({k in P for k in ks})>1:raise SystemExit(f'{lab}: {c}/{s} is split between the trees')
    extra=[k for k in I if not ADDED.fullmatch(k) and k not in base]
    if extra:raise SystemExit(f'{lab}: unexpected import files {extra[:3]}')
    if not quiet:print(json.dumps({'check_import':'pass','batch':lab,'files':len(E),'added':len(added),'installed_campaign_dirs':sum(1 for c in cs for s in ('checkpoints','merged') if (planned/c/s).exists())}))
    return E,P,I

def unstage(a)->None:
    """Takes the batch's transfer registration .incoming.<label> (mkdir: atomic) for its whole duration, so it is
    serialized with imports and the close (which refuses while any registration exists, after publishing its lock)."""
    lab=a.label;I=W/'runs'/'ext1_a3_import';G=I/f'.incoming.{lab}'
    if lab not in A3:raise SystemExit('label must be b12, b13 or b14')
    I.mkdir(parents=True,exist_ok=True)
    try:G.mkdir()
    except FileExistsError:raise SystemExit(f'a transfer or unstaging of {lab} is registered ({G})')
    def refuse(m):G.rmdir();raise SystemExit(m)
    if (R/'A3_CLOSE.lock').exists():refuse('the close has begun: unstaging is a new, documented decision now')
    if any(os.path.lexists(R/lab/c/s) for c in campaigns(R/lab) for s in ('checkpoints','merged')):refuse(f'{lab}: partly installed in runs/ext1')
    if not (I/lab).exists() and not (I/f'{lab}.expanse_manifest.txt').exists():refuse(f'{lab}: nothing staged')
    k=0
    while (I/'withdrawn'/f'{lab}.{k}').exists():k+=1
    dst=I/'withdrawn'/f'{lab}.{k}';dst.mkdir(parents=True)
    for src in (I/lab,I/f'{lab}.expanse_manifest.txt',R/f'A3_verified_{lab}.json'):
        if src.exists():os.rename(src,dst/src.name)
    G.rmdir() # last: an interrupted unstaging leaves its registration, which stops the close until inspected
    print('withdrawn to',dst)

def install(a)->None:
    if not os.environ.get('SLURM_JOB_ID') or os.environ.get('SLURM_JOB_NAME')!='c8x-finalize':raise SystemExit('install runs only inside the A3 close job (c8x-finalize)')
    planned,imp,man=a.planned.resolve(),a.imp.resolve(),a.manifest.resolve()
    check_import(planned,imp,man)
    for c in campaigns(planned):
        for s in ('checkpoints','merged'):
            src,dst=imp/c/s,planned/c/s
            if dst.exists():continue # moved by an earlier, interrupted install (check_import proved it whole)
            if not src.is_dir():raise SystemExit(f'missing {src}')
            os.rename(src,dst)
    if tree(planned)!=read_manifest(man):raise SystemExit(f'{planned}: installed tree differs from the Expanse manifest')
    print(json.dumps({'install':'done','batch':planned.name,'files':len(read_manifest(man))}))

def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='action',required=True)
    t=s.add_parser('manifest');t.add_argument('dir',type=Path);g=t.add_mutually_exclusive_group();g.add_argument('--out',type=Path);g.add_argument('--digest',action='store_true')
    t=s.add_parser('gate');t.add_argument('--early',action='store_true')
    t=s.add_parser('check-expanse');t.add_argument('dir',type=Path)
    t=s.add_parser('unstage');t.add_argument('label')
    for n in ('check-import','install'):
        t=s.add_parser(n);t.add_argument('planned',type=Path);t.add_argument('imp',type=Path);t.add_argument('manifest',type=Path)
    a=p.parse_args()
    if a.action=='manifest':
        m=text(tree(a.dir))
        if not m:raise SystemExit(f'{a.dir}: empty tree')
        if a.digest:print(hashlib.sha256(m.encode()).hexdigest());return
        if not a.out:sys.stdout.write(m);return
        if a.out.exists():
            if a.out.read_text()!=m:raise SystemExit(f'{a.out} exists and differs')
            print('manifest exists and matches',a.out);return
        fd,tmp=tempfile.mkstemp(dir=a.out.parent,prefix='.'+a.out.name);os.write(fd,m.encode());os.fsync(fd);os.close(fd)
        try:os.link(tmp,a.out)
        finally:os.unlink(tmp)
        print('manifest written',a.out,len(m.splitlines()),'files');return
    if a.action=='gate':gate(a);return
    if a.action=='check-expanse':planned_only(a.dir.resolve(),a.dir.resolve().name);print('planned and untouched',a.dir);return
    if a.action=='check-import':check_import(a.planned.resolve(),a.imp.resolve(),a.manifest.resolve());return
    if a.action=='unstage':unstage(a);return
    install(a)

if __name__=='__main__':main()
