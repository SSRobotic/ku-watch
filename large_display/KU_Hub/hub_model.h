#pragma once
#include <math.h>
#include "espnow_protocol.h"
#include "map_zoom.h"

namespace Hub {
struct Command {KuLink::Action action=KuLink::Heartbeat;int32_t argument=0;float a=0,b=0;bool valid=false;};
// Navigation remains usable locally while disconnected. Actions that alter the
// watch require a fresh authenticated snapshot; the actual watch owns state.
inline Command action(const KuLink::TelemetryPacket& p,unsigned page,unsigned button,bool fresh) {
  Command c;if(!fresh || button>1)return c;
  switch(page) {
    case 1:c.action=KuLink::AlertLimits;c.a=fminf(80,fmaxf(-20,p.temperatureLimit+(button?1:-1)));c.b=p.iaqLimit;break;
    case 4:c.action=KuLink::CompassCalibration;break;
    case 5:c.action=KuLink::Setup;break;
    case 6:c.action=button?KuLink::MapZoom:KuLink::MapArea;c.argument=button?MapZoom::next(p.zoom):(p.area==0?1:0);break;
    case 7:if(!(p.flags&KuLink::Recording) && !(p.flags&KuLink::Clock))return c;
      c.action=p.flags&KuLink::Recording?KuLink::RecordStop:KuLink::RecordStart;break;
    case 8:c.action=KuLink::AlertLimits;c.a=p.temperatureLimit;c.b=fminf(500,fmaxf(10,p.iaqLimit+(button?10:-10)));break;
    case 10:c.action=button?KuLink::PetPlay:KuLink::PetFeed;break;
    default:return c;
  }
  c.valid=true;return c;
}
inline const char* label(unsigned page,unsigned button,bool recording) {
  switch(page) {
    case 1:return button?"TEMP +":"TEMP -";
    case 4:return "CALIBRATE";case 5:return "PHONE SETUP";
    case 6:return button?"ZOOM":"AREA";
    case 7:return recording?"STOP + SAVE":"START WALK";
    case 8:return button?"IAQ +":"IAQ -";
    case 10:return button?"PLAY":"FEED";default:return "";
  }
}
inline unsigned buttons(unsigned page){return page==1||page==6||page==8||page==10?2:page==4||page==5||page==7?1:0;}
// Stable physical rectangles inside the round 480 px screen. Release must stay
// in the pressed target. Finger hold never repeats a recording/care command.
inline int target(unsigned x,unsigned y,unsigned page) {
  if(y>=398 && y<463) {if(x>=80&&x<192)return 0;if(x>=192&&x<288)return 1;if(x>=288&&x<400)return 2;}
  unsigned count=buttons(page);
  if(y>=350 && y<393) {
    if(count==1 && x>=151&&x<329)return 3;
    if(count==2 && x>=105&&x<230)return 3;
    if(count==2 && x>=250&&x<375)return 4;
  }
  return -1;
}
}
