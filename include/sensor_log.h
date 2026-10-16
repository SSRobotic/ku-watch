#pragma once
#include <Arduino.h>
#include <LittleFS.h>

// The network worker owns log writes, so FIFO/GPS sampling never waits on flash.
class SensorLog {
  uint32_t at=0;unsigned rows=0;bool enabled=true;
  File file;
  static constexpr unsigned LIMIT=16384,FILES=4,RESERVE=196608;
public:
  uint32_t written=0,skipped=0;
  static constexpr const char* fields="timestamp,uptime_ms,temp,humidity,pressure,bpm,spo2,spo2_valid,iaq,iaq_valid,iaq_accuracy,gas_ohms,battery_voltage,battery_percent,battery_current_ma,battery_power_mw,current_valid,acc_x,acc_y,acc_z,mag_x,mag_y,mag_z,heading,gps_fix,latitude,longitude,speed_kmh,recording,elapsed_s,distance_m,alert_mask";
  void configure(bool enable) {enabled=enable;if(!enable && file)file.close();}
  static String cell(const char* json,const String& key) {
    String needle="\""+key+"\":";const char* begin=strstr(json,needle.c_str());if(!begin)return "";
    begin+=needle.length();const char* end=begin;while(*end&&*end!=','&&*end!='}')++end;
    String s;s.reserve(end-begin);for(auto p=begin;p<end;++p)s+=*p;return s=="null"?"":s;
  }
  void append(const char* json,uint32_t captured,bool ready) {
    if(!enabled||!ready || (written && uint32_t(captured-at)<5000))return;
    // Anchor subsequent writes to the 5-second slots, rather than accumulating
    // capture/render jitter. A long stall still creates only one real row.
    if(!written)at=captured;
    else at+=uint32_t(captured-at)/5000*5000;
    if(LittleFS.totalBytes()-LittleFS.usedBytes()<RESERVE+4096) {++skipped;return;}
    if(!file || file.size()>=LIMIT) {
      if(file)file.close();
      // Explicit bounded rotation affects only our sensor CSVs.
      LittleFS.remove("/sensors3.csv");
      for(int i=2;i>=0;--i) {char a[24],b[24];snprintf(a,sizeof(a),"/sensors%d.csv",i);snprintf(b,sizeof(b),"/sensors%d.csv",i+1);
        if(LittleFS.exists(a))LittleFS.rename(a,b);}
      file=LittleFS.open("/sensors0.csv",FILE_WRITE);if(!file) {++skipped;return;}
      file.println(fields);rows=0;
    }
    String line;line.reserve(400);String names(fields);int start=0;
    for(int i=0;i<=int(names.length());++i) if(i==int(names.length())||names[i]==',') {
      if(start)line+=',';line+=cell(json,names.substring(start,i));start=i+1;
    }
    line+='\n';if(file.print(line)!=line.length()) {file.close();++skipped;return;}
    file.flush();++written;++rows;
  }
};
