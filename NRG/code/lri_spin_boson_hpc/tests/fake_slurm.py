"""Stand-in for sbatch/squeue/sacct in tests; state lives in $FAKE_SLURM_STATE (JSON)."""
import fcntl,json,os,sys
from pathlib import Path

STATE=Path(os.environ['FAKE_SLURM_STATE'])


def load():
    if STATE.exists():return json.loads(STATE.read_text())
    return {'next':1000,'jobs':{},'calls':[],'fail':{}}


def handle(st,cmd,args):
    st['calls'].append([cmd]+args)
    if st['fail'].get(cmd):
        print('fake '+cmd+' failure',file=sys.stderr);return 1
    if cmd=='sbatch':
        name=args[args.index('-J')+1]
        if '--test-only' in args:
            print('sbatch: Job 999 to start at 2026-10-02T00:00:00 using 64 processors on nodes cn100',file=sys.stderr);return 0
        jid=str(st['next']);st['next']+=1
        st['jobs'][jid]={'name':name,'state':'PENDING','live':True,'args':args}
        print(jid);return 0
    if cmd=='squeue':
        for jid,j in st['jobs'].items():
            if j['live']:print(f"{jid}|{j['name']}|{j['state']}")
        return 0
    if cmd=='sacct':
        if '-j' in args:
            jid=args[args.index('-j')+1];j=st['jobs'].get(jid)
            if j:print(f"{jid}|{j['name']}|{j['state']}")
        else:
            name=args[args.index('--name')+1]
            for jid,j in st['jobs'].items():
                if j['name']==name:print(f"{jid}|{j['name']}|{j['state']}")
        return 0
    return 2


def main():
    cmd=sys.argv[1];args=sys.argv[2:]
    with open(str(STATE)+'.lock','a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        st=load();rc=handle(st,cmd,args);STATE.write_text(json.dumps(st))
    return rc


if __name__=='__main__':
    raise SystemExit(main())
