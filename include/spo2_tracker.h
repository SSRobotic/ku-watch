#pragma once
#include <stdint.h>
#include <math.h>
#include <string.h>
#include <spo2_algorithm.h>
#include "ppg_period.h"

// MAXREFDES117 expects 25 Hz. Use real 25 Hz records directly or decimate 100 Hz by four.
// Experimental optical estimate, not a clinically calibrated pulse oximeter.
class Spo2Tracker {
  uint32_t irs[100]={}, reds[100]={}, sumIr=0, sumRed=0;
  unsigned sub=0, used=0, good=0;
  unsigned decimation=4;
  float previous=NAN;

public:
  float value=NAN, quality=NAN, pulseBpm=NAN;
  uint32_t windows=0;int32_t candidateOxygen=-999,candidateHeartRate=-999;
  bool signalAccepted=false,rhythmAccepted=false,oxygenAccepted=false;
  float perfusionIr=0,perfusionRed=0;
  bool referenceHeartRateAgrees=false;
  float periodicCorrelation=0,periodicIr=0,periodicRed=0;
  // 0 no finger, 1 collecting, 2 poor signal, 3 estimate ready, 4 outside range.
  uint8_t status=0;
  void reset() {
    used=sub=good=0;sumIr=sumRed=0;value=quality=previous=pulseBpm=NAN;status=0;
    candidateOxygen=candidateHeartRate=-999;
    signalAccepted=rhythmAccepted=oxygenAccepted=referenceHeartRateAgrees=false;
    perfusionIr=perfusionRed=periodicCorrelation=periodicIr=periodicRed=0;
  }
  bool setSampleRate(unsigned hz){if(hz!=25&&hz!=100)return false;decimation=hz/25;reset();return true;}
  void sample(uint32_t ir,uint32_t red,uint32_t threshold,float bpm) {
    if(ir<threshold || red<1000 || ir>=260000 || red>=260000) { reset(); return; }
    if(!used) status=1;
    sumIr+=ir;sumRed+=red;
    if(++sub<decimation) return;
    // Retain weak-signal resolution; choose a shared safe scale per window.
    irs[used]=sumIr/decimation;reds[used]=sumRed/decimation;sumIr=sumRed=sub=0;
    ++used;
    if(used<100) return;
    double mi=0,mr=0,vi=0,vr=0,cov=0;
    for(unsigned i=0;i<100;++i) {mi+=irs[i];mr+=reds[i];} mi/=100;mr/=100;
    for(unsigned i=0;i<100;++i) {double a=irs[i]-mi,b=reds[i]-mr;vi+=a*a;vr+=b*b;cov+=a*b;}
    double corr=vi>0 && vr>0?cov/sqrt(vi*vr):0;
    quality=float(fmax(0,fmin(1,corr)));
    double pi=sqrt(vi/100)/mi,pr=sqrt(vr/100)/mr;
    int32_t oxygen=-999,hr=-999;int8_t ov=0,hv=0;
    bool signal=corr>=.8 && pi>=.001 && pi<=.15 && pr>=.001 && pr<=.15;
    bool weak=false;float periodCorr=0,periodIr=0,periodRed=0;
    PpgPeriod period=PpgPeriod::measure(irs,reds);
    bool periodic=period.valid;periodCorr=period.correlation;periodIr=period.irRatio;periodRed=period.redRatio;
    if(!signal && pi>=.00015 && pr>=.00015 && pi<=.15 && pr<=.15 && periodic) {
      signal=weak=true;quality=periodCorr;
    }
    if(signal) {
      uint32_t imax=0,rmax=0,imin=UINT32_MAX,rmin=UINT32_MAX;
      for(unsigned i=0;i<100;++i) {
        if(irs[i]>imax) imax=irs[i];if(irs[i]<imin) imin=irs[i];
        if(reds[i]>rmax) rmax=reds[i];if(reds[i]<rmin) rmin=reds[i];
      }
      uint64_t product=uint64_t(imax>rmax?imax:rmax)*((imax-imin)>(rmax-rmin)?(imax-imin):(rmax-rmin));
      uint32_t scale=1;while(product/(uint64_t(scale)*scale)>1000000000ULL) scale*=2;
      uint32_t wi[100],wr[100];
      for(unsigned i=0;i<100;++i) {wi[i]=irs[i]/scale;wr[i]=reds[i]/scale;}
      maxim_heart_rate_and_oxygen_saturation(wi,100,wr,&oxygen,&ov,&hr,&hv);
    }
    referenceHeartRateAgrees=hv && hr>=40 && hr<=200 && isfinite(bpm) && fabsf(hr-bpm)<=fmaxf(12,bpm*.2f);
    // Preserve reference validity/range checks and verify a fresh optical
    // period independently in both channels. The peak counter is diagnostic.
    bool rhythm=hv && hr>=40 && hr<=200 && periodic;
    pulseBpm=signal && rhythm?period.bpm:NAN;
    ++windows;candidateOxygen=oxygen;candidateHeartRate=hr;
    signalAccepted=signal;rhythmAccepted=rhythm;oxygenAccepted=ov;
    perfusionIr=pi;perfusionRed=pr;
    periodicCorrelation=periodCorr;periodicIr=periodIr;periodicRed=periodRed;
    if(signal && rhythm && ov && oxygen>=70 && oxygen<=100) {
      good=isfinite(previous) && fabsf(oxygen-previous)<=3?good+1:1;
      unsigned required=weak?4:2;
      previous=float(oxygen);value=good>=required?previous:NAN;status=good>=required?3:1;
    } else {value=previous=NAN;good=0;status=signal && rhythm && ov?4:2;}
    memmove(irs,irs+25,75*sizeof(uint32_t));memmove(reds,reds+25,75*sizeof(uint32_t));
    used=75;
  }
};
