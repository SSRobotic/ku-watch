#include <cassert>
#include <iostream>
#include <limits>
#include "watch_extensions.h"
#include "espnow_protocol.h"
int main() {
  using namespace WatchExt;
  Settings s;strcpy(s.topic,"ku_watch/live");seal(s);assert(intact(s));
  Settings bad=s;bad.led=0;seal(bad);assert(!intact(bad));
  bad=s;bad.average=2;seal(bad);assert(!intact(bad));
  bad=s;bad.shuntOhms=std::numeric_limits<float>::quiet_NaN();seal(bad);assert(!intact(bad));
  bad=s;strcpy(bad.manifest,"http://example.com/manifest.json");seal(bad);assert(!intact(bad));
  bad=s;memset(bad.ssid,'A',sizeof(bad.ssid));seal(bad);assert(!intact(bad));
  bad=s;strcpy(bad.topic,"a/#");seal(bad);assert(!intact(bad));
  bad=s;bad.crc^=1;assert(!intact(bad));
  strcpy(s.manifest,"https://example.com/manifest.json");seal(s);assert(intact(s));
  Backoff b;b.reset(0);assert(b.due(0));b.failed(0);assert(!b.due(999));assert(b.due(1000));
  b.failed(1000);assert(!b.due(2999));assert(b.due(3000));
  for(unsigned i=0;i<30;++i)b.failed(3000);assert(b.delay()==60000);
  b.reset(0xfffffff0);b.failed(0xfffffff0);assert(!b.due(0));assert(b.due(1000));
  int16_t raw[3]={1000,0,0};assert(isnan(heading(raw,s)));
  s.magCalibrated=1;for(unsigned i=0;i<3;++i){s.magMin[i]=-1000;s.magMax[i]=1000;}
  assert(fabs(heading(raw,s))<.001);raw[0]=0;raw[1]=1000;assert(fabs(heading(raw,s)-90)<.001);
  raw[2]=-4096;assert(isnan(heading(raw,s)));
  KuLink::CommandPacket p;p.action=KuLink::RecordStart;p.receiverSession=111;
  KuLink::seal(p,KuLink::Command,77,1);assert(KuLink::valid(p,KuLink::Command));
  p.argument^=1;assert(!KuLink::valid(p,KuLink::Command));p.argument^=1;
  assert(!KuLink::valid(p,KuLink::Ack));
  KuLink::Commands c;assert(c.accept(77,1));assert(!c.accept(77,1));assert(!c.accept(77,0));
  assert(c.accept(77,2));assert(!c.accept(77,1));assert(c.accept(78,1));
  KuLink::TelemetryPacket t;KuLink::seal(t,KuLink::Telemetry,1,1);assert(KuLink::valid(t,KuLink::Telemetry));
  assert(sizeof(t)<=250);std::cout<<"Watch settings, backoff, compass and protocol checks passed; telemetry "<<sizeof(t)<<" bytes\n";
}
