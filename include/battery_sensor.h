#pragma once
#include <Arduino.h>
#include <Wire.h>
#include "config.h"
#include "battery_estimate.h"

class BatterySensor {
  uint32_t next=0;
  bool initialized=false;
  float shuntOhms=0;
  bool read(uint8_t reg,uint16_t& val) {
    Wire.beginTransmission(INA226_I2C_ADDRESS);Wire.write(reg);
    if(Wire.endTransmission(false)!=0 || Wire.requestFrom(INA226_I2C_ADDRESS,uint8_t(2))!=2) return false;
    val=uint16_t(Wire.read())<<8;val|=Wire.read();return true;
  }
  bool configure() {
    uint16_t manufacturer,die;
    if(!read(0xfe,manufacturer)||!read(0xff,die)||manufacturer!=0x5449||(die&0xfff0)!=0x2260) return false;
    // 16-sample averaging, 1.1 ms conversion, continuous BUS ONLY. No shunt/current assumption.
    Wire.beginTransmission(INA226_I2C_ADDRESS);Wire.write(0x00);Wire.write(0x45);Wire.write(shuntOhms>0?0x27:0x26);
    return Wire.endTransmission(true)==0;
  }
  void invalid() {valid=currentValid=false;volts=percent=currentMa=powerMw=NAN;}
public:
  bool detected=false,valid=false;
  bool currentValid=false;
  float volts=NAN,percent=NAN;
  float currentMa=NAN,powerMw=NAN;
  void setShunt(float ohms) {if(shuntOhms!=ohms) {shuntOhms=ohms;initialized=false;invalid();}}
  void tick(uint32_t now) {
    if(int32_t(now-next)<0) return;
    next=now+1000;
    if(!initialized) {detected=initialized=configure();invalid();return;}
    uint16_t mask,raw;
    if(!read(0x06,mask)||!read(0x02,raw)) {initialized=detected=false;invalid();return;}
    if(!(mask&0x0008)) {invalid();return;} // no completed conversion: never reuse old voltage
    float v=raw*.00125f,estimate=batteryPercent(v);
    if(!isfinite(estimate)) {invalid();return;}
    volts=isfinite(volts)?volts*.8f+v*.2f:v;
    percent=batteryPercent(volts);valid=true;
    currentValid=false;currentMa=powerMw=NAN;
    uint16_t shunt;
    if(shuntOhms>0 && read(0x01,shunt)) {
      currentMa=float(int16_t(shunt))*.0025f/shuntOhms;powerMw=volts*currentMa;currentValid=true;
    }
  }
};
