#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <math.h>
#include <stdlib.h>
#include "activity_format.h"

namespace WatchExt {
constexpr const char* VERSION="2.0.15";
#pragma pack(push,1)
struct Settings {
  uint32_t magic=0x3243574b;
  char ssid[33]={},password[65]={},host[129]={},user[65]={},mqttPassword[129]={},topic[97]={};
  char manifest[193]={};
  uint16_t port=8883,idleSeconds=0;
  uint8_t tls=1,led=63,red=63,average=1,logging=1;
  float shuntOhms=0,magMin[3]={},magMax[3]={};
  uint8_t magCalibrated=0;
  uint32_t crc=0;
};
#pragma pack(pop)
template<size_t N> inline bool terminated(const char (&s)[N]) {return memchr(s,0,N)!=nullptr;}
inline bool valid(const Settings& s) {
  if(s.magic!=0x3243574b || !terminated(s.ssid)||!terminated(s.password)||!terminated(s.host)||!terminated(s.user)||
     !terminated(s.mqttPassword)||!terminated(s.topic)||!terminated(s.manifest))return false;
  if(!s.port || s.tls>1 || !s.led || s.led>63 || !s.red || s.red>127 || s.average>1 || s.logging>1 ||
     (s.idleSeconds && (s.idleSeconds<15 || s.idleSeconds>3600)) || s.magCalibrated>1)return false;
  if(!isfinite(s.shuntOhms) || s.shuntOhms<0 || s.shuntOhms>1 || (s.shuntOhms>0 && s.shuntOhms<.0001f))return false;
  if(s.manifest[0] && strncmp(s.manifest,"https://",8))return false;
  if(s.topic[0] && (strchr(s.topic,'#')||strchr(s.topic,'+')))return false;
  if(s.magCalibrated)for(unsigned i=0;i<3;++i)
    if(!isfinite(s.magMin[i])||!isfinite(s.magMax[i])||s.magMax[i]-s.magMin[i]<100)return false;
  return true;
}
inline void seal(Settings& s) {s.crc=Activity::crc32(&s,offsetof(Settings,crc));}
inline bool intact(const Settings& s) {return valid(s)&&s.crc==Activity::crc32(&s,offsetof(Settings,crc));}
class Backoff {
  uint32_t delay_=1000,at_=0;
public:
  void reset(uint32_t now) {delay_=1000;at_=now;}
  bool due(uint32_t now) const {return int32_t(now-at_)>=0;}
  void failed(uint32_t now) {at_=now+delay_;delay_=delay_<60000? (delay_*2>60000?60000:delay_*2):60000;}
  uint32_t delay() const {return delay_;}
};
inline float heading(const int16_t raw[3],const Settings& s) {
  if(!s.magCalibrated)return NAN;
  float v[3],average=0;
  for(unsigned i=0;i<3;++i) {
    if(raw[i]==-4096 || abs(int(raw[i]))>30000)return NAN;
    v[i]=(s.magMax[i]-s.magMin[i])/2;average+=v[i]/3;
  }
  float x=(raw[0]-(s.magMin[0]+s.magMax[0])/2)*average/v[0];
  float y=(raw[1]-(s.magMin[1]+s.magMax[1])/2)*average/v[1];
  if(hypotf(x,y)<10)return NAN;
  float degrees=atan2f(y,x)*57.2957795f;return degrees<0?degrees+360:degrees;
}
}
