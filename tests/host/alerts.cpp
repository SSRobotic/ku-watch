#include <cstdio>
#include <cstdlib>
#include <initializer_list>
#include "environment_alert.h"
constexpr uint8_t INA226_I2C_ADDRESS=0x44;
namespace Pin {constexpr unsigned PAGE_COUNT=11;}
#include "face.h"
static unsigned checks=0;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"FAIL %d %s\n",__LINE__,#x);exit(1);}}while(0)
static void sample(EnvAlert::Model& m,uint32_t n,float t,float q=160,bool valid=true){m.update(n,true,t,valid,q,1,true,true);}
int main(){
  EnvAlert::Model m;CHECK(m.mask()==0 && m.temperature.state==0 && m.air.state==0);
  sample(m,1,36);CHECK(m.temperature.above==1 && m.mask()==0);
  for(unsigned i=0;i<100;++i)sample(m,1,36); // repeated loop calls are one reading
  CHECK(m.temperature.above==1 && m.air.above==1 && m.mask()==0);
  sample(m,2,36);CHECK(m.mask()==0);sample(m,3,36);CHECK(m.mask()==3);
  sample(m,4,35,150);CHECK(m.mask()==3); // hysteresis holds
  sample(m,5,34,140);sample(m,6,34,140);CHECK(m.mask()==3);
  sample(m,7,34,140);CHECK(m.mask()==0 && m.temperature.state==1 && m.air.state==1);
  sample(m,8,36);sample(m,9,35,150);sample(m,10,36);sample(m,11,36);CHECK(m.mask()==0);
  sample(m,12,36);CHECK(m.mask()==3);
  m.update(12,false,NAN,false,NAN,0,false,false);CHECK(m.mask()==0 && m.temperature.state==0 && m.air.state==0);
  sample(m,12,36);CHECK(m.mask()==0 && m.temperature.state==0); // no stale recount after loss
  sample(m,13,36,160,false);CHECK(m.temperature.above==1 && m.air.state==0);
  sample(m,14,36,160,false);sample(m,15,36,160,false);CHECK(m.mask()==1);
  for(unsigned flags=0;flags<4;++flags){EnvAlert::Model ready;
    for(unsigned n=1;n<5;++n)ready.update(n,true,30,true,200,1,flags&1,flags&2);
    CHECK(ready.mask()==(flags==3?2:0));CHECK(ready.air.state==(flags==3?2:0));
  }
  for(unsigned accuracy:{0u,4u,255u}) {EnvAlert::Model bad;for(unsigned n=1;n<5;++n)bad.update(n,true,30,true,200,accuracy,true,true);CHECK(bad.air.state==0);}
  for(float q:{NAN,INFINITY,-1.f,501.f}) {EnvAlert::Model bad;for(unsigned n=1;n<5;++n)sample(bad,n,30,q);CHECK(bad.air.state==0);}
  for(float t:{NAN,INFINITY,-41.f,86.f}) {EnvAlert::Model bad;for(unsigned n=1;n<5;++n)sample(bad,n,t);CHECK(bad.temperature.state==0);}
  EnvAlert::Model wrap;sample(wrap,UINT32_MAX-1,36);sample(wrap,UINT32_MAX,36);sample(wrap,0,36);CHECK(wrap.mask()==3);
  EnvAlert::Model gap;sample(gap,1,36);sample(gap,3,36);sample(gap,4,36);CHECK(gap.mask()==0);
  sample(gap,5,36);CHECK(gap.mask()==3);
  CHECK(m.configure(40,200));CHECK(m.mask()==0);sample(m,15,50);CHECK(m.mask()==0 && m.temperature.above==0);
  sample(m,16,41,201);sample(m,17,41,201);sample(m,18,41,201);CHECK(m.mask()==3);
  CHECK(!m.configure(NAN,150));CHECK(!m.configure(35,9));CHECK(!m.configure(81,150));CHECK(m.settings.temperature==40);
  auto saved=EnvAlert::save(m.settings);EnvAlert::Settings restored;CHECK(EnvAlert::restore(saved,restored));CHECK(restored.temperature==40 && restored.iaq==200);
  for(unsigned n=0;n<sizeof(saved);++n){auto corrupt=saved;reinterpret_cast<uint8_t*>(&corrupt)[n]^=1;CHECK(!EnvAlert::restore(corrupt,restored));}
  Face::State state;state.temp=36;state.bme=true;state.robotBubble=true;state.robotMessage="LET US DANCE";
  static Face::Canvas normal,alert;
  for(unsigned page=0;page<11;++page) {
    state.page=page;state.alertMask=0;normal.render(state);state.alertMask=3;alert.render(state);
    unsigned changed=0;
    for(unsigned y=0;y<240;++y)for(unsigned x=0;x<240;++x){
      if(normal.pixels[y*240+x]!=alert.pixels[y*240+x]) {++changed;CHECK(y>=25 && y<34 && x>=40 && x<200);}
    }
    CHECK(changed>0);
  }
  state.page=1;FILE* f=fopen("output/alert_environment_preview.ppm","wb");CHECK(f);fprintf(f,"P6\n240 240\n255\n");alert.render(state);
  for(auto p:alert.pixels){unsigned char rgb[]={uint8_t((p>>11)*255/31),uint8_t(((p>>5)&63)*255/63),uint8_t((p&31)*255/31)};fwrite(rgb,1,3,f);}fclose(f);
  printf("PASS environmental alert logic/settings/11-page layout: %u checks\n",checks);
}
