#pragma once
#include <stdio.h>
#include <math.h>
#include "espnow_protocol.h"

namespace HubCsv {
constexpr const char* HEADER="rtc_utc,watch_utc,watch_boot,radio_sequence,watch_uptime_ms,flags,temperature_c,humidity_pct,pressure_hpa,bpm_estimate,spo2_estimate_pct,iaq,iaq_accuracy,battery_v,battery_pct,current_ma_uncalibrated,acc_x_raw,acc_y_raw,acc_z_raw,mag_x_raw,mag_y_raw,mag_z_raw,wifi,mqtt,watch_fw,hub_fw\r\n";
struct Sample {KuLink::TelemetryPacket packet;uint64_t rtcUtc=0;};
// Cadence uses the hub monotonic clock, never a user-adjustable wall clock.
// An absent peer or invalid RTC creates a visible gap, never a fabricated row.
class Cadence {
  uint32_t attemptAt=0,session=0,sequence=0;
public:
  bool due(uint32_t now) const{return !attemptAt || uint32_t(now-attemptAt)>=5000;}
  bool accept(const KuLink::TelemetryPacket& p,uint32_t now,uint32_t receivedAt,uint64_t rtc,uint32_t rtcAt) {
    if(!due(now))return false;attemptAt=now?now:1;
    if(!receivedAt || uint32_t(now-receivedAt)>1500 || !rtcAt || uint32_t(now-rtcAt)>2000 || rtc<1704067200ULL || rtc>4102444799ULL ||
       !p.h.session || !p.h.sequence || !(p.flags&KuLink::Clock) || p.utc<1704067200ULL || p.utc>4102444799ULL ||
       (session==p.h.session && sequence==p.h.sequence))return false;
    session=p.h.session;sequence=p.h.sequence;return true;
  }
};
inline void number(char* dest,size_t size,bool valid,double value,unsigned decimals=3){
  if(valid && isfinite(value))snprintf(dest,size,"%.*f",int(decimals),value);else dest[0]=0;
}
inline bool format(const Sample& s,char* dest,size_t size,const char* hubVersion) {
  const auto& p=s.packet;char v[15][24]{};
  const double values[]={p.temperature,p.humidity,p.pressure,p.bpm,p.spo2,p.iaq,p.batteryVolts,p.batteryPercent,p.current,double(p.acc[0]),double(p.acc[1]),double(p.acc[2]),double(p.mag[0]),double(p.mag[1]),double(p.mag[2])};
  const uint32_t flags[]={KuLink::Environment,KuLink::Environment,KuLink::Environment,KuLink::Pulse,KuLink::Spo2,KuLink::Iaq,KuLink::Battery,KuLink::Battery,KuLink::Current,KuLink::Motion,KuLink::Motion,KuLink::Motion,KuLink::Mag,KuLink::Mag,KuLink::Mag};
  for(unsigned i=0;i<15;++i)number(v[i],sizeof(v[i]),p.flags&flags[i],values[i],i>=9?0:3);
  char accuracy[8]{};if(p.flags&KuLink::Iaq)snprintf(accuracy,sizeof(accuracy),"%u",p.iaqAccuracy);
  char firmware[12];memcpy(firmware,p.firmware,11);firmware[11]=0;
  for(char* c=firmware;*c;++c)if(!((*c>='0'&&*c<='9')||(*c>='a'&&*c<='z')||(*c>='A'&&*c<='Z')||*c=='.'||*c=='-'||*c=='_'))*c='_';
  int n=snprintf(dest,size,"%llu,%llu,%08lx,%lu,%lu,%lu,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%u,%u,%s,%s\r\n",
    (unsigned long long)s.rtcUtc,(unsigned long long)p.utc,(unsigned long)p.h.session,(unsigned long)p.h.sequence,(unsigned long)p.uptime,(unsigned long)p.flags,
    v[0],v[1],v[2],v[3],v[4],v[5],accuracy,v[6],v[7],v[8],v[9],v[10],v[11],v[12],v[13],v[14],bool(p.flags&KuLink::Wifi),bool(p.flags&KuLink::Mqtt),firmware,hubVersion);
  return n>0 && size_t(n)<size;
}
}
