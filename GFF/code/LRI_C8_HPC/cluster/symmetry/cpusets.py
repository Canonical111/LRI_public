#!/usr/bin/env python3
"""Print one line per NUMA node of this job's allowed CPUs: '<node> <ncpus> <cpu,list>'.
mode phys: one hardware thread per physical core; mode ht: every allowed hardware thread."""
import os,subprocess,sys,collections
mode=sys.argv[1]
if mode not in ('phys','ht'):sys.exit('mode must be phys or ht')
allowed=os.sched_getaffinity(0);out=subprocess.run(['lscpu','-p=CPU,CORE,SOCKET,NODE'],capture_output=True,text=True,check=True).stdout
by=collections.defaultdict(list);seen=set()
for line in out.splitlines():
    if not line or line[0]=='#':continue
    cpu,core,sock,node=(int(x) if x else 0 for x in line.split(','))
    if cpu not in allowed or (mode=='phys' and (sock,core) in seen):continue
    seen.add((sock,core));by[node].append(cpu)
for node,cpus in sorted(by.items()):print(node,len(cpus),','.join(map(str,sorted(cpus))))
