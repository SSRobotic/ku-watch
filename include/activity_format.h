#pragma once
#include <stdint.h>
#include <stddef.h>
#include <math.h>
#include <string.h>

namespace Activity {
enum : uint16_t { GPS=1, HEART=2, ALTITUDE=4, STOP=0x8000 };
#pragma pack(push,1)
struct Header {
  char magic[8]; uint32_t version, recordSize; uint64_t utc;
  uint32_t intervalMs, crc;
};
struct Record {
  uint32_t elapsedMs;
  int32_t latitudeE7, longitudeE7, altitudeCm;
  uint16_t bpm10, flags;
  uint32_t distanceCm, reserved, crc;
};
#pragma pack(pop)
static_assert(sizeof(Header)==32 && sizeof(Record)==32,"Activity format must stay fixed");
inline uint32_t crcUpdate(uint32_t crc,const void* data,size_t size) {
  auto p=static_cast<const uint8_t*>(data);
  while(size--) {
    crc^=*p++;
    for(unsigned i=0;i<8;++i) crc=(crc>>1)^((crc&1)?0xedb88320u:0);
  }
  return crc;
}
inline uint32_t crc32(const void* data,size_t size) { return ~crcUpdate(0xffffffffu,data,size); }
inline Header header(uint64_t utc) {
  Header h={}; memcpy(h.magic,"KUWALK1",7); h.version=1;
  h.recordSize=sizeof(Record); h.utc=utc; h.intervalMs=1000;
  h.crc=crc32(&h,offsetof(Header,crc)); return h;
}
inline void seal(Record& r) { r.crc=crc32(&r,offsetof(Record,crc)); }
inline double distance(double lat1,double lon1,double lat2,double lon2) {
  constexpr double rad=0.017453292519943295;
  double a=sin((lat2-lat1)*rad/2),b=sin((lon2-lon1)*rad/2);
  double h=a*a+cos(lat1*rad)*cos(lat2*rad)*b*b;
  return 6371000*2*asin(sqrt(fmin(1.0,fmax(0.0,h))));
}
class Track {
  bool anchored=false;
  double lat=0,lon=0;
  uint32_t anchorMs=0,lastFixMs=0;
public:
  double meters=0;
  bool point(uint32_t ms,double latitude,double longitude,bool valid) {
    if(!valid || !isfinite(latitude) || !isfinite(longitude) || fabs(latitude)>90 || fabs(longitude)>180) {
      anchored=false; return false;
    }
    if(!anchored || uint32_t(ms-lastFixMs)>5000) {
      lat=latitude; lon=longitude; anchorMs=lastFixMs=ms; anchored=true; return true;
    }
    double step=distance(lat,lon,latitude,longitude);
    // A walking recorder: reject implausible jumps and suppress small stationary drift.
    if(step>12.0*(ms-anchorMs)/1000.0+10.0) { anchored=false; return false; }
    lastFixMs=ms;
    if(step>=3.0) { meters+=step; lat=latitude; lon=longitude; anchorMs=ms; }
    return true;
  }
};
}
