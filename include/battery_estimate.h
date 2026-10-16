#pragma once
#include <math.h>

// Generic 1S Li-ion/LiPo 4.20 V curve only. Not measured for the user's cell.
// A voltage estimate changes with load, temperature and charging; not coulomb counting.
inline float batteryPercent(float volts) {
  if(!isfinite(volts) || volts<2.5f || volts>4.25f) return NAN;
  const float v[]={3.30f,3.50f,3.60f,3.70f,3.75f,3.80f,3.85f,3.90f,4.00f,4.10f,4.20f};
  const float p[]={0,5,10,25,40,50,60,70,80,90,100};
  if(volts<=v[0]) return 0;
  for(unsigned i=1;i<11;++i) if(volts<v[i]) return p[i-1]+(p[i]-p[i-1])*(volts-v[i-1])/(v[i]-v[i-1]);
  return 100;
}
