#include <Arduino.h>
#include <Wire.h>
#include "config.h"
#include "pulse_sensor.h"

static PulseSensor pulse;
void setup() {
  Serial.begin(115200);
  Wire.begin(Pin::SDA,Pin::SCL,100000); Wire.setTimeOut(10);
  Serial.printf("MAX30102 TEST: VIN=3V3 GND=GND SDA=GPIO%d SCL=GPIO%d\n",Pin::SDA,Pin::SCL);
}
void loop() {
  pulse.tick(millis());
  static uint32_t reportAt=0;
  if(uint32_t(millis()-reportAt)>=500) {
    reportAt=millis();
    Serial.printf("MAX30102 %s IR=%lu RED=%lu finger=%s BPM=",pulse.live?"LIVE":"WAITING",pulse.ir,pulse.red,pulse.finger?"YES":"NO");
    if(isfinite(pulse.bpm)) Serial.printf("%.1f",pulse.bpm); else Serial.print("--");
    Serial.printf(" dropped_batches=%lu\n",pulse.droppedBatches);
  }
  delay(1);
}
