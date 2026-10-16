#pragma once
#include <stdint.h>
#include <stddef.h>

// PUBACKs may arrive out of order. Retire only the acknowledged prefix so
// durable journal rows always advance in capture order. Reset only when the
// MQTT client/outbox is destroyed; unsent journal rows remain on flash.
class TelemetryWindow {
public:
  static constexpr size_t CAPACITY=8;
  struct Flight {uint64_t token;int packet;uint32_t at;bool acknowledged;};
private:
  Flight rows[CAPACITY]{};
  size_t used=0;
public:
  size_t size() const {return used;}
  bool full() const {return used==CAPACITY;}
  void clear() {used=0;}
  bool push(uint64_t token,int packet,uint32_t at) {
    if(full() || !token || packet<0)return false;
    rows[used++]={token,packet,at,false};return true;
  }
  bool acknowledge(int packet) {
    for(size_t i=0;i<used;++i)if(rows[i].packet==packet){rows[i].acknowledged=true;return true;}
    return false;
  }
  bool contains(int packet) const {
    for(size_t i=0;i<used;++i)if(rows[i].packet==packet)return true;
    return false;
  }
  uint64_t ready() const {return used && rows[0].acknowledged?rows[0].token:0;}
  void retire() {if(ready()){for(size_t i=1;i<used;++i)rows[i-1]=rows[i];--used;}}
  bool expired(uint32_t now) const {return used && uint32_t(now-rows[0].at)>60000;}
};
