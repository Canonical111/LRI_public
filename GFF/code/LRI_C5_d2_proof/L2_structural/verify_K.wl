(* Check of the duality K-star: Barnes side vs reciprocal bilateral side, general parameters, complex tau *)
lam[as_]:=Module[{S=Total[as]},2^(2-2S) Product[Gamma[as[[i]]+as[[j]]],{i,4},{j,i+1,4}] Times@@Gamma[2as]/(Pi^(9/2) Gamma[S-1/2])];
J[m_,as_]:=NIntegrate[Cosh[2Pi m y] Re[Times@@(Gamma[as+I y]Gamma[as-I y])],{y,0,Infinity},WorkingPrecision->40,PrecisionGoal->28,MaxRecursion->40]/Pi;
bil[u_,v_]:=(Times@@Gamma[u]/Times@@Gamma[v]) HypergeometricPFQ[Join[{1},u],v,1] +
   (Times@@(Sin[Pi v]/Sin[Pi u]))(Times@@Gamma[2-v]/Times@@Gamma[2-u]) HypergeometricPFQ[Join[{1},2-v],2-u,1];
OmSharp[tau_,as_]:=Module[{c=1/2+as},Times@@(Sin[Pi(c-tau)]/Pi) bil[1-c+tau,c+tau]];
as={0.21`40,0.17`40,0.26`40,0.19`40};
j0=J[0,as]; j1=J[1,as]; l=lam[as];
Do[Print["tau=",tau,"  Barnes side=",N[j1+j0 Cos[2Pi tau],22],"  reciprocal side=",N[4Pi^7 l OmSharp[tau,as],22]],{tau,{0.13`40+0.07`40 I,0.31`40,0.5`40+0.2`40 I}}];
Iint[as3_,b_]:=NIntegrate[Times@@(Gamma[as3+I y]Gamma[as3-I y])/(Gamma[b+I y]Gamma[b-I y]),{y,-Infinity,Infinity},WorkingPrecision->40,PrecisionGoal->25,MaxRecursion->40]/(2Pi);
rhsR[as3_,b_]:=Module[{A=Total[as3]},2 Sqrt[Pi] 2^(2b-2A) Gamma[as3[[1]]+as3[[2]]]Gamma[as3[[1]]+as3[[3]]]Gamma[as3[[2]]+as3[[3]]] (Times@@Gamma[2as3])/(Gamma[A+1/2-b] Times@@Gamma[as3+b]) HypergeometricPFQ[Join[{2b-1},b-as3],b+as3,1]];
p3={0.31`40+0.05`40 I,0.22`40-0.03`40 I,0.4`40}; bb=0.83`40+0.1`40 I;
Print["R'' complex params: LHS=",N[Iint[p3,bb],22],"  RHS=",N[rhsR[p3,bb],22]];
