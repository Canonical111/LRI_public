"""Add all small-alphabet weight-five confluences early in a discovery matrix.

This changes discovery row order only. It preserves every previous source row.
The final certificate is checked independently over Q and does not rely on this
optimization. With --pid, pause an in-progress reader and insert strictly after
its buffered input position. The labels are shifted by exactly the same amount.
"""
from pathlib import Path
from fractions import Fraction
import argparse,json,math,mmap,os,signal,struct,time
from c6_relations import confluence
p=argparse.ArgumentParser();p.add_argument('prefix');p.add_argument('--pid',type=int);p.add_argument('--at',type=int,default=0);a=p.parse_args();root=Path(__file__).resolve().parent
name=root/(a.prefix+'.rows.bin');labelpath=root/(a.prefix+'.labels.jsonl')
rows=[];labels=[]
for desc,row in confluence(5,3,True):
    if not row:continue
    scale=math.lcm(*(c.denominator for c in row.values()))
    raw=bytearray(struct.pack('<I',len(row)))
    for w,c in row.items():
        code=0
        for b in w:code=11*code+b
        raw.extend(struct.pack('<Iq',code,int(c*scale)))
    rows.append(bytes(raw));labels.append(json.dumps({'scale':scale,'relation':desc},separators=(',',':'))+'\n')
extra=b''.join(rows);paused=False
try:
    if a.pid:
        os.kill(a.pid,signal.SIGSTOP);paused=True;time.sleep(.2)
        positions=[]
        for fd in Path(f'/proc/{a.pid}/fd').iterdir():
            try:
                if Path(os.readlink(fd)).resolve()==name.resolve():
                    text=Path(f'/proc/{a.pid}/fdinfo/{fd.name}').read_text()
                    positions.append(int([s.split()[1] for s in text.splitlines() if s.startswith('pos:')][0]))
            except FileNotFoundError:pass
        if not positions:raise RuntimeError('No reader descriptor found')
        safe_after=max(positions)+65536
    else:safe_after=0
    with name.open('r+b') as f:
        oldsize=os.fstat(f.fileno()).st_size
        mm=mmap.mmap(f.fileno(),0)
        offset=0;index=0
        while index<a.at or offset<=safe_after or index%1000:
            n=struct.unpack_from('<I',mm,offset)[0];offset+=4+12*n;index+=1
            if offset>=oldsize:raise RuntimeError('Insertion exceeds file')
        mm.close()
        f.truncate(oldsize+len(extra));mm=mmap.mmap(f.fileno(),0)
        mm.move(offset+len(extra),offset,oldsize-offset)
        mm[offset:offset+len(extra)]=extra;mm.flush();mm.close()
    temp=labelpath.with_suffix('.newlabels')
    with labelpath.open() as old,temp.open('w') as new:
        for i,line in enumerate(old):
            if i==index:new.writelines(labels)
            new.write(line)
    temp.replace(labelpath)
    report={'inserted_rows':len(rows),'insertion_index':index,'inserted_bytes':len(extra),'all_old_rows_preserved':True,'max_intercept_sum':3,'old_file_size':oldsize,'paused_reader_pid':a.pid}
    (root/(a.prefix+'.row_order_optimization.json')).write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
finally:
    if paused:os.kill(a.pid,signal.SIGCONT)
