#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include "map_geometry.h"
#include "map_zoom.h"
#include "robot_pet.h"

// Portable renderer: the exact same pixels are rendered on-device and in preview.
namespace Face {
constexpr int SIZE = 240;
constexpr uint16_t BLACK = 0, WHITE = 0xffff, TEAL = 0x032c;
constexpr uint16_t LIME = 0xbda0, CYAN = 0x07ff, GRAY = 0x94b2, DIM = 0x2124;
struct State {
  int hour = 0, minute = 0, second = 0, day = 1, month = 1, weekday = 0;
  float temp = NAN, humidity = NAN, pressure = NAN;
  float bpm = NAN;
  float spo2=NAN,gas=NAN,iaq=NAN,batteryVolts=NAN,batteryPercent=NAN;
  uint8_t spo2Status=0,iaqAccuracy=0;
  bool iaqValid=false,iaqStable=false,iaqRunIn=false,batteryDetected=false,batteryValid=false;
  uint32_t ir = 0, red = 0;
  bool finger = false;
  bool gpsData = false, gpsFix = false, gpsReliable=false;
  bool mapAutomatic=true;
  double latitude = NAN, longitude = NAN;
  float altitude = NAN, speed = NAN;
  uint32_t satellites = 0;
  uint32_t gpsChars = 0;
  bool gpsViewValid = false, gpsSignalValid = false;
  uint32_t gpsInView = 0, gpsSignal = 0;
  bool recording=false,storageReady=false,timeFromGps=false,timeFromNet=false;
  uint32_t recordElapsed=0,recordId=0,recordFree=0;
  float recordDistance=0;
  const char* recordMessage="READY";
  int16_t accX = 0, accY = 0, accZ = 0;
  int16_t magX = 0, magY = 0, magZ = 0;
  bool bme = false, timeSet = false, sound = false;
  const char* clockSource="WAIT GPS/WIFI";
  bool max30102 = false;
  bool gy51 = false;
  bool wifi = false, influx = false, mqtt = false;
  uint32_t networkPending=0,networkDropped=0,networkErrors=0;
  bool networkStorage=false;
  bool addrIna = false, addr57 = false, addr18 = false, addr19 = false;
  bool addr1d = false, addr1e = false;
  unsigned page = 0;
  const WatchMap::Data* map=nullptr;
  const WatchMap::Trail* trail=nullptr;
  unsigned mapZoom=1;
  bool (*mapService)()=nullptr;
  uint32_t robotXp=0,robotPhase=0;
  uint8_t robotFood=3,robotMood=75,robotEnergy=80;
  RobotPet::Pose robotPose=RobotPet::Pose::Idle;
  const char* robotMessage="HELLO I AM KU-BOT";
  bool robotBubble=false;
  uint8_t alertMask=0,alertTemperature=0,alertAir=0;
  bool batteryLow=false;
  const char* firmware="";
  bool setupActive=false,linkOnline=false;
  const char* setupSsid="",*setupPassword="";
  float heading=NAN,batteryCurrent=NAN,batteryPower=NAN;
};
inline const char* warning(const State& s) {
  if(s.batteryLow)return s.alertMask==3?"HIGH TEMP IAQ / BAT LOW":s.alertMask==1?"HIGH TEMP / BATTERY LOW":s.alertMask==2?"HIGH IAQ / BATTERY LOW":"LOW BATTERY 20% EST";
  return s.alertMask==3?"HIGH TEMP AND IAQ":s.alertMask==1?"HIGH TEMPERATURE":"HIGH IAQ";
}

// Compact 5 x 7 alphabet, rows encoded as five bits. Original UI glyph data.
inline const uint8_t *glyph(char ch) {
  static const char chars[] = "\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x41\x42\x43\x44\x45\x46\x47\x48\x49\x4a\x4b\x4c\x4d\x4e\x4f\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5a\x2d\x2e\x3a\x2f\x25\x2b\x3f\x28\x29\x20";
  static const uint8_t rows[][7] = {
    {14,17,19,21,25,17,14},{4,12,4,4,4,4,14},{14,17,1,2,4,8,31},
    {30,1,1,14,1,1,30},{2,6,10,18,31,2,2},{31,16,16,30,1,1,30},
    {14,16,16,30,17,17,14},{31,1,2,4,8,8,8},{14,17,17,14,17,17,14},
    {14,17,17,15,1,1,14},{14,17,17,31,17,17,17},{30,17,17,30,17,17,30},
    {14,17,16,16,16,17,14},{30,17,17,17,17,17,30},{31,16,16,30,16,16,31},
    {31,16,16,30,16,16,16},{14,17,16,23,17,17,15},{17,17,17,31,17,17,17},
    {14,4,4,4,4,4,14},{7,2,2,2,2,18,12},{17,18,20,24,20,18,17},
    {16,16,16,16,16,16,31},{17,27,21,21,17,17,17},{17,25,25,21,19,19,17},
    {14,17,17,17,17,17,14},{30,17,17,30,16,16,16},{14,17,17,17,21,18,13},
    {30,17,17,30,20,18,17},{15,16,16,14,1,1,30},{31,4,4,4,4,4,4},
    {17,17,17,17,17,17,14},{17,17,17,17,17,10,4},{17,17,17,21,21,21,10},
    {17,17,10,4,10,17,17},{17,17,10,4,4,4,4},{31,1,2,4,8,16,31},
    {0,0,0,31,0,0,0},{0,0,0,0,0,6,6},{0,6,6,0,6,6,0},
    {1,2,2,4,8,8,16},{17,2,4,4,8,16,17},{0,4,4,31,4,4,0},
    {14,17,1,2,4,0,4},{2,4,8,8,8,4,2},{8,4,2,2,2,4,8},{0,0,0,0,0,0,0}
  };
  const char *p = strchr(chars, ch);
  return rows[p ? p - chars : sizeof(chars) - 2];
}
class Canvas {
public:
  uint16_t pixels[SIZE * SIZE];
  void clear() { memset(pixels, 0, sizeof(pixels)); }
  void dot(int x, int y, uint16_t c) {
    if (x >= 0 && y >= 0 && x < SIZE && y < SIZE) pixels[y * SIZE + x] = c;
  }
  void rect(int x, int y, int w, int h, uint16_t c) {
    for (int j = 0; j < h; ++j) for (int i = 0; i < w; ++i) dot(x+i,y+j,c);
  }
  void line(int x0, int y0, int x1, int y1, uint16_t c) {
    int dx = abs(x1-x0), sx = x0<x1 ? 1 : -1;
    int dy = -abs(y1-y0), sy = y0<y1 ? 1 : -1, e = dx+dy;
    for (;;) {
      dot(x0,y0,c); if (x0 == x1 && y0 == y1) break;
      int e2 = e*2;
      if (e2 >= dy) { e += dy; x0 += sx; }
      if (e2 <= dx) { e += dx; y0 += sy; }
    }
  }
  int textWidth(const char *s, int scale) { return int(strlen(s)) * 6 * scale - scale; }
  void text(int x, int y, const char *s, int scale, uint16_t c) {
    for (; *s; ++s, x += 6*scale) {
      const uint8_t *g = glyph(*s);
      for (int j=0;j<7;++j) for (int i=0;i<5;++i)
        if (g[j] & (1 << (4-i))) rect(x+i*scale,y+j*scale,scale,scale,c);
    }
  }
  void center(int y, const char *s, int scale, uint16_t c) {
    text((SIZE-textWidth(s,scale))/2,y,s,scale,c);
  }
  void hseg(int x, int y, uint16_t c) {
    for (int j=0;j<5;++j) { int inset = abs(j-2); rect(x+inset,y+j,22-2*inset,1,c); }
  }
  void vseg(int x, int y, uint16_t c) {
    for (int i=0;i<5;++i) { int inset = abs(i-2); rect(x+i,y+inset,1,18-2*inset,c); }
  }
  void digit(int x, int y, int n) {
    static const uint8_t mask[] = {0x3f,0x06,0x5b,0x4f,0x66,0x6d,0x7d,0x07,0x7f,0x6f};
    uint8_t m = mask[n%10];
    if(m&1) hseg(x+3,y,WHITE);
    if(m&2) vseg(x+23,y+4,WHITE);
    if(m&4) vseg(x+23,y+25,WHITE);
    if(m&8) hseg(x+3,y+43,WHITE);
    if(m&16) vseg(x,y+25,WHITE);
    if(m&32) vseg(x,y+4,WHITE);
    if(m&64) hseg(x+3,y+21,WHITE);
  }
  void rim(int second) {
    for(int i=0;i<60;++i) {
      float a = (i*6-90)*0.01745329252f;
      int inner = i%5 == 0 ? 108 : 112;
      uint16_t c = i<=second ? LIME : DIM;
      for(int r=inner;r<=116;++r) {
        int x = int(lroundf(119.5f+cosf(a)*r)), y = int(lroundf(119.5f+sinf(a)*r));
        dot(x,y,c); if(i%5 == 0) dot(x+1,y,c);
      }
    }
  }
  void logo() {
    // Pixel-built KU mark, redrawn from the supplied design rather than a screenshot.
    rect(92,34,7,37,TEAL);
    for(int y=0;y<19;++y) rect(99+16-y,34+y,8,1,TEAL);
    for(int y=0;y<19;++y) rect(99+y,52+y,8,1,TEAL);
    rect(126,34,7,30,TEAL); rect(147,34,7,30,TEAL);
    rect(131,63,18,8,TEAL); rect(128,60,7,7,TEAL); rect(145,60,7,7,TEAL);
    rect(92,76,62,6,LIME);
  }
  void value(char *b, size_t cap, float v, int decimals, const char *suffix) {
    if (isfinite(v)) snprintf(b,cap,"%.*f%s",decimals,double(v),suffix);
    else snprintf(b,cap,"--%s",suffix);
  }
  void mapLine(double x0,double y0,double x1,double y1,uint16_t color,int width=1) {
    if(!WatchMap::clip(x0,y0,x1,y1)) return;
    int a=int(lround(x0)),b=int(lround(y0)),c=int(lround(x1)),d=int(lround(y1));
    line(a,b,c,d,color);
    for(int i=1;i<=width/2;++i) {
      line(a+i,b,c+i,d,color);line(a-i,b,c-i,d,color);
      line(a,b+i,c,d+i,color);line(a,b-i,c,d-i,color);
    }
  }
  void mapPage(const State& s) {
    constexpr uint16_t LAND=0xf7bc,PARK=0xd715,LAKE=0x9e7c,STRUCTURE=0xdedb;
    constexpr uint16_t ROAD_EDGE=0xc5f7,MAIN_ROAD=0xff2b,ROUTE=0x901b,POSITION=0x051f;
    double scale=MapZoom::metersPerPixel(s.mapZoom);
    bool goodFix=s.gpsFix && s.gpsReliable && isfinite(s.latitude) && isfinite(s.longitude) && fabs(s.latitude)<=90 && fabs(s.longitude)<=180;
    bool inside=goodFix && WatchMap::covers(s.map,s.latitude,s.longitude);
    // Manual area selection can preview a different place from the live GPS.
    bool fix=goodFix && (s.mapAutomatic || inside);
    double lat=fix?s.latitude:s.map?s.map->header.latitudeE7/1e7:0;
    double lon=fix?s.longitude:s.map?s.map->header.longitudeE7/1e7:0;
    int32_t centerLat=int32_t(lround(lat*1e7)),centerLon=int32_t(lround(lon*1e7));
    float latitudeScale=float(.0111319490793/scale),longitudeScale=float(latitudeScale*cos(lat*.017453292519943295));
    double longitudeSpan=longitudeScale>0?122.0/longitudeScale:double(INT32_MAX);
    int32_t latSpan=int32_t(122/latitudeScale),lonSpan=longitudeSpan>=INT32_MAX?INT32_MAX:int32_t(longitudeSpan);
    auto project=[&](const WatchMap::Point& p,double& x,double& y) {
      int64_t dx=int64_t(p.lon)-centerLon;
      if(dx>1800000000LL) dx-=3600000000LL;if(dx< -1800000000LL) dx+=3600000000LL;
      x=119.5f+float(dx)*longitudeScale;
      y=119.5f-float(int64_t(p.lat)-centerLat)*latitudeScale;
    };
    for(auto& pixel:pixels) pixel=LAND;
    if(s.map) {
      // Areas first, then roads, so the streets stay visible over land and buildings.
      for(unsigned pass=0;pass<2;++pass) for(unsigned i=0;i<s.map->header.features;++i) {
        if(i%32==0 && s.mapService && !s.mapService()) return;
        const auto& f=s.map->features[i];bool road=f.kind==WatchMap::ROAD || f.kind==WatchMap::WATERWAY;
        if(road!=bool(pass)) continue;
        const auto& bounds=s.map->bounds[i];
        if(bounds.maxLat<int64_t(centerLat)-latSpan || bounds.minLat>int64_t(centerLat)+latSpan) continue;
        if(fabs(lon)<179 && (bounds.maxLon<int64_t(centerLon)-lonSpan || bounds.minLon>int64_t(centerLon)+lonSpan)) continue;
        uint16_t color=f.kind==WatchMap::GREEN?PARK:f.kind==WatchMap::WATER?LAKE:STRUCTURE;
        if(!road && f.count<=128) {
          float x[128],y[128],minY=240,maxY=-1;
          for(unsigned j=0;j<f.count;++j) {double a,b;project(s.map->points[f.offset+j],a,b);x[j]=a;y[j]=b;minY=fminf(minY,y[j]);maxY=fmaxf(maxY,y[j]);}
          int first=int(fmaxf(0,fminf(240,ceilf(minY)))),last=int(fmaxf(-1,fminf(239,floorf(maxY))));
          for(int row=first;row<=last;++row) {
            float cross[128];unsigned count=0;
            for(unsigned j=0,k=f.count-1;j<f.count;k=j++) {
              if((y[j]>row)!=(y[k]>row)) cross[count++]=x[j]+(row-y[j])*(x[k]-x[j])/(y[k]-y[j]);
            }
            for(unsigned j=1;j<count;++j) {float v=cross[j];unsigned k=j;while(k && cross[k-1]>v) {cross[k]=cross[k-1];--k;}cross[k]=v;}
            for(unsigned j=0;j+1<count;j+=2) {
              int a=int(fmaxf(0,fminf(240,ceilf(cross[j])))),b=int(fmaxf(-1,fminf(239,floorf(cross[j+1]))));
              for(int column=a;column<=b;++column) pixels[row*SIZE+column]=color;
            }
          }
        }
        for(unsigned j=1;j<f.count;++j) {
          double a,b,c,d;project(s.map->points[f.offset+j-1],a,b);project(s.map->points[f.offset+j],c,d);
          if(f.kind==WatchMap::ROAD) {
            int width=f.style==0?5:f.style==1?3:1;
            mapLine(a,b,c,d,ROAD_EDGE,width+2);
            mapLine(a,b,c,d,f.style==0?MAIN_ROAD:WHITE,width);
          } else mapLine(a,b,c,d,f.kind==WatchMap::WATERWAY?LAKE:color,1);
        }
      }
    }
    if(s.trail) for(unsigned i=1;i<s.trail->count();++i) {
      if(s.trail->at(i).gap) continue;
      double a,b,c,d;project(s.trail->at(i-1).point,a,b);project(s.trail->at(i).point,c,d);
      mapLine(a,b,c,d,WHITE,5);mapLine(a,b,c,d,ROUTE,3);
    }
    if(fix) {
      for(int y=-8;y<=8;++y) for(int x=-8;x<=8;++x) if(x*x+y*y<=64) dot(120+x,120+y,WHITE);
      for(int y=-5;y<=5;++y) for(int x=-5;x<=5;++x) if(x*x+y*y<=25) dot(120+x,120+y,POSITION);
    }
    rect(39,35,162,22,DIM);center(38,s.mapAutomatic?"MAP AUTO":"MAP MANUAL",1,WHITE);
    center(49,s.map?s.map->header.name:"NO MAP LOADED",1,CYAN);
    rect(178,59,13,20,DIM);text(182,61,"N",1,WHITE);
    line(184,72,184,77,WHITE);line(184,72,181,75,WHITE);line(184,72,187,75,WHITE);
    rect(68,157,74,20,LAND);line(73,171,123,171,BLACK);line(73,167,73,173,BLACK);line(123,167,123,173,BLACK);
    char b[48];snprintf(b,sizeof(b),"%.0f M",50*scale);text(75,160,b,1,BLACK);
    rect(33,183,174,38,DIM);
    center(186,goodFix?(inside?(s.recording?"GPS FIX - RECORDING":"GPS FIX"):s.mapAutomatic?"GPS FIX - OUTSIDE MAP":"GPS FIX - OTHER AREA"):(s.gpsFix?"GPS WEAK - WAIT FIX":s.gpsData?"WAIT GPS FIX":"NO GPS DATA"),1,WHITE);
    center(197,"2T AREA HOLD ZOOM TAP WALK",1,CYAN);
    // Visible attribution for the OpenStreetMap database (ODbL).
    center(208,"(C) OPENSTREETMAP",1,GRAY);
    for(int y=0;y<SIZE;++y) for(int x=0;x<SIZE;++x)
      if((2*x-239)*(2*x-239)+(2*y-239)*(2*y-239)>236*236) dot(x,y,BLACK);
  }
  void robotSprite(int cx,int top,int scale,unsigned stage,RobotPet::Pose pose,uint32_t phase) {
    bool alternate=phase%2;unsigned frame=phase%4;
    int bob=(pose==RobotPet::Pose::Walk || pose==RobotPet::Pose::Happy || pose==RobotPet::Pose::Dance)?int(alternate):0;
    if(pose==RobotPet::Pose::Jump) {static const int heights[]={0,-2,-3,-1};bob=heights[frame];}
    if(pose==RobotPet::Pose::Dance) cx+=(alternate?2:-2)*scale;
    top+=bob*scale;
    uint16_t trim=stage==2?LIME:stage==1?CYAN:0x5dff;
    auto box=[&](int x,int y,int w,int h,uint16_t c){rect(cx+x*scale,top+y*scale,w*scale,h*scale,c);};
    if(scale>1) {box(-9,21,18,1,DIM);box(-7,22,14,1,DIM);}
    box(0,0,1,2,GRAY);box(-1,0,3,1,trim);
    box(-5,2,10,7,WHITE);box(-6,3,1,4,GRAY);box(5,3,1,4,GRAY);
    box(-4,3,8,4,DIM);
    if(pose==RobotPet::Pose::Sleep || phase%8==6) {
      box(-3,5,2,1,trim);box(1,5,2,1,trim);
    } else {
      int look=pose==RobotPet::Pose::Think?int(alternate):0;
      box(-3+look,4,2,2,trim);box(1+look,4,2,2,trim);
    }
    if(pose==RobotPet::Pose::Happy) {box(-2,7,4,1,trim);box(-1,8,2,1,trim);}
    else box(-1,7,2,1,trim);
    box(-1,9,2,1,GRAY);box(-4,10,8,6,WHITE);box(-3,11,6,3,0x032c);
    box(-1,11,2,2,trim);box(-3,15,6,1,GRAY);
    int left=pose==RobotPet::Pose::Walk?(alternate?2:-1):0;
    int right=pose==RobotPet::Pose::Wave || pose==RobotPet::Pose::Happy?int(frame==0?-2:frame==1?-5:frame==2?-3:-6):pose==RobotPet::Pose::Walk?(alternate?-1:2):0;
    if(pose==RobotPet::Pose::Dance) {left=alternate?-4:1;right=alternate?1:-4;}
    if(pose==RobotPet::Pose::Stretch || pose==RobotPet::Pose::Jump) {left=-5-int(alternate);right=-5-int(alternate);}
    box(-6,10+left,2,5,GRAY);box(-7,14+left,3,2,trim);
    box(4,10+right,2,5,GRAY);box(4,14+right,3,2,trim);
    if(stage>0) {box(-6,10+left,2,2,trim);box(4,10+right,2,2,trim);box(-3,13,6,1,trim);}
    if(stage==2) {box(-7,9+left,3,2,LIME);box(4,9+right,3,2,LIME);box(-5,2,2,1,LIME);box(3,2,2,1,LIME);}
    int stride=pose==RobotPet::Pose::Walk || pose==RobotPet::Pose::Dance?int(alternate):0;
    box(-3,16,2,3+stride,GRAY);box(1,16,2,4-stride,GRAY);
    box(-4,19+stride,3,2,trim);box(1,20-stride,3,2,trim);
    if(pose==RobotPet::Pose::Sleep && scale>1) text(cx+8*scale,top+3*scale,"Z",scale,GRAY);
    if(pose==RobotPet::Pose::Scan && scale>1) {
      int reach=8+int(phase%3);line(cx+reach*scale,top+5*scale,cx+reach*scale,top+9*scale,CYAN);
    }
    if(pose==RobotPet::Pose::Jump && bob<0) {box(-2,22,1,1,trim);box(1,23,1,1,LIME);}
    if(pose==RobotPet::Pose::Dance && scale>1) {text(cx+9*scale,top+3*scale,"+",scale,trim);}
  }
  void robotPage(const State& s) {
    char b[48];unsigned n=RobotPet::level(s.robotXp),stage=RobotPet::stage(s.robotXp);
    center(36,"KU-BOT",2,CYAN);
    snprintf(b,sizeof(b),"LV %u  %s",n,stage==0?"BABY":stage==1?"BUDDY":"HERO");center(58,b,1,WHITE);
    robotSprite(120,stage==0?88:72,stage==0?2:3,stage,s.robotPose,s.robotPhase);
    center(148,s.robotMessage,1,CYAN);
    snprintf(b,sizeof(b),"MOOD %u  ENERGY %u",s.robotMood,s.robotEnergy);center(166,b,1,WHITE);
    snprintf(b,sizeof(b),"XP %lu / %lu",(unsigned long)s.robotXp,(unsigned long)RobotPet::nextXp(s.robotXp));center(180,b,1,LIME);
    uint32_t next=RobotPet::nextXp(s.robotXp);unsigned bar=next?unsigned(fmin(126.0,double(s.robotXp)*126/next)):126;
    rect(57,190,126,3,DIM);rect(57,190,bar,3,CYAN);
    snprintf(b,sizeof(b),"FOOD %u",s.robotFood);center(197,b,1,WHITE);
    center(209,"2 TAP PLAY  HOLD FEED",1,CYAN);
  }
  void robotOverlay(const State& s) {
    if(s.page!=10) {
      rect(107,1,26,24,BLACK);
      robotSprite(120,1,1,RobotPet::stage(s.robotXp),s.robotPose,s.robotPhase);
    }
    if(s.robotBubble && s.page!=10) {
      // Reserved top band: never paint over dates, measurements or map scale/footer.
      rect(40,25,160,9,BLACK);center(26,s.robotMessage,1,CYAN);
    }
  }
  void render(const State &s) {
    clear(); rim(s.second); char b[48];
    if(s.page == 0) {
      logo();
      digit(43,88,s.hour/10); digit(78,88,s.hour%10);
      if(s.second%2 == 0) { rect(118,99,5,5,WHITE); rect(118,121,5,5,WHITE); }
      digit(136,88,s.minute/10); digit(171,88,s.minute%10);
      line(47,148,193,148,DIM);
      value(b,sizeof(b),s.bme?s.temp:NAN,1,"C"); text(49,160,b,2,LIME);
      value(b,sizeof(b),s.bme?s.humidity:NAN,0,"%"); text(150,160,b,2,CYAN);
      static const char *days[] = {"SUN","MON","TUE","WED","THU","FRI","SAT"};
      static const char *months[] = {"JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"};
      snprintf(b,sizeof(b),"%s %02d %s",days[s.weekday%7],s.day,months[(s.month+11)%12]);
      center(184,b,2,GRAY);
      center(199,s.clockSource,1,s.timeSet?DIM:LIME);
      if(s.batteryValid) snprintf(b,sizeof(b),"BAT %.0f%% EST",double(s.batteryPercent));
      else snprintf(b,sizeof(b),"BAT --%%");
      center(209,b,1,s.batteryValid?CYAN:GRAY);
    } else if(s.page == 1) {
      center(38,"ENVIRONMENT",2,TEAL); center(63,s.bme?"BME680 LIVE":"WAITING FOR BME680",1,GRAY);
      value(b,sizeof(b),s.bme?s.temp:NAN,1," C"); center(87,b,3,LIME);
      value(b,sizeof(b),s.bme?s.humidity:NAN,0," % RH"); center(121,b,2,CYAN);
      value(b,sizeof(b),s.bme?s.pressure:NAN,1," HPA"); center(151,b,2,WHITE);
      value(b,sizeof(b),s.bpm,1," BPM"); center(180,b,1,s.max30102?LIME:GRAY);
      center(203,"PRESS: NEXT",1,GRAY);
    } else if(s.page == 2) {
      center(38,"DEVICES",2,TEAL); center(61,"I2C ADDRESS CHECK",1,GRAY);
      text(48,85,"BME680",1,WHITE); text(142,85,s.bme?"DATA":"--",1,s.bme?LIME:GRAY);
      text(48,104,"MAX 0X57",1,WHITE); text(142,104,s.max30102?"DATA":(s.addr57?"ACK":"--"),1,s.max30102?LIME:(s.addr57?CYAN:GRAY));
      snprintf(b,sizeof(b),"INA 0X%02X",unsigned(INA226_I2C_ADDRESS));
      text(48,123,b,1,WHITE); text(142,123,s.batteryValid?"DATA":s.batteryDetected?"ID":s.addrIna?"ACK":"--",1,s.batteryValid?LIME:GRAY);
      char acc[36], mag[36];
      snprintf(acc,sizeof(acc),"ACC %d %d %d",s.accX,s.accY,s.accZ);
      snprintf(mag,sizeof(mag),"MAG %d %d %d",s.magX,s.magY,s.magZ);
      center(142,s.gy51?acc:"ACC -- -- --",1,s.gy51?LIME:GRAY);
      center(158,s.gy51?mag:"MAG -- -- --",1,s.gy51?CYAN:GRAY);
      center(181,s.sound?"SOUND: DRIVER ON":"SOUND: DRIVER NEEDED",1,GRAY);
      center(198,"HOLD: HOME",1,GRAY);
    } else if(s.page == 3) {
      center(38,"HEART RATE",2,TEAL);
      center(67,s.max30102?"MAX30102 LIVE":"WAITING FOR MAX30102",1,GRAY);
      if(s.max30102 && !isfinite(s.bpm)) {
        center(86,"IR SIGNAL",1,CYAN);
        snprintf(b,sizeof(b),"%lu",(unsigned long)s.ir); center(105,b,4,LIME);
      } else {
        value(b,sizeof(b),s.bpm,1," BPM"); center(92,b,4,s.max30102?LIME:GRAY);
      }
      if(isfinite(s.spo2)) snprintf(b,sizeof(b),"SPO2 %.0f%%",double(s.spo2));
      else snprintf(b,sizeof(b),"SPO2 --%%");
      center(145,b,2,CYAN);
      const char* oxStatus[]={"PLACE FINGER","COLLECTING - KEEP STILL","WEAK OR MOVING SIGNAL","ESTIMATE - NOT MEDICAL","OUTSIDE ESTIMATE RANGE"};
      center(170,oxStatus[s.spo2Status<=4?s.spo2Status:0],1,WHITE);
      snprintf(b,sizeof(b),"IR %lu RED %lu",(unsigned long)s.ir,(unsigned long)s.red); center(188,b,1,GRAY);
      center(205,"PRESS: NEXT",1,GRAY);
    } else if(s.page == 4) {
      center(38,"MOTION",2,TEAL);
      snprintf(b,sizeof(b),"X %d",s.accX); center(76,b,2,LIME);
      snprintf(b,sizeof(b),"Y %d",s.accY); center(111,b,2,LIME);
      snprintf(b,sizeof(b),"Z %d",s.accZ); center(146,b,2,LIME);
      if(isfinite(s.heading)) {snprintf(b,sizeof(b),"MAG N %.0f DEG",double(s.heading));center(184,b,1,CYAN);}
      else center(184,"COMPASS NEEDS CALIBRATION",1,GRAY);
      center(207,"PRESS: NEXT",1,GRAY);
    } else if(s.page == 5) {
      center(38,"NETWORK",2,TEAL);
      if(s.setupActive) {
        center(72,s.setupSsid,1,CYAN);center(95,"WIFI PASSWORD",1,GRAY);
        center(115,s.setupPassword,2,LIME);center(148,"192.168.4.1",2,WHITE);
        center(174,"LOGIN: ADMIN / SAME PASSWORD",1,GRAY);center(199,"HOLD: CLOSE SETUP",1,CYAN);
      } else {
      center(75,s.wifi?"WIFI: CONNECTED":"WIFI: OFFLINE",1,s.wifi?LIME:GRAY);
      center(105,s.mqtt?"MQTT: CONNECTED":"MQTT: OFFLINE",1,s.mqtt?LIME:GRAY);
      snprintf(b,sizeof(b),"PENDING %lu / 768",(unsigned long)s.networkPending);center(136,b,1,CYAN);
      center(158,s.networkStorage?"AUTO SYNC - QOS 1":"QUEUE STORAGE ERROR",1,s.networkStorage?LIME:uint16_t(0xf800));
      if(s.networkDropped) {snprintf(b,sizeof(b),"NOT STORED %lu",(unsigned long)s.networkDropped);center(180,b,1,uint16_t(0xf800));}
      else center(180,s.networkPending?"KEEPING CAPTURE TIME":"ALL SENT TO BROKER",1,GRAY);
      center(198,s.linkOnline?"BIG DISPLAY ONLINE":"HOLD: PHONE SETUP",1,CYAN);
      snprintf(b,sizeof(b),"FW %s PRESS: NEXT",s.firmware[0]?s.firmware:"--");center(211,b,1,GRAY);
      }
    } else if(s.page == 6) {
      mapPage(s);
    } else if(s.page==7) {
      center(38,"WALK",2,TEAL);
      center(62,s.recording?(s.gpsReliable?"RECORDING - GPS FIX":s.gpsFix?"RECORDING - WEAK GPS":"RECORDING - WAIT GPS"):s.recordMessage,1,s.recording?LIME:GRAY);
      unsigned seconds=s.recordElapsed/1000;
      snprintf(b,sizeof(b),"%02u:%02u:%02u",seconds/3600,(seconds/60)%60,seconds%60); center(86,b,3,WHITE);
      snprintf(b,sizeof(b),"%.2f KM",double(s.recordDistance/1000)); center(122,b,2,LIME);
      value(b,sizeof(b),s.bpm,0," BPM"); center(153,b,2,CYAN);
      snprintf(b,sizeof(b),"FILE %lu FREE %lu KB",(unsigned long)s.recordId,(unsigned long)(s.recordFree/1024)); center(178,b,1,GRAY);
      center(198,s.recording?"HOLD: STOP AND SAVE":(s.timeSet?"HOLD: START WALK":"WAIT GPS OR SET TIME"),1,WHITE);
    } else if(s.page==8) {
      center(38,"AIR QUALITY",2,TEAL);
      center(64,s.bme?"BME68X AND BOSCH BSEC":"WAITING FOR BME68X",1,GRAY);
      value(b,sizeof(b),s.iaqValid?s.iaq:NAN,0," IAQ");center(88,b,3,LIME);
      snprintf(b,sizeof(b),"ACCURACY %u/3",s.iaqAccuracy);center(125,b,1,CYAN);
      center(146,s.iaqValid?"IAQ ESTIMATE READY":!s.iaqStable?"HEATER WARMING UP":!s.iaqRunIn?"SENSOR RUN-IN":"LEARNING AIR BASELINE",1,WHITE);
      value(b,sizeof(b),s.gas/1000,1," KOHM");center(172,b,2,CYAN);
      center(204,"IAQ IS NOT PM2.5",1,GRAY);
    } else if(s.page==9) {
      center(38,"BATTERY",2,TEAL);
      center(64,s.batteryDetected?"INA226 DETECTED":"WAITING FOR INA226",1,GRAY);
      value(b,sizeof(b),s.batteryValid?s.batteryPercent:NAN,0,"%");center(92,b,4,LIME);
      value(b,sizeof(b),s.batteryValid?s.batteryVolts:NAN,3," V");center(136,b,2,CYAN);
      center(169,s.batteryValid?"VOLTAGE ESTIMATE":"CHECK BATTERY SENSE",1,WHITE);
      if(isfinite(s.batteryCurrent)) {snprintf(b,sizeof(b),"%.1f MA %.1f MW",double(s.batteryCurrent),double(s.batteryPower));center(190,b,1,CYAN);}
      else center(190,"CURRENT NEEDS SHUNT SETUP",1,GRAY);
      center(206,"NOT A CHARGE CONTROLLER",1,GRAY);
    } else if(s.page==10) {
      robotPage(s);
    }
    robotOverlay(s);
    if(s.alertMask || s.batteryLow) {
      rect(40,25,160,9,BLACK);
      center(26,warning(s),1,0xf800);
    }
    if(s.recording && s.page!=7) { rect(145,17,24,9,BLACK); text(148,18,"REC",1,LIME); }
    for(int i=0;i<Pin::PAGE_COUNT;++i) rect((SIZE-(Pin::PAGE_COUNT*8-4))/2+i*8,220,4,3,s.page==unsigned(i)?LIME:DIM);
  }
};
}
