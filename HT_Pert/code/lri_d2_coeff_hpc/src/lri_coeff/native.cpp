// Fused shared-graph Taylor products and deterministic long-double reductions.
// Deliberately no fast-math or contracted multiply-add.
#include <cstdint>
#include <cfloat>
#include <algorithm>
#include <vector>
#include <omp.h>
extern "C" int lri_ld_bits(){return LDBL_MANT_DIG;}
extern "C" int lri_ld_size(){return sizeof(long double);}

template<int D,int NX,bool CR,typename Index>
void apply(const int64_t*ptr,const Index*neighbor,const int64_t*edge,
           const uint16_t*mode,const double*amp,const double*u,int nu,
           const double*x,double*y,int64_t n,int nt,const double*add,double scale){
 std::vector<uint8_t> first(n,NX);
 #pragma omp parallel for schedule(static) num_threads(nt) if(nt>1 && n>=5000)
 for(int64_t i=0;i<n;++i){for(int j=0;j<NX;++j)if(x[i*NX+j]!=0.){first[i]=j;break;}}
 #pragma omp parallel for schedule(static) num_threads(nt) if(nt>1 && n>=5000)
 for(int64_t i=0;i<n;++i){
  double acc[D]={};
  for(int64_t k=ptr[i];k<ptr[i+1];++k){
   const int64_t nbr=neighbor[k];
   if(!CR && nbr>=n)break;
   const int begin=first[nbr];if(begin==NX)continue;
   const int64_t e=CR?k:edge[k];
   const unsigned md=mode[e];const double w=amp[e];
   const double*xx=x+nbr*NX;
   if(md==0){
    for(int j=begin;j<std::min(D,NX);++j)acc[j]+=w*xx[j];
   }else{
    const double*uu=u+int64_t(md)*nu;
    for(int j=0;j<D-begin;++j){
     const double coeff=w*uu[j];
     for(int l=begin;l<std::min(NX,D-j);++l)acc[l+j]+=coeff*xx[l];
    }
   }
  }
  for(int j=0;j<D;++j)y[i*D+j]=add?acc[j]+scale*add[i*D+j]:acc[j];
 }
}

template<int D,bool CR,typename Index>
void bynx(int nx,const int64_t*p,const Index*c,const int64_t*e,const uint16_t*m,const double*a,const double*u,int nu,const double*x,double*y,int64_t n,int nt,const double*add,double scale){
 #define ONE(X) case X:apply<D,X,CR>(p,c,e,m,a,u,nu,x,y,n,nt,add,scale);break;
 switch(nx){ONE(1) ONE(2) ONE(3) ONE(4) ONE(5) ONE(6) ONE(7) ONE(8)}
 #undef ONE
}
template<bool CR,typename Index>
void byd(int d,int nx,const int64_t*p,const Index*c,const int64_t*e,const uint16_t*m,const double*a,const double*u,int nu,const double*x,double*y,int64_t n,int nt,const double*add,double scale){
 #define ONE(D) case D:bynx<D,CR>(nx,p,c,e,m,a,u,nu,x,y,n,nt,add,scale);break;
 switch(d){ONE(1) ONE(2) ONE(3) ONE(4) ONE(5) ONE(6) ONE(7) ONE(8)}
 #undef ONE
}
extern "C" int lri_apply(int creation,int indexbytes,int d,int nx,const int64_t*p,const void*c,const int64_t*e,const uint16_t*m,const double*a,const double*u,int nu,const double*x,double*y,int64_t n,int nt,const double*add,double scale){
 if(d<1||d>8||nx<1||nx>8||nu<d||nt<1)return 1;
 #define RUN(I) if(creation)byd<true>(d,nx,p,(const I*)c,e,m,a,u,nu,x,y,n,nt,add,scale);else byd<false>(d,nx,p,(const I*)c,e,m,a,u,nu,x,y,n,nt,add,scale);
 if(indexbytes==4){RUN(int32_t)}else if(indexbytes==8){RUN(int64_t)}else return 2;
 #undef RUN
 return 0;
}
extern "C" int lri_dot(const double*x,int nx,const double*y,int ny,int nd,int64_t n,int nt,long double*out){
 if(nd<1||nd>8||nx<1||ny<1||nt<1)return 1;
 const int64_t BS=1024,nb=(n+BS-1)/BS;
 std::vector<long double> tmp(nb*nd,0.L);
 #pragma omp parallel for schedule(static) num_threads(nt) if(nt>1 && nb>=8)
 for(int64_t b=0;b<nb;++b){
  long double*acc=&tmp[b*nd];
  for(int64_t i=b*BS;i<std::min(n,(b+1)*BS);++i){
   const double*xx=x+i*nx;const double*yy=y+i*ny;
   for(int k=0;k<nd;++k)
    for(int j=std::max(0,k-ny+1);j<std::min(k+1,nx);++j){
      const double prod=xx[j]*yy[k-j];
      acc[k]+=(long double)prod;
    }
  }
 }
 for(int k=0;k<nd;++k){out[k]=0;for(int64_t b=0;b<nb;++b)out[k]+=tmp[b*nd+k];}
 return 0;
}

extern "C" void lri_project(double*m,double*v,int nd,const int32_t*jabs,int64_t n,int nt){
 #pragma omp parallel for schedule(static) num_threads(nt) if(nt>1 && n>=5000)
 for(int64_t i=0;i<n;++i){
  for(int k=0;k<nd;++k){if(jabs[i]){m[i*nd+k]=0;v[i*nd+k]=0;}else v[i*nd+k]/=12.;}
 }

}
