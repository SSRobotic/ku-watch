#pragma once
#include <Arduino.h>
#include "config.h"
#include "gps_receiver.h"

class GpsUart {
  HardwareSerial uart{1};
  uint32_t polledAt = 0;
  bool begun = false;
  bool tracing = false;
  uint32_t traceAt = 0;
  char traceLine[128] = {};
  unsigned traceLength = 0;
  void trace(char c, uint32_t now) {
    if(!tracing) return;
    if(uint32_t(now-traceAt)>=30000) {
      tracing=false; traceLength=0; Serial.println("GPS TRACE END"); return;
    }
    if(c=='$') traceLength=0;
    if(c=='\r') return;
    if(c=='\n') {
      if(traceLength && traceLine[0]=='$') {
        traceLine[traceLength]=0;
        Serial.print("GPS NMEA "); Serial.println(traceLine);
      }
      traceLength=0;
    } else if(traceLength<sizeof(traceLine)-1) traceLine[traceLength++]=c;
  }
public:
  GpsReceiver receiver;
  void startTrace() {
    traceAt=millis(); traceLength=0; tracing=true;
    Serial.println("GPS TRACE BEGIN (30 seconds, USB only)");
  }
  void begin() {
    uart.setRxBufferSize(8192);
    uart.begin(GPS_BAUD,SERIAL_8N1,Pin::GPS_RX,Pin::GPS_TX);
    polledAt=millis();
    begun=true;
    Serial.printf("ATGM336H UART1: GPS TX -> GPIO%d, GPS RX -> GPIO%d, %lu baud\n",Pin::GPS_RX,Pin::GPS_TX,GPS_BAUD);
  }
  void poll() {
    if(!begun) return;
    uint32_t now=millis();
    if (uint32_t(now-polledAt)>=GPS_STALE_MS) {
      // Drop a backlog after a long stall; it must not become a fresh location.
      unsigned old=uart.available(); while(old-- && uart.available()) uart.read();
    }
    polledAt=now;
    unsigned budget=2048;
    while(uart.available() && budget--) {
      char c=char(uart.read()); receiver.encode(c,now); trace(c,now);
    }
    if(tracing && uint32_t(now-traceAt)>=30000) {
      tracing=false; traceLength=0; Serial.println("GPS TRACE END");
    }
  }
  GpsReading reading() { return receiver.reading(millis(),GPS_STALE_MS); }
  void report() {
    auto r=reading();
    Serial.printf("GPS %s SAT=%lu chars=%lu bad_checksum=%lu",r.fix?"FIX":(r.data?"WAIT FIX":"NO DATA"),r.satellites,receiver.chars(),receiver.checksumErrors());
    if(r.viewValid) Serial.printf(" VIEW=%lu",r.inView);
    if(r.signalValid) Serial.printf(" CNO=%lu",r.signal);
    if(r.fix) Serial.printf(" LAT=%.6f LON=%.6f ALT=%.1f SPEED=%.1f HDOP=%.1f",r.latitude,r.longitude,r.altitude,r.speed,r.hdop);
    Serial.println();
  }
};
