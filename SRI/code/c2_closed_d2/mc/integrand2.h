/* Templated integrand R on S^7 (homogeneous of degree -8+4 delta); inputs in precision RT.
 * eps(0), eps(inf) normalised; spins w1..w4; GFF pairing (12)(34).
 * R = K12 K34 (F - D12 - D34) - T12 - T34 + T12T34.
 */
typedef struct { RT re, im; } SUF(cx);
static inline SUF(cx) SUF(cmk)(RT a, RT b){ SUF(cx) z; z.re=a; z.im=b; return z; }
static inline SUF(cx) SUF(cadd)(SUF(cx) a, SUF(cx) b){ return SUF(cmk)(a.re+b.re, a.im+b.im); }
static inline SUF(cx) SUF(csub)(SUF(cx) a, SUF(cx) b){ return SUF(cmk)(a.re-b.re, a.im-b.im); }
static inline SUF(cx) SUF(cmul)(SUF(cx) a, SUF(cx) b){ return SUF(cmk)(a.re*b.re-a.im*b.im, a.re*b.im+a.im*b.re); }
static inline SUF(cx) SUF(cscal)(SUF(cx) a, RT s){ return SUF(cmk)(a.re*s, a.im*s); }
static inline RT SUF(cabs2)(SUF(cx) a){ return a.re*a.re+a.im*a.im; }
static inline RT SUF(cabs)(SUF(cx) a){ return RSQRT(a.re*a.re+a.im*a.im); }
static inline SUF(cx) SUF(cinv)(SUF(cx) a){ RT n=a.re*a.re+a.im*a.im; return SUF(cmk)(a.re/n, -a.im/n); }
static inline SUF(cx) SUF(cdiv)(SUF(cx) a, SUF(cx) b){ return SUF(cmul)(a, SUF(cinv)(b)); }

/* G5'(c;a,b) = <e0 einf e(c) s(a) s(b)> - <e(c) s s> - |c|^-2 <einf s s> - <e0 s s>; ab = a-b, ca = c-a, cb = c-b given accurately */
static RT SUF(G5p)(SUF(cx) c, SUF(cx) a, SUF(cx) b, SUF(cx) ab, SUF(cx) ca, SUF(cx) cb, RT *mag)
{
    RT lab = RLOG(SUF(cabs)(ab));
    SUF(cx) half_ab = SUF(cscal)(ab, (RT)0.5);
    SUF(cx) Q0 = SUF(cdiv)(half_ab, SUF(cmul)(a,b));
    SUF(cx) Qc = SUF(cdiv)(half_ab, SUF(cmul)(ca, cb));
    SUF(cx) M = half_ab;
    SUF(cx) c2 = SUF(cmul)(c,c);
    SUF(cx) P = SUF(cadd)(SUF(cadd)(Qc,Q0), SUF(cadd)(SUF(cdiv)(M,c2), SUF(cmul)(SUF(cmul)(Q0,Qc),M)));
    RT pre = REXP(-lab/4);
    RT C5 = pre*SUF(cabs)(P);
    RT C3 = pre*SUF(cabs)(Qc);
    RT einf = (RT)0.5*REXP((RT)0.75*lab);
    RT e0 = pre*SUF(cabs)(Q0);
    RT ic2 = 1/SUF(cabs2)(c);
    *mag = C5 + C3 + einf*ic2 + e0;
    return C5 - C3 - einf*ic2 - e0;
}

/* G4'(c,c'), with dcc = c - c' given accurately */
static RT SUF(G4p)(SUF(cx) c, SUF(cx) cp, SUF(cx) dcc, RT *mag)
{
    /* c^2 - c c' + c'^2 = (c - c')^2 + c c' */
    SUF(cx) num = SUF(cadd)(SUF(cmul)(dcc,dcc), SUF(cmul)(c,cp));
    RT a2 = SUF(cabs2)(c), b2 = SUF(cabs2)(cp), d2 = SUF(cabs2)(dcc);
    RT t0 = SUF(cabs2)(num)/(a2*b2*d2);
    *mag = t0 + 1/d2 + 1/a2 + 1/b2;
    return t0 - 1/d2 - 1/a2 - 1/b2;
}

/* inputs: w[i] (RT re/im) ; differences are recomputed in RT (accurate if inputs exact in RT) */
static RT SUF(Rint)(const RT *wre, const RT *wim, RT d, RT *errmag)
{
    SUF(cx) w[4], D[4][4];
    for (int i=0;i<4;i++) w[i] = SUF(cmk)(wre[i], wim[i]);
    RT L[4][4];
    for (int i=0;i<4;i++) for (int j=0;j<4;j++) if (i!=j) D[i][j] = SUF(csub)(w[i],w[j]);
    for (int i=0;i<4;i++) for (int j=i+1;j<4;j++) { L[i][j] = RLOG(SUF(cabs)(D[i][j])); L[j][i]=L[i][j]; }
    static const int E[3][4] = {{1,1,-1,-1},{1,-1,1,-1},{1,-1,-1,1}};
    RT sumH=0, sumS=0;
    SUF(cx) iw[4];
    for (int i=0;i<4;i++) iw[i] = SUF(cinv)(w[i]);
    for (int k=0;k<3;k++) {
        RT lw = 0;
        for (int i=0;i<4;i++) for (int j=i+1;j<4;j++) lw += (RT)(E[k][i]*E[k][j])*L[i][j];
        RT W = REXP(lw/2);
        /* A = sum e_i z_i and B = sum e_i / z_i, written through differences:
           e = (1,1,-1,-1): A = D02 + D13 ; (1,-1,1,-1): A = D01 + D23 ; (1,-1,-1,1): A = D01 + D32 */
        SUF(cx) A;
        if (k==0) A = SUF(cadd)(D[0][2], D[1][3]);
        else if (k==1) A = SUF(cadd)(D[0][1], D[2][3]);
        else A = SUF(cadd)(D[0][1], D[3][2]);
        /* 1/a - 1/b = (b-a)/(ab) */
        SUF(cx) B;
        #define INVD(a,b) SUF(cdiv)(D[b][a], SUF(cmul)(w[a],w[b]))
        if (k==0) B = SUF(cadd)(INVD(0,2), INVD(1,3));
        else if (k==1) B = SUF(cadd)(INVD(0,1), INVD(2,3));
        else B = SUF(cadd)(INVD(0,1), INVD(3,2));
        #undef INVD
        SUF(cx) AB = SUF(cmul)(A,B);
        SUF(cx) P = SUF(cmk)(1 - AB.re/4, -AB.im/4);
        sumH += W*SUF(cabs2)(P);
        sumS += W;
    }
    RT H4 = RSQRT(sumH/2), S4 = RSQRT(sumS/2);
    RT a12 = SUF(cabs)(SUF(cadd)(w[0],w[1])), a34 = SUF(cabs)(SUF(cadd)(w[2],w[3]));
    RT m1 = SUF(cabs)(w[0]), m2 = SUF(cabs)(w[1]), m3 = SUF(cabs)(w[2]), m4 = SUF(cabs)(w[3]);
    RT s12 = REXP(-L[0][1]/4), s34 = REXP(-L[2][3]/4);
    RT H12 = a12*a12/(4*m1*m2)*s12, H34 = a34*a34/(4*m3*m4)*s34;
    RT e0_12 = (RT)0.5*REXP((RT)0.75*L[0][1])/(m1*m2), e0_34 = (RT)0.5*REXP((RT)0.75*L[2][3])/(m3*m4);
    RT ei_12 = (RT)0.5*REXP((RT)0.75*L[0][1]), ei_34 = (RT)0.5*REXP((RT)0.75*L[2][3]);
    RT D12 = e0_12*ei_34, D34 = e0_34*ei_12;
    RT Fp = H4 - S4 - H12*H34 + s12*s34 - D12 - D34;
    RT magF = H4 + S4 + H12*H34 + s12*s34 + D12 + D34;
    RT kexp = (RT)(-3.75) + 2*d;
    RT K12 = REXP(kexp*L[0][1]), K34 = REXP(kexp*L[2][3]);
    RT Phi = K12*K34*Fp;
    RT p12 = REXP(((RT)(-3) + 2*d)*L[0][1]), p34 = REXP(((RT)(-3) + 2*d)*L[2][3]);
    SUF(cx) c12 = SUF(cscal)(SUF(cadd)(w[0],w[1]), (RT)0.5), c34 = SUF(cscal)(SUF(cadd)(w[2],w[3]), (RT)0.5);
    /* accurate differences: c12 - w3 = (D02 + D12)/2, etc. */
    SUF(cx) c12m3 = SUF(cscal)(SUF(cadd)(D[0][2],D[1][2]),(RT)0.5), c12m4 = SUF(cscal)(SUF(cadd)(D[0][3],D[1][3]),(RT)0.5);
    SUF(cx) c34m1 = SUF(cscal)(SUF(cadd)(D[2][0],D[3][0]),(RT)0.5), c34m2 = SUF(cscal)(SUF(cadd)(D[2][1],D[3][1]),(RT)0.5);
    SUF(cx) dcc = SUF(cscal)(SUF(cadd)(c12m3, c12m4), (RT)0.5); /* c12 - c34 */
    RT mg1, mg2, mg3;
    RT g5a = SUF(G5p)(c12, w[2], w[3], D[2][3], c12m3, c12m4, &mg1);
    RT g5b = SUF(G5p)(c34, w[0], w[1], D[0][1], c34m1, c34m2, &mg2);
    RT g4 = SUF(G4p)(c12, c34, dcc, &mg3);
    RT T12 = (RT)0.5*p12*K34*g5a, T34 = (RT)0.5*p34*K12*g5b, TT = (RT)0.25*p12*p34*g4;
    RT R = Phi - T12 - T34 + TT;
    *errmag = K12*K34*magF + (RT)0.5*p12*K34*mg1 + (RT)0.5*p34*K12*mg2 + (RT)0.25*p12*p34*mg3;
    return R;
}
