"""Write L{L}_coord.txt.idx in the C7IDX1 format, byte-for-byte the logic of
tools/prepare_inputs.py (graph-header byte offsets) but only for the named files and without
touching hpc_input_manifest.json or the weight files.
Usage: python index_coord.py <L*_coord.txt> [...]"""
import sys
from pathlib import Path
for name in sys.argv[1:]:
 file=Path(name);offsets=[]
 with file.open('rb') as f:
  L,ng=map(int,f.readline().split())
  for expected in range(ng):
   offsets.append(f.tell());row=f.readline().split()
   if len(row)!=6 or int(row[0])!=expected:raise ValueError(f'Invalid graph header {file}:{expected}')
   for _ in range(int(row[5])):
    if not f.readline():raise ValueError(f'Truncated {file}')
  if f.read().strip():raise ValueError(f'Extra data in {file}')
 tmp=file.with_name(file.name+'.idx.tmp');tmp.write_text(f'C7IDX1 {file.stat().st_size} {ng}\n'+'\n'.join(map(str,offsets))+'\n');tmp.replace(file.with_name(file.name+'.idx'))
 print(file.name,L,ng)
