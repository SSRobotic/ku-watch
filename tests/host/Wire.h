#pragma once
#include <stdint.h>
#include <deque>
#include <vector>
class TwoWire {
  uint8_t reg = 0;
  uint8_t address = 0;
  std::vector<uint8_t> written;
  std::deque<uint8_t> response;
public:
  bool connected = true;
  unsigned redLed=31,irLed=31;
  unsigned average=1,adcRate=100;
  uint8_t overflow = 0;
  bool stickyOverflow = false;
  std::deque<uint32_t> samples;
  std::vector<unsigned> batches;
  bool inaConnected=true;
  uint8_t inaAddress=0x44; // Address of the user's module, verified on the physical bus.
  uint16_t inaManufacturer=0x5449, inaDie=0x2260, inaVoltage=3200, inaMask=8, inaConfig=0;
  bool environmentConnected=true;
  void beginTransmission(uint8_t a) { address=a;written.clear(); }
  void write(uint8_t r) { if(written.empty()) reg=r;written.push_back(r); }
  int endTransmission(bool=true) {
    if(address==inaAddress) {
      if(written.size()==3 && reg==0) inaConfig=(written[1]<<8)|written[2];
      return inaConnected?0:2;
    }
    if(address==0x76 || address==0x77) return environmentConnected?0:2;
    return connected?0:2;
  }
  unsigned requestFrom(uint8_t, uint8_t size) {
    response.clear();
    if(address==inaAddress) {
      if(!inaConnected) return 0;
      uint16_t value=reg==0xfe?inaManufacturer:reg==0xff?inaDie:reg==0x06?inaMask:inaVoltage;
      response={uint8_t(value>>8),uint8_t(value)};return 2;
    }
    if(!connected) return 0;
    if(reg==4) {
      response={uint8_t(samples.size()&31),overflow,0};
    } else if(reg==7) {
      batches.push_back(size/6);
      for(unsigned i=0;i<size/6 && !samples.empty();++i) {
        uint32_t ir=samples.front(); samples.pop_front();
        overflow=0;
        for(uint32_t value:{ir/2,ir}) {
          response.push_back(value>>16); response.push_back(value>>8); response.push_back(value);
        }
      }
    }
    return unsigned(response.size());
  }
  int read() { auto v=response.front(); response.pop_front(); return v; }
  void clear() { samples.clear(); if(!stickyOverflow) overflow=0; }
};
extern TwoWire Wire;
