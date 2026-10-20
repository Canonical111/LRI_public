#!/usr/bin/env python3
"""Independently verify every graph identity and exact Wick weight with nauty."""
from __future__ import annotations
import argparse
import collections
from fractions import Fraction
import json
import math
from pathlib import Path
import time
from generate_graphs import ROOT,read,save

def incidence(g,pynauty):
 n=g['L']+1;edges=g['edges'];adj={v:[]for v in range(n+len(edges))}
 for k,(u,v)in enumerate(edges,n):adj[k]=[u,v];adj[u].append(k);adj[v].append(k)
 return pynauty.Graph(n+len(edges),adjacency_dict=adj,vertex_coloring=[set(range(n)),set(range(n,n+len(edges)))])
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,default=ROOT/'inputs');p.add_argument('--output',type=Path,default=ROOT/'verification/census_recheck.json');a=p.parse_args()
 try:import pynauty
 except ImportError as error:raise SystemExit('Independent census verification requires pynauty; normal generation and integration do not')from error
 start=time.time();baseline=read(ROOT/'verification/graph_validation.json');report={'method':'Independent nauty on two-color vertex-edge incidence graphs; exact integer automorphisms and rational Wick weights','loops':{}}
 for L in range(2,9):
  gs=read(ROOT/f'regeneration/graphs_n{L+1}.json');certificates={};sumwa=Fraction();sumwb=Fraction();labelled=0
  for g in gs:
   graph=incidence(g,pynauty);certificate=pynauty.certificate(graph)
   if certificate in certificates:raise AssertionError((L,g['id'],'duplicate graph'))
   certificates[certificate]=g;group=pynauty.autgrp(graph);incidence_aut=int(round(group[1]*10**group[2]));multiplicity=math.prod(math.factorial(k)for k in collections.Counter(map(tuple,g['edges'])).values())
   if incidence_aut%multiplicity:raise AssertionError('Nonintegral vertex automorphism order')
   aut=incidence_aut//multiplicity
   if aut!=g['automorphisms']:raise AssertionError((L,g['id'],'automorphism mismatch'))
   degree=collections.Counter(v for e in g['edges']for v in e);den=aut*multiplicity*math.prod(math.factorial(4-degree[v])for v in range(L+1));mass=sum((4-degree[v])*(3-degree[v])for v in range(L+1))
   if(den,mass)!=(g['denominator'],g['mass_numerator']):raise AssertionError('Wick-weight mismatch')
   sumwa+=Fraction(24,den);sumwb+=Fraction(2*mass,den);labelled+=math.factorial(L+1)//aut
  row={'classes':len(gs),'independent_nauty_unique_classes':len(certificates),'independent_automorphism_checks':len(gs),'labelled_graphs':labelled,'exact_sum_wA':str(sumwa),'exact_sum_wB':str(sumwb)}
  for key,value in row.items():
   if baseline['loops'][str(L)][key]!=value:raise AssertionError((L,key,'delivered census mismatch'))
  if L>=3:
   complete=read(a.inputs/f'complete_inventory_L{L}.json')
   if len(complete)!=len(certificates):raise AssertionError('Incomplete numerical graph inventory')
   seen=set()
   for g in complete:
    certificate=pynauty.certificate(incidence(g,pynauty))
    if certificate not in certificates or certificate in seen:raise AssertionError('Missing or duplicate numerical graph')
    seen.add(certificate);canonical=certificates[certificate]
    if(g['denominator'],g['mass_numerator'],g['automorphisms'])!=(canonical['denominator'],canonical['mass_numerator'],canonical['automorphisms']):raise AssertionError('Numerical graph weight mismatch')
   row['numerical_inventory_exact_isomorphism_matches']=len(seen)
  report['loops'][str(L)]=row;print(f'L{L}: {len(gs)} independent graph and weight checks passed',flush=True)
 report.update(all_checks_passed=True,seconds=time.time()-start);a.output.parent.mkdir(parents=True,exist_ok=True);save(a.output,report)
 print(json.dumps({'all_checks_passed':True,'output':str(a.output)},indent=2))
if __name__=='__main__':main()
