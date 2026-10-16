#include <fstream>
#include <cassert>
namespace Pin {constexpr unsigned PAGE_COUNT=11;}
constexpr unsigned INA226_I2C_ADDRESS=0x44;
#include "face.h"
int main() {
  Face::State s;s.page=5;s.setupActive=true;s.setupSsid="KU-WATCH-05D4";s.setupPassword="A1B2C3D4E5F6";
  Face::Canvas image;image.render(s);std::ofstream f("output/setup_preview.ppm",std::ios::binary);f<<"P6\n240 240\n255\n";
  for(auto c:image.pixels) {char rgb[3]={char(((c>>11)&31)*255/31),char(((c>>5)&63)*255/63),char((c&31)*255/31)};f.write(rgb,3);}
  for(const char* p=s.setupPassword;*p;++p) {unsigned sum=0;auto g=Face::glyph(*p);for(unsigned j=0;j<7;++j)sum+=g[j];assert(sum>0);}
}
