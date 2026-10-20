#include <gmpxx.h>
#include <unordered_map>
#include <vector>
#include <sstream>
#include <string>
#include <cstring>
#include <cstdlib>
#include <cstdint>
static constexpr uint64_t P=1000000007;
static uint64_t power(uint64_t a,uint64_t n){uint64_t r=1;while(n){if(n&1)r=r*a%P;a=a*a%P;n>>=1;}return r;}
extern "C" char* spec_qq(const char* text,int idx){
 try{
  uint64_t values[8]={37,101,211,307,419,509,613,701};uint64_t pw[8][128];
  for(int j=0;j<8;++j){pw[j][0]=1;for(int k=1;k<128;++k)pw[j][k]=pw[j][k-1]*values[j]%P;}
  std::vector<uint64_t> c(1,0);std::unordered_map<uint64_t,uint64_t> inv;
  std::istringstream input(text);uint64_t mon;std::string s;
  while(input>>mon>>s){mpq_class q(s);q.canonicalize();uint64_t d=mpz_fdiv_ui(q.get_den_mpz_t(),P);if(!d)return nullptr;
   uint64_t inverse;auto it=inv.find(d);if(it==inv.end()){inverse=power(d,P-2);inv.emplace(d,inverse);}else inverse=it->second;
   uint64_t v=mpz_fdiv_ui(q.get_num_mpz_t(),P)*inverse%P;unsigned degree=(mon>>(7*idx))&127;
   for(int j=0;j<8;++j)if(j!=idx)v=v*pw[j][(mon>>(7*j))&127]%P;
   if(c.size()<=degree)c.resize(degree+1,0);c[degree]=(c[degree]+v)%P;
  }
  std::ostringstream out;for(auto x:c)out<<x<<' ';auto result=out.str();char* r=(char*)std::malloc(result.size()+1);if(!r)return nullptr;std::memcpy(r,result.c_str(),result.size()+1);return r;
 }catch(...){return nullptr;}
}
extern "C" void free_result(char* p){std::free(p);}
