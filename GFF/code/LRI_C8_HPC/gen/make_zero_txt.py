"""Write exact_zero_L{L}.txt (count, newline, space-separated class ids, newline) from the
<forest_audit output>.zero.json list, the format of reference/inputs/exact_zero_L5..7.txt.
Usage: python make_zero_txt.py <forest_polynomials.json.zero.json> <outdir> L [L ...]"""
import json,sys
from pathlib import Path
z=json.load(open(sys.argv[1]));out=Path(sys.argv[2])
for L in sys.argv[3:]:
 ids=z[L];(out/f'exact_zero_L{L}.txt').write_text(f'{len(ids)}\n'+' '.join(map(str,ids))+'\n');print(L,len(ids))
