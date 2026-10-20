#!/usr/bin/env python3
"""Admission check before one sbatch of the Stage-4a profiling jobs (fails closed). Standard library only, so it runs
with any python3 on the Mac; its constants equal tools/slurm_submit.py's (tests/test_profiling.py checks that).

  ssh expanse "squeue -A yun124 -h -r -o '%i|%T|%P|%q|%D|%u|%j'" | h7_admit.py --site expanse --me zzheng8 \
      --job c8d2-prof1 --partition compute [--nodes 1]
  ssh symmetry "squeue -u zzheng1 -h -r -o '%i|%T|%P|%q|%D|%u|%j'" | h7_admit.py --site symmetry --me zzheng1 \
      --job c8d2-prof4 --partition amddebugq

Expanse, H7E-R (LRI_C8_shared/inventory/DECISIONS.md, 2026-10-03): counting this user's live c8d2-* jobs, a new
compute job is admitted when the session's normal-QOS jobs stay at most 11 running and 27 submitted, the whole yun124
account at most 32 running normal-QOS jobs, and the session's compute nodes at most 4, each counted WITH the new job; a
new shared-partition job when the session's live shared jobs stay at most 32. Symmetry, H7: at most 4 live c8d2-* jobs
of this user in amdq, amddebugq and amdpreq together, the new one included; other jobs of the user (another project's)
are never counted or touched. A line that does not parse refuses (69); a cap that would be exceeded refuses (65).
Prints one JSON line with the counts either way.
"""
import argparse,json,sys,time
H7E_R={'C8_EXP_RUNNING':11,'C8_EXP_SUBMITTED':27,'C8_EXP_ACCOUNT_RUNNING':32,'C8_EXP_SHARED':32,'C8_EXP_NODES':4}
H7_AMD_CAP=4
AMD_PARTITIONS=frozenset({'amdq','amddebugq','amdpreq'})
EXPANSE_NODE_PARTITIONS=frozenset({'compute','debug'})
RUNNING_LIKE=frozenset('RUNNING COMPLETING CONFIGURING STAGE_OUT SIGNALING RESIZING'.split())
LIVE_STATES=frozenset('PENDING RUNNING SUSPENDED CONFIGURING REQUEUED REQUEUE_HOLD REQUEUE_FED SPECIAL_EXIT RESIZING SIGNALING STOPPED RESV_DEL_HOLD POWER_UP_NODE'.split())

class Refused(Exception):
    def __init__(self,code,msg):super().__init__(msg);self.code=code

def records(text):
    out=[]
    for line in text.splitlines():
        if not line.strip():continue
        f=[x.strip()for x in line.split('|',6)]
        if len(f)!=7 or not all(f[i]for i in (0,1,2,5)):raise Refused(69,f'squeue line does not parse as %i|%T|%P|%q|%D|%u|%j: {line[:200]!r}')
        jid,state,part,qos,nodes,user,name=f
        out.append({'jobid':jid,'state':state,'partitions':[p for p in part.split(',')if p],'qos':qos,'nodes':int(nodes)if nodes.isdigit()else 1,'user':user,'name':name})
    return out

def admit(text,site,me,job,partition,nodes=1):
    """The admission record, or Refused(65/69)."""
    if not job.startswith('c8d2-'):raise Refused(64,f'job name {job!r} must start with c8d2-')
    rs=records(text);live=lambda r:r['state']in LIVE_STATES or r['state']in RUNNING_LIKE
    mine=[r for r in rs if r['user']==me and r['name'].startswith('c8d2-')and live(r)]
    rec={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'site':site,'job':job,'partition':partition,'nodes':nodes}
    if site=='expanse':
        acc_run=sum(1 for r in rs if r['qos']=='normal'and r['state']in RUNNING_LIKE)
        my_run=sum(1 for r in mine if r['qos']=='normal'and r['state']in RUNNING_LIKE);my_sub=sum(1 for r in mine if r['qos']=='normal')
        my_shared=sum(1 for r in mine if 'shared'in r['partitions']);my_nodes=sum(r['nodes']for r in mine if set(r['partitions'])&EXPANSE_NODE_PARTITIONS)
        rec.update(account_running_normal=acc_run,my_running_normal=my_run,my_submitted_normal=my_sub,my_shared_live=my_shared,my_compute_nodes_live=my_nodes)
        if partition in EXPANSE_NODE_PARTITIONS:
            checks=[('c8d2 running normal-QOS',my_run+1,H7E_R['C8_EXP_RUNNING']),('c8d2 submitted normal-QOS',my_sub+1,H7E_R['C8_EXP_SUBMITTED']),
                    ('yun124 running normal-QOS',acc_run+1,H7E_R['C8_EXP_ACCOUNT_RUNNING']),('c8d2 compute nodes',my_nodes+nodes,H7E_R['C8_EXP_NODES'])]
        elif partition=='shared':checks=[('c8d2 shared-partition jobs',my_shared+1,H7E_R['C8_EXP_SHARED'])]
        else:raise Refused(64,f'Expanse partition {partition!r}: the profiling jobs use compute or shared')
    elif site=='symmetry':
        amd=[r for r in mine if set(r['partitions'])&AMD_PARTITIONS];rec.update(amd_live=len(amd),amd_live_jobs=[r['jobid']for r in amd])
        if partition not in AMD_PARTITIONS:raise Refused(64,f'symmetry partition {partition!r}: the P4 job uses amddebugq (or amdq)')
        checks=[('c8d2 AMD-pool jobs (amdq, amddebugq, amdpreq)',len(amd)+1,H7_AMD_CAP)]
    else:raise Refused(64,f'unknown site {site!r}')
    rec['checks']={n:{'with_new':v,'cap':c}for n,v,c in checks};over=[n for n,v,c in checks if v>c];rec['admitted']=not over
    if over:raise Refused(65,'admission refused ('+', '.join(over)+'): '+json.dumps(rec,sort_keys=True))
    return rec

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--site',required=True,choices=('expanse','symmetry'));p.add_argument('--me',required=True);p.add_argument('--job',required=True)
    p.add_argument('--partition',required=True);p.add_argument('--nodes',type=int,default=1);a=p.parse_args(argv)
    try:rec=admit(sys.stdin.read(),a.site,a.me,a.job,a.partition,a.nodes)
    except Refused as e:print(f'h7_admit: {e}',file=sys.stderr);return e.code
    print(json.dumps(rec,sort_keys=True));return 0

if __name__=='__main__':sys.exit(main())
