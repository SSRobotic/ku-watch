#pragma once
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <mqtt_client.h>
#include <esp_timer.h>
#include <esp_netif.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>
#include <time.h>
#include "config.h"
#include "cloud_settings.h"
#include "telemetry_store.h"
#include "telemetry_window.h"
#include "runtime_settings.h"
#include "sensor_log.h"
// Arduino's bundle helper is linked by WiFiClientSecure, but its public class
// header does not declare these C entry points used by ESP-MQTT.
extern "C" esp_err_t arduino_esp_crt_bundle_attach(void* conf);
extern "C" void arduino_esp_crt_bundle_set(const uint8_t* bundle);

// Capture, display and I2C stay on loop(). This worker owns the telemetry
// journal and transport. Only PUBACK advances the journal; no flash work on
// the sampling loop. LittleFS VFS locks each shared-partition operation.
namespace LiveNetwork {
struct Sample {char json[2560];uint64_t token=0;uint32_t capturedMs=0;};
struct Status {
  bool wifi=false,mqtt=false,storage=false;
  int error=0,rssi=0,tlsError=0,socketError=0,errorType=0,dnsFallback=-1;
  uint32_t sent=0,pending=0,dropped=0,errors=0,maxWriteUs=0,freeBytes=0,maxMqttUs=0;
  unsigned encoded=0,ingress=0;
};
struct Event {esp_mqtt_event_id_t type;int id,error,tlsError=0,socketError=0,errorType=0;};
inline QueueHandle_t samples=nullptr,statuses=nullptr,events=nullptr,settingsQueue=nullptr;
struct Diagnostic {char json[512];uint32_t createdMs;};
inline QueueHandle_t diagnostics=nullptr;
inline WatchExt::Settings initialSettings;
inline SensorLog sensorLog;
inline TelemetryStore journal;
inline uint32_t ingressDropped=0,session=0;
inline uint32_t pauseUntil=0;
extern const uint8_t caBundle[] asm("_binary_tools_certs_x509_crt_bundle_start");
inline esp_err_t event(esp_mqtt_event_handle_t e) {
  Event next{e->event_id,e->msg_id,0};
  if(e->event_id==MQTT_EVENT_ERROR && e->error_handle) {
    next.error=e->error_handle->error_type==MQTT_ERROR_TYPE_CONNECTION_REFUSED?
      int(e->error_handle->connect_return_code):int(e->error_handle->esp_tls_last_esp_err);
    next.tlsError=e->error_handle->esp_tls_stack_err;
    next.socketError=e->error_handle->esp_transport_sock_errno;
    next.errorType=e->error_handle->error_type;
  }
  if(e->event_id==MQTT_EVENT_CONNECTED || e->event_id==MQTT_EVENT_DISCONNECTED ||
     e->event_id==MQTT_EVENT_PUBLISHED || e->event_id==MQTT_EVENT_ERROR || e->event_id==MQTT_EVENT_DELETED)
    xQueueSend(events,&next,pdMS_TO_TICKS(10)); // timeout will retry a missed PUBACK
  return ESP_OK;
}
inline void pause(unsigned seconds) {
  __atomic_store_n(&pauseUntil,seconds?millis()+seconds*1000u:0u,__ATOMIC_RELAXED);
}
inline bool configure(const WatchExt::Settings& settings) {
  return settingsQueue && xQueueOverwrite(settingsQueue,&settings)==pdTRUE;
}
inline void run(void*) {
  WatchExt::Settings settings=initialSettings;
  WatchExt::Backoff wifiRetry,mqttRetry;wifiRetry.reset(millis());mqttRetry.reset(millis());
  char id[40],topic[160],online[100],offline[100];
  snprintf(id,sizeof(id),"ku-watch-%llx",ESP.getEfuseMac());
  snprintf(topic,sizeof(topic),"%s/status",MQTT_TOPIC);
  snprintf(online,sizeof(online),"{\"online\":true,\"device\":\"%s\",\"version\":\"%s\"}",id,WatchExt::VERSION);
  snprintf(offline,sizeof(offline),"{\"online\":false,\"device\":\"%s\",\"version\":\"%s\"}",id,WatchExt::VERSION);
  arduino_esp_crt_bundle_set(caBundle);
  esp_mqtt_client_config_t config{};
  config.host=settings.host;
  config.port=settings.port;
  config.transport=settings.tls?MQTT_TRANSPORT_OVER_SSL:MQTT_TRANSPORT_OVER_TCP;
  config.username=settings.user;
  config.password=settings.mqttPassword;
  if(!config.username[0]) {config.username=nullptr;config.password=nullptr;}
  config.client_id=id;config.event_handle=event;
  config.crt_bundle_attach=settings.tls?arduino_esp_crt_bundle_attach:nullptr;
  config.lwt_topic=topic;config.lwt_msg=offline;config.lwt_qos=1;config.lwt_retain=1;
  config.keepalive=30;config.buffer_size=3072;config.task_stack=8192;
  config.network_timeout_ms=10000;config.reconnect_timeout_ms=10000;
  config.disable_auto_reconnect=true;
  config.message_retransmit_timeout=3000;config.protocol_ver=MQTT_PROTOCOL_V_3_1_1;
  esp_mqtt_client_handle_t client=nullptr;
  snprintf(topic,sizeof(topic),"%s/status",settings.topic);
  WiFi.setAutoReconnect(false);WiFi.setSleep(false);if(settings.ssid[0])WiFi.begin(settings.ssid,settings.password);
  sensorLog.configure(settings.logging);
  uint32_t wifiAt=millis(),lastSend=0;
  bool ntpStarted=false,paused=false,dnsConfigured=false;
  TelemetryWindow flights;bool rebuildOutbox=false;
  Sample sample;
  Status status;
  for(;;) {
    uint32_t now=millis(),until=__atomic_load_n(&pauseUntil,__ATOMIC_RELAXED);
    WatchExt::Settings changed;
    if(xQueueReceive(settingsQueue,&changed,0)==pdTRUE) {
      bool reconnect=strcmp(settings.ssid,changed.ssid)||strcmp(settings.password,changed.password)||strcmp(settings.host,changed.host)||
        strcmp(settings.user,changed.user)||strcmp(settings.mqttPassword,changed.mqttPassword)||strcmp(settings.topic,changed.topic)||
        settings.port!=changed.port || settings.tls!=changed.tls;
      if(!reconnect) {settings=changed;sensorLog.configure(settings.logging);}
      else {
      if(client) {esp_mqtt_client_stop(client);esp_mqtt_client_destroy(client);client=nullptr;}
      settings=changed;flights.clear();status.mqtt=false;ntpStarted=false;dnsConfigured=false;xQueueReset(events);
      config.host=settings.host;config.port=settings.port;config.transport=settings.tls?MQTT_TRANSPORT_OVER_SSL:MQTT_TRANSPORT_OVER_TCP;
      config.username=settings.user[0]?settings.user:nullptr;config.password=settings.user[0]?settings.mqttPassword:nullptr;
      config.crt_bundle_attach=settings.tls?arduino_esp_crt_bundle_attach:nullptr;
      snprintf(topic,sizeof(topic),"%s/status",settings.topic);sensorLog.configure(settings.logging);
      WiFi.disconnect(false,false);if(settings.ssid[0])WiFi.begin(settings.ssid,settings.password);
      wifiRetry.reset(now);mqttRetry.reset(now);wifiAt=now;
      }
    }
    if(xQueueReceive(samples,&sample,0)==pdTRUE) {
      uint64_t before=esp_timer_get_time();
      journal.append(sample.json,sample.token,sample.capturedMs);
      status.maxWriteUs=max(status.maxWriteUs,uint32_t(esp_timer_get_time()-before));
      status.freeBytes=LittleFS.totalBytes()-LittleFS.usedBytes();
      sensorLog.append(sample.json,sample.capturedMs,journal.ready);
    }
    bool shouldPause=until && int32_t(until-now)>0;
    if(shouldPause && !paused) {WiFi.disconnect(false,false);paused=true;}
    if(!shouldPause && paused) {if(settings.ssid[0])WiFi.begin(settings.ssid,settings.password);wifiAt=now;paused=false;wifiRetry.reset(now);}
    status.wifi=!paused && WiFi.status()==WL_CONNECTED;
    status.rssi=status.wifi?WiFi.RSSI():0;
    if(!status.wifi) {
      status.mqtt=false;
      dnsConfigured=false;
      if(!paused && settings.ssid[0] && uint32_t(now-wifiAt)>=5000 && wifiRetry.due(now)) {WiFi.reconnect();wifiRetry.failed(now);}
    } else {
      wifiRetry.reset(now);
      if(!dnsConfigured) {
        // Keep the DHCP main/backup resolvers. The third slot is not replaced
        // by a DHCP lease and recovers when a hotspot DNS forwarder fails.
        auto* station=esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
        esp_netif_dns_info_t fallback{};
        fallback.ip.type=ESP_IPADDR_TYPE_V4;
        fallback.ip.u_addr.ip4.addr=uint32_t(IPAddress(1,1,1,1));
        status.dnsFallback=station?esp_netif_set_dns_info(station,ESP_NETIF_DNS_FALLBACK,&fallback):ESP_ERR_INVALID_STATE;
        dnsConfigured=status.dnsFallback==ESP_OK;
      }
      if(!ntpStarted) {configTime(0,0,"pool.ntp.org","time.google.com");ntpStarted=true;}
      if(!client && config.host[0] && mqttRetry.due(now) && (!settings.tls || time(nullptr)>=1704067200)) {
        client=esp_mqtt_client_init(&config);
        if(client && esp_mqtt_client_start(client)!=ESP_OK) {esp_mqtt_client_destroy(client);client=nullptr;status.error=-1;}
        mqttRetry.failed(now);
      }
      if(client && !status.mqtt && mqttRetry.due(now)) {esp_mqtt_client_reconnect(client);mqttRetry.failed(now);}
    }
    Event e;
    while(xQueueReceive(events,&e,0)==pdTRUE) {
      if(e.type==MQTT_EVENT_CONNECTED) {
        mqttRetry.reset(now);
        status.mqtt=status.wifi;status.error=0;status.tlsError=0;status.socketError=0;status.errorType=0;
        // Keep the status announcement on the MQTT task as well. A direct
        // publish can wait for the socket while the durable ingress fills.
        if(client) esp_mqtt_client_enqueue(client,topic,online,0,1,1,true);
      } else if(e.type==MQTT_EVENT_DISCONNECTED) {status.mqtt=false;mqttRetry.failed(now);}
      else if(e.type==MQTT_EVENT_ERROR) {
        status.error=e.error;status.mqtt=false;status.tlsError=e.tlsError;
        status.socketError=e.socketError;status.errorType=e.errorType;
        Serial.printf("MQTT ERROR code=%d type=%d tls=%d socket=%d\n",e.error,e.errorType,e.tlsError,e.socketError);
      }
      else if(e.type==MQTT_EVENT_PUBLISHED) flights.acknowledge(e.id);
      else if(e.type==MQTT_EVENT_DELETED && flights.contains(e.id)) rebuildOutbox=true;
    }
    while(uint64_t acknowledged=flights.ready()) {
      if(!journal.ack(acknowledged)){status.error=-3;break;}
      ++status.sent;flights.retire();
    }
    // Rebuild an expired/stuck MQTT outbox; the flash record is still present.
    if(client && (rebuildOutbox || flights.expired(now))) {
      uint64_t transportAt=esp_timer_get_time();
      esp_mqtt_client_stop(client);esp_mqtt_client_destroy(client);client=nullptr;
      status.maxMqttUs=max(status.maxMqttUs,uint32_t(esp_timer_get_time()-transportAt));
      flights.clear();rebuildOutbox=false;status.mqtt=false;
      xQueueReset(events);
    }
    // Fill the bounded flight window between journal writes. A slow flash
    // append must not limit backlog recovery to one publication per loop.
    // Stop the burst after a slow enqueue so socket mutex waits do not stack.
    uint32_t burstTransportUs=0;
    bool sendDue=uint32_t(now-lastSend)>=100;
    while(sendDue && status.mqtt && client && !flights.full() && journal.pending>flights.size() &&
       journal.peekAt(flights.size(),sample.json,sizeof(sample.json),sample.token,sample.capturedMs)) {
      lastSend=now;
      bool backfill=uint32_t(sample.token>>32)!=session || uint32_t(now-sample.capturedMs)>3000;
      size_t length=strlen(sample.json);
      if(!length || sample.json[length-1]!='}' || length+24>=sizeof(sample.json)) {status.error=-2;break;}
      snprintf(sample.json+length-1,sizeof(sample.json)-length+1,",\"backfill\":%s}",backfill?"true":"false");
      // Copy into MQTT's outbox without waiting for network I/O on this worker.
      uint64_t transportAt=esp_timer_get_time();
      int packet=esp_mqtt_client_enqueue(client,settings.topic,sample.json,0,1,0,true);
      uint32_t transportUs=uint32_t(esp_timer_get_time()-transportAt);
      status.maxMqttUs=max(status.maxMqttUs,transportUs);burstTransportUs+=transportUs;
      if(packet<0 || !flights.push(sample.token,packet,now))break;
      if(burstTransportUs>=10000)break;
    }
    // Explicit test observations have a separate, non-retained MQTT topic and
    // never enter the real-data journal/CSV or the cumulative soak subscription.
    Diagnostic diagnostic;
    if(status.mqtt && client && diagnostics && xQueueReceive(diagnostics,&diagnostic,0)==pdTRUE &&
       uint32_t(millis()-diagnostic.createdMs)<5000) {
      char diagnosticTopic[160];snprintf(diagnosticTopic,sizeof(diagnosticTopic),"%s/test/alerts",settings.topic);
      esp_mqtt_client_enqueue(client,diagnosticTopic,diagnostic.json,0,1,0,true);
    }
    status.storage=journal.ready;status.pending=journal.pending;status.errors=journal.errors;
    status.dropped=journal.dropped+__atomic_load_n(&ingressDropped,__ATOMIC_RELAXED);
    status.encoded=journal.largestEncoded;status.ingress=uxQueueMessagesWaiting(samples);
    xQueueOverwrite(statuses,&status);vTaskDelay(pdMS_TO_TICKS(20));
  }
}
inline bool begin(bool storageReady,uint32_t bootSession,const WatchExt::Settings& settings) {
  initialSettings=settings;
  journal.begin(storageReady);journal.report();session=bootSession;
  // A socket recovery can exceed eight 1-Hz capture intervals. This bounded
  // RAM buffer covers 32 seconds while the worker resumes its flash journal.
  samples=xQueueCreate(32,sizeof(Sample));statuses=xQueueCreate(1,sizeof(Status));
  events=xQueueCreate(32,sizeof(Event));
  settingsQueue=xQueueCreate(1,sizeof(WatchExt::Settings));
  diagnostics=xQueueCreate(8,sizeof(Diagnostic));
  if(samples && statuses && events && settingsQueue && diagnostics && xTaskCreatePinnedToCore(run,"ku-network",12288,nullptr,1,nullptr,0)==pdPASS)return true;
  for(auto q:{samples,statuses,events,settingsQueue,diagnostics})if(q)vQueueDelete(q);
  samples=statuses=events=settingsQueue=diagnostics=nullptr;return false;
}
inline bool publishDiagnostic(const char* json) {
  if(!json || strlen(json)>=sizeof(Diagnostic::json))return false;
  Diagnostic item{};strlcpy(item.json,json,sizeof(item.json));item.createdMs=millis();
  return diagnostics && xQueueSend(diagnostics,&item,0)==pdTRUE;
}
inline bool capture(const Sample& sample) {
  if(samples && xQueueSend(samples,&sample,0)==pdTRUE)return true;
  __atomic_fetch_add(&ingressDropped,1u,__ATOMIC_RELAXED);return false;
}
inline void report(const Status& s) {
  Serial.printf("NETDNS fallback_result=%d main=%s backup=%s fallback=%s error_type=%d tls=%d socket=%d\n",
    s.dnsFallback,WiFi.dnsIP(0).toString().c_str(),WiFi.dnsIP(1).toString().c_str(),WiFi.dnsIP(2).toString().c_str(),s.errorType,s.tlsError,s.socketError);
  Serial.printf("QUEUE ready=%u pending=%lu acked=%lu dropped=%lu errors=%lu max_encoded=%u capacity=%u reserve=%u\n",
    s.storage,(unsigned long)s.pending,(unsigned long)s.sent,(unsigned long)s.dropped,(unsigned long)s.errors,s.encoded,Telemetry::MAX_PENDING,unsigned(TelemetryStore::RESERVE));
  Serial.printf("QUEUE write_max_us=%lu mqtt_call_max_us=%lu ingress=%u ingress_capacity=32 free=%lu\n",(unsigned long)s.maxWriteUs,(unsigned long)s.maxMqttUs,s.ingress,(unsigned long)s.freeBytes);
}
}
