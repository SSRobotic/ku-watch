#include <Arduino.h>
#include "gps_uart.h"

static GpsUart gps;
void setup() { Serial.begin(115200); gps.begin(); }
void loop() {
  gps.poll();
  static uint32_t reportAt=0;
  if(uint32_t(millis()-reportAt)>=1000) { reportAt=millis(); gps.report(); }
  delay(1);
}
