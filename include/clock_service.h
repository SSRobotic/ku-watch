#pragma once
#include <Arduino.h>
#include <Preferences.h>
#include <esp_timer.h>
#include <esp_sntp.h>
#include <sys/time.h>
#include <time.h>
#include "clock_model.h"

class ClockService {
  Preferences storage;
  bool ready=false;
  uint64_t savedUtc=0,lastSyncUtc=0;
  uint32_t savedAt=0,gpsAt=0;
  inline static uint32_t networkRevision=0;
  uint32_t consumedRevision=0;
  static void networkSync(struct timeval*) {__atomic_fetch_add(&networkRevision,1u,__ATOMIC_RELAXED);}
  void persist(bool force=false) {
    if(!ready || !model.live)return;
    uint64_t value=utc();
    if(savedUtc && !force && uint32_t(millis()-savedAt)<300000)return;
    auto saved=ClockModel::checkpoint(value);
    if(storage.putBytes("utc",&saved,sizeof(saved))==sizeof(saved)){savedUtc=value;savedAt=millis();}
  }
public:
  ClockModel::Model model;
  void begin(uint64_t build) {
    ready=storage.begin("ku-clock2",false);ClockModel::Saved saved;
    bool loaded=ready && storage.getBytesLength("utc")==sizeof(saved) && storage.getBytes("utc",&saved,sizeof(saved))==sizeof(saved) && ClockModel::intact(saved);
    model.begin(build,uint64_t(time(nullptr)),loaded?&saved:nullptr,esp_timer_get_time());
    if(loaded)savedUtc=saved.utc;savedAt=millis();
    sntp_set_time_sync_notification_cb(networkSync);
    sntp_set_sync_interval(15*60*1000);
    if(model.live)persist(true);
  }
  uint64_t utc() const {
    uint64_t value=uint64_t(time(nullptr));
    return model.live && ClockModel::valid(value)?value:model.utc(esp_timer_get_time());
  }
  void set(uint64_t value,ClockModel::Source source,uint32_t fractionUs=0) {
    uint64_t before=utc();bool wasLive=model.live;
    if(!model.synchronize(value,source,esp_timer_get_time()))return;
    struct timeval tv{time_t(value),suseconds_t(fractionUs%1000000)};settimeofday(&tv,nullptr);
    lastSyncUtc=value;persist(!wasLive || !savedUtc || (value>before?value-before:before-value)>30);
  }
  void gps(uint64_t value,uint32_t ageMs) {
    if(!value || ageMs>=2000)return;
    uint32_t now=millis();
    if(model.live && model.source==ClockModel::Gps && uint32_t(now-gpsAt)<60000)return;
    // GPS time stays eligible after USB/NTP time was set. It does not depend on
    // Internet, the computer or an MQTT connection.
    gpsAt=now;set(value+ageMs/1000,ClockModel::Gps,(ageMs%1000)*1000);
  }
  bool hub(uint64_t value) {
    if(!model.restoreFromHub(value,esp_timer_get_time()))return false;
    struct timeval tv{time_t(value),0};settimeofday(&tv,nullptr);
    lastSyncUtc=value;persist(true);return true;
  }
  void tick() {
    uint32_t revision=__atomic_load_n(&networkRevision,__ATOMIC_RELAXED);
    if(revision!=consumedRevision) {
      consumedRevision=revision;uint64_t value=uint64_t(time(nullptr));
      bool wasLive=model.live;uint64_t before=utc();
      if(model.synchronize(value,ClockModel::Network,esp_timer_get_time())){
        lastSyncUtc=value;persist(!wasLive || (value>before?value-before:before-value)>30);
      }
    }
    persist();
  }
  void report() const {
    Serial.printf("CLOCK utc=%llu valid=%u source=%s restored=%u sync_utc=%llu checkpoint=%llu uptime=%lu\n",
      (unsigned long long)utc(),model.live,model.label(),model.restored,(unsigned long long)lastSyncUtc,
      (unsigned long long)savedUtc,(unsigned long)millis());
  }
};
