#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>

// Exact pixel comparison, never a hash approximation. Storage is supplied by
// the caller so the device can fall back to full frames if PSRAM is unavailable.
class FrameCache {
  uint16_t* memory=nullptr;
  bool valid=false;
public:
  static constexpr size_t WIDTH=240,HEIGHT=240,PIXELS=WIDTH*HEIGHT;
  void attach(uint16_t* buffer){memory=buffer;valid=false;}
  void invalidate(){valid=false;}
  bool same(const uint16_t* pixels,size_t y,size_t rows)const{
    return memory && valid && y<=HEIGHT && rows<=HEIGHT-y &&
      memcmp(memory+y*WIDTH,pixels+y*WIDTH,rows*WIDTH*sizeof(uint16_t))==0;
  }
  void written(const uint16_t* pixels,size_t y,size_t rows){
    if(memory && y<=HEIGHT && rows<=HEIGHT-y)memcpy(memory+y*WIDTH,pixels+y*WIDTH,rows*WIDTH*sizeof(uint16_t));
  }
  void complete(){valid=memory!=nullptr;}
};
