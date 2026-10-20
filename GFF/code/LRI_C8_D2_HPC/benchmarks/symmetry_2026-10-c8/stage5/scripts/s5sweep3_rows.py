#!/usr/bin/env python3
"""J-SWEEP-3 identity check (rerun of the comparison at the end of s5sweep3.slurm, whose inline copy keyed the rows by
'rep'; the file's columns are replicate,graph,jet_0,...): every (replicate, graph) row of graph_replicates.csv of the
Intel J-SWEEP-3 campaign must equal J-SWEEP-2's row (same seed, same chunking, same points), byte for byte as text.
  s5sweep3_rows.py W3 W2 OUT.json"""
import csv,json,sys
from pathlib import Path
w3,w2,out=map(Path,sys.argv[1:4]);m=json.loads((w3/'manifest.json').read_text());res={};bad=0;n=0
def rows(w,name):
    with open(w/'groups'/name/'graph_replicates.csv')as f:
        r=csv.reader(f);head=next(r);return head,{(x[0],x[1]):x for x in r}
for g in m['groups']:
    name=g['name'];h3,a=rows(w3,name);h2,b=rows(w2,name)
    miss=[k for k in a if k not in b];diff=[k for k in a if k in b and a[k]!=b[k]]
    res[name]={'rows':len(a),'header_equal':h3==h2,'missing_in_sweep2':len(miss),'different':len(diff),'examples':[list(k)for k in diff[:3]]};n+=len(a);bad+=len(miss)+len(diff)+(h3!=h2)
doc={'rule':'every (replicate, graph) row of graph_replicates.csv of the J-SWEEP-3 campaign (Intel Xeon Gold 6148) equals J-SWEEP-2\'s row (AMD EPYC 7543): same seed, same chunking, same points',
     'sweep3':str(w3),'sweep2':str(w2),'rows':n,'mismatches':bad,'identical':bad==0,'groups':res}
out.write_text(json.dumps(doc,indent=1)+'\n');print(json.dumps({k:doc[k]for k in('rows','mismatches','identical')}));sys.exit(0 if bad==0 else 3)
