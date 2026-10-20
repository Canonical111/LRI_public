#!/usr/bin/env python3
"""Build comparison executables from archived sources.
Only remove hard-coded num_threads clauses to permit matched thread counts.
No integrand, RNG, precision, weight or arithmetic expression is changed.
"""
from pathlib import Path
import argparse, shutil, subprocess, sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import toolchain
def main():
 p=argparse.ArgumentParser();p.add_argument('--quad',action='store_true');a=p.parse_args()
 (ROOT/'bin').mkdir(parents=True,exist_ok=True)
 dst=ROOT/'build/reference';shutil.copytree(ROOT/'reference/code',dst,dirs_exist_ok=True)
 for f in dst.rglob('*.cpp'):
  s=f.read_text().replace('num_threads(2)','').replace('num_threads(4)','');f.write_text(s)
 names=[('coordinate_tree_qmc.cpp','reference_qmc'),('coordinate_tree_integrate_allocated.cpp','reference_power')]
 if a.quad:names.append(('precision_quad/coordinate_tree_integrate_allocated.cpp','reference_power_quad'))
 for src,out in names:
  subprocess.run(toolchain.compile_cmd([dst/src],ROOT/'bin'/out,opt=['-O3','-g']),check=True)
if __name__=='__main__':main()
