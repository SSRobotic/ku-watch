#pragma once
#include <math.h>
#include <stdint.h>

// Linear detrending and lag-zero-normalized autocorrelation follow the method
// described by Robert Fraczkiewicz, MAX30102_by_RF (2017-2020):
// https://github.com/aromring/MAX30102_by_RF
// Its published autocorrelation threshold is 0.5. Here BOTH optical channels
// must pass, with a stricter Pearson threshold of 0.90 and RMS >= 10 counts.
// No stale estimate, synthetic sample, or previous BPM participates in a pass.
struct PpgPeriod {
  float bpm=NAN,correlation=0,irRatio=0,redRatio=0;
  bool valid=false;
  static PpgPeriod measure(const uint32_t* ir,const uint32_t* red) {
    PpgPeriod result;
    float ai[100],ar[100],mi=0,mr=0,bi=0,br=0;
    for(int i=0;i<100;++i){mi+=ir[i];mr+=red[i];}
    mi/=100;mr/=100;
    for(int i=0;i<100;++i){float x=i-49.5f;bi+=x*(ir[i]-mi);br+=x*(red[i]-mr);}
    bi/=83325; br/=83325;
    float vi=0,vr=0,cov=0;
    for(int i=0;i<100;++i){
      float x=i-49.5f;ai[i]=ir[i]-mi-bi*x;ar[i]=red[i]-mr-br*x;
      vi+=ai[i]*ai[i];vr+=ar[i]*ar[i];cov+=ai[i]*ar[i];
    }
    if(vi<10000 || vr<10000)return result;
    result.correlation=cov/sqrtf(vi*vr);
    if(result.correlation<.90f)return result;
    float ci[41]={},cr[41]={};
    for(int lag=6;lag<=40;++lag){
      float si=0,sr=0;
      for(int i=0;i<100-lag;++i){si+=ai[i]*ai[i+lag];sr+=ar[i]*ar[i+lag];}
      ci[lag]=(si/(100-lag))/(vi/100);cr[lag]=(sr/(100-lag))/(vr/100);
    }
    for(int lag=7;lag<=39;++lag){
      if(ci[lag]<.5f || cr[lag]<.5f || ci[lag]<=ci[lag-1] || ci[lag]<ci[lag+1])continue;
      // First supported local maximum prevents choosing a multiple of a cycle.
      float denominator=ci[lag-1]-2*ci[lag]+ci[lag+1];
      float delta=fabsf(denominator)>1e-6f?.5f*(ci[lag-1]-ci[lag+1])/denominator:0;
      delta=fmaxf(-.5f,fminf(.5f,delta));
      float bpm=1500/(lag+delta);
      if(bpm<40 || bpm>180)return result;
      result.bpm=bpm;result.irRatio=ci[lag];result.redRatio=cr[lag];result.valid=true;
      return result;
    }
    return result;
  }
};
