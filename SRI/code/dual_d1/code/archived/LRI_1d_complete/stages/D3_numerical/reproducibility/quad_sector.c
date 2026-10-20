#include <complex.h>
#include <quadmath.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <omp.h>
typedef __complex128 cq;
static cq getc128(const char*r,const char*i){cq z;__real__ z=strtoflt128(r,NULL);__imag__ z=strtoflt128(i,NULL);return z;}
static cq poly(cq*x,int d,const int64_t*mons,const double*coef,int n){cq ans=0.Q;for(int j=0;j<n;j++){cq y=(__float128)coef[j];for(int a=0;a<d;a++){int p=mons[j*d+a];for(int k=0;k<p;k++)y*=x[a];}ans+=y;}return ans;}
static cq ipow(cq z,int p){cq y=1.Q;int n=p<0?-p:p;while(n){if(n&1)y*=z;z*=z;n>>=1;}return p<0?1.Q/y:y;}
void integrate(int d,int N,int nf,int nm,int nsm,
 const char**node,const char**weight,const int64_t*mons,const double*coef,const int64_t*pn,const int64_t*ex,const int64_t*sl,const int64_t*sl2,
 const int64_t*sm,const double*sc,const char*qr,const char*qi,const char*vr,const char*vi,const char*wr,const char*wi,char*outre,char*outim){
 cq q=getc128(qr,qi),dv=getc128(vr,vi),dw=getc128(wr,wi);int hasv=(crealq(dv)!=0.Q||cimagq(dv)!=0.Q||crealq(dw)!=0.Q||cimagq(dw)!=0.Q);
 cq *xn=malloc(d*N*sizeof(cq)),*wn=malloc(d*N*sizeof(cq));
 for(int a=0;a<d*N;a++){xn[a]=getc128(node[2*a],node[2*a+1]);wn[a]=getc128(weight[2*a],weight[2*a+1]);}
 int64_t nt=1;for(int j=0;j<d;j++)nt*=N;cq sum=0.Q;
 #pragma omp parallel
 {cq tsum=0.Q;
 #pragma omp for schedule(static)
 for(int64_t i=0;i<nt;i++){
  cq x[8];cq W=1.Q;int64_t index=i;
  for(int a=0;a<d;a++){int j=index%N;index/=N;x[a]=xn[a*N+j];W*=wn[a*N+j];}
  cq F=1.Q,lg=0.Q;
  for(int j=0;j<nf;j++){
   cq pp=poly(x,d,mons+j*nm*d,coef+j*nm,pn[j]);
   if(ex[j])F*=ipow(pp,ex[j]);if(hasv&&(sl[j]||sl2[j]))lg+=((__float128)sl[j]*dv+(__float128)sl2[j]*dw)*clogq(pp);
  }
  cq S=poly(x,d,sm,sc,nsm);F*=cexpq(-q*clogq(S)+lg);tsum+=W*F;
 }
 #pragma omp critical
 sum+=tsum;
 }
 quadmath_snprintf(outre,128,"%.33Qg",crealq(sum));quadmath_snprintf(outim,128,"%.33Qg",cimagq(sum));free(xn);free(wn);
}
