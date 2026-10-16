#include <cassert>
#include <iostream>
#include "telemetry_window.h"
int main() {
  TelemetryWindow w;assert(!w.ready());assert(!w.push(0,1,0));assert(!w.push(1,-1,0));
  for(int i=0;i<8;++i)assert(w.push(100+i,10+i,1000));
  assert(w.full());assert(!w.push(108,18,1000));assert(!w.acknowledge(99));
  // Later PUBACK cannot remove an earlier unacknowledged flash row.
  for(int i=7;i>0;--i)assert(w.acknowledge(10+i));assert(!w.ready());
  assert(!w.expired(61000));assert(w.expired(61001));
  assert(w.acknowledge(10));assert(w.acknowledge(10));
  for(int i=0;i<8;++i){assert(w.ready()==uint64_t(100+i));w.retire();}
  assert(!w.size());assert(!w.ready());
  // Wraparound timestamps and destruction/replay preserve non-ACKed records.
  assert(w.push(999,1,0xfffffff0));assert(!w.expired(100));assert(w.expired(60000));
  w.clear();assert(!w.acknowledge(1));assert(w.push(999,2,100));
  assert(!w.acknowledge(1));assert(!w.ready());assert(w.acknowledge(2));assert(w.ready()==999);
  std::cout<<"Ordered PUBACK window, replay and timeout checks passed\n";
}
