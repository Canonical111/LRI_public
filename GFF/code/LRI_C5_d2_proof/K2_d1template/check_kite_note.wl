(* Numerical check: the note's done:kiteFactorization at p = (1,1,1,2-2tau,1) equals Pi^2(F(tau)^2+F(1-tau)^2);
   its four factors equal the Euler-moment forms used in Route B; and the three-term relation (R1). *)
FF[t_?NumericQ] := HypergeometricPFQ[{1/2, 1/2, t}, {1, 1}, 1];
Ob[a_, b_, A_, B_, c_] := Beta[a + 1, c + 1] Beta[a + A + c + 2, B + 1] HypergeometricPFQ[{-b, a + 1, a + A + c + 2}, {a + c + 2, a + A + B + c + 3}, 1];
Mb[a_, b_, A_, B_, c_] := Beta[a + 1, -a - b - c - 1] Beta[B + 1, -A - B - c - 1] HypergeometricPFQ[{-c, a + 1, B + 1}, {-b - c, -A - c}, 1];
kite[p1_, p2_, p3_, p4_, p5_] := Module[{a = -p1/2, b = -p2/2, A = -p3/2, B = -p4/2, c = -p5/2},
   (1/Pi^2) (Sin[Pi a] Sin[Pi B] Ob[a, b, A, B, c] Mb[a, b, A, B, c] + Sin[Pi A] Sin[Pi b] Ob[A, B, a, b, c] Mb[A, B, a, b, c])];
Do[
  Module[{J1 = N[kite[1, 1, 1, 2 - 2 tau, 1], 40], J2 = N[Pi^2 (FF[tau]^2 + FF[1 - tau]^2), 40], X, R1},
   Print["tau=", tau, "  kite(note) = ", NumberForm[J1, 30], "   diff vs Pi^2(F^2+F'^2) = ", N[J1 - J2, 3]];
   Print["   O1 - Pi B(1/2,tau) 3F2 = ", N[Ob[-1/2, -1/2, -1/2, tau - 1, -1/2] - Pi Beta[1/2, tau] HypergeometricPFQ[{1/2, 1/2, 1/2}, {1, 1/2 + tau}, 1], 3],
         "   M1 - Pi Gamma Gamma F(tau) = ", N[Mb[-1/2, -1/2, -1/2, tau - 1, -1/2] - Pi Gamma[tau] Gamma[1 - tau] FF[tau], 3],
         "   O2 - Pi^2 F(1-tau) = ", N[Ob[-1/2, tau - 1, -1/2, -1/2, -1/2] - Pi^2 FF[1 - tau], 3]];
   X = HypergeometricPFQ[{1/2, 1/2, 1/2}, {1, 1/2 + tau}, 1];
   R1 = N[Beta[1/2, tau] X - Pi (FF[tau] + Cot[Pi tau] FF[1 - tau]), 40];
   Print["   (R1) B(1/2,tau) 3F2(1/2,1/2,1/2;1,1/2+tau;1) - Pi[F(tau)+cot(pi tau)F(1-tau)] = ", N[R1, 3]];
  ], {tau, {3/10, 3/5, 1/7}}];
Quiet@CloseKernels[]; Exit[0];
