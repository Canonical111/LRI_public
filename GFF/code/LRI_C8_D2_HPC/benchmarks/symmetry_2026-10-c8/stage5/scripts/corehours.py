#!/usr/bin/env python3
"""Core-hours of this session's Stage-5 symmetry jobs (every c8d2-* job of <USER> since 2026-10-05 04:50 EDT; other
<USER> jobs are another project's and are never counted): sacct -X --duplicates, ElapsedRaw x physical cores
(AllocCPUS / ThreadsPerCore of the node: 1 on the AMD EPYC 75x3 nodes, 2 on the Intel Xeon nodes of sharedq and
debugq), every attempt of a requeued job counted.   corehours.py OUT.json"""
import json,subprocess,sys
out=subprocess.run(['sacct','-u','<USER>','-X','--duplicates','-S','2026-10-05T04:50:00','-n','-P','-o','JobID,JobName,Partition,State,ElapsedRaw,AllocCPUS,NodeList,Start,End'],capture_output=True,text=True).stdout
rows=[];tot=0.;by={}
for l in out.strip().splitlines():
    j,n,p,s,e,c,nl,st,en=l.split('|')
    if not n.startswith('c8d2'):continue
    tpc=1 if p.split(',')[0].startswith('amd')else 2   # sinfo: <NODE>-<NODE> Intel 80 CPUs, 2 threads per core; <NODE>+ AMD 64 CPUs, 1
    if nl.startswith('cn')and nl[2:].isdigit():tpc=1 if int(nl[2:])>=77 else 2
    ch=int(e)*int(c)/tpc/3600;tot+=ch;by[p]=by.get(p,0)+ch
    rows.append({'job':j,'name':n,'partition':p,'state':s,'elapsed_s':int(e),'alloc_cpus':int(c),'threads_per_core':tpc,'node':nl,'start':st,'end':en,'core_hours':round(ch,3)})
doc={'rule':__doc__.split('\n')[0],'jobs':rows,'total_core_hours':round(tot,2),'by_partition':{k:round(v,2)for k,v in by.items()}}
open(sys.argv[1],'w').write(json.dumps(doc,indent=1)+'\n');print(json.dumps({k:v for k,v in doc.items()if k!='jobs'}));print(len(rows),'jobs')
