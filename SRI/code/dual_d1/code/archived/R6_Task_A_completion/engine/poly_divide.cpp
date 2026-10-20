#include <gmpxx.h>
#include <unordered_map>
#include <vector>
#include <sstream>
#include <string>
#include <cstring>
#include <cstdlib>
#include <cstdint>
using Poly=std::unordered_map<uint64_t,mpq_class>;
static Poly parse(const char* s){Poly v;std::istringstream in(s);uint64_t k;std::string c;while(in>>k>>c){mpq_class q(c);q.canonicalize();v[k]+=q;}return v;}
static void print(std::ostringstream& out,const Poly& p){for(const auto& x:p)if(x.second!=0)out<<x.first<<' '<<x.second.get_str()<<'\n';}
extern "C" char* divide_linear_qq(const char* aa,const char* bb,int idx){
 try{
  auto p=parse(aa),f=parse(bb);uint64_t unit=uint64_t(1)<<(7*idx),mask=uint64_t(127)<<(7*idx);
  mpq_class lead=f.at(unit);f.erase(unit);for(auto& v:f)v.second=-v.second/lead;
  unsigned deg=0;for(const auto& v:p){unsigned d=(v.first&mask)>>(7*idx);if(d>deg)deg=d;}
  std::vector<Poly> co(deg+1);for(const auto& v:p)co[(v.first&mask)>>(7*idx)][v.first&~mask]+=v.second;
  Poly val=std::move(co[deg]),quo;
  for(unsigned n=deg;n>0;--n){
   for(const auto& v:val)if(v.second!=0)quo[v.first+(n-1)*unit]+=v.second/lead;
   Poly next=std::move(co[n-1]);
   for(const auto& v:val)if(v.second!=0)for(const auto& r:f)next[v.first+r.first]+=v.second*r.second;
   val=std::move(next);
  }
  std::ostringstream out;print(out,quo);out<<"#\n";print(out,val);auto s=out.str();char* r=(char*)std::malloc(s.size()+1);if(!r)return nullptr;std::memcpy(r,s.c_str(),s.size()+1);return r;
 }catch(...){return nullptr;}
}
extern "C" void free_result(char* p){std::free(p);}
