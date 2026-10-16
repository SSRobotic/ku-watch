#pragma once
#include <stdint.h>
#include <stddef.h>
#include "activity_format.h"

namespace ClockModel {
enum Source : uint8_t {Waiting,Retained,Gps,Network,Manual,Hub};
inline bool valid(uint64_t utc){return utc>=1704067200ULL && utc<=4102444799ULL;}
#pragma pack(push,1)
struct Saved {uint32_t magic=0x32434c4b;uint64_t utc=0;uint32_t crc=0;};
#pragma pack(pop)
inline Saved checkpoint(uint64_t utc) {Saved s;s.utc=utc;s.crc=Activity::crc32(&s,offsetof(Saved,crc));return s;}
inline bool intact(const Saved& s){return s.magic==0x32434c4b && valid(s.utc) && s.crc==Activity::crc32(&s,offsetof(Saved,crc));}
class Model {
  uint64_t base=0,at=0;
public:
  Source source=Waiting;
  bool live=false,restored=false;
  void begin(uint64_t build,uint64_t retained,const Saved* saved,uint64_t us) {
    base=build;at=us;source=Waiting;live=false;restored=false;
    if(valid(retained)){base=retained;source=Retained;live=true;restored=true;}
    else if(saved && intact(*saved)){base=saved->utc;restored=true;}
    // A flash checkpoint has no knowledge of time spent fully powered off.
  }
  bool synchronize(uint64_t utc,Source next,uint64_t us) {
    if(!valid(utc) || next==Waiting)return false;
    base=utc;at=us;source=next;live=true;return true;
  }
  bool restoreFromHub(uint64_t utc,uint64_t us) {
    // The paired hub is a fallback after a cold boot. It must not overwrite
    // an already established GPS, NTP, manual or retained clock.
    return !live && synchronize(utc,Hub,us);
  }
  uint64_t utc(uint64_t us) const {return base+(us>=at?(us-at)/1000000ULL:0);}
  const char* label() const {
    switch(source){case Retained:return "RTC TIME";case Gps:return "GPS TIME";
      case Network:return "NET TIME";case Manual:return "MANUAL TIME";
      case Hub:return "HUB RTC TIME";default:return "WAIT GPS/WIFI";}
  }
};
}
