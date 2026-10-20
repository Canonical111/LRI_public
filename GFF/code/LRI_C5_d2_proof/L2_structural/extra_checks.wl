(* Lemma 6: |Gamma(w+iy)Gamma(w-iy)| <= e^(2/3)|Gamma(w)|^2 for Re w >= 1/2 *)
SeedRandom[1];
mx=Max[Table[Module[{w=RandomReal[{0.5,8}]+I RandomReal[{-40,40}],y=RandomReal[{-60,60}]},
   Abs[Gamma[w+I y]Gamma[w-I y]]/Abs[Gamma[w]]^2],{20000}]];
Print["Lemma 6: max ratio over 20000 random samples = ",mx,"   bound e^(2/3) = ",N[Exp[2/3]]];
(* Proposition 2 at x = 2/5: W = gamma(1-x)^4 pi^-4 (A J0 + B J1) *)
Hp[u_,d_]:=Gamma[u]^4/Gamma[u+d]^4 HypergeometricPFQ[{1,u,u,u,u},{u+d,u+d,u+d,u+d},1];
Omt[u_,d_]:=Sin[Pi u]^4 Hp[u,d]+Sin[Pi(u+d)]^4 Hp[2-u-d,d];
AB[x_]:=Module[{d=1-x,p,m},p=Omt[(1-d)/2,d]; m=Omt[-d/2,d]; {(p+m)/2,(p-m)/2}];
J[m_,a_]:=NIntegrate[Cosh[2Pi m y] (Gamma[a+I y]Gamma[a-I y])^4,{y,-Infinity,Infinity},WorkingPrecision->40,PrecisionGoal->28,MaxRecursion->40]/(2Pi);
x=2/5; a=x/2; {aa,bb}=N[AB[x],40];
w2=(Gamma[1-x]/Gamma[x])^4 Pi^-4 (aa Re[J[0,a]] + bb Re[J[1,a]]);
Print["Prop 2 at x=2/5: gamma^4 pi^-4 (A J0 + B J1) = ",N[w2,25],"   W(2/5) = 384.99338524641731699999644567798"];
(* A, B as real-line integrals of reciprocal Gammas vs the 5F4 evaluations, x=2/5 *)
Gx[s_]:=1/(Gamma[1-x/2+s]Gamma[1-x/2-s])^4;
Aint=Pi^4 NIntegrate[Gx[s],{s,-Infinity,Infinity},WorkingPrecision->30,PrecisionGoal->15,MaxRecursion->60,Method->"DoubleExponentialOscillatory"];
Print["A(2/5): integral form = ",Aint,"   mode form = ",N[aa,20]];
