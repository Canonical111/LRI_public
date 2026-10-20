#pragma once
// Build and runtime identity for --describe and the native JSON (PLAN.md C.2, HD9, A-KER-2/3).
//  * "gmp" is backend-specific. GMP build (-DC7_USE_GMP): {"applicable":true,"header_version":"<gmp.h macros>",
//    "runtime_version":"<gmp_version of the loaded library>","library":"<realpath>"}, where "library" is the object,
//    found with dl_iterate_phdr, whose PT_LOAD segments contain the ADDRESS HELD IN gmp_version (the string lies in
//    libgmp's read-only data; the address of the variable itself, or of a GMP function, can resolve into the
//    executable through a copy relocation or a PLT entry). Decimal build: {"applicable":false}; this translation unit
//    then includes no gmp.h and references no GMP symbol.
//  * "libraries": the realpath of every object dl_iterate_phdr reports (the executable first; libquadmath included).
// dl_iterate_phdr is in glibc's libc (no -ldl).
#include "kernel.hpp"
#include <link.h>
#include <climits>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
#include <boost/version.hpp>
#ifdef C7_USE_GMP
#include <gmp.h>
#endif
inline std::string json_escape(const std::string&s){
    std::string o;for(unsigned char c:s){if(c=='"'||c=='\\'){o+='\\';o+=char(c);}else if(c<0x20){char b[8];std::snprintf(b,sizeof b,"\\u%04x",c);o+=b;}else o+=char(c);}
    return o;
}
inline std::string real_path(const std::string&p){char buf[PATH_MAX];return ::realpath(p.c_str(),buf)?std::string(buf):p;}
struct LoadedObjects {std::vector<std::string> paths;std::string containing;};
// Every loaded object, and the one whose PT_LOAD segments contain addr (empty if none or addr is null).
inline LoadedObjects loaded_objects(const void*addr){
    LoadedObjects r;struct Ctx{const void*addr;LoadedObjects*r;} ctx{addr,&r};
    dl_iterate_phdr([](struct dl_phdr_info*info,size_t,void*data)->int{
        auto*c=static_cast<Ctx*>(data);
        std::string name=info->dlpi_name&&*info->dlpi_name?real_path(info->dlpi_name):real_path("/proc/self/exe");
        c->r->paths.push_back(name);
        if(c->addr)for(int i=0;i<info->dlpi_phnum;++i){const auto&p=info->dlpi_phdr[i];if(p.p_type!=PT_LOAD)continue;
            uintptr_t lo=info->dlpi_addr+p.p_vaddr,a=reinterpret_cast<uintptr_t>(c->addr);
            if(a>=lo&&a<lo+p.p_memsz)c->r->containing=name;}
        return 0;},&ctx);
    return r;
}
// The "gmp" block; mismatch is set when the header and runtime versions differ (--describe then exits 3).
inline std::string gmp_block(bool&mismatch){
#ifdef C7_USE_GMP
    std::string header=std::to_string(__GNU_MP_VERSION)+"."+std::to_string(__GNU_MP_VERSION_MINOR)+"."+std::to_string(__GNU_MP_VERSION_PATCHLEVEL);
    std::string runtime=gmp_version;LoadedObjects o=loaded_objects(static_cast<const void*>(gmp_version));
    mismatch=header!=runtime;
    return "{\"applicable\":true,\"header_version\":\""+header+"\",\"runtime_version\":\""+json_escape(runtime)+"\",\"library\":\""+json_escape(o.containing)+"\"}";
#else
    mismatch=false;return "{\"applicable\":false}";
#endif
}
inline std::string libraries_json(){
    LoadedObjects o=loaded_objects(nullptr);std::string s="[";
    for(size_t i=0;i<o.paths.size();++i){if(i)s+=',';s+="\""+json_escape(o.paths[i])+"\"";}
    return s+"]";
}
// Diagnostic identity (plan refuses every diagnostic executable, A-KER-3).
#if defined(C8_TEST_UNGUARDED_INDEX)
static constexpr const char* diagnostic_kind="unguarded_index_selftest";
#elif defined(C8_TIER_TIMERS) || defined(C8_RATIO_HISTOGRAM)
static constexpr const char* diagnostic_kind=C8_DIAGNOSTIC_KIND;
#elif defined(__SANITIZE_ADDRESS__) || defined(_GLIBCXX_ASSERTIONS)
static constexpr const char* diagnostic_kind="sanitize";
#elif defined(C8_NO_TAIL_FIELDS)
static constexpr const char* diagnostic_kind="no_tail_fields";
#elif defined(C8_ORDER_TRACE)
static constexpr const char* diagnostic_kind="order_trace";
#else
static constexpr const char* diagnostic_kind=nullptr;
#endif
static constexpr const char* numerics_profile="exact";  // opt-in profiles (A-FLAG, Stage 4c) are separate builds
// The fields both executables' --describe share, after "schema" (no braces).
inline std::string describe_common(bool&mismatch){
    std::string s="\"dimension\":3,\"orders\":["+std::to_string(ORDER_MIN)+","+std::to_string(ORDER_MAX)+"],\"lmax\":"+std::to_string(LMAX)
        +",\"kmax\":"+std::to_string(KMAX)+",\"emax\":"+std::to_string(EMAX)+",\"dimmax\":"+std::to_string(DIMMAX)
        +",\"numerics\":\""+numerics_profile+"\",\"diagnostic\":"+(diagnostic_kind?"true":"false");
    if(diagnostic_kind)s+=std::string(",\"diagnostic_kind\":\"")+diagnostic_kind+"\"";
#ifdef C8_TEST_UNGUARDED_INDEX
    s+=",\"unguarded_index_selftest\":true";
#endif
    s+=std::string(",\"boost\":\"")+BOOST_LIB_VERSION+"\",\"boost_version\":"+std::to_string(BOOST_VERSION)+",\"gmp\":"+gmp_block(mismatch)+",\"libraries\":"+libraries_json()
        +",\"compiler\":\""+json_escape(__VERSION__)+"\",\"long_double_bits\":"+std::to_string(std::numeric_limits<ld>::digits)+",\"mp_backend\":\""+mp_backend
        +"\",\"mp_digits10\":"+std::to_string(std::numeric_limits<MP>::digits10)+",\"mp_max_digits10\":"+std::to_string(std::numeric_limits<MP>::max_digits10)
        +",\"openmp\":"+std::to_string(_OPENMP);
    return s;
}
