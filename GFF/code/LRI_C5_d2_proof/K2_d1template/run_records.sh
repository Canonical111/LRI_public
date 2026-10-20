#!/bin/bash
# regenerate the check records sequentially (one Mathematica kernel at a time)
cd <PROJECT>/LRI_C5_d2_proof/K2_d1template
timeout 900 python3 check_routeA_chain_mp.py > check_routeA_chain_mp.out 2>&1
timeout 900 python3 check_residues_mp.py > check_residues_mp.out 2>&1
timeout 600 wolframscript -file exact_algebra.wl 2>&1 | grep -E "^S[123]|^    k=" > exact_algebra.out
timeout 600 wolframscript -file check1_quick.wl 2>&1 | grep -E "^J\(|^Z2|^Thomae" > check1_quick.out
echo "=== done ===" >> exact_algebra.out
