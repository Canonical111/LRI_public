#include <gmpxx.h>
#include <unordered_map>
#include <vector>
#include <sstream>
#include <string>
#include <cstring>
#include <cstdlib>
#include <cstdint>
using Term=std::pair<uint64_t,mpq_class>;
static std::vector<Term> parse(const char*s){std::vector<Term>v;std::istringstream in(s);uint64_t k;std::string c;while(in>>k>>c){mpq_class q(c);q.canonicalize();v.emplace_back(k,q);}return v;}
extern "C" char* add_products_qq(const char*a,const char*b,const char*c,const char*d){
 try{auto aa=parse(a),bb=parse(b),cc=parse(c),dd=parse(d);std::unordered_map<uint64_t,mpq_class> out;out.reserve(aa.size()+cc.size());
 for(const auto&x:aa)for(const auto&y:bb)out[x.first+y.first]+=x.second*y.second;
 for(const auto&x:cc)for(const auto&y:dd)out[x.first+y.first]+=x.second*y.second;
 std::ostringstream stream;for(const auto&x:out)if(x.second!=0)stream<<x.first<<' '<<x.second.get_str()<<'\n';auto s=stream.str();char*r=(char*)std::malloc(s.size()+1);if(!r)return nullptr;std::memcpy(r,s.c_str(),s.size()+1);return r;
 }catch(...){return nullptr;}}
extern "C" void free_result(char*p){std::free(p);}
