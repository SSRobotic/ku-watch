#pragma once
#include <Arduino.h>
#include <Preferences.h>
#include "environment_alert.h"

class AlertService {
  Preferences prefs;
public:
  EnvAlert::Model model;
  bool storage=false,loaded=false,saved=false;
  bool configure(float temperature,float iaq) {
    if(!storage || !EnvAlert::Settings::valid(temperature,iaq))return false;
    EnvAlert::Settings s;s.temperature=temperature;s.iaq=iaq;auto record=EnvAlert::save(s);
    if(prefs.putBytes("limits",&record,sizeof(record))!=sizeof(record))return false;
    model.configure(temperature,iaq);saved=true;return true;
  }
  void begin() {
    storage=prefs.begin("ku_alert",false);
    if(storage && prefs.getBytesLength("limits")==sizeof(EnvAlert::Saved)) {
      EnvAlert::Saved record;
      loaded=prefs.getBytes("limits",&record,sizeof(record))==sizeof(record) && EnvAlert::restore(record,model.settings);
    }
    saved=loaded;report();
  }
  void report() const {
    Serial.printf("ALERT temp_limit=%.2f iaq_limit=%.2f temp_state=%u iaq_state=%u mask=%u temp_count=%u iaq_count=%u storage=%u saved=%u loaded=%u\n",
      model.settings.temperature,model.settings.iaq,model.temperature.state,model.air.state,model.mask(),model.temperature.above,model.air.above,storage,saved,loaded);
  }
  bool command(const char* line) {
    if(strncmp(line,"ALERT",5))return false;
    if(!strcmp(line,"ALERTINFO"))report();
    else if(!strcmp(line,"ALERTSHOW")) {Serial.println("ALERT SHOW ENVIRONMENT");}
    else if(!strncmp(line,"ALERTSET ",9)) {
      float temp,iaq;char extra;
      if(sscanf(line+9,"%f %f %c",&temp,&iaq,&extra)!=2 || !EnvAlert::Settings::valid(temp,iaq))
        Serial.println("ALERT ERROR USE ALERTSET TEMPERATURE(-20..80) IAQ(10..500)");
      else if(!storage)Serial.println("ALERT ERROR STORAGE UNAVAILABLE");
      else {
        EnvAlert::Settings requested;requested.temperature=temp;requested.iaq=iaq;auto record=EnvAlert::save(requested);
        if(prefs.putBytes("limits",&record,sizeof(record))!=sizeof(record))Serial.println("ALERT ERROR SAVE FAILED");
        else {model.configure(temp,iaq);saved=true;Serial.println("ALERT SAVED");report();}
      }
    } else Serial.println("ALERT ERROR UNKNOWN COMMAND");
    return true;
  }
};
