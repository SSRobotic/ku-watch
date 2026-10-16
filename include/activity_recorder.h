#pragma once
#include <Arduino.h>
#include <LittleFS.h>
#include <Preferences.h>
#include <esp_partition.h>
#include <esp_timer.h>
#include "activity_format.h"
#include "gps_receiver.h"

class ActivityRecorder {
  File file, download;
  Preferences sequence;
  Activity::Track track;
  uint64_t beganUs=0;
  uint32_t nextId=1,lastSampleMs=0,lastFlushMs=0;
  uint32_t downloadId=0,downloadSize=0,downloadOffset=0,downloadCrc=0xffffffffu;
  static constexpr size_t RESERVE=65536;
  static void path(char* b,uint32_t id) { snprintf(b,32,"/rec%06lu.kua",(unsigned long)id); }
  static bool blankPartition() {
    const auto* p=esp_partition_find_first(ESP_PARTITION_TYPE_DATA,ESP_PARTITION_SUBTYPE_ANY,"storage");
    if(!p) return false;
    uint8_t buf[512];
    for(size_t at=0;at<p->size;at+=sizeof(buf)) {
      if(esp_partition_read(p,at,buf,sizeof(buf))!=ESP_OK) return false;
      for(auto b:buf) if(b!=0xff) return false;
      yield();
    }
    return true;
  }
  bool append(Activity::Record& r) {
    Activity::seal(r);
    if(file.write(reinterpret_cast<const uint8_t*>(&r),sizeof(r))!=sizeof(r)) {
      file.close(); active=false; message="WRITE ERROR"; return false;
    }
    latestRecord=r; ++samples; return true;
  }
public:
  bool ready=false,active=false;
  Activity::Record latestRecord={};
  uint32_t id=0,samples=0,elapsedMs=0,freeBytes=0,count=0;
  const char* message="READY";
  double meters() const { return track.meters; }
  bool exporting() const { return bool(download); }
  void begin() {
    ready=LittleFS.begin(false,"/littlefs",4,"storage");
    if(!ready && blankPartition()) ready=LittleFS.begin(true,"/littlefs",4,"storage");
    if(!ready) { message="STORAGE ERROR"; return; }
    if(!sequence.begin("ku_activity",false)) { ready=false; message="STORAGE ERROR"; return; }
    nextId=sequence.getUInt("next",1);
    File root=LittleFS.open("/");
    for(File f=root.openNextFile();f;f=root.openNextFile()) {
      const char* name=f.name(); if(*name=='/') ++name;
      unsigned long found=0; char extra=0;
      if(sscanf(name,"rec%6lu.kua%c",&found,&extra)==1 && found && found<=999999) {
        ++count; if(found>=nextId) nextId=found+1;
      }
      f.close();
    }
    refreshFree(); report();
  }
  void refreshFree() { freeBytes=ready?LittleFS.totalBytes()-LittleFS.usedBytes():0; }
  bool start(uint64_t utc,bool clockReady) {
    if(active || download) return false;
    if(!ready) { message="STORAGE ERROR"; return false; }
    if(!clockReady || utc<1704067200ULL || utc>4102444799ULL) { message="SET TIME VIA USB"; return false; }
    refreshFree();
    if(freeBytes<RESERVE+4096 || nextId>999999) { message="STORAGE FULL"; return false; }
    char name[32]; path(name,nextId);
    if(LittleFS.exists(name)) { message="FILE EXISTS"; return false; }
    if(sequence.putUInt("next",nextId+1)!=sizeof(uint32_t)) { message="WRITE ERROR"; return false; }
    file=LittleFS.open(name,FILE_WRITE);
    if(!file) { message="WRITE ERROR"; return false; }
    auto h=Activity::header(utc);
    if(file.write(reinterpret_cast<const uint8_t*>(&h),sizeof(h))!=sizeof(h)) {
      file.close(); message="WRITE ERROR"; return false;
    }
    file.flush(); id=nextId++; ++count; samples=elapsedMs=lastSampleMs=lastFlushMs=0;
    track=Activity::Track(); beganUs=esp_timer_get_time(); active=true; message="RECORDING";
    report(); return true;
  }
  void stop(const char* reason="SAVED") {
    if(!active) return;
    elapsedMs=uint32_t((esp_timer_get_time()-beganUs)/1000);
    Activity::Record end={}; end.elapsedMs=elapsedMs; end.flags=Activity::STOP;
    end.distanceCm=uint32_t(lround(track.meters*100));
    if(!append(end)) { refreshFree(); report(); return; }
    file.flush(); file.close(); active=false; message=reason; refreshFree(); report();
  }
  void tick(const GpsReading& gps,float bpm) {
    if(!active) return;
    elapsedMs=uint32_t((esp_timer_get_time()-beganUs)/1000);
    if(samples && uint32_t(elapsedMs-lastSampleMs)<1000) return;
    if(elapsedMs>=24u*3600u*1000u) { stop("24H LIMIT"); return; }
    if(uint32_t(elapsedMs-lastFlushMs)>=5000) {
      file.flush(); lastFlushMs=elapsedMs; refreshFree();
      if(freeBytes<RESERVE) { stop("FULL - SAVED"); return; }
    }
    lastSampleMs=elapsedMs;
    Activity::Record r={}; r.elapsedMs=elapsedMs;
    bool good=gps.reliable();
    if(track.point(elapsedMs,gps.latitude,gps.longitude,good)) {
      r.flags|=Activity::GPS;
      r.latitudeE7=int32_t(lround(gps.latitude*1e7)); r.longitudeE7=int32_t(lround(gps.longitude*1e7));
      if(isfinite(gps.altitude) && fabs(gps.altitude)<100000) {
        r.flags|=Activity::ALTITUDE; r.altitudeCm=int32_t(lround(gps.altitude*100));
      }
    }
    if(isfinite(bpm) && bpm>=30 && bpm<=220) { r.flags|=Activity::HEART; r.bpm10=uint16_t(lround(bpm*10)); }
    r.distanceCm=uint32_t(lround(track.meters*100)); append(r);
  }
  void report() {
    Serial.printf("REC STATUS active=%u ready=%u id=%lu samples=%lu elapsed_ms=%lu distance_cm=%lu free=%lu count=%lu message=%s\n",
      active,ready,id,samples,elapsedMs,uint32_t(lround(track.meters*100)),freeBytes,count,message);
  }
  void list() {
    Serial.println("REC LIST BEGIN");
    if(ready) {
      File root=LittleFS.open("/");
      for(File f=root.openNextFile();f;f=root.openNextFile()) {
        const char* name=f.name(); if(*name=='/') ++name;
        unsigned long found=0; char extra=0;
        if(sscanf(name,"rec%6lu.kua%c",&found,&extra)==1 && found && found<=999999)
          Serial.printf("REC FILE %lu %u\n",found,unsigned(f.size()));
        f.close();
      }
    }
    Serial.println("REC LIST END");
  }
  void get(uint32_t requested) {
    if(!ready || active || download || !requested || requested>999999) { Serial.println("REC ERROR STOP RECORDING FIRST"); return; }
    char name[32]; path(name,requested); download=LittleFS.open(name,FILE_READ);
    if(!download) { Serial.println("REC ERROR FILE NOT FOUND"); return; }
    downloadId=requested; downloadSize=download.size(); downloadOffset=0; downloadCrc=0xffffffffu;
    Serial.printf("REC BEGIN %lu %lu\n",downloadId,downloadSize);
  }
  void exportTick() {
    if(!download) return;
    if(!Serial) { download.close(); return; }
    uint8_t bytes[96]; size_t n=download.read(bytes,sizeof(bytes));
    if(n) {
      char hex[193]; const char* digits="\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x61\x62\x63\x64\x65\x66";
      for(size_t i=0;i<n;++i) { hex[i*2]=digits[bytes[i]>>4]; hex[i*2+1]=digits[bytes[i]&15]; }
      hex[n*2]=0; downloadCrc=Activity::crcUpdate(downloadCrc,bytes,n);
      Serial.printf("REC DATA %lu %lu %s\n",downloadId,downloadOffset,hex); downloadOffset+=n;
    } else {
      Serial.printf("REC END %lu %lu %08lx\n",downloadId,downloadOffset,~downloadCrc);
      download.close();
    }
  }
  void remove(uint32_t requested) {
    if(!ready || active || download || !requested || requested>999999) { Serial.println("REC ERROR BUSY"); return; }
    char name[32]; path(name,requested);
    if(LittleFS.remove(name)) { if(count) --count; refreshFree(); Serial.printf("REC DELETED %lu\n",requested); }
    else Serial.println("REC ERROR DELETE FAILED");
  }
};
