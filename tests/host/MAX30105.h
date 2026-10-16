#pragma once
#include "Wire.h"
constexpr unsigned I2C_SPEED_STANDARD=100000;
class MAX30105 {
public:
  bool begin(TwoWire& w,unsigned) { return w.connected; }
  void setup(unsigned level,unsigned average,unsigned mode,unsigned rate,unsigned,unsigned) {
    Wire.redLed=Wire.irLed=level;Wire.average=average;Wire.adcRate=rate;
  }
  void setPulseAmplitudeGreen(unsigned) {}
  void setPulseAmplitudeRed(unsigned value) { Wire.redLed=value; }
  void setPulseAmplitudeIR(unsigned value) { Wire.irLed=value; }
  void clearFIFO() { Wire.clear(); }
};
