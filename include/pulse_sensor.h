#pragma once
#include <Arduino.h>
#include <Wire.h>
#include "MAX30105.h"
#include "config.h"
#include "pulse_tracker.h"
#include "spo2_tracker.h"

class PulseSensor {
  MAX30105 chip;
  PulseTracker tracker;
  Spo2Tracker oxygen;
  uint32_t polledAt = 0, sampleAt = 0, retryAt = 0;
  bool initialized = false;
  uint8_t ledCurrent=MAX30102_LED_CURRENT;
  uint8_t redCurrent=MAX30102_LED_CURRENT;
  bool averaged=false;
  unsigned fifoRate() const {return averaged?25:100;}
  struct TraceSample { uint32_t ir, red; } trace[1000];
  unsigned traceUsed=0;
  bool tracing=false;
  bool read(uint8_t reg, uint8_t *out, uint8_t size) {
    Wire.beginTransmission(0x57); Wire.write(reg);
    if (Wire.endTransmission(false) != 0 || Wire.requestFrom(uint8_t(0x57),size) != size) return false;
    for (uint8_t i=0;i<size;++i) out[i]=Wire.read();
    return true;
  }
  void lost(uint32_t now) {
    tracing=false;
    initialized=live=finger=false; bpm=NAN; ir=red=0;
    tracker.reset(); oxygen.reset(); spo2=NAN; spo2Quality=NAN; spo2Status=0; retryAt=now+5000;
  }
public:
  void setAveraging(bool enable) {
    averaged=enable;
    tracker.setSampleRate(fifoRate());oxygen.setSampleRate(fifoRate());
    if(initialized) {
      chip.setup(ledCurrent,averaged?16:1,2,averaged?400:100,411,4096);
      chip.setPulseAmplitudeRed(redCurrent);chip.setPulseAmplitudeGreen(0);chip.clearFIFO();tracker.reset();oxygen.reset();
      live=finger=false;bpm=spo2=spo2Quality=NAN;spo2Status=0;ir=red=0;
      tracing=false;polledAt=sampleAt=millis();
    }
    Serial.printf("MAXAVG OK average=%u adc_rate=%u fifo_rate=%u\n",averaged?16:1,averaged?400:100,fifoRate());
  }
  bool setLedCurrent(unsigned value) {
    if(value<1 || value>0x3f) return false;
    ledCurrent=redCurrent=uint8_t(value);
    if(initialized) {
      chip.setPulseAmplitudeRed(ledCurrent);chip.setPulseAmplitudeIR(ledCurrent);
      chip.clearFIFO();tracker.reset();oxygen.reset();
      live=finger=false;bpm=spo2=spo2Quality=NAN;spo2Status=0;ir=red=0;
      tracing=false;polledAt=sampleAt=millis();
    }
    Serial.printf("MAXLED OK level=%u\n",ledCurrent);
    return true;
  }
  bool setRedCurrent(unsigned value) {
    if(value<1 || value>0x7f) return false;
    redCurrent=uint8_t(value);
    if(initialized) {
      chip.setPulseAmplitudeRed(redCurrent);chip.clearFIFO();tracker.reset();oxygen.reset();
      live=finger=false;bpm=spo2=spo2Quality=NAN;spo2Status=0;ir=red=0;
      tracing=false;polledAt=sampleAt=millis();
    }
    Serial.printf("MAXRED OK level=%u\n",redCurrent);
    return true;
  }
  void startTrace() { traceUsed=0; tracing=true; Serial.printf("PULSETRACE START %uHz 1000 samples\n",fifoRate()); }
  void reportTrace() {
    Serial.printf("PULSETRACE DATA count=%u complete=%u\n",traceUsed,traceUsed==1000);
    for(unsigned i=0;i<traceUsed;++i) Serial.printf("PPG %u %lu %lu\n",i,trace[i].ir,trace[i].red);
    Serial.println("PULSETRACE END");
  }
  bool live = false, finger = false;
  float bpm = NAN;
  float spo2=NAN,spo2Quality=NAN;
  uint8_t spo2Status=0;
  uint32_t ir = 0, red = 0, droppedBatches = 0;
  uint32_t acquiredSamples=0;
  uint32_t lastSampleMs() const {return sampleAt;}
  unsigned sampleRate() const {return fifoRate();}
  void reportQuality() const {
    Serial.printf("PPGQUALITY windows=%lu signal=%u rhythm=%u oxygen_valid=%u candidate_spo2=%ld candidate_hr=%ld bpm=%.1f perfusion_ir=%.6f perfusion_red=%.6f good_status=%u reference_hr_agrees=%u period_corr=%.6f period_ir=%.6f period_red=%.6f\n",
      (unsigned long)oxygen.windows,oxygen.signalAccepted,oxygen.rhythmAccepted,oxygen.oxygenAccepted,
      (long)oxygen.candidateOxygen,(long)oxygen.candidateHeartRate,bpm,oxygen.perfusionIr,oxygen.perfusionRed,spo2Status,
      oxygen.referenceHeartRateAgrees,oxygen.periodicCorrelation,oxygen.periodicIr,oxygen.periodicRed);
  }
  uint32_t lastGap = 0;
  uint8_t lastWrite = 0, lastOverflow = 0, lastRead = 0;
  void tick(uint32_t now) {
    if (!initialized) {
      if (int32_t(now-retryAt)<0) return;
      retryAt=now+5000;
      if (!chip.begin(Wire,I2C_SPEED_STANDARD)) return;
      // 400 ADC samples/s averaged by 16 leaves 1.28 s of FIFO headroom.
      // The 25 Hz estimators use each real record once, with its true period.
      chip.setup(ledCurrent,averaged?16:1,2,averaged?400:100,411,4096);
      chip.setPulseAmplitudeRed(redCurrent);
      chip.setPulseAmplitudeGreen(0); chip.clearFIFO(); tracker.reset(); oxygen.reset();
      initialized=true; polledAt=sampleAt=millis();
      Serial.printf("MAX30102 ready: 0x57, RED+IR, %u samples/s\n",fifoRate());
      return;
    }
    uint32_t gap=now-polledAt;
    if (gap<10) return;
    polledAt=now;
    uint8_t pointers[3]; // FIFO_WR_PTR, OVF_COUNTER, FIFO_RD_PTR
    if (!read(0x04,pointers,3)) { lost(now); return; }
    lastGap=gap; lastWrite=pointers[0]; lastOverflow=pointers[1]; lastRead=pointers[2];
    if (gap>(averaged?1100u:250u) || (pointers[1]&0x1f)) {
      tracing=false;
      // Network calls may stall the loop. Never derive BPM across lost samples.
      // A complete FIFO read clears OVF_COUNTER (MAX30102 datasheet p13).
      // This module retained 0x1f after pointer/overflow writes alone, causing
      // an endless reset loop. Pop one whole RED+IR record before clearing.
      if(pointers[1]&0x1f) {
        uint8_t discarded[6];
        if(!read(0x07,discarded,sizeof(discarded))) { lost(now); return; }
      }
      chip.clearFIFO(); tracker.reset(); oxygen.reset(); live=finger=false; bpm=spo2=spo2Quality=NAN;spo2Status=0;
      ir=red=0; sampleAt=now; ++droppedBatches; return;
    }
    unsigned pending=(pointers[0]-pointers[2])&0x1f;
    // Read the hardware FIFO directly: the library's four-record software ring
    // can overwrite samples while a complete display frame is being transferred.
    while (pending) {
      uint8_t buf[30]; unsigned records=pending>5?5:pending;
      if (!read(0x07,buf,uint8_t(records*6))) { lost(now); return; }
      for (unsigned i=0;i<records;++i) {
        const uint8_t *p=buf+i*6;
        red=((uint32_t(p[0])<<16)|(uint32_t(p[1])<<8)|p[2])&0x3ffff;
        ir=((uint32_t(p[3])<<16)|(uint32_t(p[4])<<8)|p[5])&0x3ffff;
        ++acquiredSamples;
        if(tracing) {
          trace[traceUsed++]={ir,red};
          if(traceUsed==1000) tracing=false;
        }
        tracker.sample(ir,MAX30102_FINGER_IR_MIN);
        oxygen.sample(ir,red,MAX30102_FINGER_IR_MIN,tracker.bpm);
      }
      pending-=records; sampleAt=now; live=true;
    }
    finger=tracker.finger; bpm=oxygen.pulseBpm;
    spo2=oxygen.value;spo2Quality=oxygen.quality;spo2Status=oxygen.status;
    if (uint32_t(now-sampleAt)>1000) lost(now);
  }
};
