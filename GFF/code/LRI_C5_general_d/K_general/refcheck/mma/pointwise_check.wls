(* refcheck: Mathematica pointwise values of the five spectral integrands (gs:w12, gs:LZspectral, gs:Kweights)
   at d = 5/4, spins l = 0, 3, 1/2 + 3 I (complex, as used by the Abel-Plana tail), nu in {0.1, 0.7, 3, 25, 400}; precision 40.
   Complex l uses the analytic continuation Re F(a+i nu) -> (F(a+i nu)+F(a-i nu))/2, Im F -> (F(a+i nu)-F(a-i nu))/(2i). *)
d = 5/4; q = d/4; wp = 40;
cs = PolyGamma[0, 1] + PolyGamma[0, 2 q]; p0q = PolyGamma[0, q];
vals[l_, nu_] := Module[{a = l/2 + q/2, b, z1, z2, z3, z4, t, P, Re2, Im2, w1, w2, p, h, j, k, r, E2},
   b = a + q; z1 = a + I nu; z2 = a - I nu; z3 = b + I nu; z4 = b - I nu;
   t = Gamma[2 q] Gamma[z1] Gamma[z2]/(Gamma[z3] Gamma[z4]);
   P[m_, z_] := PolyGamma[m, z];
   Re2[m_, x_, y_] := (P[m, x] + P[m, y])/2; Im2[m_, x_, y_] := (P[m, x] - P[m, y])/(2 I);
   w1 = -p0q + (Re2[0, z1, z2] + Re2[0, z3, z4])/2; w2 = (Re2[1, z1, z2] - Re2[1, z3, z4])/8;
   p = Re2[0, z1, z2] + Re2[0, z3, z4]; h = Im2[0, z1, z2] - Im2[0, z3, z4];
   j = Re2[1, z1, z2] - Re2[1, z3, z4]; k = Im2[1, z1, z2] + Im2[1, z3, z4]; r = Re2[2, z1, z2] + Re2[2, z3, z4];
   E2 = -h^2/2 - 5 j/8;
   N[{t^3, t^4, 4 t^4 w1, t^3 (w1^2 + w2/3), t^2 ((cs - p) E2 - h k/2 - 5 r/32)}, wp]];
Do[Print[l, " | ", nu, " | ", StringRiffle[ToString[InputForm[#]] & /@ vals[l, nu], " | "]], {l, {0, 3, 1/2 + 3 I}}, {nu, {1/10, 7/10, 3, 25, 400}}];
Quiet@CloseKernels[];
Exit[0];
