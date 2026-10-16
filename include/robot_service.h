#pragma once
#include <Arduino.h>
#include <Preferences.h>
#include "robot_pet.h"

class RobotService {
  Preferences storage;
  bool ready_=false,restored_=false;
  uint32_t savedRevision_=0,savedAt_=0;
public:
  RobotPet::Model model;
  void begin() {
    ready_=storage.begin("ku_robot",false);
    if(ready_ && storage.getBytesLength("pet")==sizeof(RobotPet::Saved)) {
      RobotPet::Saved value;
      if(storage.getBytes("pet",&value,sizeof(value))==sizeof(value)) restored_=model.restore(value);
    }
    savedAt_=millis();
  }
  bool flush() {
    if(!ready_) return false;
    auto value=model.snapshot();
    if(storage.putBytes("pet",&value,sizeof(value))!=sizeof(value)) return false;
    savedRevision_=model.revision;savedAt_=millis();return true;
  }
  void tick(bool force=false) {
    if(!ready_) return;
    if(model.revision!=savedRevision_ && (force || uint32_t(millis()-savedAt_)>=60000)) {
      if(!flush()) Serial.println("ROBOT SAVE ERROR");
    }
  }
  void report() {
    const auto& s=model.saved;
    Serial.printf("ROBOT name=KU-BOT level=%u stage=%u xp=%lu next=%lu food=%u mood=%u energy=%u walk_seconds=%llu walk_meters=%.2f activity=%lu storage=%u dirty=%u loaded=%u care_utc=%llu\n",
      RobotPet::level(s.xp),RobotPet::stage(s.xp),(unsigned long)s.xp,(unsigned long)RobotPet::nextXp(s.xp),
      s.food,s.mood,s.energy,(unsigned long long)(s.walkMs/1000),double(s.walkCm)/100,(unsigned long)s.activityId,ready_,model.revision!=savedRevision_,restored_,(unsigned long long)s.careUtc);
  }
};
