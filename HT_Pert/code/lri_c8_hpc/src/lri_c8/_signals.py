"""Record graceful-stop signals that arrive before the solver's StopFlag is installed."""
import signal
pending=None
def _record(signum,frame):
    global pending
    pending=signum
def install():
    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGUSR1):signal.signal(sig,_record)
