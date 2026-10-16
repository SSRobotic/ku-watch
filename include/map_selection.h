#pragma once
#include "activity_format.h"

namespace WatchMap {
#pragma pack(push,1)
struct SavedSelection {
  uint32_t magic=0x4b554d53;
  uint8_t version=1,area=0,automatic=1,reserved=0;
  uint32_t crc=0;
};
#pragma pack(pop)
static_assert(sizeof(SavedSelection)==12,"Map selection format");
class Selection {
public:
  unsigned area=0;
  bool automatic=true;
  static bool valid(const SavedSelection& saved) {
    return saved.magic==0x4b554d53 && saved.version==1 && saved.area<2 &&
      saved.automatic<=1 && saved.reserved==0 &&
      saved.crc==Activity::crc32(&saved,offsetof(SavedSelection,crc));
  }
  SavedSelection snapshot() const {
    SavedSelection saved;saved.area=area;saved.automatic=automatic;
    saved.crc=Activity::crc32(&saved,offsetof(SavedSelection,crc));return saved;
  }
  void available(bool first,bool second) {
    if((area==0 && first) || (area==1 && second)) return;
    area=first?0:second?1:0;
  }
  bool restore(const SavedSelection& saved,bool first,bool second) {
    if(!valid(saved)) return false;
    area=saved.area;automatic=saved.automatic;available(first,second);return true;
  }
  bool manual(unsigned next,bool first,bool second) {
    if(next>1 || !(next==0?first:second)) return false;
    bool changed=area!=next || automatic;area=next;automatic=false;return changed;
  }
  bool autoMode() {bool changed=!automatic;automatic=true;return changed;}
  // Cycle only usable choices: AUTO -> first area -> second area -> AUTO.
  bool cycle(bool first,bool second) {
    if(!first && !second) return false;
    if(automatic) return manual(first?0:1,first,second);
    if(area==0 && second) return manual(1,first,second);
    return autoMode();
  }
  bool follow(bool firstCovered,bool secondCovered) {
    if(!automatic || (area==0?firstCovered:secondCovered)) return false;
    if(firstCovered && area!=0) {area=0;return true;}
    if(secondCovered && area!=1) {area=1;return true;}
    return false;
  }
};
}
