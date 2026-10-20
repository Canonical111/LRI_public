#!/usr/bin/env python3
"""Collect only verified coefficient envelopes; retain scheme and source identities."""
from pathlib import Path
import argparse,csv,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_coeff.storage import read_envelope

def main():
 p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for name in a.inputs:
  d=read_envelope(name);r=d['result'];row=dict(source=str(name),identity=d['identity'],source_digest=d['source_digest'],scheme=r['scheme'],L=r['cutoff'],degree=r['degree'],threads=d['execution']['threads'],seconds=d['execution']['seconds'],peak_rss_GiB=d['execution']['peak_rss_KiB']/2**20)
  row.update({f'C{k}':v for k,v in enumerate(r['C'])});rows.append(row)
 keys=list(dict.fromkeys(k for row in rows for k in row));a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
 print(a.output)
if __name__=='__main__':main()
