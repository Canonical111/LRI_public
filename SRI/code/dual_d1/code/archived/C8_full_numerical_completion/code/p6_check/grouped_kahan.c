#define integral old_integral
#include "log_moment_quad.c"
#undef integral
static void cadd(Z *s,Z *c,Z v){Z y=v-*c; Z t=*s+y; *c=(t-*s)-y; *s=t;}
// Same smooth polynomials and five monomial-exponent patterns are shared by
// the sixty inequivalent n=6 sectors. Sum smooth parts before quadrature.
void grouped(int d,int N,int nq,int nf,int nm,int nsec,int npmax,int ng,int nth,
 const char**nodes,const char**weights,const char**qval,
 const int64_t*mon,const int64_t*coef,const int64_t*plen,const int64_t*expo,
 const int64_t*pk,const int64_t*pi,const int64_t*ps,const int64_t*np,
 const int64_t*group,const int64_t*multi,const int64_t*cs,
 int64_t begin,int64_t end,char*out){
 R*xn=malloc(N*sizeof(R));Z*wt=malloc(nq*ng*d*N*4*sizeof(Z));Z*qq=malloc(nq*sizeof(Z));
 for(int i=0;i<N;i++)xn[i]=STR(nodes[i],NULL);
 for(int i=0;i<nq*ng*d*N*4;i++)wt[i]=parse(weights[2*i],weights[2*i+1]);
 for(int i=0;i<nq;i++)qq[i]=parse(qval[2*i],qval[2*i+1]);
 Z*sum=calloc(nq*5,sizeof(Z));omp_set_num_threads(nth);
 #pragma omp parallel
 {
 Z*local=calloc(nq*5,sizeof(Z));Z*comp=calloc(nq*5,sizeof(Z));
 #pragma omp for schedule(static)
 for(int64_t t=begin;t<end;t++){
  R x[8],lv[64],pp[64],ss=1,lev=1,AG[8][24]={{0}};int idx[8];int64_t ii=t;
  for(int a=0;a<d;a++){idx[a]=ii%N;ii/=N;x[a]=xn[idx[a]];lev*=x[a];ss+=lev;}
  R ls=LOG(ss);
  for(int j=0;j<nf;j++){pp[j]=pol(x,d,mon+j*nm*d,coef+j*nm,plen[j]);lv[j]=LOG(pp[j]);}
  for(int sec=0;sec<nsec;sec++){
   R base=multi[sec],u1=0,u2=0,lin[8]={0};R*A=AG[group[sec]];
   for(int j=0;j<nf;j++)if(expo[sec*nf+j])base*=ipow(pp[j],expo[sec*nf+j]);
   for(int j=0;j<np[sec];j++){
    int off=sec*npmax+j;R h=(pi[off]<0?0:lv[pi[off]])-ls;u1+=ps[off]*h;u2+=ps[off]*h*h;
    for(int a=0;a<pk[off];a++)lin[a]+=2*ps[off]*h;
   }
   A[0]+=base;A[1]+=base*u1;A[2]+=base*u1*u1;A[3]+=base*u2;A[4]+=base*u1*u2;
   for(int a=0;a<d;a++){A[5+a]+=base*lin[a];A[5+d+a]+=base*u1*lin[a];}
  }
  for(int iq=0;iq<nq;iq++){
   Z sf=CEXP(-qq[iq]*ls);
   for(int g=0;g<ng;g++){
    R*A=AG[g];const int64_t*c=cs+g*d;
    Z W=sf,mu[8],va[8],cu[8],bb[8],s1=0,v1=0,Q=0,pcov=0,ts=0,uts=0,tcov=0;
    for(int a=0;a<d;a++){
     Z*z=wt+((((iq*ng+g)*d+a)*N+idx[a])*4);W*=z[0];mu[a]=z[1];va[a]=z[2];cu[a]=z[3];
     s1+=c[a]*mu[a];v1+=c[a]*c[a]*va[a];Q+=c[a]*va[a];ts+=A[5+a]*mu[a];uts+=A[5+d+a]*mu[a];tcov+=c[a]*va[a]*A[5+a];
    }
    for(int a=0;a<d;a++){
     bb[a]=0;for(int b=0;b<d;b++)bb[a]+=c[a>b?a:b]*mu[b];
     Q+=mu[a]*bb[a];pcov+=c[a]*(2*va[a]*bb[a]+c[a]*cu[a]);
    }
    Z m1=A[1]+A[0]*s1,m11=A[2]+2*A[1]*s1+A[0]*(s1*s1+v1),m2=A[3]+ts+A[0]*Q;
    Z m12=A[4]+A[1]*Q+s1*m2+uts+tcov+A[0]*pcov;
    cadd(local+5*iq,comp+5*iq,W*A[0]);cadd(local+5*iq+1,comp+5*iq+1,W*m1);cadd(local+5*iq+2,comp+5*iq+2,W*m11);cadd(local+5*iq+3,comp+5*iq+3,W*m2);cadd(local+5*iq+4,comp+5*iq+4,W*m12);
   }
  }
 }
 #pragma omp critical
 for(int i=0;i<5*nq;i++)sum[i]+=local[i];
 free(local);free(comp);
 }
 for(int i=0;i<5*nq;i++){fmt(out+200*i,RE(sum[i]));fmt(out+200*i+100,IM(sum[i]));}
 free(xn);free(wt);free(qq);free(sum);
}
