(* K2 = 14 zeta3 log2 + (1/4)[tau^2] T(tau), T analytic at 0; extract [tau^2] by a Cauchy integral on |tau|=rho
   using the closed form with the true 3F2 functions (no bilinear identity used). *)
wp = 90;
T[tau_] := Module[{fF, fG, Ct},
   fF = HypergeometricPFQ[{1/2, 1/2, tau}, {1, 1}, 1]; fG = HypergeometricPFQ[{tau, tau, tau}, {1/2 + tau, 1/2 + tau}, 1];
   Ct = Gamma[tau]/Gamma[1 - tau];
   Pi^2 fF^2 + Sin[Pi tau]^2 Gamma[tau]^4 fG^2/Gamma[1/2 + tau]^4 - Ct^2 (Gamma[1/2 - tau/2]/Gamma[1/2 + tau/2])^4];
rho = 1/8; Np = 128;
pts = Table[rho Exp[2 Pi I (k + 1/2)/Np], {k, 0, Np - 1}];
vals = N[T /@ pts, wp];
c2 = Total[vals pts^-2]/Np;   (* trapezoid for (1/2 pi i) \oint T tau^-3 d tau *)
c1 = Total[vals pts^-1]/Np; c0 = Total[vals]/Np;
Print["[tau^0]T=", N[c0, 10], "  [tau^1]T=", N[c1, 20], " (-21 z3 = ", N[-21 Zeta[3], 20], ")"];
K2 = 14 Zeta[3] Log[2] + c2/4;
Print["K2 (Cauchy) = ", N[K2, 30]];
Print["32G^2-28 z3 log2 = ", N[32 Catalan^2 - 28 Zeta[3] Log[2], 30]];
Print["C62d 70-digit K2 = 3.5181091385902522416490901703077395226226728094710360690845577954"];
Print["K2(Cauchy) - C62d 70-digit value = ", N[K2 - 35181091385902522416490901703077395226226728094710360690845577954/10^64, 5]];
Print["K2(Cauchy) - (32G^2-28 z3 log2)  = ", N[K2 - (32 Catalan^2 - 28 Zeta[3] Log[2]), 5]];

Quiet@CloseKernels[];
Exit[0];
