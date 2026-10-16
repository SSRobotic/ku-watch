#pragma once
#include <Arduino.h>
#include <LittleFS.h>
#include <esp_heap_caps.h>
#include <Preferences.h>
#include "map_geometry.h"
#include "map_selection.h"

class MapService {
  WatchMap::Data* areas[2]={nullptr,nullptr};
  File upload;
  unsigned slot_=0;
  WatchMap::Selection selection;
  Preferences preferences;
  bool selectionStorage=false,selectionSaved=false,selectionRestored=false;
  uint32_t expected_=0,received_=0,crc_=0xffffffffu,expectedCrc_=0,lastData_=0;
  static void path(char* out,unsigned slot) {snprintf(out,24,"/map%u.kum",slot);}
  WatchMap::Data* load(const char* name) {
    File f=LittleFS.open(name,FILE_READ); if(!f) return nullptr;
    size_t bytes=f.size(); WatchMap::Header h;
    if(f.read(reinterpret_cast<uint8_t*>(&h),sizeof(h))!=sizeof(h) || !WatchMap::validHeader(h,bytes)) return nullptr;
    auto* d=static_cast<WatchMap::Data*>(heap_caps_malloc(sizeof(WatchMap::Data),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
    // Maps are optional; preserve internal RAM for the display, sensors and TLS.
    if(!d) return nullptr;
    d->header=h;
    if(f.read(reinterpret_cast<uint8_t*>(d->features),h.features*sizeof(WatchMap::Feature))!=h.features*sizeof(WatchMap::Feature) ||
       f.read(reinterpret_cast<uint8_t*>(d->points),h.points*sizeof(WatchMap::Point))!=h.points*sizeof(WatchMap::Point) ||
       !WatchMap::valid(*d,bytes)) {free(d);return nullptr;}
    WatchMap::index(*d);return d;
  }
  void error(const char* text) { Serial.printf("MAP ERROR %s\n",text); }
  void saveSelection() {
    if(!selectionStorage) {error("SELECTION STORAGE UNAVAILABLE");return;}
    auto saved=selection.snapshot();
    selectionSaved=preferences.putBytes("selection",&saved,sizeof(saved))==sizeof(saved);
    if(!selectionSaved) error("SELECTION SAVE FAILED");
  }
  static int hex(char c) {
    if(c>='0' && c<='9') return c-'0'; if(c>='a' && c<='f') return c-'a'+10;
    if(c>='A' && c<='F') return c-'A'+10; return -1;
  }
public:
  bool ready=false;
  const WatchMap::Data* current() const {return areas[selection.area];}
  unsigned selected() const {return selection.area;}
  bool automatic() const {return selection.automatic;}
  bool choose(int area) {
    if(!ready || area< -1 || area>1 || (area>=0 && !areas[area]))return false;
    if(area<0)selection.autoMode();else selection.manual(area,bool(areas[0]),bool(areas[1]));
    saveSelection();return selectionSaved;
  }
  bool cycle() {
    if(!selection.cycle(bool(areas[0]),bool(areas[1]))) return false;
    saveSelection();Serial.printf("MAP SELECTED %u mode=%s\n",selected(),automatic()?"AUTO":"MANUAL");return true;
  }
  bool importing() const {return bool(upload);}
  void begin(bool storageReady) {
    ready=storageReady;
    if(!ready) return;
    LittleFS.remove("/map-upload.tmp");
    for(unsigned i=0;i<2;++i) {char name[24];path(name,i);areas[i]=load(name);}
    selection.available(bool(areas[0]),bool(areas[1]));
    selectionStorage=preferences.begin("ku_map",false);
    if(selectionStorage && preferences.getBytesLength("selection")==sizeof(WatchMap::SavedSelection)) {
      WatchMap::SavedSelection saved;
      if(preferences.getBytes("selection",&saved,sizeof(saved))==sizeof(saved)) {
        selectionRestored=selection.restore(saved,bool(areas[0]),bool(areas[1]));
        selectionSaved=selectionRestored && selected()==saved.area;
      }
    }
    if(!selectionSaved) saveSelection();
    report();
  }
  bool tick(bool fix,double lat,double lon) {
    if(upload && uint32_t(millis()-lastData_)>15000) {abort();error("UPLOAD TIMEOUT");}
    if(!fix) return false;
    if(!selection.follow(WatchMap::covers(areas[0],lat,lon),WatchMap::covers(areas[1],lat,lon))) return false;
    saveSelection();return true;
  }
  void abort() {upload.close(); if(ready) LittleFS.remove("/map-upload.tmp"); received_=0;}
  void report() {
    Serial.printf("MAP STATUS selected=%u importing=%u psram=%u free_psram=%u mode=%s selection_storage=%u selection_saved=%u restored=%u\n",selected(),importing(),ESP.getPsramSize(),ESP.getFreePsram(),automatic()?"AUTO":"MANUAL",selectionStorage,selectionSaved,selectionRestored);
    for(unsigned i=0;i<2;++i) {
      const auto* d=areas[i];
      if(d) Serial.printf("MAP AREA %u name=%s lat=%.7f lon=%.7f radius=%lu features=%u points=%u payload_crc=%08lx\n",
        i,d->header.name,d->header.latitudeE7/1e7,d->header.longitudeE7/1e7,(unsigned long)d->header.radius,
        d->header.features,d->header.points,(unsigned long)d->header.payloadCrc);
      else Serial.printf("MAP AREA %u EMPTY\n",i);
    }
  }
  bool command(const char* line,bool busy) {
    if(strncmp(line,"MAP",3)) return false;
    if(!strcmp(line,"MAPINFO")) report();
    else if(!strcmp(line,"MAPCYCLE")) {if(!cycle()) error("AREA EMPTY");}
    else if(!strcmp(line,"MAPAUTO")) {
      if(selection.autoMode() || !selectionSaved) saveSelection();
      Serial.printf("MAP SELECTED %u mode=AUTO\n",selected());
    }
    else if(!strcmp(line,"MAPABORT")) {abort();Serial.println("MAP ABORTED");}
    else if(!strncmp(line,"MAPAREA ",8)) {
      if(!strcmp(line+8,"0") || !strcmp(line+8,"1")) {
        unsigned n=line[8]-'0'; if(areas[n]) {if(selection.manual(n,bool(areas[0]),bool(areas[1])) || !selectionSaved) saveSelection();Serial.printf("MAP SELECTED %u mode=MANUAL\n",n);} else error("AREA EMPTY");
      } else error("AREA USE 0 OR 1");
    }
    else if(!strncmp(line,"MAPBEGIN ",9)) {
      unsigned n; unsigned long size,crc; char extra;
      if(busy || upload) error("STOP RECORDING OR EXPORT FIRST");
      else if(!ready || !ESP.getPsramSize()) error("STORAGE OR PSRAM UNAVAILABLE");
      else if(sscanf(line+9,"%u %lu %lx %c",&n,&size,&crc,&extra)!=3 || n>1 || size<64 || size>WatchMap::MAX_BYTES) error("INVALID HEADER");
      else if(LittleFS.totalBytes()-LittleFS.usedBytes()<size+65536) error("STORAGE FULL");
      else {
        upload=LittleFS.open("/map-upload.tmp",FILE_WRITE);
        if(!upload) error("OPEN FAILED");
        else {slot_=n;expected_=size;expectedCrc_=crc;received_=0;crc_=0xffffffffu;lastData_=millis();Serial.println("MAP READY 0");}
      }
    }
    else if(!strncmp(line,"MAPDATA ",8)) {
      char* end=nullptr; unsigned long offset=strtoul(line+8,&end,10);
      if(!upload || end==line+8 || *end!=' ' || offset!=received_) error("INVALID OFFSET");
      else {
        const char* s=end+1;size_t len=strlen(s);uint8_t bytes[96];bool ok=len>0 && !(len%2) && len<=sizeof(bytes)*2;
        if(ok) for(size_t i=0;i<len/2;++i) {int a=hex(s[i*2]),b=hex(s[i*2+1]);if(a<0 || b<0) {ok=false;break;}bytes[i]=(a<<4)|b;}
        if(!ok || received_+len/2>expected_) {abort();error("INVALID DATA");}
        else if(upload.write(bytes,len/2)!=len/2) {abort();error("WRITE FAILED");}
        else {received_+=len/2;crc_=Activity::crcUpdate(crc_,bytes,len/2);lastData_=millis();Serial.printf("MAP ACK %lu\n",(unsigned long)received_);}
      }
    }
    else if(!strcmp(line,"MAPEND")) {
      if(!upload || received_!=expected_ || ~crc_!=expectedCrc_) {abort();error("INCOMPLETE OR CRC");}
      else {
        upload.flush();upload.close();auto* d=load("/map-upload.tmp");
        if(!d) {abort();error("INVALID PACK OR MEMORY");}
        else {
          char name[24];path(name,slot_);
          if(!LittleFS.rename("/map-upload.tmp",name)) {free(d);abort();error("COMMIT FAILED");}
          else {free(areas[slot_]);areas[slot_]=d;selection.area=slot_;saveSelection();Serial.printf("MAP SAVED %u %lu %08lx\n",slot_,(unsigned long)received_,(unsigned long)expectedCrc_);}
        }
      }
    }
    else error("UNKNOWN COMMAND");
    return true;
  }
};
