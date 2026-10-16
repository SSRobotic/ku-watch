#pragma once
#include <stdint.h>
#include "environment_alert.h"

// Explicit, transient acceptance inputs. Never replace real sensor/model state,
// real telemetry, the journal, CSV, or ESP-NOW values with these observations.
class AlertFixture {
public:
  EnvAlert::Model model;
  bool active=false,air=false;
  uint32_t id=0,started=0,next=0,inputAt=0,sequence=0,painted=0;
  void begin(uint32_t now,uint32_t identity,bool iaq) {
    model=EnvAlert::Model();model.configure(35,150);
    model.update(0,true,25,true,50,3,true,true);
    active=true;air=iaq;id=identity;started=next=inputAt=now;sequence=painted=0;
  }
  bool advance(uint32_t now) {
    if(!active || sequence>=3 || int32_t(now-next)<0)return false;
    // Do not catch up missed observations in a burst.
    if(sequence && uint32_t(now-inputAt)>1500)model=EnvAlert::Model();
    inputAt=now;next=now+1000;++sequence;
    model.update(sequence,true,air?25:36,true,air?200:50,3,true,true);
    return true;
  }
  bool expired(uint32_t now) const {return active&&uint32_t(now-started)>=15000;}
  void stop(){active=false;}
};
