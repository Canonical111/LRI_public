#!/usr/bin/env python3
"""production.cut_blocks (PLAN D.6, R10; A-ORC-3 "Blocks"): the hand cases and a seeded random oracle. Pure Python.

  python3 -B tests/blocks_test.py [--instances N]     (default 10^4 oracle instances)

Hand cases: 257 equal tasks of 1 s at w = 16 with N = 256 give 129 + 128; 41 tasks of 90 s at w = 4, S = 900 s are cut
greedily into 40 (exactly 900 s) + 1 and rebalanced into 21 + 20 (472.5 s and 450 s); the coarse case (w = 1, S = 240 s,
tasks 100, 100, 40, 1 s) gives 100 | 141 s and records small_block with phi = 100/240; a task with s_t/w > S/2 refuses
naming it; the bootstrap basis cuts by count only. The oracle (exhaustive over the cuts of the last two blocks) agrees
with cut_blocks on validity, phi >= 1/2 for every earlier block, the max-min choice with its tie rule (the larger
B'_{k-1}) and the small_block record.
"""
from __future__ import annotations
import json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import production as prod
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,**info});print('PASS',name,flush=True)
EPS=1e-12

def sizes(r):return [r['bounds'][i+1]-r['bounds'][i]for i in range(len(r['bounds'])-1)]

def hand_cases():
    r=prod.cut_blocks([1.0]*257,256,900.,16)
    assert sizes(r)==[129,128]and r['small_block']is None,sizes(r)
    ok('257 equal tasks of 1 s at w=16, N=256 -> 129 + 128 (never 257)')
    r=prod.cut_blocks([90.0]*41,256,900.,4)
    assert sizes(r)==[21,20]and abs(r['wall'][0]-472.5)<1e-9 and abs(r['wall'][1]-450.)<1e-9 and max(r['wall'])<=900,r
    ok('41 tasks of 90 s at w=4, S=900 s -> 21 + 20 (472.5 s and 450 s), never 922.5 s')
    r=prod.cut_blocks([100.,100.,40.,1.],256,240.,1)
    assert sizes(r)==[1,3]and abs(r['wall'][1]-141.)<1e-9 and r['small_block']=={'block':0,'phi':100/240,'reason':'no valid cut gives both blocks half the target'},r
    ok('coarse case (w=1, S=240 s; 100, 100, 40, 1 s) -> 100 | 141 s with small_block phi = 100/240 and its reason')
    try:prod.cut_blocks([10.,600.,10.],256,900.,1);raise AssertionError('a task above S/2 per thread was accepted')
    except ValueError as e:assert 'task 1'in str(e),e
    ok('a task with s_t/w > S/2 refuses, naming it')
    r=prod.cut_blocks(None,4,900.,1,n=9)
    assert sizes(r)==[4,3,2]and r['wall']is None and abs(r['phi'][-1]-0.5)<1e-12,r
    ok('the bootstrap basis cuts by task count only (phi = |B|/N)')
    r=prod.cut_blocks([1.]*5,8,900.,1)
    assert sizes(r)==[5]and r['small_block']is None
    ok('a shard with a single block is not rebalanced')

def oracle(sec,N,S,w):
    """Greedy, then the exhaustive last-two re-cut (max-min phi, ties to the larger first block)."""
    n=len(sec)
    def W(i,j):return sum(sec[i:j])/w
    def phi(i,j):return max((j-i)/N,W(i,j)/S)
    def valid(i,j):return j-i<=N and W(i,j)<=S*(1+EPS)
    b=[0];i=0
    while i<n:
        j=i+1
        while j<n and valid(i,j+1):j+=1
        b.append(j);i=j
    small=None
    if len(b)>=3 and phi(b[-2],n)<.5:
        i0=b[-3];best=None
        for c in range(i0+1,n):
            if valid(i0,c)and valid(c,n):
                v=min(phi(i0,c),phi(c,n))
                if best is None or v>best[0]+EPS or (abs(v-best[0])<=EPS and c>best[1]):best=(v,c)
        b[-2]=best[1]
        for k in (len(b)-3,len(b)-2):
            if phi(b[k],b[k+1])<.5:small=(k,phi(b[k],b[k+1]));break
    return b,small

def random_oracle(count:int):
    rng=random.Random(20261004);mismatch=0;smalls=0
    for t in range(count):
        N=rng.choice([1,2,3,4,8,16,256]);w=rng.choice([1,2,4,16]);S=rng.choice([60.,240.,900.]);n=rng.randint(1,40)
        sec=[round(rng.uniform(0.01,S/2*w),3)for _ in range(n)]
        r=prod.cut_blocks(sec,N,S,w);b,small=oracle(sec,N,S,w)
        if r['bounds']!=b:mismatch+=1;raise AssertionError(f'instance {t}: bounds {r["bounds"]} != oracle {b} (N={N}, w={w}, S={S}, sec={sec})')
        for i in range(len(b)-1):
            Wb=sum(sec[b[i]:b[i+1]])/w
            assert b[i+1]-b[i]<=N and Wb<=S*(1+EPS),f'instance {t}: block {i} invalid'
            if i<len(b)-3:assert max((b[i+1]-b[i])/N,Wb/S)>=.5-EPS,f'instance {t}: an earlier block {i} has phi < 1/2'
        if small:smalls+=1;assert r['small_block']is not None and r['small_block']['block']==small[0]and abs(r['small_block']['phi']-small[1])<1e-12,(t,small,r['small_block'])
        else:assert r['small_block']is None,(t,r['small_block'])
    ok(f'seeded random oracle: {count} instances agree (validity, phi >= 1/2 for earlier blocks, max-min with ties to the larger first block, small_block)',small_blocks=smalls)

def run(count=10**4):
    hand_cases();random_oracle(count)
    return {'status':'passed','tests':len(RESULTS),'results':RESULTS}
if __name__=='__main__':
    n=int(sys.argv[sys.argv.index('--instances')+1])if '--instances'in sys.argv else 10**4
    print(json.dumps(run(n),indent=1))
