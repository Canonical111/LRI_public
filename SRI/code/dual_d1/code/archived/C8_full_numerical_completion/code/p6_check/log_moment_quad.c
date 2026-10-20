#include <complex.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <omp.h>
#ifdef QUAD
#include <quadmath.h>
typedef __float128 R;
typedef __complex128 Z;
#define RT(x) x##Q
#define LOG logq
#define CEXP cexpq
#define STR strtoflt128
#define RE crealq
#define IM cimagq
static void fmt(char *out,R v){quadmath_snprintf(out,100,"%.33Qg",v);}
#else
typedef long double R;
typedef long double complex Z;
#define RT(x) x##L
#define LOG logl
#define CEXP cexpl
#define STR strtold
#define RE creall
#define IM cimagl
static void fmt(char *out,R v){snprintf(out,100,"%.21Lg",v);}
#endif
static Z parse(const char *a,const char *b){Z z; __real__ z=STR(a,NULL);__imag__ z=STR(b,NULL);return z;}
static R pol(R*x,int d,const int64_t*mon,const int64_t*coef,int n){R out=0;for(int j=0;j<n;j++){R y=coef[j];for(int a=0;a<d;a++)for(int k=0;k<mon[j*d+a];k++)y*=x[a];out+=y;}return out;}
static R ipow(R x,int n){R o=1;int p=n<0?-n:n;while(p){if(p&1)o*=x;x*=x;p>>=1;}return n<0?1/o:o;}
// weights[q][d][N][4]: w0, mean(log), variance(log), central cubic(log).
void integral(int d,int N,int nq,int nf,int nm,int np,int nthreads,
 const char**nodes,const char**weights,const char**qval,
 const int64_t*mon,const int64_t*coef,const int64_t*plen,const int64_t*expo,
 const int64_t*pk,const int64_t*pi,const int64_t*ps,const int64_t*cs,
 char*out) {
 R*xn=malloc(N*sizeof(R));Z*wt=malloc(nq*d*N*4*sizeof(Z));Z*qq=malloc(nq*sizeof(Z));
 for(int i=0;i<N;i++)xn[i]=STR(nodes[i],NULL);
 for(int i=0;i<nq*d*N*4;i++)wt[i]=parse(weights[2*i],weights[2*i+1]);
 for(int i=0;i<nq;i++)qq[i]=parse(qval[2*i],qval[2*i+1]);
 Z *sum=calloc(nq*5,sizeof(Z));int64_t nt=1;for(int j=0;j<d;j++)nt*=N;
 omp_set_num_threads(nthreads);
 #pragma omp parallel
 {
 Z *local=calloc(nq*5,sizeof(Z));
 #pragma omp for schedule(static)
 for(int64_t t=0;t<nt;t++){
  R x[8],lv[64],ss=1,lev=1,base=1,sm1=0,sm2=0,lin[8]={0};int idx[8];int64_t ii=t;
  for(int a=0;a<d;a++){idx[a]=ii%N;ii/=N;x[a]=xn[idx[a]];lev*=x[a];ss+=lev;}
  R ls=LOG(ss);
  for(int j=0;j<nf;j++){R pp=pol(x,d,mon+j*nm*d,coef+j*nm,plen[j]);lv[j]=LOG(pp);if(expo[j])base*=ipow(pp,expo[j]);}
  for(int j=0;j<np;j++){
   R h=(pi[j]<0?0:lv[pi[j]])-ls;sm1+=ps[j]*h;sm2+=ps[j]*h*h;
   for(int a=0;a<pk[j];a++)lin[a]+=2*ps[j]*h;
  }
  for(int iq=0;iq<nq;iq++){
   Z W=base*CEXP(-qq[iq]*ls),mu[8],va[8],cu[8],bb[8],m1=sm1,m2=sm2,v1=0,cov=0;
   for(int a=0;a<d;a++){
    Z*z=wt+(((iq*d+a)*N+idx[a])*4);W*=z[0];mu[a]=z[1];va[a]=z[2];cu[a]=z[3];
    m1+=cs[a]*mu[a];v1+=cs[a]*cs[a]*va[a];m2+=lin[a]*mu[a]+cs[a]*va[a];
   }
   for(int a=0;a<d;a++){
    bb[a]=0;for(int b=0;b<d;b++)bb[a]+=cs[a>b?a:b]*mu[b];
    m2+=mu[a]*bb[a];cov+=cs[a]*(va[a]*(lin[a]+2*bb[a])+cs[a]*cu[a]);
   }
   local[5*iq]+=W;local[5*iq+1]+=W*m1;local[5*iq+2]+=W*(m1*m1+v1);local[5*iq+3]+=W*m2;local[5*iq+4]+=W*(m1*m2+cov);
  }
 }
 #pragma omp critical
 for(int i=0;i<5*nq;i++)sum[i]+=local[i];
 free(local);
 }
 for(int i=0;i<5*nq;i++){fmt(out+200*i,RE(sum[i]));fmt(out+200*i+100,IM(sum[i]));}
 free(xn);free(wt);free(qq);free(sum);
}
