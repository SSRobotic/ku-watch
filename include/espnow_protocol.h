#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "activity_format.h"

namespace KuLink {
constexpr uint32_t MAGIC=0x324e554b;
constexpr uint8_t VERSION=1;
enum Type:uint8_t {Hello=1,Telemetry=2,Command=3,Ack=4};
enum Action:uint8_t {Next=1,Home=2,Page=3,RecordStart=4,RecordStop=5,MapArea=6,MapZoom=7,
  PetFeed=8,PetPlay=9,AlertLimits=10,PulseSettings=11,ScreenWake=12,Setup=13,Heartbeat=14,CompassCalibration=15,ClockSync=16};
enum Result:uint8_t {Ok=0,Invalid=1,Busy=2,NoClock=3,StorageError=4};
#pragma pack(push,1)
struct Header {uint32_t magic=MAGIC,session=0,sequence=0;uint8_t version=VERSION,type=0;uint16_t size=0;};
struct HelloPacket {Header h;uint8_t role=0,channel=1;uint32_t challenge=0;uint8_t tag[16]={};uint32_t crc=0;};
struct CommandPacket {Header h;uint32_t receiverSession=0;uint8_t action=0;int32_t argument=0;float value=0,value2=0;uint8_t tag[16]={};uint32_t crc=0;};
struct AckPacket {Header h;uint32_t commandSession=0,commandSequence=0;uint8_t result=Invalid,page=0,recording=0;uint8_t tag[16]={};uint32_t crc=0;};
struct TelemetryPacket {
  Header h;uint64_t utc=0;uint32_t uptime=0,flags=0,elapsed=0,activity=0,pending=0,xp=0;
  float temperature=0,humidity=0,pressure=0,bpm=0,spo2=0,iaq=0,gas=0,batteryVolts=0,batteryPercent=0;
  double latitude=0,longitude=0;
  float speed=0,altitude=0,distance=0,heading=0,current=0,power=0;
  int16_t acc[3]={},mag[3]={};
  uint8_t page=0,area=0,zoom=0,channel=1,satellites=0,iaqAccuracy=0,alertMask=0,food=0,mood=0,energy=0,pose=0;
  char firmware[12]={};
  float temperatureLimit=35,iaqLimit=150;
  uint8_t spo2Status=0,finger=0,iaqStable=0,iaqRunIn=0,temperatureAlert=0,iaqAlert=0,robotBubble=0;
  char robotMessage[40]={};uint8_t magCalibration=0;uint8_t tag[16]={};uint32_t crc=0;
};
#pragma pack(pop)
enum Flag:uint32_t {Clock=1,Environment=2,Pulse=4,Spo2=8,Iaq=16,Battery=32,Gps=64,
  Recording=128,Wifi=256,Mqtt=512,Motion=1024,Mag=2048,Heading=4096,Current=8192,LowBattery=16384,HubClock=32768};
template<class P> inline void seal(P& p,Type type,uint32_t session,uint32_t seq) {
  p.h.magic=MAGIC;p.h.session=session;p.h.sequence=seq;p.h.version=VERSION;p.h.type=uint8_t(type);p.h.size=sizeof(P);
  p.crc=Activity::crc32(&p,sizeof(P)-4);
}
template<class P> inline bool valid(const P& p,Type type) {
  return p.h.magic==MAGIC && p.h.version==VERSION && p.h.type==type && p.h.size==sizeof(P) &&
    p.h.session && p.h.sequence && p.crc==Activity::crc32(&p,sizeof(P)-4);
}
class Commands {
  uint32_t session_=0,last_=0;
public:
  void reset() {session_=last_=0;}
  // A new boot session is accepted only on the authenticated paired peer.
  bool accept(uint32_t session,uint32_t sequence) {
    if(!session||!sequence)return false;
    if(session==session_ && int32_t(sequence-last_)<=0)return false;
    session_=session;last_=sequence;return true;
  }
};
static_assert(sizeof(TelemetryPacket)<=250,"ESP-NOW v1 payload limit");
static_assert(sizeof(CommandPacket)==53,"shared packed ABI");
}
