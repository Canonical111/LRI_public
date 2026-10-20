#include <complex.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <omp.h>
typedef long double complex cq;
static cq zparse(const char*r,const char*i){return strtold(r,NULL)+I*strtold(i,NULL);}
static void polydot(cq*x,cq*dx,int d,const int64_t*mons,const double*coef,int n,cq*out,cq*dout){
 cq p=0.L,dp=0.L;for(int j=0;j<n;j++){cq y=(long double)coef[j],dy=0.L;for(int a=0;a<d;a++){int pow=mons[j*d+a];for(int k=0;k<pow;k++){dy=dy*x[a]+y*dx[a];y*=x[a];}}p+=y;dp+=dy;}*out=p;*dout=dp;
}
static cq powi(cq z,int p){cq y=1.L;while(p){if(p&1)y*=z;z*=z;p>>=1;}return y;}
void integrate(int d,int N,int nf,int nm,int nsm,
 const char**node,const char**weight,const char**ndot,const char**wdlog,const int64_t*mons,const double*coef,const int64_t*pn,const int64_t*ex,const int64_t*sl,
 const int64_t*sm,const double*sc,const char*qr,const char*qi,char*outre,char*outim){
 cq q=zparse(qr,qi);cq*xn=malloc(d*N*sizeof(cq)),*wn=malloc(d*N*sizeof(cq)),*xd=malloc(d*N*sizeof(cq)),*wl=malloc(d*N*sizeof(cq));
 for(int a=0;a<d*N;a++){xn[a]=zparse(node[2*a],node[2*a+1]);wn[a]=zparse(weight[2*a],weight[2*a+1]);xd[a]=zparse(ndot[2*a],ndot[2*a+1]);wl[a]=zparse(wdlog[2*a],wdlog[2*a+1]);}
 int64_t nt=1;for(int a=0;a<d;a++)nt*=N;cq sum=0.L;
 #pragma omp parallel
 {cq total=0.L,comp=0.L;
 #pragma omp for schedule(static)
 for(int64_t i=0;i<nt;i++){
  cq x[8],dx[8],W=1.L,dlW=0.L;int64_t idx=i;
  for(int a=0;a<d;a++){int j=idx%N;idx/=N;x[a]=xn[a*N+j];dx[a]=xd[a*N+j];W*=wn[a*N+j];dlW+=wl[a*N+j];}
  cq num=1.L,den=1.L,en=1.L,ed=1.L,dl=0.L;
  for(int j=0;j<nf;j++){
   cq P,PD;polydot(x,dx,d,mons+j*nm*d,coef+j*nm,pn[j],&P,&PD);
   if(ex[j]>0)num*=powi(P,ex[j]);else if(ex[j]<0)den*=powi(P,-ex[j]);
   if(ex[j])dl+=(long double)ex[j]*PD/P;
   if(sl[j]>0)en*=powi(P,sl[j]);else if(sl[j]<0)ed*=powi(P,-sl[j]);
  }
  cq S,SD;polydot(x,dx,d,sm,sc,nsm,&S,&SD);cq F=num/den*cexpl(-q*clogl(S));dl+=clogl(en/ed)-q*SD/S;
  cq val=W*F*(dlW+dl),yy=val-comp,tmp=total+yy;comp=(tmp-total)-yy;total=tmp;
 }
 #pragma omp critical
 sum+=total;
 }
 snprintf(outre,128,"%.24Lg",creall(sum));snprintf(outim,128,"%.24Lg",cimagl(sum));free(xn);free(wn);free(xd);free(wl);
}
