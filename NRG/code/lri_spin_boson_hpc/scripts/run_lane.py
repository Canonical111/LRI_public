"""Sequential items inside one allocation; the child solver owns each item lock.

A stop request (SIGUSR1/SIGTERM/SIGINT) creates a stop file that every child
polls after each NRG site and before it starts work. Children are never
signalled, so a child still starting up cannot be killed or miss the request.
"""
import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True)
    p.add_argument('--receipt',required=True)
    p.add_argument('--indices',type=int,nargs='+',required=True)
    p.add_argument('--output-dir',required=True)
    a=p.parse_args()
    interrupted=False
    previous={}
    # Node-local: the children run on this node.
    stopdir=tempfile.mkdtemp(prefix='lri-lane-')
    stopfile=os.path.join(stopdir,'STOP')
    env=os.environ.copy();env['LRI_SPIN_STOP_FILE']=stopfile

    def stop(signum,frame):
        nonlocal interrupted
        interrupted=True
        with open(stopfile,'w'):pass

    try:
        for sig in (signal.SIGUSR1,signal.SIGTERM,signal.SIGINT):
            previous[sig]=signal.signal(sig,stop)
        failed=[]
        for index in a.indices:
            if interrupted:
                return 75
            command=[sys.executable,'-m','lri_spin','item','--manifest',a.manifest,
                '--validation-receipt',a.receipt,'--index',str(index),
                '--output-dir',a.output_dir,'--resume']
            status=subprocess.Popen(command,env=env).wait()
            if interrupted or status==75:
                return 75
            if status not in (0,73):
                failed.append(index)
        if failed:
            print('Failed item indices:',failed,file=sys.stderr)
            return 1
        return 0
    finally:
        for sig,handler in previous.items():
            signal.signal(sig,handler)
        shutil.rmtree(stopdir,ignore_errors=True)


if __name__=='__main__':
    raise SystemExit(main())
