/* c2mc2: independent S^7 Monte Carlo for the O(g^4) eps two-point residue (Gaussian source), v2:
 * points carried in extended precision (QT), accurate relative coordinates, tiered integrand precision,
 * region-restricted antithetic rotations, batch statistics.
 * usage: c2mc2 delta nsamp seed   (env: ANTI, KAP, EPSEX, TINY, ERRTOL, NBATCH)
 */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <stdint.h>
#ifdef USE_QUAD
#include <quadmath.h>
typedef __float128 QT;
#define QSQRT sqrtq
#else
typedef long double QT;
#define QSQRT sqrtl
#endif

#define RT double
#define RSQRT sqrt
#define RLOG log
#define REXP exp
#define SUF(n) n##_d
#include "integrand2.h"
#undef RT
#undef RSQRT
#undef RLOG
#undef REXP
#undef SUF

#define RT long double
#define RSQRT sqrtl
#define RLOG logl
#define REXP expl
#define SUF(n) n##_l
#include "integrand2.h"
#undef RT
#undef RSQRT
#undef RLOG
#undef REXP
#undef SUF

#ifdef USE_QUAD
#define RT __float128
#define RSQRT sqrtq
#define RLOG logq
#define REXP expq
#define SUF(n) n##_q
#include "integrand2.h"
#undef RT
#undef RSQRT
#undef RLOG
#undef REXP
#undef SUF
#endif

/* ---------------- RNG ---------------- */
static uint64_t s[4];
static inline uint64_t rotl(const uint64_t x, int k){ return (x << k) | (x >> (64 - k)); }
static uint64_t next64(void){
    const uint64_t result = rotl(s[1] * 5, 7) * 9;
    const uint64_t t = s[1] << 17;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45);
    return result;
}
static void seed_rng(uint64_t seed){
    uint64_t z = seed;
    for (int i=0;i<4;i++){ z += 0x9e3779b97f4a7c15ULL; uint64_t x=z; x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL; x=(x^(x>>27))*0x94d049bb133111ebULL; s[i]=x^(x>>31); }
}
static inline double unif(void){ return ((next64() >> 11) + 0.5) * (1.0/9007199254740992.0); }
static double gauss(void){ static int have=0; static double g2; if(have){have=0;return g2;}
    double u1=unif(), u2=unif(); double r=sqrt(-2*log(u1)); g2=r*sin(2*M_PI*u2); have=1; return r*cos(2*M_PI*u2); }
static double gamma_ge1(double a){ /* Marsaglia-Tsang, a>=1 */
    double d=a-1.0/3, c=1/sqrt(9*d);
    for(;;){ double x=gauss(), v=1+c*x; if(v<=0) continue; v=v*v*v; double u=unif();
        if(u<1-0.0331*x*x*x*x) return d*v; if(log(u)<0.5*x*x+d*(1-v+log(v))) return d*v; }
}
/* returns log of a Gamma(a) variate (to avoid underflow for tiny a) */
static double lgamma_rv(double a){
    if (a>=1) return log(gamma_ge1(a));
    return log(gamma_ge1(a+1)) + log(unif())/a;
}

/* ---------------- channels ---------------- */
/* coordinates y = L w (L real orthogonal 4x4 acting on complex coords) */
#define MAXF 3
typedef struct {
    int type;          /* 1: A (one coord), 2: B (two coords), 3: C (three coords) */
    int j[3];          /* coordinate indices */
    double a;          /* radial exponent: h ~ u^a (A: |y|^{2a}) */
    double b[3];       /* t exponents (B: t^b0 (1-t)^b1 ; C: t_i^b_i) */
} Factor;
typedef struct {
    char name[32];
    double L[4][4];
    int nf; Factor f[MAXF];
    double logZ, deg, logproj; /* logproj = log(Gamma((8+deg)/2)/(2Z)) */
    double alpha;
} Channel;

static Channel ch[96]; static int nch=0;

static void set_identity(double L[4][4]){ memset(L,0,sizeof(double)*16); for(int i=0;i<4;i++) L[i][i]=1; }

static void finalize(Channel *c){
    double logZ=0, deg=0; int used[4]={0,0,0,0};
    for (int k=0;k<c->nf;k++){
        Factor *f=&c->f[k];
        if (f->type==1){ logZ += log(M_PI)+lgamma(1+f->a); used[f->j[0]]=1; deg += 2*f->a; }
        else if (f->type==2){ logZ += 2*log(M_PI)+lgamma(f->a+2)+lgamma(f->b[0]+1)+lgamma(f->b[1]+1)-lgamma(f->b[0]+f->b[1]+2);
            used[f->j[0]]=used[f->j[1]]=1; deg += 2*f->a; }
        else { logZ += 3*log(M_PI)+lgamma(f->a+3)+lgamma(f->b[0]+1)+lgamma(f->b[1]+1)+lgamma(f->b[2]+1)-lgamma(f->b[0]+f->b[1]+f->b[2]+3);
            used[f->j[0]]=used[f->j[1]]=used[f->j[2]]=1; deg += 2*f->a; }
    }
    for (int i=0;i<4;i++) if(!used[i]) logZ += log(M_PI);
    c->logZ=logZ; c->deg=deg; c->logproj = lgamma((8+deg)/2) - log(2.0) - logZ;
}

/* log h at point y (complex coords yr, yi) */
static double logh(const Channel *c, const double *yr, const double *yi){
    double lh=0;
    for (int k=0;k<c->nf;k++){
        const Factor *f=&c->f[k];
        if (f->type==1){ int j=f->j[0]; double m=yr[j]*yr[j]+yi[j]*yi[j]; lh += f->a*log(m); }
        else if (f->type==2){ int j0=f->j[0], j1=f->j[1];
            double m0=yr[j0]*yr[j0]+yi[j0]*yi[j0], m1=yr[j1]*yr[j1]+yi[j1]*yi[j1], u=m0+m1;
            lh += f->a*log(u) + f->b[0]*log(m0/u) + f->b[1]*log(m1/u); }
        else { double m[3], u=0; for(int q=0;q<3;q++){ int j=f->j[q]; m[q]=yr[j]*yr[j]+yi[j]*yi[j]; u+=m[q]; }
            lh += f->a*log(u); for(int q=0;q<3;q++) if (f->b[q]!=0) lh += f->b[q]*log(m[q]/u); }
    }
    return lh;
}

/* sample y from density ~ h(y) e^{-|y|^2} */
static void sample_y(const Channel *c, double *yr, double *yi){
    int used[4]={0,0,0,0};
    for (int k=0;k<c->nf;k++){
        const Factor *f=&c->f[k];
        if (f->type==1){ int j=f->j[0]; double lm=lgamma_rv(1+f->a); double r=exp(0.5*lm), ph=2*M_PI*unif();
            yr[j]=r*cos(ph); yi[j]=r*sin(ph); used[j]=1; }
        else if (f->type==2){ double lu=lgamma_rv(f->a+2); double lx=lgamma_rv(f->b[0]+1), ly=lgamma_rv(f->b[1]+1);
            /* t = X/(X+Y) computed in logs */
            double mx = lx>ly?lx:ly; double lt = lx - (mx + log(exp(lx-mx)+exp(ly-mx))); double l1t = ly - (mx + log(exp(lx-mx)+exp(ly-mx)));
            double m0 = exp(lu+lt), m1 = exp(lu+l1t);
            int j0=f->j[0], j1=f->j[1]; double p0=2*M_PI*unif(), p1=2*M_PI*unif();
            yr[j0]=sqrt(m0)*cos(p0); yi[j0]=sqrt(m0)*sin(p0); yr[j1]=sqrt(m1)*cos(p1); yi[j1]=sqrt(m1)*sin(p1);
            used[j0]=used[j1]=1; }
        else { double lu=lgamma_rv(f->a+3); double lg[3], mx=-1e300;
            for(int q=0;q<3;q++){ lg[q]=lgamma_rv(f->b[q]+1); if(lg[q]>mx) mx=lg[q]; }
            double ss=0; for(int q=0;q<3;q++) ss+=exp(lg[q]-mx); double lsum = mx+log(ss);
            for(int q=0;q<3;q++){ int j=f->j[q]; double m=exp(lu+lg[q]-lsum); double p=2*M_PI*unif();
                yr[j]=sqrt(m)*cos(p); yi[j]=sqrt(m)*sin(p); used[j]=1; } }
    }
    for (int j=0;j<4;j++) if(!used[j]){ yr[j]=gauss()*M_SQRT1_2; yi[j]=gauss()*M_SQRT1_2; }
}

static void apply_L(const double L[4][4], const double *wr, const double *wi, double *yr, double *yi){
    for (int a=0;a<4;a++){ yr[a]=0; yi[a]=0; for(int i=0;i<4;i++){ yr[a]+=L[a][i]*wr[i]; yi[a]+=L[a][i]*wi[i]; } }
}
static void apply_LT(const double L[4][4], const double *yr, const double *yi, double *wr, double *wi){
    for (int i=0;i<4;i++){ wr[i]=0; wi[i]=0; for(int a=0;a<4;a++){ wr[i]+=L[a][i]*yr[a]; wi[i]+=L[a][i]*yi[a]; } }
}

/* Jacobi matrices */
static void L_pair(double L[4][4], int a, int b){ /* rows: r_ab, c_ab, other two */
    memset(L,0,sizeof(double)*16); L[0][a]=M_SQRT1_2; L[0][b]=-M_SQRT1_2; L[1][a]=M_SQRT1_2; L[1][b]=M_SQRT1_2;
    int r=2; for(int i=0;i<4;i++) if(i!=a&&i!=b){ L[r][i]=1; r++; } }
static void L_pairpair(double L[4][4]){ /* r12, c12, r34, c34 */
    memset(L,0,sizeof(double)*16); L[0][0]=M_SQRT1_2; L[0][1]=-M_SQRT1_2; L[1][0]=M_SQRT1_2; L[1][1]=M_SQRT1_2;
    L[2][2]=M_SQRT1_2; L[2][3]=-M_SQRT1_2; L[3][2]=M_SQRT1_2; L[3][3]=M_SQRT1_2; }
static void L_triple(double L[4][4], int a, int b, int k, int l){ /* r_ab, s, C3, w_l */
    memset(L,0,sizeof(double)*16);
    L[0][a]=M_SQRT1_2; L[0][b]=-M_SQRT1_2;
    double q=sqrt(2.0/3.0); L[1][a]=0.5*q; L[1][b]=0.5*q; L[1][k]=-q;
    double t=1/sqrt(3.0); L[2][a]=t; L[2][b]=t; L[2][k]=t; L[3][l]=1; }
static void L_triple4(double L[4][4], int a, int b, int k, int l){ /* r_ab, s, v, C4 */
    L_triple(L,a,b,k,l);
    double v=sqrt(0.75); L[2][a]=v/3; L[2][b]=v/3; L[2][k]=v/3; L[2][l]=-v;
    memset(L[3],0,sizeof(double)*4); for(int i=0;i<4;i++) L[3][i]=0.5; }
static void L_quad(double L[4][4]){ /* r12, r34, s=c12-c34, C4 */
    memset(L,0,sizeof(double)*16); L[0][0]=M_SQRT1_2; L[0][1]=-M_SQRT1_2; L[1][2]=M_SQRT1_2; L[1][3]=-M_SQRT1_2;
    L[2][0]=0.5; L[2][1]=0.5; L[2][2]=-0.5; L[2][3]=-0.5; for(int i=0;i<4;i++) L[3][i]=0.5; }

static Factor FA(int j, double a){ Factor f; memset(&f,0,sizeof f); f.type=1; f.j[0]=j; f.a=a; return f; }
static Factor FB(int j0, int j1, double a, double b0, double b1){ Factor f; memset(&f,0,sizeof f); f.type=2; f.j[0]=j0; f.j[1]=j1; f.a=a; f.b[0]=b0; f.b[1]=b1; return f; }
static Factor FC(int j0,int j1,int j2,double a,double b0,double b1,double b2){ Factor f; memset(&f,0,sizeof f); f.type=3; f.j[0]=j0; f.j[1]=j1; f.j[2]=j2; f.a=a; f.b[0]=b0; f.b[1]=b1; f.b[2]=b2; return f; }

static Channel *newch(const char *nm, double alpha){ Channel *c=&ch[nch++]; memset(c,0,sizeof *c); strncpy(c->name,nm,31); c->alpha=alpha; set_identity(c->L); return c; }

static void build_channels(double d, int only){
    double ep=d, et=d, eq=2*d, ee=d, ev=d;
    Channel *c;
    c=newch("U",1.0);
    c=newch("P12",1.0); L_pair(c->L,0,1); c->f[c->nf++]=FA(0,-1+ep);
    c=newch("P34",1.0); L_pair(c->L,2,3); c->f[c->nf++]=FA(0,-1+ep);
    c=newch("PP",1.0); L_pairpair(c->L); c->f[c->nf++]=FA(0,-1+ep); c->f[c->nf++]=FA(2,-1+ep);
    for (int i=0;i<4;i++){ char nm[16]; sprintf(nm,"Z%d",i+1); c=newch(nm,0.5); c->f[c->nf++]=FA(i,-0.5); }
    int tri[4][4]={{0,1,2,3},{0,1,3,2},{2,3,0,1},{2,3,1,0}};
    for (int q=0;q<4;q++){ char nm[16]; sprintf(nm,"Tr%d%d_%d",tri[q][0]+1,tri[q][1]+1,tri[q][2]+1);
        c=newch(nm,1.0); L_triple(c->L,tri[q][0],tri[q][1],tri[q][2],tri[q][3]); c->f[c->nf++]=FB(0,1,-2+et,-1+ep,-0.5); }
    for (int q=0;q<4;q++){ char nm[16]; sprintf(nm,"Tr4_%d%d_%d",tri[q][0]+1,tri[q][1]+1,tri[q][2]+1);
        c=newch(nm,0.5); L_triple4(c->L,tri[q][0],tri[q][1],tri[q][2],tri[q][3]); c->f[c->nf++]=FB(0,1,-2+et,-1+ep,-0.5); c->f[c->nf++]=FA(2,-1+ev); }
    c=newch("Q",1.0); L_quad(c->L); c->f[c->nf++]=FC(0,1,2,-3+eq,-1+ep,-1+ep,0);
    c=newch("E2_12",0.5); L_pair(c->L,0,1); c->f[c->nf++]=FB(0,1,-1.5,-1+ep,0);
    c=newch("E2_34",0.5); L_pair(c->L,2,3); c->f[c->nf++]=FB(0,1,-1.5,-1+ep,0);
    int e3[4][3]={{0,1,2},{0,1,3},{2,3,0},{2,3,1}};
    for (int q=0;q<4;q++){ char nm[16]; sprintf(nm,"E3_%d%d_%d",e3[q][0]+1,e3[q][1]+1,e3[q][2]+1);
        c=newch(nm,0.5); L_pair(c->L,e3[q][0],e3[q][1]);
        /* in L_pair rows: 0=r_ab,1=c_ab, 2,3 = remaining in increasing index order */
        int krow = -1, r=2; for(int i=0;i<4;i++) if(i!=e3[q][0]&&i!=e3[q][1]){ if(i==e3[q][2]) krow=r; r++; }
        c->f[c->nf++]=FC(0,1,krow,-2.5+ee,-1+ep,0,0); }
    /* artificial region of the global subtraction terms: c12, w3, w4 -> 0 (and 34 <-> 12) */
    c=newch("A12",0.5); L_pair(c->L,0,1); c->f[c->nf++]=FC(1,2,3,-2.5+ee,0,0,0);
    c=newch("A34",0.5); L_pair(c->L,2,3); c->f[c->nf++]=FC(1,2,3,-2.5+ee,0,0,0);
    /* nested variants */
    c=newch("A12b",0.5); L_pair(c->L,0,1); c->f[c->nf++]=FC(1,2,3,-2.5+ee,-0.5,-0.5,-0.5);
    c=newch("A34b",0.5); L_pair(c->L,2,3); c->f[c->nf++]=FC(1,2,3,-2.5+ee,-0.5,-0.5,-0.5);
    c=newch("A12c",0.5); L_pairpair(c->L); c->f[c->nf++]=FC(2,3,1,-2.5+ee,0,-0.5,-0.5); /* (r34',c34',c12') */
    c=newch("A34c",0.5); L_pairpair(c->L); c->f[c->nf++]=FC(0,1,3,-2.5+ee,0,-0.5,-0.5); /* (r12',c12',c34') */
    c=newch("Cc",0.5); L_pairpair(c->L); c->f[c->nf++]=FA(1,-0.5); c->f[c->nf++]=FA(3,-0.5);
    c=newch("E2b_12",0.25); c->f[c->nf++]=FB(0,1,-1.5,-0.5,-0.5);
    c=newch("E2b_34",0.25); c->f[c->nf++]=FB(2,3,-1.5,-0.5,-0.5);
    { int e3b[4][3]={{0,1,2},{0,1,3},{2,3,0},{2,3,1}};
      for (int q=0;q<4;q++){ char nm[16]; sprintf(nm,"E3b_%d%d_%d",e3b[q][0]+1,e3b[q][1]+1,e3b[q][2]+1);
        c=newch(nm,0.25); c->f[c->nf++]=FC(e3b[q][0],e3b[q][1],e3b[q][2],-2.5+ee,-0.5,-0.5,-0.5); } }
    for (int i=0;i<4;i++) for (int j=i+1;j<4;j++){ char nm[16]; sprintf(nm,"Z%dZ%d",i+1,j+1);
        c=newch(nm,0.125); c->f[c->nf++]=FA(i,-0.5); c->f[c->nf++]=FA(j,-0.5); }
    c=newch("P12xE2_34",0.5); L_pairpair(c->L); c->f[c->nf++]=FA(0,-1+ep); c->f[c->nf++]=FB(2,3,-1.5,-1+ep,0);
    c=newch("P34xE2_12",0.5); L_pairpair(c->L); c->f[c->nf++]=FA(2,-1+ep); c->f[c->nf++]=FB(0,1,-1.5,-1+ep,0);
    /* pair x Z */
    { int pz[4][3]={{0,1,2},{0,1,3},{2,3,0},{2,3,1}};
      for(int q=0;q<4;q++){ char nm[16]; sprintf(nm,"P%d%dxZ%d",pz[q][0]+1,pz[q][1]+1,pz[q][2]+1);
        c=newch(nm,0.25); L_pair(c->L,pz[q][0],pz[q][1]); c->f[c->nf++]=FA(0,-1+ep);
        int r=2,zrow=-1; for(int i=0;i<4;i++) if(i!=pz[q][0]&&i!=pz[q][1]){ if(i==pz[q][2]) zrow=r; r++; }
        c->f[c->nf++]=FA(zrow,-0.5); } }
    /* triple x Z(l) */
    for (int q=0;q<4;q++){ char nm[20]; sprintf(nm,"Tr%d%d_%dxZ%d",tri[q][0]+1,tri[q][1]+1,tri[q][2]+1,tri[q][3]+1);
        c=newch(nm,0.25); L_triple(c->L,tri[q][0],tri[q][1],tri[q][2],tri[q][3]); c->f[c->nf++]=FB(0,1,-2+et,-1+ep,-0.5); c->f[c->nf++]=FA(3,-0.5); }
    for (int q=0;q<4;q++){ char nm[24]; sprintf(nm,"Tr%d%d_%dxZC",tri[q][0]+1,tri[q][1]+1,tri[q][2]+1);
        c=newch(nm,0.25); L_triple(c->L,tri[q][0],tri[q][1],tri[q][2],tri[q][3]); c->f[c->nf++]=FB(0,1,-2+et,-1+ep,-0.5); c->f[c->nf++]=FA(2,-0.5); }
    double sa=0; for(int k=0;k<nch;k++){ finalize(&ch[k]); }
    if (only>=0){ for(int k=0;k<nch;k++) ch[k].alpha = (k==only)?1.0:0.0; }
    for(int k=0;k<nch;k++) sa+=ch[k].alpha; for(int k=0;k<nch;k++) ch[k].alpha/=sa;
}


/* ---------------- points ---------------- */
typedef struct {
    QT qr[4], qi[4];          /* extended-precision unit point */
    double wr[4], wi[4];      /* double copy */
    double dr[4][4], di[4][4];/* accurate differences w_i - w_j */
} Point;

static void point_finish(Point *P){
    QT nn=0; for(int i=0;i<4;i++) nn += P->qr[i]*P->qr[i]+P->qi[i]*P->qi[i];
    nn = QSQRT(nn);
    for(int i=0;i<4;i++){ P->qr[i]/=nn; P->qi[i]/=nn; P->wr[i]=(double)P->qr[i]; P->wi[i]=(double)P->qi[i]; }
    for(int i=0;i<4;i++) for(int j=0;j<4;j++){ P->dr[i][j]=(double)(P->qr[i]-P->qr[j]); P->di[i][j]=(double)(P->qi[i]-P->qi[j]); }
}

/* value of row a of L at point, using support-based differences when coefficients sum to zero */
static void rowval(const double *Lrow, const Point *P, double *vr, double *vi){
    double s=0; int ref=-1; for(int i=0;i<4;i++){ s+=Lrow[i]; if (Lrow[i]!=0 && ref<0) ref=i; }
    *vr=0; *vi=0;
    if (fabs(s) < 1e-12){
        /* choose reference as last index in support (any in support is fine) */
        for(int i=0;i<4;i++) if (Lrow[i]!=0) ref=i;
        for(int i=0;i<4;i++) if (Lrow[i]!=0 && i!=ref){ *vr += Lrow[i]*P->dr[i][ref]; *vi += Lrow[i]*P->di[i][ref]; }
    } else {
        for(int i=0;i<4;i++){ *vr += Lrow[i]*P->wr[i]; *vi += Lrow[i]*P->wi[i]; }
    }
}

static double qmix(const Point *P, double *qk){
    double q=0, yr[4], yi[4];
    for (int k=0;k<nch;k++){
        if (ch[k].alpha==0){ qk[k]=0; continue; }
        for (int a=0;a<4;a++) rowval(ch[k].L[a], P, &yr[a], &yi[a]);
        double lq = logh(&ch[k],yr,yi) + ch[k].logproj;
        qk[k]=exp(lq); q += ch[k].alpha*qk[k];
    }
    return q;
}

static double eps_ex = 1e-5, TINY = 1e-26, ERRTOL = 1e-4, KAP = 0.2;
static int ANTI = 2;

static double hyp2(double x, double y){ return sqrt(x*x+y*y); }

/* geometric excision on accurate differences: returns code>0 if excised */
static int excise(const Point *P){
    /* tiny-scale guard */
    for(int i=0;i<4;i++) for(int j=i+1;j<4;j++) if (hyp2(P->dr[i][j],P->di[i][j]) < TINY) return 6;
    for(int i=0;i<4;i++) if (hyp2(P->wr[i],P->wi[i]) < TINY) return 6;
    double r, dmin, t;
    /* pair 12: d12 = min(|c12|, |c12-w3|, |c12-w4|) */
    r = hyp2(P->dr[0][1],P->di[0][1]);
    dmin = hyp2(0.5*(P->wr[0]+P->wr[1]), 0.5*(P->wi[0]+P->wi[1]));
    t = hyp2(0.5*(P->dr[0][2]+P->dr[1][2]), 0.5*(P->di[0][2]+P->di[1][2])); if(t<dmin) dmin=t;
    t = hyp2(0.5*(P->dr[0][3]+P->dr[1][3]), 0.5*(P->di[0][3]+P->di[1][3])); if(t<dmin) dmin=t;
    if (r < eps_ex*dmin) return 1;
    r = hyp2(P->dr[2][3],P->di[2][3]);
    dmin = hyp2(0.5*(P->wr[2]+P->wr[3]), 0.5*(P->wi[2]+P->wi[3]));
    t = hyp2(0.5*(P->dr[2][0]+P->dr[3][0]), 0.5*(P->di[2][0]+P->di[3][0])); if(t<dmin) dmin=t;
    t = hyp2(0.5*(P->dr[2][1]+P->dr[3][1]), 0.5*(P->di[2][1]+P->di[3][1])); if(t<dmin) dmin=t;
    if (r < eps_ex*dmin) return 2;
    /* 4-cluster: internal rms vs |C4| ; internal sum_i |w_i - C|^2 = (1/4) sum_{i<j} |d_ij|^2 */
    { double u=0; for(int i=0;i<4;i++) for(int j=i+1;j<4;j++) u += P->dr[i][j]*P->dr[i][j]+P->di[i][j]*P->di[i][j]; u*=0.25;
      double Cr=0.25*(P->wr[0]+P->wr[1]+P->wr[2]+P->wr[3]), Ci=0.25*(P->wi[0]+P->wi[1]+P->wi[2]+P->wi[3]);
      if (sqrt(u) < eps_ex*hyp2(Cr,Ci)) return 3; }
    { double m[4]; for(int i=0;i<4;i++) m[i]=P->wr[i]*P->wr[i]+P->wi[i]*P->wi[i];
      if (m[0]+m[1] < eps_ex*eps_ex*fmin(m[2],m[3])) return 4;
      if (m[2]+m[3] < eps_ex*eps_ex*fmin(m[0],m[1])) return 5; }
    return 0;
}

static long long nex[8], nld=0, nquad=0, nbad=0, ndirectq=0, neval=0;

/* integrand with tiers; q is the sampling density at the ORIGINAL point (for absolute error control) */
static double eval_R(const Point *P, double d, double q){
    int ex = excise(P); if (ex){ nex[ex]++; return 0.0; }
    /* min relative scale */
    double mins=1e300; for(int i=0;i<4;i++){ for(int j=i+1;j<4;j++){ double t=hyp2(P->dr[i][j],P->di[i][j]); if(t<mins) mins=t; } double t=hyp2(P->wr[i],P->wi[i]); if(t<mins) mins=t; }
    double R;
    if (mins > 1e-8){
        double em; R = Rint_d(P->wr,P->wi,d,&em);
        if (1.1e-16*30*em/q < ERRTOL && isfinite(R)) return R;
        long double lr[4], li[4]; for(int i=0;i<4;i++){ lr[i]=(long double)P->qr[i]; li[i]=(long double)P->qi[i]; }
        long double eml; long double Rl = Rint_l(lr,li,(long double)d,&eml);
        if (5.4e-20*30*(double)eml/q < ERRTOL && isfinite((double)Rl)){ nld++; return (double)Rl; }
    } else ndirectq++;
#ifdef USE_QUAD
    { __float128 emq; __float128 Rq = Rint_q(P->qr,P->qi,(__float128)d,&emq);
      if (1.0e-34*30*(double)emq/q < ERRTOL && isfinite((double)Rq)){ nquad++; return (double)Rq; } }
#else
    { long double lr[4], li[4]; for(int i=0;i<4;i++){ lr[i]=P->qr[i]; li[i]=P->qi[i]; }
      long double eml; long double Rl = Rint_l(lr,li,(long double)d,&eml);
      if (5.4e-20*30*(double)eml/q < ERRTOL && isfinite((double)Rl)){ nld++; return (double)Rl; } }
#endif
    nbad++; return 0.0;
}

/* rotations by 90 degrees (multiply relative vectors by i) in extended precision */
static void rot_pair(Point *P, int a, int b){
    QT cr=(P->qr[a]+P->qr[b])/2, ci=(P->qi[a]+P->qi[b])/2, hr=(P->qr[a]-P->qr[b])/2, hi=(P->qi[a]-P->qi[b])/2;
    P->qr[a]=cr-hi; P->qi[a]=ci+hr; P->qr[b]=cr+hi; P->qi[b]=ci-hr;
}
static void rot_all(Point *P){
    QT Cr=(P->qr[0]+P->qr[1]+P->qr[2]+P->qr[3])/4, Ci=(P->qi[0]+P->qi[1]+P->qi[2]+P->qi[3])/4;
    for(int i=0;i<4;i++){ QT xr=P->qr[i]-Cr, xi=P->qi[i]-Ci; P->qr[i]=Cr-xi; P->qi[i]=Ci+xr; }
}



static double LMIN_G = -16.0;
/* antithetic delta=0 estimator at point P with density q (no histogramming) */
static double sample_weight(const Point *P0, double q){
    Point P = *P0;
    double r12=hyp2(P.dr[0][1],P.di[0][1]), r34=hyp2(P.dr[2][3],P.di[2][3]);
    int use12=0, use34=0, useQ=0;
    if (ANTI>0){
        double Cr=0.25*(P.wr[0]+P.wr[1]+P.wr[2]+P.wr[3]), Ci=0.25*(P.wi[0]+P.wi[1]+P.wi[2]+P.wi[3]);
        double rho4=0; for(int i=0;i<4;i++) for(int j=i+1;j<4;j++) rho4 += P.dr[i][j]*P.dr[i][j]+P.di[i][j]*P.di[i][j]; rho4=sqrt(0.25*rho4);
        double aC=hyp2(Cr,Ci);
        useQ = (ANTI>=2) && rho4 < KAP*aC;
        double dcr=0.25*(P.dr[0][2]+P.dr[1][2]+P.dr[0][3]+P.dr[1][3]), dci=0.25*(P.di[0][2]+P.di[1][2]+P.di[0][3]+P.di[1][3]);
        double dcc=hyp2(dcr,dci);
        double b12=fmax(0,dcc-0.5*r34), b34=fmax(0,dcc-0.5*r12), l12, l34;
        if (useQ){ l12=fmin(b12, aC-rho4); l34=fmin(b34, aC-rho4); }
        else { l12=fmin(b12, hyp2(0.5*(P.wr[0]+P.wr[1]),0.5*(P.wi[0]+P.wi[1]))); l34=fmin(b34, hyp2(0.5*(P.wr[2]+P.wr[3]),0.5*(P.wi[2]+P.wi[3]))); }
        use12 = r12 < KAP*l12; use34 = r34 < KAP*l34;
    }
    int ng=0; for (int g=0; g<8; g++){ if ((g&1) && !use12) continue; if ((g&2) && !use34) continue; if ((g&4) && !useQ) continue; ng++; }
    double wsum=0;
    for (int g=0; g<8; g++){
        if ((g&1) && !use12) continue; if ((g&2) && !use34) continue; if ((g&4) && !useQ) continue;
        Point V = P;
        if (g&4) rot_all(&V);
        if (g&1) rot_pair(&V,0,1);
        if (g&2) rot_pair(&V,2,3);
        if (g) point_finish(&V);
        wsum += eval_R(&V,0.0,q)/q/ng;
    }
    return wsum;
}
/* ---- Lambda-sliced delta=0 estimator ----
 * I(delta) = int_{S^7} e^{2 delta Lambda} Rt,  Lambda = log|w12| + log|w34|,  Rt = R at delta=0.
 * We estimate the Lambda-histogram rho(lambda) of Rt dOmega, and J(lmin) = int_{Lambda>lmin} Rt.
 * Also Lambda_S = Lambda - 0.5 log(sum|w|^4) slicing (source e^{-|w|^4}).
 */
#define NBIN 120
#define BLO (-58.0)
#define BW 0.5
int main(int argc, char **argv){
    if (argc<4){ fprintf(stderr,"usage: %s eta nsamp seed\n",argv[0]); return 1; }
    double eta=atof(argv[1]); long long N=atoll(argv[2]); uint64_t seed=strtoull(argv[3],0,10);
    if (getenv("ANTI")) ANTI=atoi(getenv("ANTI"));
    if (getenv("KAP")) KAP=atof(getenv("KAP"));
    if (getenv("EPSEX")) eps_ex=atof(getenv("EPSEX"));
    if (getenv("TINY")) TINY=atof(getenv("TINY"));
    if (getenv("ERRTOL")) ERRTOL=atof(getenv("ERRTOL"));
    double LMIN = getenv("LMIN") ? atof(getenv("LMIN")) : -16.0;
    int NB = getenv("NBATCH") ? atoi(getenv("NBATCH")) : 50;
    int only = getenv("ONLY") ? atoi(getenv("ONLY")) : -1;
    seed_rng(seed);
    build_channels(eta, only);
    if (getenv("ALPHAFILE")){ FILE *fa=fopen(getenv("ALPHAFILE"),"r"); if(fa){ for(int k=0;k<nch;k++){ if(fscanf(fa,"%lf %*s",&ch[k].alpha)!=1) break; } fclose(fa); } }
    long long NADAPT = getenv("NADAPT") ? atoll(getenv("NADAPT")) : 0;
    for (int it=0; it<(NADAPT>0?3:0); it++){
        double cumA[96]; double accA=0; for(int k=0;k<nch;k++){ accA+=ch[k].alpha; cumA[k]=accA; }
        double Wk[96]={0}; double qk2[96];
        for (long long n=0;n<NADAPT;n++){
            double u=unif(); int k=0; while(k<nch-1 && u>cumA[k]) k++;
            double yr[4], yi[4]; sample_y(&ch[k],yr,yi);
            Point P;
            for (int i=0;i<4;i++){ QT sr=0, si=0; for(int a=0;a<4;a++){ sr += (QT)ch[k].L[a][i]*(QT)yr[a]; si += (QT)ch[k].L[a][i]*(QT)yi[a]; } P.qr[i]=sr; P.qi[i]=si; }
            point_finish(&P);
            double Lam = log(hyp2(P.dr[0][1],P.di[0][1]))+log(hyp2(P.dr[2][3],P.di[2][3]));
            if (!(Lam > LMIN)) continue;
            double q = qmix(&P,qk2);
            double w = sample_weight(&P, q);
            for(int j=0;j<nch;j++) Wk[j]+=w*w*qk2[j]/q;
        }
        double sa=0; for(int k=0;k<nch;k++){ ch[k].alpha = ch[k].alpha*sqrt(Wk[k]/NADAPT); sa+=ch[k].alpha; }
        for(int k=0;k<nch;k++){ ch[k].alpha/=sa; if (ch[k].alpha<0.002) ch[k].alpha=0.002; }
        sa=0; for(int k=0;k<nch;k++) sa+=ch[k].alpha; for(int k=0;k<nch;k++) ch[k].alpha/=sa;
        fprintf(stderr,"adapt it %d done\n", it);
    }
    if (getenv("ALPHAOUT")){ FILE *fa=fopen(getenv("ALPHAOUT"),"w"); for(int k=0;k<nch;k++) fprintf(fa,"%.10g %s\n",ch[k].alpha,ch[k].name); fclose(fa); }
    double cum[96]; double acc=0; for(int k=0;k<nch;k++){ acc+=ch[k].alpha; cum[k]=acc; }
    /* per-batch histograms */
    double (*H)[NBIN] = calloc((size_t)NB, sizeof *H);
    double (*HS)[NBIN] = calloc((size_t)NB, sizeof *HS);
    double Hw2[NBIN]={0};
    #define ND 6
    const double dl[ND] = {0.05, 0.1, 0.15, 0.2, 0.3, 0.5};
    double (*Bd)[ND] = calloc((size_t)NB, sizeof *Bd);
    double (*BdS)[ND] = calloc((size_t)NB, sizeof *BdS);
    long long ncut=0;
    double topw[10]={0}; double topconf[10][10]; memset(topconf,0,sizeof topconf);
    double qk[96];
    if (N < NB) NB = 1;
    long long perb = N/NB;
    for (long long n=0;n<N;n++){
        int b = (int)(n/perb); if (b>=NB) b=NB-1;
        double u=unif(); int k=0; while(k<nch-1 && u>cum[k]) k++;
        double yr[4], yi[4];
        sample_y(&ch[k],yr,yi);
        Point P;
        for (int i=0;i<4;i++){ QT sr=0, si=0; for(int a=0;a<4;a++){ sr += (QT)ch[k].L[a][i]*(QT)yr[a]; si += (QT)ch[k].L[a][i]*(QT)yi[a]; } P.qr[i]=sr; P.qi[i]=si; }
        point_finish(&P);
        double r12=hyp2(P.dr[0][1],P.di[0][1]), r34=hyp2(P.dr[2][3],P.di[2][3]);
        double Lam = log(r12)+log(r34);
        if (!(Lam > LMIN)) { ncut++; continue; }
        double q = qmix(&P,qk);
        int use12=0, use34=0, useQ=0;
        if (ANTI>0){
            double Cr=0.25*(P.wr[0]+P.wr[1]+P.wr[2]+P.wr[3]), Ci=0.25*(P.wi[0]+P.wi[1]+P.wi[2]+P.wi[3]);
            double rho4=0; for(int i=0;i<4;i++) for(int j=i+1;j<4;j++) rho4 += P.dr[i][j]*P.dr[i][j]+P.di[i][j]*P.di[i][j]; rho4=sqrt(0.25*rho4);
            double aC=hyp2(Cr,Ci);
            useQ = (ANTI>=2) && rho4 < KAP*aC;
            double dcr=0.25*(P.dr[0][2]+P.dr[1][2]+P.dr[0][3]+P.dr[1][3]), dci=0.25*(P.di[0][2]+P.di[1][2]+P.di[0][3]+P.di[1][3]);
            double dcc=hyp2(dcr,dci);
            double b12=fmax(0,dcc-0.5*r34), b34=fmax(0,dcc-0.5*r12), l12, l34;
            if (useQ){ l12=fmin(b12, aC-rho4); l34=fmin(b34, aC-rho4); }
            else { l12=fmin(b12, hyp2(0.5*(P.wr[0]+P.wr[1]),0.5*(P.wi[0]+P.wi[1]))); l34=fmin(b34, hyp2(0.5*(P.wr[2]+P.wr[3]),0.5*(P.wi[2]+P.wi[3]))); }
            use12 = r12 < KAP*l12; use34 = r34 < KAP*l34;
        }
        int ng=0; for (int g=0; g<8; g++){ if ((g&1) && !use12) continue; if ((g&2) && !use34) continue; if ((g&4) && !useQ) continue; ng++; }
        double wsum=0;
        int ib = (int)floor((Lam-BLO)/BW); if (ib<0) ib=0; if (ib>=NBIN) ib=NBIN-1;
        for (int g=0; g<8; g++){
            if ((g&1) && !use12) continue; if ((g&2) && !use34) continue; if ((g&4) && !useQ) continue;
            Point V = P;
            if (g&4) rot_all(&V);
            if (g&1) rot_pair(&V,0,1);
            if (g&2) rot_pair(&V,2,3);
            if (g) point_finish(&V);
            double R = eval_R(&V,0.0,q);
            neval++;
            double w = R/q/ng;
            wsum += w;
            double S4n=0; for(int i=0;i<4;i++){ double m=V.wr[i]*V.wr[i]+V.wi[i]*V.wi[i]; S4n+=m*m; }
            double LamS = Lam - 0.5*log(S4n);
            int ibs = (int)floor((LamS-BLO)/BW); if (ibs<0) ibs=0; if (ibs>=NBIN) ibs=NBIN-1;
            HS[b][ibs] += w;
            for (int j=0;j<ND;j++) BdS[b][j] += w*exp(2*dl[j]*LamS);
        }
        H[b][ib] += wsum; Hw2[ib] += wsum*wsum;
        for (int j=0;j<ND;j++) Bd[b][j] += wsum*exp(2*dl[j]*Lam);
        double aw=fabs(wsum);
        if (aw>topw[9]){ int p=9; while(p>0 && aw>topw[p-1]){ topw[p]=topw[p-1]; memcpy(topconf[p],topconf[p-1],sizeof(double)*10); p--; }
            topw[p]=aw; for(int i=0;i<4;i++){ topconf[p][2*i]=P.wr[i]; topconf[p][2*i+1]=P.wi[i]; } topconf[p][8]=k; topconf[p][9]=Lam; }
    }
    printf("eta %.6f N %lld seed %llu ANTI %d KAP %.3f EPSEX %.3g TINY %.3g ERRTOL %.3g LMIN %.2f NB %d\n", eta, N, (unsigned long long)seed, ANTI, KAP, eps_ex, TINY, ERRTOL, LMIN, NB);
    printf("counts cut %lld excised %lld %lld %lld %lld %lld tiny %lld ld %lld quad %lld directq %lld bad %lld neval %lld\n", ncut, nex[1],nex[2],nex[3],nex[4],nex[5],nex[6],nld,nquad,ndirectq,nbad,neval);
    /* raw per-batch output: batch sizes */
    for (int b=0;b<NB;b++){ long long nb = (b<NB-1)?perb:(N-perb*(NB-1));
        printf("B %d %lld", b, nb); for(int i=0;i<NBIN;i++) printf(" %.10g", H[b][i]); printf("\n");
        printf("BS %d %lld", b, nb); for(int i=0;i<NBIN;i++) printf(" %.10g", HS[b][i]); printf("\n");
        printf("BD %d %lld", b, nb); for(int j=0;j<ND;j++) printf(" %.10g", Bd[b][j]); for(int j=0;j<ND;j++) printf(" %.10g", BdS[b][j]); printf("\n"); }
    printf("HW2"); for(int i=0;i<NBIN;i++) printf(" %.10g", Hw2[i]); printf("\n");
    for (int p=0;p<10;p++){ printf("top %.4g ch %s Lam %.2f :", topw[p], ch[(int)topconf[p][8]].name, topconf[p][9]); for(int i=0;i<4;i++) printf(" %.17g %.17g", topconf[p][2*i], topconf[p][2*i+1]); printf("\n"); }
    return 0;
}
