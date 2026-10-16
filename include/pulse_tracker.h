#pragma once
#include <stdint.h>
#include <math.h>

// Input is an ordered 25/100 Hz IR stream. Timing follows real samples, never FIFO drain time.
class PulseTracker {
  float baseline = 0, filtered = 0, previous = 0, amplitude = 40;
  float history[4] = {};
  uint32_t smooth[9]={}, smoothSum=0;
  unsigned smoothCount=0, smoothIndex=0;
  uint32_t sampleMs = 0, lastBeat = 0;
  unsigned warmup = 0, count = 0, index = 0;
  bool rising = false, haveBeat = false, armed = false;
  unsigned inputRate=100,tickMs=10,smoothSize=9,warmupSize=200;
  float baselineAlpha=.01f,filteredAlpha=.20f,amplitudeAlpha=.02f;
  void rate(unsigned hz) {
    inputRate=hz;tickMs=1000/hz;smoothSize=(hz*90+999)/1000;warmupSize=hz*2;
    baselineAlpha=1-powf(.99f,100.0f/hz);filteredAlpha=1-powf(.80f,100.0f/hz);amplitudeAlpha=1-powf(.98f,100.0f/hz);
  }
public:
  bool finger = false;
  float bpm = NAN;
  void reset() {unsigned hz=inputRate;*this=PulseTracker();rate(hz);}
  bool setSampleRate(unsigned hz){if(hz!=25&&hz!=100)return false;*this=PulseTracker();rate(hz);return true;}
  void sample(uint32_t ir, uint32_t threshold) {
    if (ir < threshold || ir >= 260000) { reset(); return; }
    finger = true;
    sampleMs += tickMs;
    // A 90 ms moving average suppresses small local maxima in real PPG.
    smoothSum-=smooth[smoothIndex];smooth[smoothIndex]=ir;smoothSum+=ir;
    smoothIndex=(smoothIndex+1)%smoothSize;if(smoothCount<smoothSize) ++smoothCount;
    float signal=float(smoothSum)/smoothCount;
    if (!warmup) baseline = signal;
    baseline += baselineAlpha * (signal - baseline);
    filtered += filteredAlpha * ((signal - baseline) - filtered);
    amplitude += amplitudeAlpha * (fabsf(filtered) - amplitude);
    // Require a negative excursion between beats: multiple positive peaks
    // on one pulse must not become additional beats.
    if(filtered < -fmaxf(20,amplitude*.4f)) armed=true;
    if (filtered > previous) rising = true;
    bool peak = rising && previous > fmaxf(20, amplitude * .55f) && filtered < previous;
    previous = filtered;
    if (peak) rising = false;
    if (warmup < warmupSize) { ++warmup; armed=false; return; }
    if (haveBeat && uint32_t(sampleMs-lastBeat) > 3000) {
      haveBeat = false; count = index = 0; bpm = NAN;
    }
    if (!peak || !armed || (haveBeat && uint32_t(sampleMs-lastBeat) < 300)) return;
    armed=false;
    if (haveBeat) {
      uint32_t interval = sampleMs - lastBeat;
      if (interval <= 2000) {
        history[index] = 60000.0f / interval;
        index = (index+1)%4;
        if (count < 4) ++count;
        if (count >= 2) {
          float total = 0;
          for (unsigned i=0;i<count;++i) total += history[i];
          bpm = total/count;
        }
      } else { count = index = 0; bpm = NAN; }
    }
    lastBeat = sampleMs; haveBeat = true;
  }
};
