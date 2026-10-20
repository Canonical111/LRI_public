(* A(x), B(x): Fourier coefficients of Omega_x(tau)=pi^4 Sum_k [Gamma(1-x/2+-(k+tau))]^-4 = A + B cos(2 pi tau) *)
Hp[u_,d_]:=Gamma[u]^4/Gamma[u+d]^4 HypergeometricPFQ[{1,u,u,u,u},{u+d,u+d,u+d,u+d},1];
Omt[u_,d_]:=Sin[Pi u]^4 Hp[u,d]+Sin[Pi(u+d)]^4 Hp[2-u-d,d];
AB[x_]:=Module[{d=1-x,p,m},p=Omt[(1-d)/2,d]; m=Omt[-d/2,d]; {(p+m)/2,(p-m)/2}];
W[x_]:=Module[{a,b,c,s},{a,b}=AB[x];c=Cos[Pi x];s=Sin[Pi x];
  (Gamma[1-x]/Gamma[x])^4*4*(2 a b (1+4c^2)+c(3a^2+4b^2)+c^3(2a^2+b^2))/(Pi s^7)];
Wbil[x_]:=Module[{a,b,ap,bp},{a,b}=AB[x];{ap,bp}=AB[1-x];
  2^(4-4x) Gamma[1-x]^4 Gamma[x]^6/(Pi^(11/2) Gamma[2x-1/2]) (a bp + b ap)];
Do[Print[x,"  W(residue)=",N[W[x],25],"  W(bilinear)=",N[Wbil[x],25]],{x,{1/2,2/5,1/3,3/10,0.27`40,0.6`40,0.7`40}}];
(* direct check of Omega_x via reciprocal Gamma bilateral sum at a random tau *)



