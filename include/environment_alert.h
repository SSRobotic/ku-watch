#pragma once
#include <math.h>
#include <stdint.h>
#include "activity_format.h"

namespace EnvAlert {
enum : uint8_t { WAITING=0, NORMAL=1, TRIGGERED=2 };
enum : uint8_t { TEMPERATURE=1, AIR=2 };
struct Settings {
  float temperature=35,iaq=150;
  static bool valid(float t,float q) {return isfinite(t)&&isfinite(q)&&t>=-20&&t<=80&&q>=10&&q<=500;}
};
#pragma pack(push,1)
struct Saved {uint32_t magic=0x31414b55;float temperature=35,iaq=150;uint32_t crc=0;};
#pragma pack(pop)
inline Saved save(const Settings& c) {Saved s;s.temperature=c.temperature;s.iaq=c.iaq;s.crc=Activity::crc32(&s,offsetof(Saved,crc));return s;}
inline bool restore(const Saved& s,Settings& c) {
  if(s.magic!=0x31414b55 || !Settings::valid(s.temperature,s.iaq) || s.crc!=Activity::crc32(&s,offsetof(Saved,crc)))return false;
  c.temperature=s.temperature;c.iaq=s.iaq;return true;
}
class Channel {
public:
  uint8_t state=WAITING,above=0,below=0;
  void invalidate() {state=WAITING;above=below=0;}
  void sample(float value,bool valid,float high,float clear) {
    if(!valid || !isfinite(value)) {invalidate();return;}
    if(state==WAITING)state=NORMAL;
    if(state!=TRIGGERED) {
      above=value>high?uint8_t(above+1):0;below=0;
      if(above>=3) {state=TRIGGERED;above=0;}
    } else {
      below=value<=clear?uint8_t(below+1):0;above=0;
      if(below>=3) {state=NORMAL;below=0;}
    }
  }
};
class Model {
  uint32_t lastSequence=0;
  bool haveSequence=false;
public:
  Settings settings;
  Channel temperature,air;
  uint8_t mask() const {return (temperature.state==TRIGGERED?TEMPERATURE:0)|(air.state==TRIGGERED?AIR:0);}
  bool configure(float t,float q) {
    if(!Settings::valid(t,q))return false;
    settings.temperature=t;settings.iaq=q;temperature.invalidate();air.invalidate();return true;
  }
  void update(uint32_t sequence,bool live,float temp,bool iaqValid,float iaq,unsigned accuracy,bool stable,bool runIn) {
    bool newSample=!haveSequence || sequence!=lastSequence;
    if(haveSequence && newSample && uint32_t(sequence-lastSequence)!=1) {
      // Missing readings cannot establish a consecutive run in either direction.
      temperature.above=temperature.below=air.above=air.below=0;
    }
    if(!live || !isfinite(temp) || temp< -40 || temp>85)temperature.invalidate();
    bool airReady=live&&iaqValid&&accuracy>=1&&accuracy<=3&&stable&&runIn&&isfinite(iaq)&&iaq>=0&&iaq<=500;
    if(!airReady)air.invalidate();
    if(!newSample)return;
    haveSequence=true;lastSequence=sequence;
    temperature.sample(temp,live&&isfinite(temp)&&temp>=-40&&temp<=85,settings.temperature,settings.temperature-1);
    air.sample(iaq,airReady,settings.iaq,settings.iaq-10);
  }
};
}
