"""Scheduling only: leave memory headroom before importing a new exact worker.
This changes neither the source partition nor any mathematical operation.
"""
from pathlib import Path
import fcntl,time,os
ROOT=Path(__file__).resolve().parent.parent

def acquire():
 f=(ROOT/'.worker_start.lock').open('a');fcntl.flock(f,fcntl.LOCK_EX)
 cap=int(os.environ.get('F3_START_MEMORY','2800000000'))
 path=Path('/sys/fs/cgroup/memory.stat')
 def used():
  stat=dict(line.split() for line in path.read_text().splitlines())
  return int(stat.get('anon',0))+int(stat.get('kernel',0))
 while path.exists() and used()>cap:time.sleep(2)
 return f

def release(f):fcntl.flock(f,fcntl.LOCK_UN);f.close()
