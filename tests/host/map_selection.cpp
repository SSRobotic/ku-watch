#include <cstdio>
#include <cstdlib>
#include "map_selection.h"
#include "button.h"
static unsigned checks=0;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"FAIL %d %s\n",__LINE__,#x);exit(1);}}while(0)
int main() {
  WatchMap::Selection choice;CHECK(choice.area==0 && choice.automatic);
  CHECK(choice.follow(false,true));CHECK(choice.area==1 && choice.automatic);
  auto saved=choice.snapshot();CHECK(WatchMap::Selection::valid(saved));
  WatchMap::Selection reboot;CHECK(reboot.restore(saved,true,true));CHECK(reboot.area==1 && reboot.automatic);
  CHECK(!reboot.follow(false,false));CHECK(reboot.area==1); // reboot with no fix retains last area
  CHECK(reboot.manual(1,true,true));CHECK(!reboot.automatic);CHECK(!reboot.follow(true,false));CHECK(reboot.area==1);
  saved=reboot.snapshot();WatchMap::Selection powerOn;CHECK(powerOn.restore(saved,true,true));CHECK(powerOn.area==1 && !powerOn.automatic);
  CHECK(powerOn.cycle(true,true));CHECK(powerOn.area==1 && powerOn.automatic);
  CHECK(powerOn.cycle(true,true));CHECK(powerOn.area==0 && !powerOn.automatic);
  CHECK(powerOn.cycle(true,true));CHECK(powerOn.area==1 && !powerOn.automatic);
  CHECK(!powerOn.manual(0,false,true));CHECK(powerOn.area==1); // missing slot can't be selected
  CHECK(!powerOn.manual(2,true,true));
  CHECK(powerOn.autoMode());CHECK(!powerOn.autoMode());CHECK(powerOn.follow(true,false));CHECK(powerOn.area==0);
  CHECK(!powerOn.follow(true,true));CHECK(powerOn.area==0); // overlapping coverage does not alternate
  auto invalid=saved;invalid.area=0;CHECK(!WatchMap::Selection::valid(invalid));CHECK(!powerOn.restore(invalid,true,true));CHECK(powerOn.area==0);
  for(unsigned n=0;n<sizeof(saved);++n) {
    invalid=saved;reinterpret_cast<unsigned char*>(&invalid)[n]^=1;CHECK(!WatchMap::Selection::valid(invalid));
  }
  invalid=saved;invalid.area=2;invalid.crc=Activity::crc32(&invalid,offsetof(WatchMap::SavedSelection,crc));CHECK(!WatchMap::Selection::valid(invalid));
  invalid=saved;invalid.automatic=2;invalid.crc=Activity::crc32(&invalid,offsetof(WatchMap::SavedSelection,crc));CHECK(!WatchMap::Selection::valid(invalid));
  CHECK(powerOn.restore(saved,true,false));CHECK(powerOn.area==0 && !powerOn.automatic); // unavailable saved area falls back safely
  WatchMap::Selection one;one.available(false,true);CHECK(one.area==1);CHECK(one.cycle(false,true));CHECK(one.area==1 && !one.automatic);
  CHECK(one.cycle(false,true));CHECK(one.automatic);CHECK(!one.cycle(false,false));
  MenuTaps taps;CHECK(!taps.click(100));CHECK(taps.waiting());CHECK(!taps.leave(500,false));CHECK(taps.click(540));
  CHECK(!taps.waiting());CHECK(!taps.leave(1000,false));
  CHECK(!taps.click(1100));CHECK(!taps.leave(1600,true));taps.cancel();CHECK(!taps.leave(1900,false));
  CHECK(!taps.click(2000));CHECK(taps.leave(2450,false)); // exactly one delayed page change
  printf("PASS %u map selection/button checks\n",checks);
}
