#include <cassert>
#include <cmath>
#include <cstdio>
#include <initializer_list>
#include "pulse_tracker.h"
#include "spo2_tracker.h"
#ifdef NDEBUG
#error This regression requires active assertions
#endif

static void feed(Spo2Tracker& oxygen,float opticalBpm,float measuredBpm,bool invertRed=false,bool wrongRedPeriod=false){
  for(unsigned i=0;i<1000;++i){
    double t=double(i)/25,phase=6.283185307179586*opticalBpm/60*t;
    double ir=sin(phase)+.25*sin(2*phase+.6);
    double red=wrongRedPeriod?sin(phase*.73):ir;
    if(invertRed)red=-red;
    oxygen.sample(uint32_t(100000+1000*ir),uint32_t(98000+400*red),10000,measuredBpm);
  }
}
int main(){
  for(float bpm:{45.f,60.f,67.f,90.f,120.f,150.f}){
    Spo2Tracker oxygen;assert(oxygen.setSampleRate(25));feed(oxygen,bpm,bpm);
    if(oxygen.status!=3)std::printf("Positive %.1f failed: status=%u corr=%.3f periods=%.3f/%.3f reference=%ld\n",bpm,oxygen.status,oxygen.periodicCorrelation,oxygen.periodicIr,oxygen.periodicRed,long(oxygen.candidateHeartRate));
    assert(oxygen.status==3&&std::isfinite(oxygen.value)&&oxygen.value>=70&&oxygen.value<=100);
    assert(std::isfinite(oxygen.pulseBpm)&&fabs(oxygen.pulseBpm-bpm)<3);
  }
  Spo2Tracker wrong;wrong.setSampleRate(25);feed(wrong,120,60);
  assert(wrong.rhythmAccepted&&fabs(wrong.pulseBpm-120)<3); // optical period corrects an unrelated half-rate peak counter
  wrong.reset();feed(wrong,60,120);assert(wrong.rhythmAccepted&&fabs(wrong.pulseBpm-60)<3);
  wrong.reset();feed(wrong,67,NAN);assert(wrong.status==3&&fabs(wrong.pulseBpm-67)<3);
  wrong.reset();feed(wrong,72,72,true);assert(!std::isfinite(wrong.value));
  wrong.reset();feed(wrong,72,72,false,true);assert(!std::isfinite(wrong.value));
  wrong.reset();for(unsigned i=0;i<1000;++i)wrong.sample(100000,98000,10000,72);
  assert(!std::isfinite(wrong.value));
  wrong.reset();unsigned state=1234567;
  for(unsigned i=0;i<1000;++i){state=state*1664525+1013904223;int n=int((state>>16)%2001)-1000;wrong.sample(100000+n,98000+n/2,10000,72);}
  assert(!std::isfinite(wrong.value)); // correlated aperiodic motion/noise
  wrong.reset();assert(!wrong.signalAccepted&&!wrong.rhythmAccepted&&!wrong.oxygenAccepted);
  assert(wrong.candidateHeartRate==-999&&wrong.candidateOxygen==-999);
  uint32_t ir[100],red[100];
  for(unsigned i=0;i<100;++i){ir[i]=100000+i*30;red[i]=98000+i*15;}
  assert(!PpgPeriod::measure(ir,red).valid); // correlated baseline drift is not a pulse
  for(unsigned i=0;i<100;++i){double p=6.283185307179586*i/25;ir[i]=100000+i*30+1000*sin(p);red[i]=98000+i*15+400*sin(p);}
  auto detrended=PpgPeriod::measure(ir,red);
  assert(detrended.valid&&fabs(detrended.bpm-60)<3);
  puts("Two-channel period, plausible oxygen, half/double-rate, noise, red mismatch and stale-reset checks passed; host only, not clinical accuracy.");
}
