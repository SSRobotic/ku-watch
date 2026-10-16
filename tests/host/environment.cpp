#include <cstdio>
#include <cstdlib>
#include "environment_sensor.h"
TwoWire Wire;HostSerial Serial;
static uint32_t clockMs=0;
unsigned long millis(){return clockMs;}
static unsigned checks=0;
#define CHECK(x) do {++checks;if(!(x)){std::fprintf(stderr,"FAIL %d: %s\n",__LINE__,#x);std::exit(1);}}while(0)
static void output(float iaq,unsigned accuracy,bool stable,bool runIn) {
  Bsec2::pending={7,{{BSEC_OUTPUT_RAW_TEMPERATURE,30,0},{BSEC_OUTPUT_RAW_HUMIDITY,55,0},
    {BSEC_OUTPUT_RAW_PRESSURE,100100,0},{BSEC_OUTPUT_RAW_GAS,85000,0},
    {BSEC_OUTPUT_IAQ,iaq,uint8_t(accuracy)},{BSEC_OUTPUT_STABILIZATION_STATUS,float(stable),0},
    {BSEC_OUTPUT_RUN_IN_STATUS,float(runIn),0}}};
}
int main(){
  EnvironmentSensor e;e.tick(clockMs);
  CHECK(!e.live && !e.iaqValid);
  output(25,0,false,false);e.tick(++clockMs);
  CHECK(e.live && e.temp==30 && e.pressure==1001 && e.gas==85000);
  CHECK(!e.iaqValid && !std::isfinite(e.iaq));
  output(25,1,true,false);e.tick(++clockMs);CHECK(!e.iaqValid);
  output(42,1,true,true);e.tick(++clockMs);CHECK(e.iaqValid && e.iaq==42 && e.accuracy==1);
  CHECK(Preferences::writes==0);
  Bsec2::data.status=0;output(42,3,true,true);e.tick(++clockMs);
  CHECK(!e.iaqValid && !std::isfinite(e.gas) && e.live);
  Bsec2::data.status=0x30;output(42,3,true,true);e.tick(++clockMs);
  CHECK(e.iaqValid && Preferences::writes==1);
  output(42,3,true,true);e.tick(++clockMs);CHECK(Preferences::writes==1);
  output(501,3,true,true);e.tick(++clockMs);CHECK(!e.iaqValid);
  output(NAN,3,true,true);e.tick(++clockMs);CHECK(!e.iaqValid);
  output(42,3,true,true);e.tick(++clockMs);CHECK(e.iaqValid);
  Bsec2::pending={1,{{BSEC_OUTPUT_RAW_TEMPERATURE,31,0}}};e.tick(++clockMs);
  CHECK(!e.live && !e.iaqValid && !std::isfinite(e.pressure));
  output(42,3,true,true);e.tick(++clockMs);
  clockMs+=12001;e.tick(clockMs);CHECK(!e.live && !e.iaqValid && !std::isfinite(e.temp));
  int starts=Bsec2::begins;clockMs+=3000;e.tick(clockMs);CHECK(Bsec2::begins>starts);
  output(42,3,true,true);e.tick(++clockMs);CHECK(e.iaqValid);
  Bsec2::fault=-5;e.tick(++clockMs);CHECK(!e.live && !e.iaqValid && e.status==-5);
  Bsec2::fault=0;Bsec2::stateOk=false;clockMs+=5000;e.tick(clockMs);
  CHECK(Preferences::removes==1); // Corrupted calibration discarded, sensor reinitialized.
  output(30,1,true,true);e.tick(++clockMs);CHECK(e.live && e.iaqValid);
  std::printf("Environment lifecycle: %u checks passed (BSEC boundary mocked).\n",checks);
}
