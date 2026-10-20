#include <gmpxx.h>
#include <unordered_map>
#include <vector>
#include <sstream>
#include <string>
#include <cstring>
#include <cstdlib>
#include <cstdint>
using Term=std::pair<uint64_t,mpq_class>;
static std::vector<Term> parse(const char* s){
 std::vector<Term> v;std::istringstream in(s);uint64_t k;std::string c;
 while(in>>k>>c){mpq_class q(c);q.canonicalize();v.emplace_back(k,q);}return v;
}
extern "C" char* multiply_qq(const char* a,const char* b){
 try {
  auto x=parse(a),y=parse(b);std::unordered_map<uint64_t,mpq_class> z;
  z.reserve(x.size()+y.size());
  for(const auto& u:x)for(const auto& v:y)z[u.first+v.first]+=u.second*v.second;
  std::ostringstream out;
  for(const auto& p:z)if(p.second!=0)out<<p.first<<' '<<p.second.get_str()<<'\n';
  auto s=out.str();char* ret=(char*)std::malloc(s.size()+1);
  if(!ret)return nullptr;std::memcpy(ret,s.c_str(),s.size()+1);return ret;
 } catch(...){return nullptr;}
}
extern "C" void free_result(char* p){std::free(p);}
