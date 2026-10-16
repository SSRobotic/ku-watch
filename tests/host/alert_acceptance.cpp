// Rubric permits simulated inputs. They are local fixtures, never telemetry.
#include <cassert>
#include <chrono>
#include <cstdio>
#include <ctime>
#include <thread>
#include "environment_alert.h"
constexpr uint8_t INA226_I2C_ADDRESS=0x44;
namespace Pin {constexpr unsigned PAGE_COUNT=11;}
#include "face.h"
int main(){
  EnvAlert::Model alerts;Face::State state;state.page=1;state.bme=true;
  static Face::Canvas frame;
  const auto start=std::chrono::steady_clock::now();
  FILE* report=fopen("output/acceptance/alert_simulation.json","wb");assert(report);
  fprintf(report,"{\"boundary\":\"Three simulated 1 Hz observations through production model and portable display; not BSEC physical cadence or browser paint\",\"samples\":[");
  long long triggerMs=0;
  for(unsigned n=0;n<3;n++){
    std::this_thread::sleep_until(start+std::chrono::seconds(n));
    alerts.update(n+1,true,36,true,160,1,true,true);
    assert(alerts.mask()==(n==2?3:0));
    state.temp=36;state.iaq=160;state.iaqValid=true;state.alertMask=alerts.mask();
    state.alertTemperature=alerts.temperature.state;state.alertAir=alerts.air.state;
    frame.render(state);
    auto ms=std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-start).count();
    fprintf(report,"%s{\"elapsed_ms\":%lld,\"timestamp\":%lld,\"alert_temp_state\":%u,\"alert_iaq_state\":%u,\"alert_mask\":%u}",n?",":"",(long long)ms,(long long)std::time(nullptr),alerts.temperature.state,alerts.air.state,alerts.mask());
    if(alerts.mask())triggerMs=ms;
  }
  assert(triggerMs>=2000&&triggerMs<=5000);
  fprintf(report,"],\"trigger_ms\":%lld,\"simulated_model_and_render_passed\":true,\"physical_bsec_5s_verified\":false,\"browser_paint_verified\":false}",triggerMs);fclose(report);
  printf("Rubric simulated three distinct 1 Hz samples: model + renderer alert at %lld ms; physical BSEC/browser still require separate acceptance.\n",triggerMs);
}
