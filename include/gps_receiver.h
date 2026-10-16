#pragma once
#include <TinyGPS++.h>
#include <math.h>
#include <stdint.h>
#include <initializer_list>
#include "gsv_status.h"

struct GpsReading {
  bool data = false, fix = false;
  double latitude = NAN, longitude = NAN;
  float altitude = NAN, speed = NAN, hdop = NAN;
  uint32_t satellites = 0;
  bool viewValid = false, signalValid = false;
  uint32_t inView = 0, signal = 0;
  uint32_t positionAge = 0xffffffffu;
  uint64_t utc = 0;
  uint32_t utcAgeMs = 0xffffffffu;
  bool reliable() const {
    return fix && positionAge<2000 && satellites>=4 && isfinite(hdop) && hdop>0 && hdop<=5 &&
      isfinite(latitude) && isfinite(longitude) && fabs(latitude)<=90 && fabs(longitude)<=180;
  }
};

class GpsReceiver {
  TinyGPSPlus parser;
  // TinyGPS++ retains old coordinates after a no-fix sentence. Track explicit
  // fix flags as well, so stale coordinates cannot masquerade as a current fix.
  TinyGPSCustom gpRmc{parser,"GPRMC",2}, gnRmc{parser,"GNRMC",2};
  TinyGPSCustom gbRmc{parser,"GBRMC",2};
  TinyGPSCustom gpGga{parser,"GPGGA",6}, gnGga{parser,"GNGGA",6};
  TinyGPSCustom gbGga{parser,"GBGGA",6};
  GsvStatus gpView{parser,"GPGSV"}, bdView{parser,"BDGSV"}, gbView{parser,"GBGSV"};
  GsvStatus glView{parser,"GLGSV"}, gaView{parser,"GAGSV"}, gnView{parser,"GNGSV"};
  bool seen = false, fixAllowed = false;
  uint32_t sentenceAt = 0;
  unsigned sentenceFields = 0;
public:
  void encode(char c, uint32_t now) {
    if(c=='$') sentenceFields=0;
    else if(c==',' && sentenceFields<100) ++sentenceFields;
    if (!parser.encode(c)) return; // A complete checksum-valid sentence only.
    for(auto group:{&gpView,&bdView,&gbView,&glView,&gaView,&gnView}) group->update(now,sentenceFields);
    TinyGPSCustom *rmc[]={&gpRmc,&gnRmc,&gbRmc};
    TinyGPSCustom *gga[]={&gpGga,&gnGga,&gbGga};
    for (auto field:rmc) if(field->isUpdated()) {
      fixAllowed=field->value()[0]=='A'; seen=true; sentenceAt=now;
    }
    for (auto field:gga) if(field->isUpdated()) {
      const char *v=field->value();
      // Accept GNSS/differential/RTK fixes, not estimated or simulated fixes.
      fixAllowed=v[1]==0 && (v[0]=='1'||v[0]=='2'||v[0]=='4'||v[0]=='5');
      seen=true; sentenceAt=now;
    }
  }
  GpsReading reading(uint32_t now, uint32_t staleMs) {
    GpsReading r;
    r.data=seen && uint32_t(now-sentenceAt)<staleMs;
    // BD and GB are aliases for BeiDou. GN may already combine constellations.
    GsvStatus* beidou=gbView.fresh(now,staleMs) &&
      (!bdView.fresh(now,staleMs) || uint32_t(now-gbView.at)<=uint32_t(now-bdView.at))?&gbView:&bdView;
    for(auto group:{&gpView,beidou,&glView,&gaView}) if(group->fresh(now,staleMs)) {
      r.viewValid=true; r.inView+=group->count;
      if(group->signalValid) { r.signalValid=true; if(group->signal>r.signal) r.signal=group->signal; }
    }
    if(!r.viewValid && gnView.fresh(now,staleMs)) {
      r.viewValid=true; r.inView=gnView.count;
      r.signalValid=gnView.signalValid; r.signal=gnView.signal;
    }
    r.data=r.data || r.viewValid;
    r.fix=r.data && fixAllowed && parser.location.isValid() && parser.location.age()<staleMs;
    r.positionAge=parser.location.age();
    if (r.data && parser.satellites.isValid() && parser.satellites.age()<staleMs) r.satellites=parser.satellites.value();
    if (r.data && parser.hdop.isValid() && parser.hdop.age()<staleMs) r.hdop=parser.hdop.hdop();
    if (r.fix) {
      r.latitude=parser.location.lat(); r.longitude=parser.location.lng();
      if (parser.altitude.isValid() && parser.altitude.age()<staleMs) r.altitude=parser.altitude.meters();
      if (parser.speed.isValid() && parser.speed.age()<staleMs) r.speed=parser.speed.kmph();
      if(parser.date.isValid() && parser.time.isValid() && parser.date.age()<staleMs && parser.time.age()<staleMs) {
        unsigned y=parser.date.year(),m=parser.date.month(),d=parser.date.day();
        unsigned hh=parser.time.hour(),mm=parser.time.minute(),ss=parser.time.second();
        static const unsigned monthDays[]={31,28,31,30,31,30,31,31,30,31,30,31};
        bool leap=(y%4==0 && (y%100!=0 || y%400==0));
        if(y>=2024 && y<=2099 && m>=1 && m<=12 && d>=1 &&
           d<=monthDays[m-1]+unsigned(m==2 && leap) && hh<24 && mm<60 && ss<60) {
          uint64_t days=0;
          for(unsigned year=1970;year<y;++year) days+=365+unsigned(year%4==0 && (year%100!=0 || year%400==0));
          for(unsigned month=1;month<m;++month) days+=monthDays[month-1]+unsigned(month==2 && leap);
          r.utc=(days+d-1)*86400+hh*3600+mm*60+ss;
          r.utcAgeMs=parser.time.age()+parser.time.centisecond()*10;
        }
      }
    }
    return r;
  }
  uint32_t chars() const { return parser.charsProcessed(); }
  uint32_t checksumErrors() const { return parser.failedChecksum(); }
};
