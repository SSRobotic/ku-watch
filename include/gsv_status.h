#pragma once
#include <TinyGPS++.h>
#include <stdint.h>

// GSV is available before a position fix. Publish only complete, ordered groups;
// TinyGPSCustom updates these fields only after the sentence checksum passes.
class GsvStatus {
  TinyGPSCustom messages, number, visible, snr[4];
  uint32_t startedAt=0;
  unsigned expected=0, groupSize=0, pendingView=0, pendingSignal=0;
  bool pendingSignalValid=false;
  static bool decimal(const char* s,unsigned& value,unsigned limit) {
    if(!*s) return false;
    value=0;
    for(;*s;++s) {
      if(*s<'0'||*s>'9') return false;
      value=value*10+unsigned(*s-'0');
      if(value>limit) return false;
    }
    return true;
  }
public:
  bool valid=false, signalValid=false;
  uint32_t at=0;
  unsigned count=0, signal=0;
  GsvStatus(TinyGPSPlus& p,const char* name)
    : messages(p,name,1),number(p,name,2),visible(p,name,3),
      snr{{p,name,7},{p,name,11},{p,name,15},{p,name,19}} {}
  void update(uint32_t now,unsigned fields) {
    if(!messages.isUpdated()) return;
    unsigned total=0, part=0, view=0, strongest=0;
    bool ok=decimal(messages.value(),total,25);
    ok=decimal(number.value(),part,25)&&ok;
    ok=decimal(visible.value(),view,99)&&ok;
    bool hasSignal=false;
    unsigned slot=0;
    for(auto& field:snr) {
      unsigned value=0;
      // Custom fields omitted by a short GSV sentence retain their old value.
      // Only consume satellite slots actually present in this sentence.
      if(decimal(field.value(),value,99) && part &&
         4*(part-1)+slot<view && 7+4*slot<=fields) {
        hasSignal=true; if(value>strongest) strongest=value;
      }
      ++slot;
    }
    if(!ok || fields<3 || !total || !part || part>total) { expected=0; return; }
    if(part==1) {
      expected=1; groupSize=total; pendingView=view;
      pendingSignal=0; pendingSignalValid=false; startedAt=now;
    }
    if(part!=expected || total!=groupSize || view!=pendingView || uint32_t(now-startedAt)>=5000) {
      expected=0; return;
    }
    if(hasSignal) {
      pendingSignalValid=true;
      if(strongest>pendingSignal) pendingSignal=strongest;
    }
    ++expected;
    if(part==total) {
      count=view; signal=pendingSignal; signalValid=pendingSignalValid;
      valid=true; at=now; expected=0;
    }
  }
  bool fresh(uint32_t now,uint32_t staleMs) const {
    return valid && uint32_t(now-at)<staleMs;
  }
};
