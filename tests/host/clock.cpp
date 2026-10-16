#include <cassert>
#include <iostream>
#include "clock_model.h"
int main() {
  using namespace ClockModel;Model c;
  const uint64_t real=1791474000,us=123456;
  auto saved=checkpoint(real-7200);assert(intact(saved));
  c.begin(real-86400,0,&saved,us);
  assert(c.restored && !c.live && c.source==Waiting);
  assert(c.utc(us+60000000)==real-7140); // saved estimate is never trusted as current UTC
  assert(c.synchronize(real,Manual,us));assert(c.live);
  assert(c.utc(us+25*3600ULL*1000000)==real+25*3600ULL);
  // GPS/NTP stay eligible after USB/manual synchronization and after drift.
  assert(c.synchronize(real+900,Network,us+60000000));assert(c.source==Network);
  assert(c.synchronize(real+901,Gps,us+61000000));assert(c.source==Gps);
  assert(c.utc(us+62000000)==real+902);
  c.begin(real-86400,real+1000,&saved,0);assert(c.live && c.source==Retained);
  assert(c.utc(30000000)==real+1030); // warm reset retained hardware time
  c.begin(real,0,&saved,0);assert(!c.live); // a cold restart cannot know the off duration
  assert(!c.restoreFromHub(0,0));assert(!c.live);
  assert(c.restoreFromHub(real+4000,0));assert(c.source==Hub && c.live);
  assert(c.utc(30000000)==real+4030);
  assert(!c.restoreFromHub(real-4000,31000000));assert(c.source==Hub);
  assert(c.synchronize(real+4032,Gps,32000000));assert(c.source==Gps);
  assert(!c.restoreFromHub(real-4000,33000000));assert(c.source==Gps);
  saved.crc^=1;c.begin(real,0,&saved,0);assert(!c.restored && !c.live);
  assert(!c.synchronize(0,Gps,0));assert(!c.synchronize(4102444800ULL,Network,0));
  assert(!c.synchronize(real,Waiting,0));assert(c.synchronize(real,Gps,0));
  std::cout<<"Clock holdover, warm/cold restart, source correction and CRC checks passed\n";
}
