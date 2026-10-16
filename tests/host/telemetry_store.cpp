#include <cstdlib>
#include <string>
#include "telemetry_store.h"
static unsigned checks=0;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"FAIL %d %s\n",__LINE__,#x);exit(1);}}while(0)
static std::string sample(unsigned n){return "{\"timestamp\":"+std::to_string(1790123456+n)+",\"temp\":30.12,\"sample_id\":\"a-"+std::to_string(n)+"\"}";}
static void reset(){flashFiles.clear();flashWriteLimit=-1;fakeMillis=0;flashTotal=1048576;}
static bool append(TelemetryStore& s,unsigned n){fakeMillis=n*1000;return s.append(sample(n).c_str(),n+1,fakeMillis);}
int main(){
  reset();flashFiles["/map0.kum"]={1,2,3};flashFiles["/rec000003.kua"]={4,5,6};
  TelemetryStore store;store.begin(true);CHECK(store.ready && !store.pending);
  for(unsigned n=0;n<600;++n)CHECK(append(store,n));
  CHECK(store.pending==600 && !store.dropped && !store.errors);
  CHECK(LittleFS.totalBytes()-LittleFS.usedBytes()>TelemetryStore::RESERVE);
  TelemetryStore reboot;reboot.begin(true);CHECK(reboot.ready && reboot.pending==600);
  char json[2304];uint64_t token=0;uint32_t captured=0;
  CHECK(!reboot.ack(99));CHECK(reboot.pending==600);
  // An eight-packet window crosses sealed segment boundaries without moving
  // the durable head until an ordered ACK has been received.
  for(unsigned offset:{0u,7u,63u,64u,599u}) {
    CHECK(reboot.peekAt(offset,json,sizeof(json),token,captured));CHECK(json==sample(offset));
    CHECK(token==offset+1 && captured==offset*1000);
  }
  CHECK(!reboot.peekAt(600,json,sizeof(json),token,captured));CHECK(reboot.pending==600);
  for(unsigned n=0;n<600;++n){
    if(n+7<600){CHECK(reboot.peekAt(7,json,sizeof(json),token,captured));CHECK(json==sample(n+7));}
    CHECK(reboot.peek(json,sizeof(json),token,captured));CHECK(json==sample(n));
    CHECK(token==n+1 && captured==n*1000);CHECK(reboot.ack(token));
  }
  CHECK(reboot.pending==0);CHECK(!reboot.peek(json,sizeof(json),token,captured));
  CHECK(flashFiles["/map0.kum"]==std::vector<uint8_t>({1,2,3}));
  CHECK(flashFiles["/rec000003.kua"]==std::vector<uint8_t>({4,5,6}));
  // Only final acknowledged segment is replayed after a power cut. Earlier
  // fully acknowledged segments were removed, no unacknowledged row is lost.
  TelemetryStore replay;replay.begin(true);CHECK(replay.pending==24);
  for(unsigned n=576;n<600;++n){CHECK(replay.peek(json,sizeof(json),token,captured));CHECK(json==sample(n));CHECK(replay.ack(token));}
  for(unsigned n=600;n<640;++n) {CHECK(append(replay,n));CHECK(replay.peek(json,sizeof(json),token,captured));CHECK(replay.ack(token));}
  TelemetryStore empty;empty.begin(true);CHECK(empty.ready && !empty.pending);
  reset();TelemetryStore full;full.begin(true);
  for(unsigned n=0;n<Telemetry::MAX_PENDING;++n)CHECK(append(full,n));
  CHECK(!append(full,768));CHECK(full.pending==768 && full.dropped==1);
  CHECK(full.peek(json,sizeof(json),token,captured));CHECK(json==sample(0)); // preserves oldest
  reset();TelemetryStore torn;torn.begin(true);CHECK(append(torn,0));
  flashWriteLimit=300;CHECK(!append(torn,1));CHECK(!torn.ready && torn.dropped==1);
  flashWriteLimit=-1;TelemetryStore recover;recover.begin(true);
  CHECK(recover.ready && recover.pending==1 && recover.errors==1);
  CHECK(append(recover,2));CHECK(recover.peek(json,sizeof(json),token,captured));CHECK(recover.ack(token));
  CHECK(recover.peek(json,sizeof(json),token,captured));CHECK(json==sample(2)); // incomplete slot overwritten
  reset();TelemetryStore corrupt;corrupt.begin(true);
  for(unsigned n=0;n<5;++n)CHECK(append(corrupt,n));
  flashFiles["/tq00000001.ktq"][sizeof(Telemetry::Record)+22]^=1;
  auto preserved=flashFiles;TelemetryStore rejected;rejected.begin(true);
  CHECK(!rejected.ready && rejected.errors==1);CHECK(flashFiles==preserved); // never formats or erases evidence
  reset();flashTotal=TelemetryStore::RESERVE+4096;TelemetryStore scarce;scarce.begin(true);
  CHECK(!append(scarce,0));CHECK(scarce.dropped==1 && scarce.pending==0);
  printf("PASS durable telemetry store: %u checks (10-minute replay, reboot, full, torn write, corrupt middle, reserve)\n",checks);
}
