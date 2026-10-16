#include <Arduino.h>
#include <Wire.h>
#include <Preferences.h>
#include <esp_heap_caps.h>
#include <time.h>
#include <stdarg.h>
#include "display_hardware.h"
#include "touch_sampler.h"
#include "display_receiver.h"
#include "rtc_pcf85063.h"
#include "hub_ui.h"
#include "map_assets.h"
void hubLog(const char* format,...);
#include "sd_logger.h"

// Diagnostic USB output must never wait for a terminal to read it.
// Drop a whole line when the output queue is full; UI/radio keep running.
void hubLog(const char* format,...) {
  if(!Serial)return;
  char line[512];va_list args;va_start(args,format);
  int n=vsnprintf(line,sizeof(line),format,args);va_end(args);
  if(n<=0 || size_t(n)>=sizeof(line) || Serial.availableForWrite()<n)return;
  Serial.write(reinterpret_cast<const uint8_t*>(line),size_t(n));
}

const uint8_t WATCH_MAC[6]={0xd4,0x05,0x92,0x44,0x51,0xac};
HubDisplay display;
DisplayReceiver receiver;
HubSdLogger sdLogger;
Hub::Screen screen;
Hub::Touch touchInput;
TouchSampler touchSampler;
Preferences preferences;
WatchMap::Data* maps[2]={};
WatchMap::Trail trail;
unsigned page=0,area=0;
uint32_t renderAt=0,touchAt=0,infoAt=0,rtcAt=0,rtcPollAt=0,seenSequence=0,seenSession=0,trailActivity=0;
uint64_t rtcUtc=0;uint32_t rtcSampleAt=0;
uint32_t clockOfferAt=0;
bool rtcDetected=false,rtcMarked=false,firstSnapshot=true;
bool dirty=true,navigationPending=false;
uint32_t lastRenderUs=0,maxRenderUs=0;
uint32_t maxInputAge=0,seenInputDrops=0;bool rawDown=false;
char robotMessage[40]={},notice[40]="SEARCHING FOR WATCH";
uint32_t noticeAt=0,commandAcks=0,commandTimeouts=0;

WatchMap::Data* loadMap(const uint8_t* bytes,size_t size) {
  WatchMap::Header h;memcpy(&h,bytes,sizeof(h));if(!WatchMap::validHeader(h,size))return nullptr;
  auto d=static_cast<WatchMap::Data*>(heap_caps_calloc(1,sizeof(WatchMap::Data),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
  if(!d)return nullptr;d->header=h;size_t f=h.features*sizeof(WatchMap::Feature);
  memcpy(d->features,bytes+sizeof(h),f);memcpy(d->points,bytes+sizeof(h)+f,h.points*sizeof(WatchMap::Point));
  if(!WatchMap::valid(*d,size)){free(d);return nullptr;}WatchMap::index(*d);return d;
}
void setNotice(const char* value){strlcpy(notice,value,sizeof(notice));noticeAt=millis();}
bool command(KuLink::Action a,int32_t argument=0,float value=0,float value2=0) {
  bool sent=receiver.send(a,argument,value,value2);
  setNotice(sent?"SENDING TO WATCH":!receiver.fresh()?"WATCH OFFLINE":receiver.waiting?"BUSY - TRY AGAIN":"LINK NOT READY");
  hubLog("HUB COMMAND action=%u arg=%ld sent=%u\n",unsigned(a),long(argument),sent);return sent;
}
void choosePage(unsigned next,bool remote=true) {
  page=next%11;dirty=true;firstSnapshot=false;
  // Navigation is local first. Avoid blocking flash commits on every tap and
  // queue the latest requested page if an earlier radio command is in flight.
  navigationPending=remote && receiver.fresh();
}
void navigationTick(){if(navigationPending && receiver.fresh() && !receiver.waiting){if(command(page==0?KuLink::Home:KuLink::Page,page))navigationPending=false;}}
void controls() {
  if(touchSampler.dropped!=seenInputDrops){seenInputDrops=touchSampler.dropped;touchInput.cancel();touchSampler.discard();hubLog("HUB INPUT OVERFLOW cancelled until release\n");}
  TouchSampler::Sample s;
  while(touchSampler.next(s)){
    uint32_t age=millis()-s.at;if(age>maxInputAge)maxInputAge=age;
    if(s.down!=rawDown || s.tap){rawDown=s.down;hubLog("HUB TOUCHRAW at=%lu age=%lu valid=%u down=%u gesture=%u x=%u y=%u hit=%d\n",(unsigned long)s.at,(unsigned long)age,s.valid,s.down,s.gesture,s.x,s.y,Hub::target(s.x,s.y,page));}
    int held=touchInput.held();int hit=touchInput.update(s.valid,s.down,s.x,s.y,page,s.at,s.tap);
    if(held!=touchInput.held())dirty=true;
    if(hit<0)continue;hubLog("HUB TOUCH x=%u y=%u target=%d\n",s.x,s.y,hit);
    if(hit<3){choosePage(hit==0?(page+10)%11:hit==1?0:(page+1)%11);continue;}
    auto c=Hub::action(receiver.snapshot,page,hit-3,receiver.fresh());
    if(c.valid)command(c.action,c.argument,c.a,c.b);else setNotice(receiver.fresh()?"WAIT FOR WATCH CLOCK":"WATCH OFFLINE");
  }
}
void clockTick() {
  if(!touchSampler.take(10))return;
  struct BusGuard {~BusGuard(){touchSampler.give();}} guard;
  uint32_t now=millis();
  if(receiver.fresh() && (receiver.snapshot.flags&KuLink::Clock) && !(receiver.snapshot.flags&KuLink::HubClock) && receiver.snapshot.utc>=1704067200ULL && receiver.snapshot.utc<=4102444799ULL &&
      rtcDetected && (!rtcMarked || !rtcAt || uint32_t(now-rtcAt)>=300000)) {
    time_t utc=receiver.snapshot.utc;tm calendar{};gmtime_r(&utc,&calendar);
    RtcTime value{uint16_t(calendar.tm_year+1900),uint8_t(calendar.tm_mon+1),uint8_t(calendar.tm_mday),uint8_t(calendar.tm_wday),uint8_t(calendar.tm_hour),uint8_t(calendar.tm_min),uint8_t(calendar.tm_sec)};
    if(Rtc::write(value)){if(!rtcMarked)preferences.putBool("utc",true);rtcMarked=true;rtcAt=now;hubLog("HUB RTC synced UTC from authenticated watch\n");}
  }
  if(rtcDetected && rtcMarked && uint32_t(now-rtcPollAt)>=1000) {
    rtcPollAt=now;RtcTime value{};
    if(Rtc::read(value)){tm calendar{};calendar.tm_year=value.year-1900;calendar.tm_mon=value.month-1;calendar.tm_mday=value.day;calendar.tm_hour=value.hour;calendar.tm_min=value.minute;calendar.tm_sec=value.second;
      // No process-wide TZ is set: mktime and gmtime use UTC. UI alone adds +7.
      time_t utc=mktime(&calendar);if(utc>=1704067200LL && utc<=4102444799LL){rtcUtc=utc;rtcSampleAt=now;}else rtcUtc=0;
    }else rtcUtc=0;
  }
  // Offer only a fresh RTC that was previously initialized from trusted UTC.
  // Navigation has priority. No packet ABI change is needed for a UTC second.
  if(receiver.fresh() && !(receiver.snapshot.flags&KuLink::Clock) && rtcUtc &&
      uint32_t(now-rtcSampleAt)<2000 && !receiver.waiting && !navigationPending &&
      (!clockOfferAt || uint32_t(now-clockOfferAt)>=5000)) {
    clockOfferAt=now;uint32_t seconds=uint32_t(rtcUtc+uint32_t(now-rtcSampleAt)/1000);
    int32_t argument=0;memcpy(&argument,&seconds,sizeof(argument));
    if(receiver.send(KuLink::ClockSync,argument))hubLog("HUB CLOCK offered authenticated RTC UTC=%lu\n",(unsigned long)seconds);
  }
}
void updateTrail() {
  if(!receiver.fresh()){Activity::Record gap{};trail.append(gap);return;}
  const auto& p=receiver.snapshot;if(p.h.session==seenSession && p.h.sequence==seenSequence)return;
  seenSession=p.h.session;seenSequence=p.h.sequence;
  if(firstSnapshot){firstSnapshot=false;page=p.page<11?p.page:0;}
  if(p.area<2 && p.area!=area){area=p.area;preferences.putUChar("area",area);}
  if(p.activity!=trailActivity){trail.clear();trailActivity=p.activity;}
  if(p.flags&KuLink::Recording){Activity::Record r{};r.elapsedMs=p.elapsed;
    if((p.flags&KuLink::Gps) && isfinite(p.latitude) && isfinite(p.longitude) && fabs(p.latitude)<=90 && fabs(p.longitude)<=180){r.flags=Activity::GPS;r.latitudeE7=lround(p.latitude*1e7);r.longitudeE7=lround(p.longitude*1e7);}trail.append(r);}
}
void info() {
  const auto& p=receiver.snapshot;
  hubLog("HUBINFO version=1.0.8 mac=%s lcd=%u frames=%lu touch=%u toucherr=%lu receiver=%u ready=%u seq=%lu acks=%lu timeouts=%lu page=%u watchpage=%u flags=%lu area=%u zoom=%u recording=%u rtc=%u rtcvalid=%u psram=%u\n",
    WiFi.macAddress().c_str(),display.ready,(unsigned long)display.frames,display.touchReady,(unsigned long)display.touchErrors,receiver.fresh(),receiver.ready,(unsigned long)p.h.sequence,(unsigned long)receiver.acks,(unsigned long)receiver.timeouts,page,p.page,(unsigned long)p.flags,p.area,p.zoom,bool(p.flags&KuLink::Recording),rtcDetected,bool(rtcUtc),ESP.getFreePsram());
  hubLog("HUB RADIO channel=%u incoming=%lu hellos=%lu rejected=%lu\n",receiver.channel(),(unsigned long)receiver.incoming,(unsigned long)receiver.hellos,(unsigned long)receiver.rejected);
  hubLog("HUB PERFORMANCE render_us=%lu max_render_us=%lu touch_samples=%lu\n",(unsigned long)lastRenderUs,(unsigned long)maxRenderUs,(unsigned long)display.touchSamples);
  hubLog("HUB INPUT task=%u samples=%lu dropped=%lu max_gap_ms=%lu max_age_ms=%lu\n",touchSampler.started,(unsigned long)touchSampler.samples,(unsigned long)touchSampler.dropped,(unsigned long)touchSampler.maxGap,(unsigned long)maxInputAge);
  hubLog("HUB CLOCK utc=%llu age_ms=%lu marked=%u watch_utc=%llu watch_from_hub=%u firmware=%.11s\n",(unsigned long long)rtcUtc,(unsigned long)(rtcSampleAt?millis()-rtcSampleAt:0),rtcMarked,(unsigned long long)p.utc,bool(p.flags&KuLink::HubClock),p.firmware);
  sdLogger.info();
}
void console() {
  static String line;
  while(Serial.available()){char ch=Serial.read();if(ch=='\r')continue;if(ch!='\n'){if(line.length()<100)line+=ch;continue;}
    if(line=="HUBINFO"||line=="SCREENINFO"||line=="RTCINFO")info();
    else if(line=="SDINFO")sdLogger.info();
    else if(line.startsWith("SDREAD "))sdLogger.read(strtoul(line.c_str()+7,nullptr,10));
    else if(line.startsWith("PAGE "))choosePage(line.substring(5).toInt());
    else if(line.startsWith("LINKCMD ")){int a=0,b=0;float c=0,d=0;if(sscanf(line.c_str()+8,"%d %d %f %f",&a,&b,&c,&d)>=1 && a>=1 && a<=16)command(KuLink::Action(a),b,c,d);}
    line="";
  }
}
void render() {
  if(!display.ready || !screen.pixels || !screen.small || (!dirty && uint32_t(millis()-renderAt)<250))return;renderAt=millis();dirty=false;uint32_t began=micros();
  bool fresh=receiver.fresh();auto s=Hub::state(receiver.snapshot,fresh,page,millis()/250,robotMessage);
  s.map=maps[area];s.trail=&trail;
  uint64_t utc=0;
  if(fresh && (receiver.snapshot.flags&KuLink::Clock) && receiver.snapshot.utc>=1704067200ULL && receiver.snapshot.utc<=4102444799ULL){utc=receiver.snapshot.utc+uint32_t(millis()-receiver.receivedAt)/1000;s.clockSource="WATCH TIME";}
  else if(rtcUtc && uint32_t(millis()-rtcSampleAt)<3000){utc=rtcUtc+uint32_t(millis()-rtcSampleAt)/1000;s.clockSource="HUB RTC TIME";}
  if(utc){time_t local=utc+25200;tm calendar{};gmtime_r(&local,&calendar);s.hour=calendar.tm_hour;s.minute=calendar.tm_min;s.second=calendar.tm_sec;s.day=calendar.tm_mday;s.month=calendar.tm_mon+1;s.weekday=calendar.tm_wday;s.timeSet=true;}
  const char* status=!fresh?"SEARCHING FOR WATCH":uint32_t(millis()-noticeAt)<4000?notice:"ESP-NOW LIVE";
  screen.render(s,receiver.snapshot,fresh,status,touchInput.held());
  if(page==5){auto sd=sdLogger.status();screen.center(384,!sd.mountDone?"SD: STARTING":!sd.ready?"SD: CHECK CARD":sd.rows?"SD: CSV LOGGING":"SD: WAIT RTC / WATCH",1,sd.ready?Face::LIME:Face::GRAY);}
  display.draw(screen.pixels);lastRenderUs=micros()-began;if(lastRenderUs>maxRenderUs)maxRenderUs=lastRenderUs;
}
void setup() {
  Serial.begin(115200);Serial.setTxTimeoutMs(0);delay(250);hubLog("KU HUB 1.0.8 boot: Waveshare 480x480 RGB\n");
  Wire.begin(I2C_SDA_PIN,I2C_SCL_PIN,I2C_FREQ_HZ);Wire.setTimeOut(30);
  preferences.begin("ku-hub-rtc2",false);page=preferences.getUChar("page",0)%11;area=preferences.getUChar("area",0)%2;rtcMarked=preferences.getBool("utc",false);
  screen.pixels=static_cast<uint16_t*>(heap_caps_calloc(480*480,2,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
  screen.small=static_cast<Face::Canvas*>(heap_caps_calloc(1,sizeof(Face::Canvas),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
  if(screen.pixels && screen.small){if(!display.begin())hubLog("HUB ERROR LCD initialization failed\n");}
  else hubLog("HUB ERROR missing PSRAM/framebuffers\n");
  render(); // Visible boot page before pairing or optional RTC work.
  maps[0]=loadMap(HUB_MAP_0,sizeof(HUB_MAP_0));maps[1]=loadMap(HUB_MAP_1,sizeof(HUB_MAP_1));
  hubLog("HUB MAPS ku=%u amnat=%u\n",bool(maps[0]),bool(maps[1]));
  rtcDetected=Rtc::begin();receiver.begin(WATCH_MAC);
  if(!display.releaseCommandBus() || !sdLogger.begin())hubLog("HUB ERROR SD worker initialization failed\n");
  if(!touchSampler.begin(display))hubLog("HUB ERROR independent touch sampler failed\n");info();
}
void loop() {
  receiver.tick();updateTrail();controls();navigationTick();clockTick();console();navigationTick();
  sdLogger.tick(receiver.snapshot,receiver.receivedAt,rtcUtc,rtcSampleAt);sdLogger.replyTick();
  if(receiver.acks!=commandAcks){commandAcks=receiver.acks;const char* results[]={"WATCH CONFIRMED","COMMAND INVALID","WATCH BUSY","WAIT FOR WATCH CLOCK","WATCH STORAGE ERROR"};setNotice(results[receiver.lastResult<=4?receiver.lastResult:1]);hubLog("HUB ACK result=%u count=%lu\n",receiver.lastResult,(unsigned long)receiver.acks);}
  if(receiver.timeouts!=commandTimeouts){commandTimeouts=receiver.timeouts;setNotice("NO ACK - TRY AGAIN");hubLog("HUB COMMAND TIMEOUT\n");}
  render();if(uint32_t(millis()-infoAt)>=10000){infoAt=millis();info();}delay(2);
}


