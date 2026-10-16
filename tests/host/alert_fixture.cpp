#include <cassert>
#include <initializer_list>
#include "alert_fixture.h"
int main(){
  for(bool air:{false,true}){
    AlertFixture f;f.begin(100,123,air);
    assert(f.advance(100)&&f.sequence==1&&f.model.mask()==0);
    assert(!f.advance(1099)&&f.sequence==1);
    assert(f.advance(1100)&&f.model.mask()==0);
    assert(f.advance(2100)&&f.model.mask()==(air?2:1));
    assert(!f.advance(3100)&&!f.expired(15099)&&f.expired(15100));
    f.stop();assert(!f.advance(20000)&&!f.active);
  }
  AlertFixture gap;gap.begin(0,1,false);gap.advance(0);gap.advance(2000);gap.advance(3000);assert(!gap.model.mask());
  AlertFixture rollover;rollover.begin(0xffffff00u,2,false);rollover.advance(0xffffff00u);rollover.advance(744);rollover.advance(1744);assert(rollover.model.mask()==1);
}
