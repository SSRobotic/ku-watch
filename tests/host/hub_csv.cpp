#include <assert.h>
#include <string>
#include <vector>
#include <iostream>
#include "hub_csv.h"
std::vector<std::string> fields(const char* s){std::vector<std::string> out;std::string text(s);size_t at=0;for(;;){auto end=text.find(',',at);out.push_back(text.substr(at,end==std::string::npos?end:end-at));if(end==std::string::npos)return out;at=end+1;}}
int main(){
  HubCsv::Cadence c;KuLink::TelemetryPacket p;p.h.session=7;p.h.sequence=10;p.flags=KuLink::Clock|KuLink::Environment|KuLink::Pulse;p.utc=1791955700;p.temperature=31.25;p.humidity=55;p.pressure=1001;p.bpm=75;strcpy(p.firmware,"2.0.8");
  assert(c.accept(p,1000,900,p.utc,900));
  ++p.h.sequence;assert(!c.accept(p,5999,5900,p.utc,5900));assert(c.accept(p,6000,5900,p.utc,5900));
  assert(!c.accept(p,11000,10900,p.utc,10900)); // Replayed packet cannot create a row.
  ++p.h.sequence;assert(!c.accept(p,16000,10000,p.utc,15900)); // Stale peer.
  assert(!c.accept(p,21000,20900,0,20900)); // Uninitialized RTC.
  assert(!c.accept(p,26000,25900,p.utc,23000)); // Stale RTC poll.
  p.flags&=~KuLink::Clock;assert(!c.accept(p,31000,30900,p.utc,30900));
  p.flags|=KuLink::Clock;p.h.session=8;p.h.sequence=1;assert(c.accept(p,36000,35900,p.utc,35900)); // New watch boot.
  HubCsv::Sample s;s.packet=p;s.rtcUtc=p.utc;char line[640];assert(HubCsv::format(s,line,sizeof(line),"1.0.6"));
  auto v=fields(line),h=fields(HubCsv::HEADER);assert(v.size()==26 && v.size()==h.size());
  assert(v[6]=="31.250" && v[9]=="75.000");assert(v[10].empty() && v[11].empty() && v[13].empty() && v[16].empty());
  assert(v[24]=="2.0.8");s.packet.temperature=NAN;assert(HubCsv::format(s,line,sizeof(line),"1.0.6"));assert(fields(line)[6].empty());
  s.packet.flags|=KuLink::Spo2|KuLink::Motion;s.packet.spo2=97;s.packet.acc[0]=-123;assert(HubCsv::format(s,line,sizeof(line),"1.0.6"));assert(fields(line)[10]=="97.000" && fields(line)[16]=="-123");
  char tiny[8];assert(!HubCsv::format(s,tiny,sizeof(tiny),"1.0.6"));
  std::cout<<"PASS CSV schema, validity, cadence, gaps, RTC and reboot handling\n";
}
