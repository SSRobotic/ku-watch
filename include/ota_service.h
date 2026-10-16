#pragma once
#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <Update.h>
#include <esp_ota_ops.h>
#include <mbedtls/sha256.h>
#include <atomic>
#include "runtime_settings.h"
#include "ota_local_ca.h"

class OtaService {
  inline static OtaService* owner=nullptr;
  char url[193]={};
  uint32_t next=0;
  std::atomic<bool> requested{false},allowed{false},running{false};
  std::atomic<float> battery{0};
  portMUX_TYPE urlMux=portMUX_INITIALIZER_UNLOCKED;
  static String field(const String& json,const char* key) {
    String needle=String("\"")+key+"\"";int p=json.indexOf(needle);if(p<0)return "";
    p=json.indexOf(':',p+needle.length());if(p<0)return "";++p;
    while(p<int(json.length())&&isspace(json[p]))++p;
    if(json[p]!='"')return "";int end=json.indexOf('"',p+1);return end<0?String():json.substring(p+1,end);
  }
  static bool newer(const String& s) {
    unsigned a,b,c,x,y,z;char tail;
    if(sscanf(s.c_str(),"%u.%u.%u%c",&a,&b,&c,&tail)!=3 || a>999||b>999||c>999)return false;
    sscanf(WatchExt::VERSION,"%u.%u.%u",&x,&y,&z);return a*1000000+b*1000+c>x*1000000+y*1000+z;
  }
  bool update() {
    char currentUrl[193];portENTER_CRITICAL(&urlMux);strlcpy(currentUrl,url,sizeof(currentUrl));portEXIT_CRITICAL(&urlMux);
    if(!allowed || battery<30 || WiFi.status()!=WL_CONNECTED || time(nullptr)<1704067200 || strncmp(currentUrl,"https://",8))return false;
    Serial.printf("OTA AUTO CHECK version=%s\n",WatchExt::VERSION);
    WiFiClientSecure tls;
    if(!strncmp(currentUrl,LocalOta::PREFIX,strlen(LocalOta::PREFIX)))tls.setCACert(LocalOta::CA);
    else tls.setCACertBundle(caBundle());
    HTTPClient http;http.setTimeout(5000);
    if(!http.begin(tls,currentUrl))return false;
    int status=http.GET();Serial.printf("OTA MANIFEST HTTP status=%d\n",status);
    if(status!=200 || http.getSize()>2048) {http.end();return false;}
    String manifest=http.getString();http.end();
    String version=field(manifest,"version"),binary=field(manifest,"url"),sha=field(manifest,"sha256");
    if(!newer(version)) {Serial.println("OTA NO NEW VERSION");return false;}
    if(!binary.startsWith("https://")||sha.length()!=64)return false;
    for(unsigned i=0;i<64;++i)if(!isxdigit(sha[i]))return false;
    WiFiClientSecure binaryTls;
    if(binary.startsWith(LocalOta::PREFIX))binaryTls.setCACert(LocalOta::CA);
    else binaryTls.setCACertBundle(caBundle());
    if(!http.begin(binaryTls,binary))return false;
    status=http.GET();int size=http.getSize();
    auto target=esp_ota_get_next_update_partition(nullptr);
    if(status!=200 || size<1024 || !target || size>int(target->size) || !allowed || battery<30) {http.end();return false;}
    // Write directly to the inactive partition. SHA is checked BEFORE selecting it for boot.
    esp_ota_handle_t handle;
    if(esp_ota_begin(target,size,&handle)!=ESP_OK) {http.end();return false;}
    mbedtls_sha256_context hash;mbedtls_sha256_init(&hash);mbedtls_sha256_starts_ret(&hash,0);
    uint8_t buffer[1024];int remaining=size;uint32_t progress=millis();bool ok=true;
    auto stream=http.getStreamPtr();
    while(remaining>0 && ok) {
      if(!allowed || battery<30) {ok=false;break;}
      int n=stream->readBytes(buffer,min(int(sizeof(buffer)),remaining));
      if(n>0) {progress=millis();ok=esp_ota_write(handle,buffer,n)==ESP_OK;mbedtls_sha256_update_ret(&hash,buffer,n);remaining-=n;}
      else if(!http.connected()||uint32_t(millis()-progress)>10000)ok=false;
      vTaskDelay(pdMS_TO_TICKS(1));
    }
    uint8_t digest[32];mbedtls_sha256_finish_ret(&hash,digest);mbedtls_sha256_free(&hash);http.end();
    char actual[65];for(unsigned i=0;i<32;++i)snprintf(actual+i*2,3,"%02x",digest[i]);
    ok=ok && !remaining && sha.equalsIgnoreCase(actual);
    if(!ok) {esp_ota_abort(handle);Serial.println("OTA DOWNLOAD OR HASH FAILED; OLD APP KEPT");return false;}
    if(esp_ota_end(handle)!=ESP_OK || esp_ota_set_boot_partition(target)!=ESP_OK)return false;
    Serial.printf("OTA VERIFIED version=%s sha256=%s; RESTARTING\n",version.c_str(),actual);delay(300);ESP.restart();return true;
  }
  static const uint8_t* caBundle() {extern const uint8_t bundle[] asm("_binary_tools_certs_x509_crt_bundle_start");return bundle;}
  static void task(void*) {
    for(;;) {
      if(owner->requested) {owner->requested=false;owner->running=true;bool ok=owner->update();owner->running=false;if(!ok)Serial.println("OTA CHECK COMPLETE OR DEFERRED");}
      vTaskDelay(pdMS_TO_TICKS(250));
    }
  }
public:
  bool confirmed=false;
  void begin(const char* manifest) {
    owner=this;strlcpy(url,manifest,sizeof(url));next=millis()+60000;
    xTaskCreatePinnedToCore(task,"ku-ota",12288,nullptr,1,nullptr,0);
  }
  bool busy() const {return running;}
  void configure(const char* manifest) {portENTER_CRITICAL(&urlMux);strlcpy(url,manifest,sizeof(url));portEXIT_CRITICAL(&urlMux);next=millis()+10000;}
  void check() {if(!running)requested=true;}
  void tick(bool idle,bool batteryValid,float percent,bool healthy) {
    battery=batteryValid?percent:0;allowed=idle && batteryValid && percent>=30;
    if(!confirmed && millis()>15000 && healthy) {
      esp_ota_img_states_t state;
      auto current=esp_ota_get_running_partition();
      if(esp_ota_get_state_partition(current,&state)!=ESP_OK || state!=ESP_OTA_IMG_PENDING_VERIFY ||
         esp_ota_mark_app_valid_cancel_rollback()==ESP_OK) {confirmed=true;Serial.println("OTA BOOT HEALTH CONFIRMED");}
    }
    if(!confirmed && millis()>60000) {Serial.println("OTA BOOT HEALTH FAILED");esp_ota_mark_app_invalid_rollback_and_reboot();}
    if(url[0] && int32_t(millis()-next)>=0) {next=millis()+86400000u;check();}
  }
  void report() const {
    auto current=esp_ota_get_running_partition();auto target=esp_ota_get_next_update_partition(nullptr);
    esp_ota_img_states_t image=ESP_OTA_IMG_UNDEFINED;esp_ota_get_state_partition(current,&image);
    Serial.printf("OTA version=%s current=%s next=%s state=%u confirmed=%u busy=%u server_configured=%u battery_allowed=%u\n",
      WatchExt::VERSION,current?current->label:"none",target?target->label:"none",unsigned(image),confirmed,running.load(),url[0]!=0,allowed.load());
  }
};
