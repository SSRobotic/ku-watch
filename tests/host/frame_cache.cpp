#include <cassert>
#include <stdint.h>
#include <vector>
#include "frame_cache.h"
#ifdef NDEBUG
#error Active assertions required
#endif
int main(){
  FrameCache c;std::vector<uint16_t> pixels(c.PIXELS,0x1234),previous(c.PIXELS);
  assert(!c.same(pixels.data(),0,8));c.complete();assert(!c.same(pixels.data(),0,8));
  c.attach(previous.data());assert(!c.same(pixels.data(),0,8));
  for(unsigned y=0;y<c.HEIGHT;y+=8)c.written(pixels.data(),y,8);
  c.complete();assert(c.same(pixels.data(),0,8));assert(c.same(pixels.data(),232,8));
  pixels[239*240+239]^=1;assert(!c.same(pixels.data(),232,8));assert(c.same(pixels.data(),0,8));
  c.written(pixels.data(),232,8);assert(c.same(pixels.data(),232,8));
  c.invalidate();assert(!c.same(pixels.data(),0,8)); // page change, reset or test forces a complete transfer
  assert(!c.same(pixels.data(),239,8));
}
