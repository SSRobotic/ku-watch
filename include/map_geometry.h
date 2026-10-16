#pragma once
#include "activity_format.h"
#include <stdlib.h>

namespace WatchMap {
constexpr unsigned MAX_FEATURES=4096,MAX_POINTS=32768,TRAIL_POINTS=512;
enum Kind : uint8_t { GREEN=1,WATER=2,BUILDING=3,ROAD=4,WATERWAY=5 };
#pragma pack(push,1)
struct Header {
  char magic[8]; uint32_t version;
  int32_t latitudeE7,longitudeE7; uint32_t radius;
  uint16_t features,points; uint32_t payloadCrc;
  char name[24]; uint32_t reserved,headerCrc;
};
struct Feature { uint16_t offset,count; uint8_t kind,style; };
struct Point { int32_t lat,lon; };
#pragma pack(pop)
static_assert(sizeof(Header)==64 && sizeof(Feature)==6 && sizeof(Point)==8,"Map format");
struct Bounds { int32_t minLat,maxLat,minLon,maxLon; };
struct Data { Header header; Feature features[MAX_FEATURES]; Point points[MAX_POINTS]; Bounds bounds[MAX_FEATURES]; };
constexpr size_t MAX_BYTES=sizeof(Header)+MAX_FEATURES*sizeof(Feature)+MAX_POINTS*sizeof(Point);
inline bool coordinates(int32_t lat,int32_t lon) {
  return lat>=-900000000 && lat<=900000000 && lon>=-1800000000 && lon<=1800000000;
}
inline bool validHeader(const Header& h,size_t bytes) {
  return !memcmp(h.magic,"KUMAP1\0",8) && h.version==1 && coordinates(h.latitudeE7,h.longitudeE7) &&
    abs(h.latitudeE7)<850000000 && h.radius>=100 && h.radius<=10000 && h.features>0 &&
    h.features<=MAX_FEATURES && h.points<=MAX_POINTS && h.points>=2 &&
    bytes==sizeof(Header)+h.features*sizeof(Feature)+h.points*sizeof(Point) &&
    h.name[23]==0 && Activity::crc32(&h,offsetof(Header,headerCrc))==h.headerCrc;
}
inline bool valid(const Data& d,size_t bytes) {
  const auto& h=d.header; if(!validHeader(h,bytes)) return false;
  uint32_t crc=Activity::crcUpdate(0xffffffffu,d.features,h.features*sizeof(Feature));
  crc=Activity::crcUpdate(crc,d.points,h.points*sizeof(Point));
  if(~crc!=h.payloadCrc) return false;
  for(unsigned i=0;i<h.features;++i) {
    const auto& f=d.features[i];
    if(f.count<2 || unsigned(f.offset)+f.count>h.points || f.kind<GREEN || f.kind>WATERWAY || f.style>3) return false;
  }
  for(unsigned i=0;i<h.points;++i) if(!coordinates(d.points[i].lat,d.points[i].lon)) return false;
  return true;
}
inline void index(Data& d) {
  for(unsigned i=0;i<d.header.features;++i) {
    const auto& f=d.features[i];const auto& first=d.points[f.offset];
    auto& b=d.bounds[i];b={first.lat,first.lat,first.lon,first.lon};
    for(unsigned j=1;j<f.count;++j) {
      const auto& p=d.points[f.offset+j];
      if(p.lat<b.minLat) b.minLat=p.lat;if(p.lat>b.maxLat) b.maxLat=p.lat;
      if(p.lon<b.minLon) b.minLon=p.lon;if(p.lon>b.maxLon) b.maxLon=p.lon;
    }
  }
}
inline double longitudeDelta(double a,double b) {
  double delta=a-b;
  if(delta>180) delta-=360; if(delta< -180) delta+=360;
  return delta;
}
inline void meters(double lat,double lon,double centerLat,double centerLon,double& east,double& north) {
  east=longitudeDelta(lon,centerLon)*111319.490793*cos(centerLat*.017453292519943295);
  north=(lat-centerLat)*111319.490793;
}
inline bool covers(const Data* d,double lat,double lon) {
  if(!d || !isfinite(lat) || !isfinite(lon) || fabs(lat)>90 || fabs(lon)>180) return false;
  double e,n; meters(lat,lon,d->header.latitudeE7/1e7,d->header.longitudeE7/1e7,e,n);
  return fabs(e)<=d->header.radius && fabs(n)<=d->header.radius;
}
// Liang-Barsky clipping keeps distant coordinates out of the raster line loop.
inline bool clip(double& x0,double& y0,double& x1,double& y1) {
  if(!isfinite(x0)||!isfinite(y0)||!isfinite(x1)||!isfinite(y1)) return false;
  double dx=x1-x0,dy=y1-y0,low=0,high=1;
  double p[4]={-dx,dx,-dy,dy},q[4]={x0,239-x0,y0,239-y0};
  for(unsigned i=0;i<4;++i) {
    if(p[i]==0) {if(q[i]<0) return false;}
    else { double r=q[i]/p[i]; if(p[i]<0) {if(r>high) return false; if(r>low) low=r;}
      else {if(r<low) return false; if(r<high) high=r;} }
  }
  x1=x0+high*dx; y1=y0+high*dy; x0+=low*dx; y0+=low*dy; return true;
}
struct TrailPoint { Point point; bool gap; };
class Trail {
  TrailPoint points_[TRAIL_POINTS]; unsigned start_=0,count_=0; bool gap_=true;
  uint32_t lastMs_=0;
public:
  unsigned count() const { return count_; }
  const TrailPoint& at(unsigned index) const { return points_[(start_+index)%TRAIL_POINTS]; }
  void clear() { start_=count_=0; gap_=true; lastMs_=0; }
  void append(const Activity::Record& r) {
    if(!(r.flags&Activity::GPS) || !coordinates(r.latitudeE7,r.longitudeE7)) {gap_=true;return;}
    bool split=gap_ || (count_ && uint32_t(r.elapsedMs-lastMs_)>5000);
    lastMs_=r.elapsedMs;
    if(count_ && !split) {
      const auto& last=at(count_-1).point;
      if(Activity::distance(last.lat/1e7,last.lon/1e7,r.latitudeE7/1e7,r.longitudeE7/1e7)<3) return;
    }
    if(count_==TRAIL_POINTS) { start_=(start_+1)%TRAIL_POINTS; --count_; }
    points_[(start_+count_)%TRAIL_POINTS]={{r.latitudeE7,r.longitudeE7},split}; ++count_; gap_=false;
  }
};
}
