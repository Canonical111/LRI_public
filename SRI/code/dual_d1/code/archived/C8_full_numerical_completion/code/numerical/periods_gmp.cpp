// Full regularized hyperlogarithm constants from their triangular ODE.
// No fitted transcendental basis or stored period table is used.
#include <gmpxx.h>
#include <omp.h>
#include <fstream>
#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <iomanip>
using F=mpf_class;
using Poly=std::vector<F>;
int main(int argc,char**argv){
 if(argc!=3){std::cerr<<"input output required\n";return 2;}
 std::ifstream in(argv[1]);int n,dps,nt,na;std::string Rstr,sfstr,logstr;
 in>>n>>dps>>nt>>na>>Rstr>>sfstr>>logstr;
 if(!in||n<1)return 3;
 mpf_set_default_prec((mp_bitcnt_t)std::ceil((dps+20)*3.321928094887363)+64);
 std::vector<int> a(n),tail(n),len(n),need(n),use(n);
 std::vector<std::vector<int>> suffix(n);
 bool haszero=false;
 for(int i=0;i<n;++i){in>>a[i]>>tail[i]>>len[i]>>need[i];suffix[i].resize(len[i]);for(int &x:suffix[i])in>>x;if(i){use[tail[i]]++;if(a[i]==0)haszero=true;}}
 if(!in)return 4;
 F end(Rstr),sf(sfstr),lr(logstr),t=0,h,hn=1;
 std::vector<F> vals(n),prev(n),cn(n),ans(n),inv(n);vals[0]=1;
 int steps=0;double start=omp_get_wtime();
 while(t<end){
  h=sf*((t>0&&haszero)?t:t+1);if(h>end-t)h=end-t;
  prev=vals;ans=vals;hn=1;
  for(int i=0;i<n;++i){F den=t+a[i];inv[i]=den==0?F(0):F(1)/den;}
  bool origin=t==0;
  for(int k=1;k<=nt;++k){
   hn*=h;cn[0]=0;
   if(origin){F tmp;
    for(int i=1;i<n;++i){
     if(a[i]==0)mpf_div_ui(cn[i].get_mpf_t(),cn[tail[i]].get_mpf_t(),k);
     else{mpf_mul_ui(tmp.get_mpf_t(),prev[i].get_mpf_t(),k-1);mpf_sub(cn[i].get_mpf_t(),prev[tail[i]].get_mpf_t(),tmp.get_mpf_t());mpf_mul(cn[i].get_mpf_t(),cn[i].get_mpf_t(),inv[i].get_mpf_t());mpf_div_ui(cn[i].get_mpf_t(),cn[i].get_mpf_t(),k);}
     mpf_mul(tmp.get_mpf_t(),hn.get_mpf_t(),cn[i].get_mpf_t());mpf_add(ans[i].get_mpf_t(),ans[i].get_mpf_t(),tmp.get_mpf_t());
    }
   }else{
    #pragma omp parallel
    {F tmp;
     #pragma omp for schedule(static)
     for(int i=1;i<n;++i){
      mpf_mul_ui(tmp.get_mpf_t(),prev[i].get_mpf_t(),k-1);mpf_sub(cn[i].get_mpf_t(),prev[tail[i]].get_mpf_t(),tmp.get_mpf_t());mpf_mul(cn[i].get_mpf_t(),cn[i].get_mpf_t(),inv[i].get_mpf_t());mpf_div_ui(cn[i].get_mpf_t(),cn[i].get_mpf_t(),k);mpf_mul(tmp.get_mpf_t(),hn.get_mpf_t(),cn[i].get_mpf_t());mpf_add(ans[i].get_mpf_t(),ans[i].get_mpf_t(),tmp.get_mpf_t());
     }
    }
   }
   prev.swap(cn);
  }
  t+=h;vals.swap(ans);steps++;
  if(steps%5==0)std::cerr<<"GMP_ODE "<<steps<<" T="<<t<<" seconds="<<omp_get_wtime()-start<<"\n";
 }
 if(na<0){
  std::ofstream out(argv[2]);out<<std::setprecision(dps+8);
  for(int i=0;i<n;++i)out<<i<<" "<<vals[i]<<"\n";
  std::cerr<<"FINITE_GMP_DONE words="<<n<<" seconds="<<omp_get_wtime()-start<<"\n";
  return out?0:6;
 }
 std::vector<F> constants(n);constants[0]=1;
 std::vector<std::vector<Poly>> polys(n);polys[0].assign(na+1,Poly(1,F(0)));polys[0][0][0]=1;
 auto polyvalue=[&](const Poly&p){F v=0;for(auto it=p.rbegin();it!=p.rend();++it)v=v*lr+*it;return v;};
 for(int i=1;i<n;++i){
  Poly p0(len[i]+1,F(0));unsigned long fac=1;
  for(int j=1;j<=len[i];++j){fac*=j;p0[j]=constants[suffix[i][j-1]]/fac;}
  bool save=need[i];if(save){polys[i].reserve(na+1);polys[i].push_back(p0);}
  auto &pt=polys[tail[i]];if(pt.empty()){std::cerr<<"missing suffix\n";return 5;}
  Poly sn=pt[0];F rem=0,ip=1;
  for(int k=1;k<=na;++k){
   for(size_t j=0;j<sn.size();++j)sn[j]=(j<pt[k].size()?pt[k][j]:F(0))-a[i]*sn[j];
   Poly yy(sn.size(),F(0));
   for(int j=(int)sn.size()-1;j>=0;--j)yy[j]=((j+1<(int)sn.size()?F(j+1)*yy[j+1]:F(0))-sn[j])/k;
   ip/=end;rem+=ip*polyvalue(yy);if(save)polys[i].push_back(std::move(yy));
  }
  constants[i]=vals[i]-polyvalue(p0)-rem;
  if(save)polys[i][0][0]=constants[i];
  if(--use[tail[i]]==0)std::vector<Poly>().swap(polys[tail[i]]);
  if(i%10000==0)std::cerr<<"GMP_ASYM "<<i<<"/"<<n<<" seconds="<<omp_get_wtime()-start<<"\n";
 }
 std::ofstream out(argv[2]);out<<std::setprecision(dps+8);
 for(int i=0;i<n;++i)out<<i<<" "<<constants[i]<<"\n";
 std::cerr<<"GMP_DONE words="<<n<<" seconds="<<omp_get_wtime()-start<<"\n";
 return out?0:6;
}
