#pragma once
#include <Arduino.h>
#include <LittleFS.h>
#include "telemetry_format.h"

// One worker owns this journal; VFS serializes access to the shared partition.
// Remove only fully acknowledged, sealed segments. A reboot may resend the
// acknowledged prefix of the final segment (QoS1 permits duplicates).
class TelemetryStore {
  uint32_t head=1,tail=1;
  unsigned readAt=0,writeAt=0;
  static void path(char* out,uint32_t id) {snprintf(out,32,"/tq%08lu.ktq",(unsigned long)id);}
  bool load(uint32_t segment,unsigned row,Telemetry::Record& r) {
    char name[32];path(name,segment);File f=LittleFS.open(name,FILE_READ);
    return f && f.seek(row*sizeof(r)) && f.read(reinterpret_cast<uint8_t*>(&r),sizeof(r))==sizeof(r) && Telemetry::valid(r);
  }
public:
  bool ready=false;
  uint32_t pending=0,dropped=0,errors=0,acknowledged=0;
  unsigned largestEncoded=0;
  static constexpr size_t RESERVE=131072;
  void begin(bool storageReady) {
    ready=storageReady;if(!ready)return;
    uint32_t first=UINT32_MAX,last=0;
    File root=LittleFS.open("/");
    for(File f=root.openNextFile();f;f=root.openNextFile()) {
      const char* n=f.name();if(*n=='/')++n;unsigned long id=0;char extra;
      if(sscanf(n,"tq%8lu.ktq%c",&id,&extra)==1 && id && id<100000000UL) {
        first=min(first,uint32_t(id));last=max(last,uint32_t(id));
      }
      f.close();
    }
    root.close();if(!last)return;
    head=first;tail=last;
    // Bounded scan protects against malformed segment names/ranges.
    if(tail-head>13) {ready=false;++errors;return;}
    for(uint32_t id=head;id<=tail;++id) {
      char name[32];path(name,id);File f=LittleFS.open(name,FILE_READ);
      if(!f) {ready=false;++errors;return;}
      size_t bytes=f.size();unsigned rows=bytes/sizeof(Telemetry::Record);f.close();
      if(rows>Telemetry::SEGMENT_RECORDS) {ready=false;++errors;return;}
      unsigned good=0;Telemetry::Record r;
      for(;good<rows;++good) {if(!load(id,good,r))break;yield();}
      // A power cut can leave only the final slot incomplete. Never erase a
      // corrupt middle record or format the partition to conceal an error.
      if(good<rows && (id!=tail || good+1<rows)) {ready=false;++errors;return;}
      if(id!=tail && (good!=Telemetry::SEGMENT_RECORDS || bytes%sizeof(r))) {ready=false;++errors;return;}
      pending+=good;if(id==tail)writeAt=good;
      if(good<rows || bytes%sizeof(r))++errors;
    }
  }
  bool append(const char* json,uint64_t token,uint32_t capturedMs=0) {
    Telemetry::Record r;
    if(!ready || pending>=Telemetry::MAX_PENDING || !Telemetry::encode(json,token,r,capturedMs)) {++dropped;return false;}
    if(LittleFS.totalBytes()-LittleFS.usedBytes()<RESERVE+sizeof(r)+4096) {++dropped;return false;}
    if(writeAt==Telemetry::SEGMENT_RECORDS) {
      if(tail==99999999UL) {++dropped;return false;}
      ++tail;writeAt=0;
    }
    char name[32];path(name,tail);
    // r+ permits overwriting an incomplete last slot after power failure.
    File f=LittleFS.open(name,LittleFS.exists(name)?"r+":FILE_WRITE);
    bool ok=f && f.seek(writeAt*sizeof(r)) && f.write(reinterpret_cast<const uint8_t*>(&r),sizeof(r))==sizeof(r);
    if(f) {f.flush();f.close();}
    if(!ok) {++errors;++dropped;ready=false;return false;}
    largestEncoded=max(largestEncoded,unsigned(r.size));++writeAt;++pending;return true;
  }
  bool peekAt(unsigned offset,char* json,size_t capacity,uint64_t& token,uint32_t& capturedMs) {
    if(!ready || offset>=pending)return false;
    unsigned row=readAt+offset;
    Telemetry::Record r;
    if(!load(head+row/Telemetry::SEGMENT_RECORDS,row%Telemetry::SEGMENT_RECORDS,r) ||
       !Telemetry::decode(r,json,capacity)) {++errors;ready=false;return false;}
    token=r.token;capturedMs=r.capturedMs;return true;
  }
  bool peek(char* json,size_t capacity,uint64_t& token,uint32_t& capturedMs) {
    return peekAt(0,json,capacity,token,capturedMs);
  }
  bool ack(uint64_t token) {
    Telemetry::Record r;
    if(!ready || !pending || !load(head,readAt,r) || r.token!=token)return false;
    if(readAt+1==Telemetry::SEGMENT_RECORDS) {
      char name[32];path(name,head);
      if(!LittleFS.remove(name)) {++errors;ready=false;return false;}
      ++head;readAt=0;
      if(head>tail) {tail=head;writeAt=0;}
    } else ++readAt;
    --pending;++acknowledged;return true;
  }
  void report() const {
    Serial.printf("QUEUE ready=%u pending=%lu acked=%lu dropped=%lu errors=%lu max_encoded=%u capacity=%u reserve=%u\n",
      ready,(unsigned long)pending,(unsigned long)acknowledged,(unsigned long)dropped,(unsigned long)errors,largestEncoded,Telemetry::MAX_PENDING,unsigned(RESERVE));
  }
};
