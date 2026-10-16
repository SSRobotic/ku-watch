#include <cassert>
#include <iostream>
#include "battery_alert.h"
constexpr uint8_t INA226_I2C_ADDRESS=0x44;
namespace Pin {constexpr unsigned PAGE_COUNT=11;}
#include "face.h"
int main(){
  using namespace BatteryAlert;
  auto s=update(Waiting,true,21);assert(s==Normal);
  s=update(s,true,20);assert(s==Low);s=update(s,true,21.99f);assert(s==Low);
  s=update(s,true,22);assert(s==Normal);assert(update(Normal,true,0)==Low);
  for(float p:{NAN,INFINITY,-1.f,101.f})assert(update(Low,true,p)==Waiting);
  assert(update(Low,false,10)==Waiting);assert(update(Waiting,true,100)==Normal);
  static Face::Canvas normal,low;Face::State state;state.firmware="2.0.1";
  for(unsigned page=0;page<11;++page){state.page=page;state.batteryLow=false;normal.render(state);
    state.batteryLow=true;low.render(state);unsigned changed=0;
    for(unsigned y=0;y<240;++y)for(unsigned x=0;x<240;++x)if(normal.pixels[y*240+x]!=low.pixels[y*240+x]){
      ++changed;assert(y>=25 && y<34 && x>=40 && x<200);}
    assert(changed);}
  std::cout<<"Battery boundary/hysteresis/invalid input and all 11-page warning bounds passed\n";
}
