#pragma once
#include <stdint.h>
#include <vector>
class FakeWire {
  std::vector<uint8_t> transmit;unsigned position=0,readLeft=0;uint8_t address=0;
public:
  uint8_t registers[256]={};unsigned writes=0,failWrite=0;bool connected=true,shortRead=false;
  void beginTransmission(uint8_t a){address=a;transmit.clear();}
  void write(uint8_t v){transmit.push_back(v);}
  int endTransmission(bool stop=true){
    if(!connected||address!=0x51||transmit.empty())return 4;
    if(transmit.size()>1 && ++writes==failWrite)return 4;
    position=transmit[0];for(unsigned i=1;i<transmit.size();++i)registers[position++]=transmit[i];return 0;
  }
  unsigned requestFrom(int address,int count){readLeft=shortRead?count-1:count;return readLeft;}
  uint8_t read(){--readLeft;return registers[position++];}
};
inline FakeWire Wire;
