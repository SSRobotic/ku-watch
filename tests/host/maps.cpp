#include <cstdio>
#include <cstdlib>
#include <chrono>
#include "map_geometry.h"
constexpr uint8_t INA226_I2C_ADDRESS=0x44;
namespace Pin { constexpr int PAGE_COUNT=10; }
#include "face.h"
static unsigned checks=0;
#define CHECK(x) do {++checks;if(!(x)){fprintf(stderr,"FAIL %d %s\n",__LINE__,#x);exit(1);}}while(0)
static void seal(WatchMap::Data& d) {
  auto& h=d.header;uint32_t crc=Activity::crcUpdate(0xffffffffu,d.features,h.features*sizeof(WatchMap::Feature));
  h.payloadCrc=~Activity::crcUpdate(crc,d.points,h.points*sizeof(WatchMap::Point));
  h.headerCrc=Activity::crc32(&h,offsetof(WatchMap::Header,headerCrc));
  if(h.features<=WatchMap::MAX_FEATURES && h.points<=WatchMap::MAX_POINTS && d.features[0].offset==0) WatchMap::index(d);
}
static void preview(const char* path,const Face::Canvas& c) {
  FILE* f=fopen(path,"wb");CHECK(f);fprintf(f,"P6\n240 240\n255\n");
  for(auto v:c.pixels) {uint8_t rgb[]={uint8_t(((v>>11)&31)*255/31),uint8_t(((v>>5)&63)*255/63),uint8_t((v&31)*255/31)};fwrite(rgb,1,3,f);}fclose(f);
}
int main(int argc,char** argv) {
  static WatchMap::Data d={};auto& h=d.header;
  memcpy(h.magic,"KUMAP1\0",8);h.version=1;h.latitudeE7=138470500;h.longitudeE7=1005719420;h.radius=1200;h.features=1;h.points=2;strcpy(h.name,"TEST AREA");
  d.features[0]={0,2,WatchMap::ROAD,0};d.points[0]={h.latitudeE7,h.longitudeE7};d.points[1]={h.latitudeE7+1000,h.longitudeE7+1000};seal(d);
  size_t bytes=sizeof(h)+6+16;
  CHECK(WatchMap::valid(d,bytes));CHECK(!WatchMap::valid(d,bytes+1));CHECK(!WatchMap::valid(d,bytes-1));
  CHECK(WatchMap::covers(&d,13.84705,100.571942));CHECK(!WatchMap::covers(&d,15.8,104.6));CHECK(!WatchMap::covers(&d,NAN,100));CHECK(!WatchMap::covers(nullptr,0,0));
  h.version=2;CHECK(!WatchMap::valid(d,bytes));h.version=1;seal(d);
  d.points[0].lat++;CHECK(!WatchMap::valid(d,bytes));d.points[0].lat--;seal(d);
  d.features[0].offset=2;seal(d);CHECK(!WatchMap::valid(d,bytes));d.features[0].offset=0;seal(d);
  h.points=32769;CHECK(!WatchMap::validHeader(h,bytes));h.points=2;seal(d);
  h.features=65535;CHECK(!WatchMap::validHeader(h,bytes));h.features=1;seal(d);
  double a=-1e9,b=120,c=1e9,e=120;CHECK(WatchMap::clip(a,b,c,e));CHECK(fabs(a)<1e-6 && fabs(c-239)<1e-6);
  a=-100;b=-100;c=-10;e=-10;CHECK(!WatchMap::clip(a,b,c,e));
  a=NAN;b=0;c=10;e=10;CHECK(!WatchMap::clip(a,b,c,e));
  CHECK(fabs(WatchMap::longitudeDelta(-179.99,179.99)-.02)<1e-8);
  WatchMap::Trail trail;Activity::Record r={};r.flags=Activity::GPS;r.latitudeE7=h.latitudeE7;r.longitudeE7=h.longitudeE7;
  trail.append(r);CHECK(trail.count()==1 && trail.at(0).gap);
  r.elapsedMs=1000;r.latitudeE7+=10;trail.append(r);CHECK(trail.count()==1);
  r.elapsedMs=2000;r.latitudeE7+=400;trail.append(r);CHECK(trail.count()==2 && !trail.at(1).gap);
  r.flags=0;trail.append(r);r.flags=Activity::GPS;r.elapsedMs=3000;r.latitudeE7+=400;trail.append(r);CHECK(trail.at(2).gap);
  r.elapsedMs=10000;r.latitudeE7+=400;trail.append(r);CHECK(trail.at(3).gap);
  for(unsigned i=0;i<600;++i){r.elapsedMs+=1000;r.latitudeE7+=400;trail.append(r);}
  CHECK(trail.count()==WatchMap::TRAIL_POINTS);CHECK(trail.at(trail.count()-1).point.lat==r.latitudeE7);
  trail.clear();CHECK(trail.count()==0);
  Face::State s;s.page=6;s.map=&d;s.trail=&trail;s.latitude=13.84705;s.longitude=100.571942;s.gpsData=true;
  static Face::Canvas canvas;canvas.render(s);CHECK(canvas.pixels[120*240+120]!=0x051f); // no position marker for cached coordinates
  s.gpsFix=true;s.gpsReliable=true;canvas.render(s);CHECK(canvas.pixels[120*240+120]==0x051f);
  s.gpsReliable=false;canvas.render(s);CHECK(canvas.pixels[120*240+120]!=0x051f);s.gpsReliable=true;
  s.mapAutomatic=false;s.latitude=15.87594;s.longitude=104.51444;
  canvas.render(s);CHECK(canvas.pixels[120*240+120]!=0x051f); // manual other-area preview has no invented wearer marker
  s.latitude=13.84705;s.longitude=100.571942;canvas.render(s);CHECK(canvas.pixels[120*240+120]==0x051f);
  s.mapAutomatic=true;
  s.latitude=NAN;canvas.render(s);CHECK(canvas.pixels[120*240+120]!=0x051f);
  s.latitude=90;s.longitude=180;s.gpsFix=true;canvas.render(s);CHECK(canvas.pixels[120*240+120]==0x051f);
  s.latitude=13.84705;s.longitude=100.571942;
  for(unsigned zoom=0;zoom<MapZoom::COUNT;++zoom) {
    s.mapZoom=zoom;canvas.render(s);
    CHECK(canvas.pixels[120*240+120]==0x051f);
  }
  s.mapZoom=MapZoom::DEFAULT_INDEX;
  if(argc>1) {
    FILE* f=fopen(argv[1],"rb");CHECK(f);fseek(f,0,SEEK_END);size_t size=ftell(f);rewind(f);
    CHECK(fread(&h,1,sizeof(h),f)==sizeof(h));CHECK(WatchMap::validHeader(h,size));
    CHECK(fread(d.features,sizeof(WatchMap::Feature),h.features,f)==h.features);
    CHECK(fread(d.points,sizeof(WatchMap::Point),h.points,f)==h.points);fclose(f);CHECK(WatchMap::valid(d,size));
    WatchMap::index(d);
    s.latitude=NAN;s.gpsFix=false;auto began=std::chrono::steady_clock::now();canvas.render(s);
    auto ms=std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-began).count();
    printf("REAL MAP %s features=%u points=%u render_ms=%lld\n",h.name,h.features,h.points,(long long)ms);
    const char* prefix=argc>2?argv[2]:"output/maps/ku_bangkhen";char imagePath[512];
    snprintf(imagePath,sizeof(imagePath),"%s_wait_gps.ppm",prefix);preview(imagePath,canvas);
    s.gpsFix=true;s.latitude=h.latitudeE7/1e7;s.longitude=h.longitudeE7/1e7;
    canvas.render(s);snprintf(imagePath,sizeof(imagePath),"%s_position_demo.ppm",prefix);preview(imagePath,canvas);
    // Synthetic location above is host preview only; never transmitted to the watch.
  }
  printf("PASS %u map checks\n",checks);
}
