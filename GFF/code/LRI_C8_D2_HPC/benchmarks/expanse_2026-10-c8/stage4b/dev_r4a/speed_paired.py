#!/usr/bin/env python3
"""Socket-paired speedups from an r4a_speed.py record (offline; standard library only).

  speed_paired.py SPEED_JSON [--fractions free=0.347,power=0.421] [--mp-speedup S]

r4a_speed.py runs two streams at once, one per socket, and rotates the variants per repeat. With 3 repeats and 2
variants a variant gets two runs on one socket and one on the other, and in job 54666291 socket 1 was about 2% faster
than socket 0 for both binaries, with "base" on socket 0 twice per block. The plain median of 3 then mixes the socket
difference into the speedup. This script compares like with like: per block and socket, the mean integration seconds
of each variant on that socket; the block's speedup is the geometric mean over the two sockets of base/variant. It also
prints the plain medians for reference and, given the MP tier's share of each block (--fractions, the P1 tier timers of
Stage 4a: heavy free L8 34.7%, heavy power L8 42.1%) and a measured MP-tier speedup (--mp-speedup, r4a_mpdiff), the
overall speedup that MP-tier speedup implies: 1/(1 - f + f/S).
"""
import argparse,json,math,statistics,sys

def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('speed_json');ap.add_argument('--fractions',default='free=0.347,power=0.421');ap.add_argument('--mp-speedup',type=float)
    a=ap.parse_args();d=json.load(open(a.speed_json));runs=d['runs'];fr=dict(kv.split('=')for kv in a.fractions.split(','))
    variants=sorted({r['variant']for r in runs}-{'base'});out={}
    for bn in sorted(d['blocks']):
        res={}
        for v in variants:
            per={}
            for s in sorted({r['stream']for r in runs}):
                b=[r['integration_seconds']for r in runs if r['block']==bn and r['variant']=='base'and r['stream']==s]
                c=[r['integration_seconds']for r in runs if r['block']==bn and r['variant']==v and r['stream']==s]
                if b and c:per[s]={'base_mean':statistics.mean(b),'variant_mean':statistics.mean(c),'runs':[len(b),len(c)],'speedup':statistics.mean(b)/statistics.mean(c)}
            paired=math.exp(statistics.mean(math.log(p['speedup'])for p in per.values()))if per else None
            sector=next((k for k in fr if f'_{k}_'in f'_{bn}_'),None);f=float(fr[sector])if sector else None
            implied=1/(1-f+f/a.mp_speedup)if(f and a.mp_speedup)else None
            res[v]={'per_socket':per,'socket_paired_speedup':paired,'median_of_3_speedup':d['blocks'][bn]['speedup_vs_base'][v],
                    'mp_tier_share':f,'implied_by_mp_speedup':implied}
        out[bn]=res
    print(json.dumps({'source':a.speed_json,'slurm_job':d.get('slurm_job'),'mp_speedup':a.mp_speedup,'blocks':out},indent=1))

if __name__=='__main__':sys.exit(main())
