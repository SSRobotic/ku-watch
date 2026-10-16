#pragma once
#include "hub_model.h"
namespace Pin {constexpr unsigned PAGE_COUNT=11;}
constexpr uint8_t INA226_I2C_ADDRESS=0x44;
#include "face.h"

namespace Hub {
class Touch {
  bool down=false,releasing=false,dispatched=false,fired=false;int pressed=-1;
  uint32_t releaseAt=0,lastFire=0;
public:
  void cancel(){down=true;pressed=-1;dispatched=true;releasing=false;}
  int held() const{return down?pressed:-1;}
  int update(bool valid,bool contact,unsigned x,unsigned y,unsigned page,uint32_t now,bool tap=false) {
    if(!valid){pressed=-1;return -1;}
    int hit=target(x,y,page);
    if(contact){releasing=false;if(!down){down=true;pressed=hit;dispatched=false;
        // Browsing responds on contact. State-changing actions still wait for
        // release, so a drag out of FEED/START/etc. can cancel the action.
        if(hit>=0 && hit<3){dispatched=true;fired=true;lastFire=now;return hit;}}
      else {
        // The first coordinate can land outside a small target before settling.
        // Navigation may acquire the target once; data-changing actions cannot.
        if(!dispatched && pressed<0 && hit>=0 && hit<3){pressed=hit;dispatched=true;fired=true;lastFire=now;return hit;}
        if(hit!=pressed)pressed=-1;
      }return -1;}
    // CST820 releases may zero the coordinate registers. Use the last contact
    // rectangle, cancelling a drag outside it, rather than release coordinates.
    if(down){if(!releasing){releasing=true;releaseAt=now;}
      if(uint32_t(now-releaseAt)<40)return -1;
      int result=dispatched?-1:pressed;down=false;pressed=-1;releasing=false;
      if(result>=0){fired=true;lastFire=now;}return result;}
    // An interrupt-backed completed tap also works if its short contact fell
    // between main-loop polls. Never replay a latched gesture on every poll.
    if(tap && hit>=0 && (!fired || uint32_t(now-lastFire)>=120)){fired=true;lastFire=now;return hit;}
    return -1;
  }
};
inline Face::State state(const KuLink::TelemetryPacket& p,bool fresh,unsigned page,uint32_t phase,char message[40]) {
  Face::State s;s.page=page;s.robotPhase=phase;s.mapAutomatic=false;
  if(!fresh){s.robotMessage="WAITING FOR WATCH";s.clockSource="WAIT WATCH TIME";return s;}
  const auto f=p.flags;s.bme=f&KuLink::Environment;
  s.temp=s.bme?p.temperature:NAN;s.humidity=s.bme?p.humidity:NAN;s.pressure=s.bme?p.pressure:NAN;
  s.bpm=f&KuLink::Pulse?p.bpm:NAN;s.spo2=f&KuLink::Spo2?p.spo2:NAN;
  s.max30102=(f&(KuLink::Pulse|KuLink::Spo2))||p.finger||p.spo2Status;
  s.finger=p.finger;s.spo2Status=p.spo2Status;
  s.iaqValid=f&KuLink::Iaq;s.iaq=s.iaqValid?p.iaq:NAN;s.gas=s.bme?p.gas:NAN;
  s.iaqAccuracy=p.iaqAccuracy;s.iaqStable=p.iaqStable;s.iaqRunIn=p.iaqRunIn;
  s.batteryValid=f&KuLink::Battery;s.batteryDetected=s.batteryValid;
  s.batteryVolts=s.batteryValid?p.batteryVolts:NAN;s.batteryPercent=s.batteryValid?p.batteryPercent:NAN;
  s.batteryLow=s.batteryValid && (f&KuLink::LowBattery);
  s.batteryCurrent=f&KuLink::Current?p.current:NAN;s.batteryPower=f&KuLink::Current?p.power:NAN;
  s.gpsReliable=s.gpsFix=s.gpsData=f&KuLink::Gps;
  s.latitude=s.gpsReliable?p.latitude:NAN;s.longitude=s.gpsReliable?p.longitude:NAN;
  s.altitude=s.gpsReliable?p.altitude:NAN;s.speed=s.gpsReliable?p.speed:NAN;s.satellites=p.satellites;
  s.recording=f&KuLink::Recording;s.recordElapsed=p.elapsed;s.recordDistance=p.distance;s.recordId=p.activity;
  s.gy51=f&(KuLink::Motion|KuLink::Mag);
  if(f&KuLink::Motion){s.accX=p.acc[0];s.accY=p.acc[1];s.accZ=p.acc[2];}
  if(f&KuLink::Mag){s.magX=p.mag[0];s.magY=p.mag[1];s.magZ=p.mag[2];}
  s.heading=f&KuLink::Heading?p.heading:NAN;s.wifi=f&KuLink::Wifi;s.mqtt=f&KuLink::Mqtt;
  s.networkPending=p.pending;s.mapZoom=MapZoom::valid(p.zoom)?p.zoom:MapZoom::DEFAULT_INDEX;
  s.robotXp=p.xp;s.robotFood=p.food;s.robotMood=p.mood;s.robotEnergy=p.energy;
  s.robotPose=p.pose<RobotPet::POSE_COUNT?RobotPet::Pose(p.pose):RobotPet::Pose::Idle;
  memcpy(message,p.robotMessage,39);message[39]=0;s.robotMessage=message;s.robotBubble=p.robotBubble;
  s.alertMask=p.alertMask;s.alertTemperature=p.temperatureAlert;s.alertAir=p.iaqAlert;
  return s;
}
class Screen {
public:
  uint16_t* pixels=nullptr;Face::Canvas* small=nullptr;
  void rect(int x,int y,int w,int h,uint16_t c){for(int j=y;j<y+h;++j)for(int i=x;i<x+w;++i)if(i>=0&&j>=0&&i<480&&j<480)pixels[j*480+i]=c;}
  void text(int x,int y,const char* s,int scale,uint16_t c) {
    for(;*s;++s,x+=6*scale){auto g=Face::glyph(*s);for(int j=0;j<7;++j)for(int i=0;i<5;++i)if(g[j]&(1<<(4-i)))rect(x+i*scale,y+j*scale,scale,scale,c);}
  }
  void center(int y,const char* s,int scale,uint16_t c){text((480-int(strlen(s))*6*scale+scale)/2,y,s,scale,c);}
  void button(int x,int w,int y,const char* label,bool enabled,bool pressed) {
    rect(x,y,w,44,enabled?(pressed?Face::TEAL:Face::DIM):uint16_t(0x1082));
    text(x+(w-int(strlen(label))*12+2)/2,y+15,label,2,enabled?Face::WHITE:Face::GRAY);
  }
  void render(Face::State& s,const KuLink::TelemetryPacket& p,bool fresh,const char* status,int held=-1) {
    small->render(s);char b[64];
    if(!fresh && s.page==10){small->clear();small->rim(s.second);small->center(45,"KU-BOT",3,Face::TEAL);small->center(108,"WAITING FOR WATCH",1,Face::GRAY);small->center(155,"CARE DATA OFFLINE",1,Face::GRAY);}
    // These fields are not in the radio contract: use actual transmitted state
    // instead of displaying an invented I2C scan, IR sample or free-flash count.
    if(s.page==2||s.page==3||s.page==4||s.page==5||s.page==7) {
      small->clear();small->rim(s.second);
      if(s.page==2){small->center(38,"WATCH SENSORS",2,Face::TEAL);
        static const char* names[]={"BME680","BPM","SPO2","BATTERY","GPS","MOTION","MAGNETOMETER"};
        static const uint32_t flags[]={KuLink::Environment,KuLink::Pulse,KuLink::Spo2,KuLink::Battery,KuLink::Gps,KuLink::Motion,KuLink::Mag};
        for(unsigned i=0;i<7;++i){small->text(40,72+19*i,names[i],1,Face::WHITE);small->text(157,72+19*i,fresh&&(p.flags&flags[i])?"LIVE":"--",1,Face::CYAN);}}
      if(s.page==3){small->center(38,"HEART RATE",2,Face::TEAL);small->value(b,sizeof(b),s.bpm,1," BPM");small->center(91,b,3,Face::LIME);
        small->value(b,sizeof(b),s.spo2,0,"% SPO2");small->center(143,b,2,Face::CYAN);
        small->center(180,!fresh?"WAITING FOR WATCH":s.finger?"KEEP WRIST STILL":"WAITING FOR PULSE",1,Face::GRAY);}
      if(s.page==3)small->center(190,"ESTIMATE - NOT MEDICAL",1,Face::GRAY);
      if(s.page==4){small->center(38,"MOTION",2,Face::TEAL);const char axes[]="XYZ";
        for(unsigned i=0;i<3;++i){if(fresh&&(p.flags&KuLink::Motion))snprintf(b,sizeof(b),"%c %d",axes[i],p.acc[i]);else snprintf(b,sizeof(b),"%c --",axes[i]);small->center(77+34*i,b,2,Face::LIME);}
        small->value(b,sizeof(b),s.heading,0," DEG");small->center(183,b,2,Face::CYAN);
        small->center(207,!fresh?"WAITING FOR WATCH":p.magCalibration==1?"ROTATE WATCH SLOWLY":p.magCalibration==2?"COMPASS CALIBRATED":"COMPASS NEEDS CALIBRATION",1,Face::GRAY);}
      if(s.page==5){small->center(38,"NETWORK",2,Face::TEAL);small->center(72,fresh?"ESP-NOW: LIVE":"ESP-NOW: WAITING",1,Face::CYAN);
        char version[40];snprintf(version,sizeof(version),"HUB 1.0.8 WATCH %.11s",fresh?p.firmware:"--");small->center(211,version,1,Face::GRAY);
        small->center(105,!fresh?"WIFI: --":s.wifi?"WATCH WIFI: CONNECTED":"WATCH WIFI: OFFLINE",1,Face::GRAY);
        small->center(137,!fresh?"MQTT: --":s.mqtt?"WATCH MQTT: CONNECTED":"WATCH MQTT: OFFLINE",1,Face::GRAY);
        if(fresh)snprintf(b,sizeof(b),"PENDING %lu",(unsigned long)p.pending);else strcpy(b,"PENDING --");small->center(168,b,1,Face::LIME);
        small->center(198,"SETUP OPENS ON WATCH",1,Face::GRAY);}
      if(s.page==7){small->center(38,"WALK",2,Face::TEAL);small->center(65,!fresh?"WAITING FOR WATCH":s.recording?"RECORDING":"READY",1,Face::CYAN);
        unsigned sec=s.recordElapsed/1000;if(fresh)snprintf(b,sizeof(b),"%02u:%02u:%02u",sec/3600,sec/60%60,sec%60);else strcpy(b,"--:--:--");small->center(91,b,3,Face::WHITE);
        small->value(b,sizeof(b),fresh?s.recordDistance/1000:NAN,2," KM");small->center(136,b,2,Face::LIME);
        if(fresh)snprintf(b,sizeof(b),"ACTIVITY %lu",(unsigned long)p.activity);else strcpy(b,"ACTIVITY --");small->center(175,b,1,Face::GRAY);
        small->center(202,s.timeSet?"RECORDS ON WATCH":"WAIT GPS OR SET TIME",1,Face::GRAY);}
      small->robotOverlay(s);
      if(s.alertMask || s.batteryLow){small->rect(40,25,160,9,Face::BLACK);small->center(26,Face::warning(s),1,0xf800);}
    }
    if(s.page==6){small->rect(35,15,170,13,Face::BLACK);small->center(18,"MAP FROM WATCH",1,Face::CYAN);}
    if(s.page==0 && !s.timeSet){small->rect(39,86,164,48,Face::BLACK);small->center(99,"--:--",4,Face::GRAY);small->rect(40,182,160,15,Face::BLACK);small->center(185,"WAIT FOR TRUSTED TIME",1,Face::GRAY);}
    // Remove small-watch hardware-button hints; touch controls live below.
    if(s.page==1||s.page==3||s.page==4)small->rect(44,202,152,12,Face::BLACK);
    memset(pixels,0,480*480*2);
    // Exact nearest-neighbour 3:2 scaling. Expand each 2x2 source block into
    // 3x3 pixels without division in the pixel loop (expensive on Xtensa -Os).
    for(int sy=0,dy=12;sy<240;sy+=2,dy+=3){
      const uint16_t* source=small->pixels+sy*240;
      uint16_t* row=pixels+dy*480+60;
      for(int sx=0,dx=0;sx<240;sx+=2,dx+=3){
        uint16_t a=source[sx],b=source[sx+1],c=source[sx+240],d=source[sx+241];
        row[dx]=row[dx+1]=a;row[dx+2]=b;
        row[480+dx]=row[481+dx]=a;row[482+dx]=b;
        row[960+dx]=row[961+dx]=c;row[962+dx]=d;
      }
    }
    unsigned n=buttons(s.page);bool enabled=fresh;
    if(n==1)button(151,178,350,label(s.page,0,s.recording),enabled,held==3);
    if(n==2){button(105,125,350,label(s.page,0,s.recording),enabled,held==3);button(250,125,350,label(s.page,1,s.recording),enabled,held==4);}
    button(94,96,403,"PREV",true,held==0);button(192,96,403,"HOME",true,held==1);button(290,96,403,"NEXT",true,held==2);
    // Fill the lower portion too: 58 px high visible targets, with padded hitboxes.
    rect(94,447,96,14,held==0?Face::TEAL:Face::DIM);rect(192,447,96,14,held==1?Face::TEAL:Face::DIM);rect(290,447,96,14,held==2?Face::TEAL:Face::DIM);
    rect(105,n?342:379,270,8,Face::BLACK);center(n?342:379,status,1,fresh?Face::CYAN:Face::LIME);
  }
};
}
