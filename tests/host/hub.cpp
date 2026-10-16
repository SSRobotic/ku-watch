#include <cassert>
#include <fstream>
#include <iostream>
#include "../../large_display/KU_Hub/hub_ui.h"
int main() {
  using namespace Hub;using namespace KuLink;
  TelemetryPacket p;p.flags=Clock|Environment|Pulse|Battery|Motion;p.temperature=34.5;p.humidity=57;p.bpm=75;p.batteryVolts=4;p.batteryPercent=80;
  p.temperatureLimit=35;p.iaqLimit=150;p.area=1;p.zoom=3;p.elapsed=65000;p.distance=120;p.food=0;p.xp=31;p.pose=4;
  char msg[40];auto s=state(p,true,7,0,msg);
  assert(s.recordElapsed==65000 && s.recordDistance==120 && s.bpm==75 && isnan(s.spo2));
  s=state(p,false,7,0,msg);assert(!s.bme && !s.recording && isnan(s.bpm) && isnan(s.batteryVolts) && isnan(s.latitude));
  assert(!action(p,7,0,false).valid);
  p.flags=0;assert(!action(p,7,0,true).valid);
  p.flags=Clock;assert(action(p,7,0,true).action==RecordStart);
  p.flags=Recording;assert(action(p,7,0,true).action==RecordStop); // stop works even if clock lost
  assert(action(p,6,0,true).argument==0);assert(action(p,6,1,true).argument==2);
  // Telemetry must retain the new close scales on the hub instead of clamping
  // them to the old default. Both ends must cycle from 100 m to 50 m to 25 m.
  for(unsigned zoom: {4u,5u}) {
    p.zoom=zoom;s=state(p,true,6,0,msg);assert(s.mapZoom==zoom);
  }
  p.zoom=0;assert(action(p,6,1,true).argument==4);
  p.zoom=4;assert(action(p,6,1,true).argument==5);
  p.zoom=5;assert(action(p,6,1,true).argument==3);
  p.zoom=255;s=state(p,true,6,0,msg);assert(s.mapZoom==MapZoom::DEFAULT_INDEX);
  p.temperatureLimit=80;assert(action(p,1,1,true).a==80);
  p.iaqLimit=10;assert(action(p,8,0,true).b==10);
  Touch touch;
  assert(touch.update(true,true,240,425,0,100)==1); // navigation reacts before release
  for(int i=0;i<200;++i)assert(touch.update(true,true,240,425,0,101+i)==-1);
  assert(touch.update(true,false,0,0,0,301)==-1);
  assert(touch.update(true,true,240,425,0,320)==-1); // short release noise is not a second press
  assert(touch.update(true,false,0,0,0,330)==-1);
  assert(touch.update(true,false,0,0,0,380)==-1);
  assert(touch.update(true,false,340,425,0,500,true)==2); // completed IRQ-backed short tap
  assert(touch.update(true,false,340,425,0,501,true)==-1); // no latched-gesture repeat
  assert(touch.update(true,true,240,372,7,700)==-1); // START/STOP only on release
  for(unsigned i=0;i<200;++i)assert(touch.update(true,true,240,372,7,701+i)==-1);
  assert(touch.update(true,false,0,0,7,901)==-1);
  assert(touch.update(true,false,0,0,7,941)==3); // zero-coordinate release still activates once
  assert(touch.update(true,false,0,0,7,951)==-1);
  assert(touch.update(true,true,240,372,7,1000)==-1);
  assert(touch.update(true,true,400,372,7,1001)==-1);
  assert(touch.update(true,false,240,372,7,1002)==-1);
  assert(touch.update(true,false,240,372,7,1042)==-1); // drag-out cancels
  touch.update(true,true,240,372,7,1200);touch.update(false,false,0,0,7,1201);
  touch.update(true,false,0,0,7,1202);assert(touch.update(true,false,0,0,7,1242)==-1);
  Touch wrap;assert(wrap.update(true,true,240,372,7,0xffffff00u)==-1);
  assert(wrap.update(true,false,0,0,7,0xfffffff0u)==-1);assert(wrap.update(true,false,0,0,7,40)==3);
  assert(target(240,372,7)==3 && target(240,372,0)==-1);
  // Full sampled contact/release histories may be drained together after a
  // slow render. Six distinct rapid taps must still give six page changes.
  Touch rapid;unsigned accepted=0;
  for(unsigned n=0;n<6;++n){uint32_t at=1000+n*104;
    for(unsigned t=0;t<104;t+=4){int event=rapid.update(true,t<24,t<24?322:0,t<24?431:0,0,at+t);accepted+=event==2;}}
  assert(accepted==6);
  Touch landing;assert(landing.update(true,true,0,0,0,100)==-1);
  assert(landing.update(true,true,322,431,0,104)==2);
  assert(landing.update(true,true,322,431,1,108)==-1);
  Touch overflow;overflow.cancel();assert(overflow.update(true,true,240,372,7,100)==-1);
  overflow.update(true,false,0,0,7,104);assert(overflow.update(true,false,0,0,7,144)==-1);
  assert(overflow.update(true,true,322,431,7,148)==2);
  Screen screen;screen.pixels=new uint16_t[480*480];screen.small=new Face::Canvas;
  for(unsigned page=0;page<11;++page) {
    s=state(p,false,page,0,msg);screen.render(s,p,false,"SEARCHING FOR WATCH");
    if(page==0)for(int y=0;y<360;++y)for(int x=0;x<360;++x)
      assert(screen.pixels[(y+12)*480+x+60]==screen.small->pixels[(y*2/3)*240+x*2/3]);
    unsigned lit=0;for(unsigned i=0;i<480*480;++i)lit+=screen.pixels[i]!=0;assert(lit>1000);
    if(page==0 || page==6 || page==10){std::ofstream out("output/hub_preview_"+std::to_string(page)+".ppm",std::ios::binary);out<<"P6\n480 480\n255\n";for(unsigned i=0;i<480*480;++i){uint16_t c=screen.pixels[i];char rgb[]={char(((c>>11)&31)*255/31),char(((c>>5)&63)*255/63),char((c&31)*255/31)};out.write(rgb,3);}}
  }
  std::cout<<"Hub fresh/stale data, recording clock gate, limits, touch hold/release/drag/error and 11-screen render checks passed\n";
}
