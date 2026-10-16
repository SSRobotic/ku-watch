#pragma once
// Host-only boundary double. BSEC's proprietary ESP32 binary is tested by the
// target build, not emulated here; these tests exercise our lifecycle/gates.
#include <Arduino.h>
#include <Wire.h>
#include <cstring>
#define BSEC_INSTANCE_SIZE 1024
#define BSEC_MAX_STATE_BLOB_SIZE 238
#define BME68X_GASM_VALID_MSK 0x20
#define BME68X_HEAT_STAB_MSK 0x10
#define BME68X_ERROR -1
#define BSEC_SAMPLE_RATE_LP .33333f
enum bsecSensor { BSEC_OUTPUT_RAW_TEMPERATURE,BSEC_OUTPUT_RAW_HUMIDITY,
  BSEC_OUTPUT_RAW_PRESSURE,BSEC_OUTPUT_RAW_GAS,BSEC_OUTPUT_IAQ,
  BSEC_OUTPUT_STABILIZATION_STATUS,BSEC_OUTPUT_RUN_IN_STATUS };
struct bme68xData {uint8_t status=0x30;float pressure=1001;};
struct bsecOutput { bsecSensor sensor_id;float signal;uint8_t accuracy;};
struct bsecOutputs {unsigned nOutputs=0;bsecOutput output[7];};
class Bsec2 {
  void (*callback)(bme68xData,bsecOutputs,Bsec2)=nullptr;
public:
  static inline bsecOutputs pending{};
  static inline bme68xData data{};
  static inline int fault=0,begins=0,stateLoads=0;
  static inline bool stateOk=true;
  struct Sensor {int checkStatus(){return fault<0?BME68X_ERROR:0;}} sensor;
  int status=0;
  void allocateMemory(uint8_t*){}
  bool begin(uint8_t,TwoWire&){++begins;status=0;return true;}
  bool setConfig(const uint8_t*){return true;}
  bool setState(const uint8_t*){++stateLoads;return stateOk;}
  bool updateSubscription(const bsecSensor*,unsigned,float){return true;}
  void attachCallback(void(*cb)(bme68xData,bsecOutputs,Bsec2)){callback=cb;}
  void run(){status=fault;if(pending.nOutputs){callback(data,pending,*this);pending.nOutputs=0;}}
  bool getState(uint8_t* blob){std::memset(blob,1,BSEC_MAX_STATE_BLOB_SIZE);return true;}
};
