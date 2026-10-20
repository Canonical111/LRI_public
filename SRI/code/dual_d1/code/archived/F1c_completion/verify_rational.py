#!/usr/bin/env python3
from pathlib import Path
from fractions import Fraction
import json
ROOT=Path(__file__).resolve().parent
def main():
 a=json.loads((ROOT/'data/assembly.json').read_text())
 expected={'ct_Q2_b5':Fraction(1020),'ct_K4_b3':Fraction(-7200),
 'ct_lambda2_h4':Fraction(704),'ct_lambda4':Fraction(-184624)}
 for key,v in expected.items():
  assert Fraction(a['parts'][key]['pi0'])==v
 dc=sum(expected.values())
 assert dc==-190100
 P=Fraction(399343,2);dn=Fraction(-8719,2)
 assert -4*(P+dn+dc)==-20848
 r=json.loads((ROOT/'result.json').read_text())
 assert r['Dct_rational']==str(dc)
 assert r['full_C8_not_evaluated']
 print('Independent exact rational assembly:',dc,'; N_delta rational:',-4*(P+dn+dc))
if __name__=='__main__':main()
