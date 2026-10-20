"""Recompute retained d=3 formulas at 100 decimal working digits.
This is a formula-side calculation, not independent graph verification.
"""
from pathlib import Path
import sys,json
import mpmath as mp
sys.path.insert(0,str(Path(__file__).resolve().parent/'general_d3'))
import d3_reduction

def printable(value):
    if isinstance(value,dict): return {key:printable(item) for key,item in value.items()}
    if isinstance(value,list): return list(map(printable,value))
    return mp.nstr(value,100)

if __name__=='__main__':
    mp.mp.dps=100
    values=d3_reduction.periods(220,80)
    output=Path(__file__).resolve().parents[1]/'verification/fresh_primitive_values_rerun.json'
    output.write_text(json.dumps({'dps':100,'radial_cutoff':220,'asymptotic_order':80,
              'values':printable(values)},indent=2))
    print(output)
