#pragma once
#include <bsec2.h>
#include <Preferences.h>

// BSEC owns the BME68x heater profile and timing; no second reader may configure it.
class EnvironmentSensor {
  Bsec2 sensor;
  alignas(8) uint8_t memory[BSEC_INSTANCE_SIZE];
  Preferences prefs;
  bool initialized=false,allocated=false,prefsReady=false,saved=false;
  uint32_t retryAt=0,sampleAt=0,savedAt=0,nextSaveAttempt=0;
  static inline EnvironmentSensor* owner=nullptr;
  static void output(const bme68xData data,const bsecOutputs outputs,Bsec2) {
    if(owner) owner->receive(data,outputs);
  }
  void receive(const bme68xData& data,const bsecOutputs& out) {
    if(!out.nOutputs) return;
    invalidate(); // All subscribed outputs use the same cadence; never mix old and new fields.
    bool fresh=false,gotIaq=false;
    for(unsigned i=0;i<out.nOutputs;++i) {
      const auto& o=out.output[i];
      switch(o.sensor_id) {
        case BSEC_OUTPUT_RAW_TEMPERATURE:temp=o.signal;fresh=true;break;
        case BSEC_OUTPUT_RAW_HUMIDITY:humidity=o.signal;break;
        // Pinned BSEC2 1.10.2610 converts callback data.pressure from Pa to hPa.
        // Use that explicit source; the BSEC output documentation still says Pa.
        case BSEC_OUTPUT_RAW_PRESSURE:pressure=data.pressure;break;
        case BSEC_OUTPUT_RAW_GAS:gas=o.signal;break;
        case BSEC_OUTPUT_IAQ:iaq=o.signal;accuracy=o.accuracy;gotIaq=true;break;
        case BSEC_OUTPUT_STABILIZATION_STATUS:stable=o.signal>=1;break;
        case BSEC_OUTPUT_RUN_IN_STATUS:runIn=o.signal>=1;break;
      }
    }
    gasValid=(data.status&BME68X_GASM_VALID_MSK)&&(data.status&BME68X_HEAT_STAB_MSK)&&isfinite(gas)&&gas>0;
    iaqValid=gotIaq&&gasValid&&stable&&runIn&&accuracy>=1&&isfinite(iaq)&&iaq>=0&&iaq<=500;
    if(!iaqValid) iaq=NAN;
    if(!gasValid) gas=NAN;
    live=fresh&&isfinite(temp)&&isfinite(humidity)&&isfinite(pressure);
    if(live) {sampleAt=millis();++sequence;}
  }
  void invalidate() {live=gasValid=iaqValid=stable=runIn=false;temp=humidity=pressure=gas=iaq=NAN;accuracy=0;}
public:
  bool live=false,gasValid=false,iaqValid=false,stable=false,runIn=false;
  float temp=NAN,humidity=NAN,pressure=NAN,gas=NAN,iaq=NAN;
  uint8_t accuracy=0;
  int status=0;
  uint32_t sequence=0;
  uint32_t lastSampleMs() const {return sampleAt;}
  void tick(uint32_t now) {
    owner=this;
    if(!allocated) {sensor.allocateMemory(memory);allocated=true;prefsReady=prefs.begin("ku-bsec15",false);}
    if(live && uint32_t(now-sampleAt)>12000) {invalidate();initialized=false;retryAt=now+3000;}
    if(!initialized) {
      if(int32_t(now-retryAt)<0) return;
      retryAt=now+10000;
      static const uint8_t config[]={
        #include "config/bme680/bme680_iaq_33v_3s_4d/bsec_iaq.txt"
      };
      for(uint8_t addr:{uint8_t(0x76),uint8_t(0x77)}) {
        Wire.beginTransmission(addr);if(Wire.endTransmission()!=0) continue;
        if(!sensor.begin(addr,Wire)||!sensor.setConfig(config)) {status=sensor.status;continue;}
        const char* key=addr==0x76?"state76":"state77";
        uint8_t blob[BSEC_MAX_STATE_BLOB_SIZE];
        if(prefsReady && prefs.getBytesLength(key)==sizeof(blob)) {
          prefs.getBytes(key,blob,sizeof(blob));
          if(!sensor.setState(blob)) {
            prefs.remove(key);
            if(!sensor.begin(addr,Wire)||!sensor.setConfig(config)) {status=sensor.status;continue;}
          }
        }
        bsecSensor wanted[]={BSEC_OUTPUT_RAW_TEMPERATURE,BSEC_OUTPUT_RAW_HUMIDITY,
          BSEC_OUTPUT_RAW_PRESSURE,BSEC_OUTPUT_RAW_GAS,BSEC_OUTPUT_IAQ,
          BSEC_OUTPUT_STABILIZATION_STATUS,BSEC_OUTPUT_RUN_IN_STATUS};
        if(!sensor.updateSubscription(wanted,7,BSEC_SAMPLE_RATE_LP)) {status=sensor.status;continue;}
        address=addr;sensor.attachCallback(output);initialized=true;sampleAt=now;
        Serial.printf("BSEC2 IAQ ready 0x%02X, 3.3V LP 3s profile\n",addr);break;
      }
      return;
    }
    sensor.run();status=sensor.status;
    if(status<0 || sensor.sensor.checkStatus()==BME68X_ERROR) {invalidate();initialized=false;retryAt=now+5000;return;}
    if(!live && uint32_t(now-sampleAt)>15000) {invalidate();initialized=false;retryAt=now+5000;return;}
    if(prefsReady && iaqValid && accuracy==3 && int32_t(now-nextSaveAttempt)>=0 && (!saved || uint32_t(now-savedAt)>=21600000)) {
      nextSaveAttempt=now+60000;
      uint8_t blob[BSEC_MAX_STATE_BLOB_SIZE];
      if(sensor.getState(blob) && prefs.putBytes(address==0x76?"state76":"state77",blob,sizeof(blob))==sizeof(blob)) {saved=true;savedAt=now;}
    }
  }
private:
  uint8_t address=0x76;
};
