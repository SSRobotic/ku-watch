#include <cassert>
#include <cmath>
#include <cstdio>
#include "pulse_tracker.h"
#include "spo2_tracker.h"
#ifdef NDEBUG
#error This regression requires active assertions
#endif
int main(){
  for(float rate : {45.f,60.f,90.f,120.f,150.f}){
    PulseTracker pulse;assert(pulse.setSampleRate(25));
    for(unsigned i=0;i<750;++i)pulse.sample(uint32_t(50000+1000*sin(6.283185307*rate/60*i/25)),10000);
    assert(pulse.finger&&std::isfinite(pulse.bpm)&&fabs(pulse.bpm-rate)<3);
    pulse.sample(500,10000);assert(!pulse.finger&&!std::isfinite(pulse.bpm));
    for(unsigned i=0;i<750;++i)pulse.sample(uint32_t(50000+1000*sin(6.283185307*rate/60*i/25)),10000);
    assert(std::isfinite(pulse.bpm)&&fabs(pulse.bpm-rate)<3);
  }
  Spo2Tracker oxygen;assert(oxygen.setSampleRate(25));
  for(unsigned i=0;i<300;++i){double s=sin(6.283185307*1.2*i/25);oxygen.sample(uint32_t(50000+1000*s),uint32_t(30000+300*s),10000,72);}
  assert(oxygen.status==3&&oxygen.value>=90&&oxygen.value<=100);
  oxygen.reset();for(unsigned i=0;i<300;++i)oxygen.sample(50000,30000,10000,72);assert(!std::isfinite(oxygen.value));
  oxygen.reset();for(unsigned i=0;i<300;++i){double s=sin(6.283185307*1.2*i/25);oxygen.sample(uint32_t(50000+1000*s),uint32_t(30000-300*s),10000,72);}assert(!std::isfinite(oxygen.value));
  puts("25 Hz sample timing, reset preservation, stable estimates, flat and anticorrelated rejection passed; not a clinical calibration.");
}
