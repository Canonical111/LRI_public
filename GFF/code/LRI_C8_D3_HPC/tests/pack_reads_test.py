#!/usr/bin/env python3
"""F12 (ported from LRI_C8_D2_HPC d5dfd38, C62d's test_pack_reads): every reader of pack members reads exactly the
members' bytes (common.read_member: os.pread in a loop, no Python buffer), and the staged bytes are unchanged.

A fake pack of 48 members with gaps (every fifth adjacent to the one before), of 1 B to 1.2 MB (around and above the
524,288-byte BeeGFS buffer), and a selection of 30 of them (five named twice). For each reader, production.stage_members,
benchkit.stage_members, members.extract_to and stage_runtime's member copy (the last through tests/staging.py, which
runs it on a real plan): every os.pread is counted through a wrapper; the bytes read equal the members' bytes, every read
lies inside a member, the pack is never opened through open() and the staged files equal the members byte for byte;
with an os.pread that returns at most 4,097 bytes per call (short reads) the same bytes are staged; a pack truncated
inside a member is refused and leaves no descriptor open. read_member stops at the end of the file. Control: the
pre-fix read (seek, read through a BufferedReader with BeeGFS's 512 KiB buffer over a counting raw file) of the same
members reads exactly what C62d's replay model predicts, at least one 512 KiB buffer more than the members.
Usage: python3 -B tests/pack_reads_test.py [--output FILE]"""
from __future__ import annotations
import argparse,builtins,hashlib,io,json,os,random,sys,tempfile
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools')]
import common,production,benchkit,members

BEEGFS_BLKSIZE=524288  # os.stat(pack).st_blksize on symmetry's BeeGFS (C62d, 2026-10-05): the buffer size Python's open() picks there

class CountingRaw(io.RawIOBase):
    """A raw file that counts the bytes it reads; under io.BufferedReader it sees every byte the buffered reader reads."""
    def __init__(s,path):super().__init__();s._f=io.FileIO(path,'r');s.nbytes=0
    def readable(s):return True
    def seekable(s):return True
    def readinto(s,b):n=s._f.readinto(b);s.nbytes+=n or 0;return n
    def seek(s,pos,whence=0):return s._f.seek(pos,whence)
    def tell(s):return s._f.tell()
    def close(s):
        if not s.closed:s._f.close()
        super().close()

def buffered_model(spans,B:int)->int:
    """Bytes a CPython BufferedReader with buffer size B reads for seek(offset); read(length) over sorted members (C62d's
    replay model, LRI_C8_D2_HPC tests/unit_orchestration.py)."""
    tot=0;bs=be=None
    for off,ln in spans:
        if not(bs is not None and bs<=off<=be):bs=be=None
        avail=(be-off)if bs is not None else 0
        if ln<=avail:continue
        rem=ln-avail;pos=off+avail;direct=rem-rem%B;tot+=direct;pos+=direct;rem-=direct
        if rem>0:tot+=B;bs,be=pos,pos+B
        else:bs=be=None
    return tot

def open_fds()->int:
    return len(os.listdir('/proc/self/fd'if os.path.isdir('/proc/self/fd')else'/dev/fd'))

def fake_pack(t:Path,L:int):
    rng=random.Random(12);B=BEEGFS_BLKSIZE
    lengths=[1,7,349,2728,4096,4097,33416,94344,B-1,B,B+1,1200000]+[rng.randrange(1,200000)for _ in range(36)];rng.shuffle(lengths)
    rows=[];buf=bytearray()
    for i,n in enumerate(lengths):
        buf+=rng.randbytes(0 if i%5==0 else rng.randrange(1,300000));data=rng.randbytes(n)
        rows.append({'id':i,'offset':len(buf),'length':n,'sha256':hashlib.sha256(data).hexdigest()});buf+=data
    buf+=rng.randbytes(2*B);buf=bytes(buf)   # beyond the last member, so the control's refills are never cut by the end
    inp=t/'inputs';(inp/'packs').mkdir(parents=True);pack=inp/f'packs/free_L{L}.pack';pack.write_bytes(buf)
    inv=json.dumps({'free':{str(L):rows}}).encode();(inp/'inventory.json').write_bytes(inv)
    (inp/'manifest.json').write_text(json.dumps({'sha256':{'inventory.json':hashlib.sha256(inv).hexdigest()}}))
    pick=sorted(rng.sample(range(len(rows)),30))
    return inp,pack,buf,{r['id']:r for r in rows},pick

class Spy:
    """Counts os.pread (optionally capped per call, for short reads) and refuses any open() of the pack."""
    def __init__(s,pack:Path,cap:int|None=None):s.pack=str(pack.resolve());s.cap=cap;s.calls=[]
    def __enter__(s):
        real_pread,real_open,real_path_open=os.pread,builtins.open,Path.open
        def pread(fd,n,off):
            b=real_pread(fd,n if s.cap is None else min(n,s.cap),off);s.calls.append((off,len(b)));return b
        def refuse(f):
            if isinstance(f,(str,os.PathLike))and os.path.realpath(f)==s.pack:raise AssertionError(f'the pack was opened through open(): {f}')
        def opn(f,*a,**k):refuse(f);return real_open(f,*a,**k)
        def path_open(p,*a,**k):refuse(p);return real_path_open(p,*a,**k)   # Path.open does not go through io.open on every Python
        s._p=[mock.patch.object(os,'pread',pread),mock.patch.object(builtins,'open',opn),mock.patch.object(io,'open',opn),mock.patch.object(Path,'open',path_open)]
        for p in s._p:p.start()
        return s
    def __exit__(s,*e):
        for p in reversed(s._p):p.stop()

def readers(inp:Path,pack:Path,inv:dict,L:int):
    """Each reader as f(dest, pack) -> the staged L<L> directory; `pack` lets the truncation case swap the pack."""
    I=lambda pk:NS(pack=lambda sector,LL:pk)
    def prod(dest,pk,ids):production.stage_members(dest,I(pk),'free',L,ids,inv);return dest/f'L{L}'
    def bench(dest,pk,ids):benchkit.stage_members(pk,inv,L,ids,dest);return dest/f'L{L}'
    def memb(dest,pk,ids):
        src=inp
        if pk!=pack:   # a copy of the inputs whose pack is the truncated one
            src=dest.parent/(dest.name+'_inputs');(src/'packs').mkdir(parents=True)
            for n in ('inventory.json','manifest.json'):(src/n).write_bytes((inp/n).read_bytes())
            (src/f'packs/free_L{L}.pack').write_bytes(pk.read_bytes())
        members.extract_to([('free',L,g)for g in ids],dest,src);return dest/f'free/L{L}'
    return {'production.stage_members':(prod,ValueError,'Packed graph content mismatch'),
            'benchkit.stage_members':(bench,benchkit.BenchError,'does not match its inventory sha256'),
            'members.extract_to':(memb,members.MemberError,'differs from its inventory')}

def main()->dict:
    L=5;out={'schema':'c8-d3-pack-reads-1','readers':{}}
    with tempfile.TemporaryDirectory(prefix='c8d3_f12_')as td:
        t=Path(td);inp,pack,buf,inv,pick=fake_pack(t,L)
        ids=pick+pick[:5];want=sum(inv[g]['length']for g in pick)
        spans=[(inv[g]['offset'],inv[g]['offset']+inv[g]['length'])for g in pick]
        member=lambda g:buf[inv[g]['offset']:inv[g]['offset']+inv[g]['length']]
        expect={f'G{g}.txt':member(g)for g in pick}
        staged=lambda d:{f.name:f.read_bytes()for f in d.iterdir()}
        cut=t/'cut.pack';cut.write_bytes(buf[:inv[pick[-1]]['offset']+inv[pick[-1]]['length']//2])
        for name,(f,err,msg) in readers(inp,pack,inv,L).items():
            k=name.replace('.','_')
            with Spy(pack)as s:d=f(t/f'{k}_a',pack,ids)
            assert sum(n for _,n in s.calls)==want,(name,sum(n for _,n in s.calls),want)
            assert all(any(a<=off and off+n<=b for a,b in spans)for off,n in s.calls),(name,'a read outside the members')
            assert staged(d)==expect,(name,'staged bytes differ')
            with Spy(pack,cap=4097)as s2:d2=f(t/f'{k}_b',pack,ids)
            assert sum(n for _,n in s2.calls)==want and len(s2.calls)>len(s.calls)and staged(d2)==expect,(name,'short reads')
            n0=open_fds()
            try:f(t/f'{k}_c',cut,ids);raise AssertionError(f'{name} accepted a truncated pack')
            except err as e:assert msg in str(e),(name,str(e))
            assert open_fds()==n0,(name,'a descriptor left open',open_fds(),n0)
            out['readers'][name]={'preads':len(s.calls),'short_preads':len(s2.calls),'bytes':want,'truncated_pack_refused':True}
        fd=os.open(pack,os.O_RDONLY)
        try:assert common.read_member(fd,len(buf)-10,100)==buf[-10:]and common.read_member(fd,5,0)==b''and common.read_member(fd,len(buf),7)==b''
        finally:os.close(fd)
        raw=CountingRaw(pack)
        with io.BufferedReader(raw,buffer_size=BEEGFS_BLKSIZE)as fh:
            for g in pick:fh.seek(inv[g]['offset']);assert fh.read(inv[g]['length'])==member(g)
            old=raw.nbytes
        model=buffered_model([(inv[g]['offset'],inv[g]['length'])for g in pick],BEEGFS_BLKSIZE)
        assert old==model and old-want>=BEEGFS_BLKSIZE,(old,model,want)
        out.update(members=len(pick),member_bytes=want,prefix_buffered_bytes=old,prefix_overread_per_staged_byte=round((old-want)/want,3),
                   read_member_eof=True,status='passed')
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--output',type=Path);a=ap.parse_args()
    try:rec=main()
    except AssertionError as e:rec={'schema':'c8-d3-pack-reads-1','status':'failed','error':repr(e)}
    text=json.dumps(rec,indent=1)+'\n';print(text,end='')
    if a.output:a.output.write_text(text)
    sys.exit(0 if rec['status']=='passed'else 1)
