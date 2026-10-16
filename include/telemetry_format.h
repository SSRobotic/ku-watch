#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "activity_format.h"

namespace Telemetry {
// Append-only dictionary: a token represents a complete JSON key, including
// its quotes and colon. Values remain byte-for-byte identical to capture.
inline constexpr const char* keys[]={
  "temp","humidity","pressure","bpm","spo2","spo2_status","spo2_quality","spo2_valid",
  "gas_ohms","iaq","iaq_accuracy","iaq_valid","iaq_stable","iaq_run_in","bsec_status",
  "battery_voltage","battery_percent","battery_valid","ina226_detected","ir","red","finger",
  "pulse_live","env_live","acc_live","mag_live","acc_x","acc_y","acc_z","mag_x","mag_y","mag_z",
  "gps_fix","gps_raw_fix","latitude","longitude","altitude","speed_kmh","satellites","satellites_view",
  "gps_signal","gps_data","gps_hdop","gps_age_s","gps_chars","gps_checksum_errors","recording",
  "elapsed_s","distance_m","activity_id","uptime_ms","wifi_rssi","heap_free","storage_free",
  "record_samples","mqtt_sent","timestamp","device","sample_id",
  "alert_temp_state","alert_iaq_state","alert_mask","alert_temp_limit","alert_iaq_limit",
  "battery_current_ma","battery_power_mw","current_valid","heading","espnow_online",
  "alert_battery_state","battery_low","firmware"
};
constexpr size_t KEY_COUNT=sizeof(keys)/sizeof(keys[0]);
constexpr unsigned SEGMENT_RECORDS=64, MAX_PENDING=768;
#pragma pack(push,1)
struct Record {
  uint32_t magic=0x3151544b; // KTQ1, version includes dictionary
  uint16_t size=0, reserved=0;
  uint64_t token=0;
  uint32_t capturedMs=0;
  uint8_t bytes[744]={};
  uint32_t crc=0;
};
#pragma pack(pop)
static_assert(sizeof(Record)==768,"fixed journal slot");
inline bool encode(const char* json,uint64_t token,Record& r,uint32_t capturedMs=0) {
  r=Record{};r.token=token;r.capturedMs=capturedMs;
  if(!json || !token) return false;
  for(size_t i=0;json[i];) {
    uint8_t c=uint8_t(json[i]);
    if(c>=128) return false; // current firmware emits ASCII JSON only
    size_t matched=KEY_COUNT;
    if(c=='"' && (i==1 || json[i-1]==',')) {
      for(size_t k=0;k<KEY_COUNT;++k) {
        size_t n=strlen(keys[k]);
        if(!strncmp(json+i+1,keys[k],n) && json[i+n+1]=='"' && json[i+n+2]==':') {matched=k;break;}
      }
    }
    if(r.size==sizeof(r.bytes)) return false;
    if(matched<KEY_COUNT) {r.bytes[r.size++]=128+matched;i+=strlen(keys[matched])+3;}
    else {r.bytes[r.size++]=c;++i;}
  }
  r.crc=Activity::crc32(&r,offsetof(Record,crc));return r.size>0;
}
inline bool valid(const Record& r) {
  return r.magic==0x3151544b && !r.reserved && r.token && r.size && r.size<=sizeof(r.bytes)
    && r.crc==Activity::crc32(&r,offsetof(Record,crc));
}
inline bool decode(const Record& r,char* json,size_t capacity) {
  if(!valid(r) || !json || !capacity) return false;
  size_t at=0;
  for(unsigned i=0;i<r.size;++i) {
    unsigned c=r.bytes[i];
    if(c>=128) {
      if(c-128>=KEY_COUNT) return false;
      const char* key=keys[c-128];size_t n=strlen(key);
      if(at+n+3>=capacity) return false;
      json[at++]='"';memcpy(json+at,key,n);at+=n;json[at++]='"';json[at++]=':';
    } else {if(at+1>=capacity)return false;json[at++]=char(c);}
  }
  json[at]=0;return true;
}
// Only the exact in-flight token may advance the durable queue.
struct Flight {
  uint64_t token=0;
  bool start(uint64_t next) {if(token || !next)return false;token=next;return true;}
  bool acknowledged(uint64_t ack) {if(!token || ack!=token)return false;token=0;return true;}
};
}
