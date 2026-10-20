(* Terminating case a3 = b + n of (R''):
   LHS = (a2+b)_n (b-a2)_n Gamma(2a1)Gamma(2a2)Gamma(a1+a2)^2/Gamma(2a1+2a2) * F_L,
   F_L = 4F3(-n, a1+a2, a2, a2+1/2; a2+b, 1+a2-b-n, a1+a2+1/2; 1)
   RHS = Pref * F_R,  F_R = 4F3(2b-1, b-a1, b-a2, -n; b+a1, b+a2, 2b+n; 1)
   Whipple 16.4.15 + Whipple 16.4.14:  F_R = K_n F_L *)
ClearAll[a1,a2,b,n];
Pref[n_]:=Module[{a3=b+n,A},A=a1+a2+a3; 2 Sqrt[Pi] 2^(2b-2A) Gamma[a1+a2]Gamma[a1+a3]Gamma[a2+a3] Gamma[2a1]Gamma[2a2]Gamma[2a3]/(Gamma[A+1/2-b]Gamma[a1+b]Gamma[a2+b]Gamma[a3+b])];
Kn[n_]:=Pochhammer[2b,n]Pochhammer[1/2,n]/(Pochhammer[b+1/2,n]Pochhammer[b,n]) * Pochhammer[b-a2,n]Pochhammer[1/2-n-a1-a2,n]/(Pochhammer[b+a1,n]Pochhammer[1/2-n,n]);
LHSpref[n_]:=Pochhammer[a2+b,n]Pochhammer[b-a2,n]Gamma[2a1]Gamma[2a2]Gamma[a1+a2]^2/Gamma[2a1+2a2];
Do[Print["n=",nn,"  prefactor ratio simplifies to: ",FullSimplify[FunctionExpand[Pref[nn]Kn[nn]/LHSpref[nn]]]],{nn,0,5}];
(* check the two 4F3 transformation steps exactly for n=0..4 with random rational parameters *)
FL[n_,p_]:=HypergeometricPFQ[{-n,p[[1]]+p[[2]],p[[2]],p[[2]]+1/2},{p[[2]]+p[[3]],1+p[[2]]-p[[3]]-n,p[[1]]+p[[2]]+1/2},1];
FR[n_,p_]:=HypergeometricPFQ[{2p[[3]]-1,p[[3]]-p[[1]],p[[3]]-p[[2]],-n},{p[[3]]+p[[1]],p[[3]]+p[[2]],2p[[3]]+n},1];
pp={3/17,5/13,7/11};
Do[Print["n=",nn," F_R - K_n F_L = ",Simplify[FR[nn,pp]-(Kn[nn]/.{a1->pp[[1]],a2->pp[[2]],b->pp[[3]]})FL[nn,pp]]],{nn,0,6}];
