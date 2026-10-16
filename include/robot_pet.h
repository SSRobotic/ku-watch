#pragma once
#include "activity_format.h"

namespace RobotPet {
enum class Pose : uint8_t { Idle,Walk,Wave,Happy,Think,Sleep,Scan,Dance,Jump,Stretch };
constexpr unsigned POSE_COUNT=10;
#pragma pack(push,1)
struct Saved {
  uint32_t magic=0x31544252,version=1,xp=0,activityId=0,activityMs=0,activityCm=0;
  uint64_t walkMs=0,walkCm=0,careUtc=0;
  uint32_t feedDay=0,visitDay=0;
  uint8_t food=3,mood=75,energy=80,visited=0;
  uint32_t crc=0;
};
#pragma pack(pop)
inline bool valid(const Saved& s) {
  return s.magic==0x31544252 && s.version==1 && s.xp<=1000000 && s.activityId<=999999 &&
    s.food<=99 && s.mood<=100 && s.energy<=100 && s.visited<=3 && s.feedDay<=47482 && s.visitDay<=47482 && s.activityMs<=86400000 &&
    s.activityCm<=120000000 && s.walkMs<=86400000000000ULL && s.walkCm<=120000000000000ULL &&
    (!s.careUtc || (s.careUtc>=1704067200ULL && s.careUtc<=4102444799ULL)) &&
    Activity::crc32(&s,offsetof(Saved,crc))==s.crc;
}
inline unsigned level(uint32_t xp) {
  static constexpr uint32_t thresholds[]={0,10,30,75,150,300,600,1000,2000};
  unsigned result=1;for(unsigned i=1;i<9;++i) if(xp>=thresholds[i]) result=i+1;return result;
}
inline unsigned stage(uint32_t xp) {unsigned n=level(xp);return n<3?0:n<6?1:2;}
inline uint32_t nextXp(uint32_t xp) {
  static constexpr uint32_t thresholds[]={0,10,30,75,150,300,600,1000,2000};
  unsigned n=level(xp);return n<9?thresholds[n]:2000;
}
class Model {
public:
  Saved saved;
  uint32_t revision=0;
  bool restore(const Saved& value) {if(!valid(value)) return false;saved=value;return true;}
  Saved snapshot() const {auto out=saved;out.crc=Activity::crc32(&out,offsetof(Saved,crc));return out;}
  void play() {if(saved.mood<98) saved.mood+=2;else saved.mood=100;if(saved.energy>10) --saved.energy;++revision;}
  bool feed(uint64_t utc=0) {
    if(!saved.food) return false;
    --saved.food;saved.mood=saved.mood>90?100:saved.mood+10;saved.energy=saved.energy>85?100:saved.energy+15;
    if(utc>=1704067200ULL && utc<=4102444799ULL) {
      uint32_t day=uint32_t((utc+25200)/86400);
      if(day>saved.feedDay) {saved.feedDay=day;if(saved.xp<1000000) ++saved.xp;}
    }
    ++revision;return true;
  }
  bool visit(unsigned area,uint64_t utc) {
    if(area>1 || utc<1704067200ULL || utc>4102444799ULL) return false;
    uint32_t day=uint32_t((utc+25200)/86400);
    if(day<saved.visitDay) return false;
    if(day>saved.visitDay) {saved.visitDay=day;saved.visited=0;}
    uint8_t bit=1u<<area;if(saved.visited&bit) return false;
    saved.visited|=bit;saved.xp=saved.xp>=999998?1000000:saved.xp+2;++revision;return true;
  }
  bool activity(uint32_t id,uint32_t elapsed,double meters) {
    if(!id || id>999999 || elapsed>86400000 || !isfinite(meters) || meters<0 || meters>1200000 || id<saved.activityId) return false;
    uint32_t cm=uint32_t(lround(meters*100));
    if(id!=saved.activityId) {saved.activityId=id;saved.activityMs=0;saved.activityCm=0;++revision;}
    if(elapsed<saved.activityMs || cm<saved.activityCm) return false;
    uint64_t before=saved.walkMs/60000+saved.walkCm/5000,foodBefore=saved.walkMs/300000;
    uint32_t deltaMs=elapsed-saved.activityMs,deltaCm=cm-saved.activityCm;
    if(!deltaMs && !deltaCm) return false;
    saved.walkMs+=deltaMs;saved.walkCm+=deltaCm;saved.activityMs=elapsed;saved.activityCm=cm;
    uint64_t earned=saved.walkMs/60000+saved.walkCm/5000-before;
    if(earned) {
      saved.xp=uint32_t(fmin(1000000.0,double(saved.xp)+earned));
      saved.mood=saved.mood>=99?100:saved.mood+1;
    }
    uint64_t food=saved.walkMs/300000-foodBefore;
    if(food) {saved.food=uint8_t(fmin(99.0,double(saved.food)+food));if(saved.energy>10) --saved.energy;}
    ++revision;return earned>0;
  }
  void care(uint64_t utc) {
    if(utc<1704067200ULL || utc>4102444799ULL) return;
    if(!saved.careUtc) {saved.careUtc=utc;++revision;return;}
    if(utc<saved.careUtc) {saved.careUtc=utc;++revision;return;}
    uint64_t hours=(utc-saved.careUtc)/3600;if(!hours) return;
    unsigned decay=unsigned(hours>24?24:hours);
    saved.mood=saved.mood>20+decay?saved.mood-decay:20;
    saved.energy=uint8_t(fmin(100.0,double(saved.energy)+decay*3));
    saved.careUtc=hours>24?utc:saved.careUtc+hours*3600;++revision;
  }
};
}
