#!/usr/bin/env python3
"""One lane step: run the unmodified point driver (ht3d.hpc.main) with gap-free stop handling.

The lane runner starts this with every stop signal ignored (inherited SIG_IGN), so a stop
cannot kill the interpreter while it starts. Here, before importing anything heavy,
USR1/TERM/INT get a handler that only records a pending stop.
* A stop already pending before the driver is entered: exit 75 at once (nothing claimed).
* A stop pending when ht3d.hpc.run installs its own flag handler (signal.signal is wrapped
  for this hand-off only): the wrapper raises SystemExit(75) there. In hpc.run that is
  before the output claim and before any solver setup, so no expensive work starts (IR10).
* Later stops reach the driver's own handler: checkpoint at the next Newton/publication
  boundary, exit 75.
After the driver returns, the stop signals are set to SIG_IGN, so a re-forwarded stop that
arrives during interpreter shutdown (when CPython resets Python handlers to SIG_DFL)
cannot kill a step that has already published or checkpointed.
Exit code: the driver's own (0 published or reused, 73 claimed, 75 safe stop), 1 on an
uncaught exception (traceback printed).
"""
import signal,sys,traceback
from pathlib import Path

STOPS=(signal.SIGUSR1,signal.SIGTERM,signal.SIGINT)
pending=[]
_install=signal.signal


def _record(s,f):pending.append(s)


def _handoff(sig,handler):
    prev=_install(sig,handler)
    if sig in STOPS and pending and callable(handler):
        handler(pending[-1],None)
        raise SystemExit(75)          # stop raced with launch: leave before claim/solver setup
    return prev


def install():
    for s in STOPS:_install(s,_record)
    signal.signal=_handoff


def main(argv):
    install()
    rc=1
    try:
        if pending:return 75
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'code'))
        from ht3d.hpc import main as driver
        rc=driver(argv)
    except SystemExit as exc:
        rc=exc.code if isinstance(exc.code,int) else 1
    except BaseException:
        traceback.print_exc();rc=1
    finally:
        for s in STOPS:_install(s,signal.SIG_IGN)
        signal.signal=_install
    return rc


if __name__=='__main__':sys.exit(main(sys.argv[1:]))
