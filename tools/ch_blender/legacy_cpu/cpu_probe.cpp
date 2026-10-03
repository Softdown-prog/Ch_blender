#include <intrin.h>
#include <cstdio>
int main() {
 int r[4]; __cpuid(r,1); unsigned c=r[2],d=r[3]; __cpuid(r,0x80000001); unsigned e=r[2];
 int b[13] = {}; for(int i=0;i<3;i++) __cpuid(b+i*4,0x80000002+i);
 std::printf("{\"model\":\"%s\",\"x86_64\":true,\"sse\":%s,\"sse2\":%s,\"sse3\":%s,\"ssse3\":%s,\"sse4a\":%s,\"sse41\":%s,\"sse42\":%s,\"avx\":%s,\"f16c\":%s,",(char*)b,(d&(1u<<25))?"true":"false",(d&(1u<<26))?"true":"false",(c&1)?"true":"false",(c&(1u<<9))?"true":"false",(e&(1u<<6))?"true":"false",(c&(1u<<19))?"true":"false",(c&(1u<<20))?"true":"false",(c&(1u<<28))?"true":"false",(c&(1u<<29))?"true":"false");
 __cpuidex(r,7,0); std::printf("\"avx2\":%s}\n",(r[1]&(1u<<5))?"true":"false"); return 0;
}
