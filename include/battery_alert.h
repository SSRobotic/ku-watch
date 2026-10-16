#pragma once
#include <math.h>
#include <stdint.h>
namespace BatteryAlert {
enum State:uint8_t {Waiting=0,Normal=1,Low=2};
// Unknown/invalid input must never look like a healthy battery. Small hysteresis
// avoids repeated warnings around the voltage-based 20% estimate.
inline State update(State previous,bool valid,float percent) {
  if(!valid || !isfinite(percent) || percent<0 || percent>100)return Waiting;
  if(percent<=20 || (previous==Low && percent<22))return Low;
  return Normal;
}
}
