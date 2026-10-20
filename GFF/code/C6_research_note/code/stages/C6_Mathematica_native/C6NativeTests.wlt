(* Run with TestReport after loading C6Native.wl. These tests were supplied,
   not executed in a Wolfram kernel in the authoring environment. *)
VerificationTest[
 Module[{m=1/5,x},x=4m(1-m);
  Abs[N[Hypergeometric2F1[1/4,1/4,1,x]-2EllipticK[m]/Pi,60]]<10^-50],
 True,TestID->"Gauss-to-EllipticK"]
VerificationTest[
 Module[{x=1/3,m,q},m=(1-Sqrt[1-x])/2;q=Gamma[1/4]^4/Pi;
  Abs[N[Sqrt[q]Hypergeometric2F1[1/4,1/4,1/2,1-x]-2(EllipticK[m]+EllipticK[1-m]),60]]<10^-50],
 True,TestID->"Logarithmic-Gauss-to-complementary-K"]
VerificationTest[
 Module[{x=1/4,m,g},m=(1-Sqrt[1-x])/2;
  g=MeijerG[{{1/2},{1/2,1/2}},{{0,0},{0}},x];
  Abs[N[g-4EllipticK[m]EllipticK[1-m]/Pi^(3/2),60]]<10^-50],
 True,TestID->"MeijerG22-to-K-product"]
VerificationTest[
 FreeQ[C6NativeExpression[], _FoxH|_MeijerG], True,
 TestID->"No-FoxH-or-MeijerG-in-active-expression"]
VerificationTest[
 !FreeQ[C6NativeExpression[],Inactive[Integrate]], True,
 TestID->"Explicit-quadrature-not-hidden-as-closed-form"]
