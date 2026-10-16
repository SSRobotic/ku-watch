#include <cstdio>
#include <cstdlib>
#include <string>
#include "telemetry_format.h"
static unsigned checks=0;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"FAIL %d %s\n",__LINE__,#x);exit(1);}}while(0)
int main() {
  Telemetry::Record r;
  char decoded[2304];
  std::string sample="{";
  for(unsigned k=0;k<Telemetry::KEY_COUNT;++k) {
    if(k)sample+=',';
    sample+='"';sample+=Telemetry::keys[k];sample+="\":";
    sample+=(k%5==0)?"null":(k%5==1)?"true":(k%5==2)?"-123.4567":(k%5==3)?"1790123456":"\"test_watch\"";
  }
  sample+='}';
  CHECK(Telemetry::encode(sample.c_str(),1311768465173141112ULL,r,0xfffffff0));
  CHECK(r.size<sizeof(r.bytes));CHECK(Telemetry::valid(r));
  CHECK(Telemetry::decode(r,decoded,sizeof(decoded)));CHECK(sample==decoded);
  CHECK(r.capturedMs==0xfffffff0);
  for(size_t i=0;i<sizeof(r);++i) {
    auto broken=r;reinterpret_cast<uint8_t*>(&broken)[i]^=1;
    CHECK(!Telemetry::valid(broken));CHECK(!Telemetry::decode(broken,decoded,sizeof(decoded)));
  }
  for(size_t n=0;n<=sample.size();++n)CHECK(!Telemetry::decode(r,decoded,n));
  CHECK(Telemetry::decode(r,decoded,sample.size()+1));
  for(unsigned k=0;k<Telemetry::KEY_COUNT;++k) {
    std::string json="{\"unknown\":\"escaped\\\"value\",\""+std::string(Telemetry::keys[k])+"\":null}";
    CHECK(Telemetry::encode(json.c_str(),k+1,r));CHECK(Telemetry::decode(r,decoded,sizeof(decoded)));CHECK(json==decoded);
  }
  CHECK(!Telemetry::encode(nullptr,1,r));CHECK(!Telemetry::encode("{}",0,r));
  CHECK(!Telemetry::encode("{\"x\":\"\xc3\xa9\"}",1,r));
  std::string enormous(1000,'x');CHECK(!Telemetry::encode(enormous.c_str(),1,r));
  CHECK(Telemetry::encode("{}",1,r));r.bytes[0]=255;r.crc=Activity::crc32(&r,offsetof(Telemetry::Record,crc));
  CHECK(!Telemetry::decode(r,decoded,sizeof(decoded)));
  Telemetry::Flight flight;
  CHECK(!flight.start(0));CHECK(flight.start(7));CHECK(!flight.start(8));
  CHECK(!flight.acknowledged(0));CHECK(!flight.acknowledged(8));CHECK(flight.token==7);
  CHECK(flight.acknowledged(7));CHECK(!flight.acknowledged(7));CHECK(flight.start(8));
  // Ten minutes of capture retains exactly the original JSON and sequence.
  for(unsigned i=0;i<600;++i) {
    std::string original="{\"temp\":30.12,\"timestamp\":"+std::to_string(1790123456+i)+",\"sample_id\":\"s-"+std::to_string(i)+"\",\"bpm\":null}";
    CHECK(Telemetry::encode(original.c_str(),uint64_t(i)+1,r,i*1000));
    CHECK(Telemetry::decode(r,decoded,sizeof(decoded)));CHECK(original==decoded);
  }
  printf("PASS telemetry codec/CRC/ACK: %u checks; full fixture %zu bytes\n",checks,sample.size());
}
