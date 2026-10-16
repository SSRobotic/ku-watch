#pragma once
#include <Arduino.h>
#include <Preferences.h>
#include "config.h"
#include "cloud_settings.h"
#include "watch_extensions.h"

class RuntimeSettings {
  Preferences prefs;
public:
  WatchExt::Settings value;
  bool ready=false,restored=false;
  String apPassword;
  void begin() {
    strlcpy(value.ssid,WIFI_SSID,sizeof(value.ssid));strlcpy(value.password,WIFI_PASSWORD,sizeof(value.password));
    strlcpy(value.host,KU_CLOUD_ENABLED?KU_CLOUD_HOST:MQTT_HOST,sizeof(value.host));
    strlcpy(value.user,KU_CLOUD_ENABLED?KU_CLOUD_USER:MQTT_USER,sizeof(value.user));
    strlcpy(value.mqttPassword,KU_CLOUD_ENABLED?KU_CLOUD_PASSWORD:MQTT_PASSWORD,sizeof(value.mqttPassword));
    strlcpy(value.topic,MQTT_TOPIC,sizeof(value.topic));value.port=KU_CLOUD_ENABLED?8883:MQTT_PORT;value.tls=KU_CLOUD_ENABLED;
    ready=prefs.begin("ku-runtime2",false);
    if(ready && prefs.getBytesLength("settings")==sizeof(value)) {
      WatchExt::Settings saved; if(prefs.getBytes("settings",&saved,sizeof(saved))==sizeof(saved)&&WatchExt::intact(saved)) {
        value=saved;restored=true;
      }
    }
    if(ready)apPassword=prefs.getString("apkey","");
    if(apPassword.length()!=12) {
      char p[13];snprintf(p,sizeof(p),"%08lx%04x",(unsigned long)esp_random(),unsigned(esp_random()&0xffff));apPassword=p;
    }
    // The round-screen font has uppercase glyphs. Keep the actual WPA2/login
    // credential uppercase too, so what the user reads is exactly what works.
    apPassword.toUpperCase();if(ready)prefs.putString("apkey",apPassword);
    Serial.printf("SETTINGS ready=%u restored=%u version=%s\n",ready,restored,WatchExt::VERSION);
  }
  bool save(WatchExt::Settings next) {
    if(!ready || !WatchExt::valid(next))return false;
    WatchExt::seal(next);if(prefs.putBytes("settings",&next,sizeof(next))!=sizeof(next))return false;
    value=next;return true;
  }
};
