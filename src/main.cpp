#include <Arduino.h>
#include <Adafruit_GC9A01A.h>
#include <SPI.h>
#include <Wire.h>
#include <WiFi.h>
#include <sys/time.h>
#include "network_worker.h"
#include "environment_sensor.h"
#include "alert_service.h"
#include "alert_fixture.h"
#include "battery_sensor.h"
#include "battery_alert.h"
#include "pulse_sensor.h"
#include "gps_uart.h"
#include "activity_recorder.h"
#include "telemetry_store.h"
#include "map_service.h"
#include "robot_service.h"
#include <esp_timer.h>
#include <time.h>
#include "config.h"
#include "build_stamp.h"
#include "button.h"
#include "face.h"
#include "runtime_settings.h"
#include "espnow_service.h"
#include "ota_service.h"
#include "setup_service.h"
#include "clock_service.h"
#include "frame_cache.h"

// The assembled button also pulls LCD RST low. Keep GPIO5 passive and use
// the driver's software-reset path so it never drives HIGH against the switch.
static Adafruit_GC9A01A display(&SPI, Pin::DC, Pin::CS, -1);
static Face::Canvas* frame=nullptr;
static FrameCache frameCache;
static Face::State state;
static MenuButton button;
static EnvironmentSensor environment;
static AlertService alerts;
static AlertFixture alertFixture;
static BatterySensor battery;
static BatteryAlert::State batteryAlert=BatteryAlert::Waiting;
static PulseSensor pulse;
static GpsUart gps;
static ActivityRecorder recorder;
static uint32_t telemetrySession=0,telemetrySequence=0;
static MapService maps;
static WatchMap::Trail trail;
static RobotService robot;
static bool robotFeedRequested=false;
static bool robotPlayRequested=false;
static MenuTaps robotTaps,mapTaps;
static uint32_t robotSpeechAt=0,robotSpeechMs=0;
static const char* robotSpeech="HELLO I AM KU-BOT";
static RobotPet::Pose robotGesture=RobotPet::Pose::Wave;
static bool recordToggleRequested=false;
static bool dirty = true, tonePlaying = false;
static void alertFixtureTick(uint32_t now) {
  if(alertFixture.expired(now)){alertFixture.stop();dirty=true;Serial.println("ALERTTEST AUTO STOPPED");}
  if(alertFixture.advance(now)){
    dirty=true;Serial.printf("ALERTTEST INPUT id=%lu sequence=%lu elapsed_ms=%lu mask=%u\n",(unsigned long)alertFixture.id,(unsigned long)alertFixture.sequence,(unsigned long)(now-alertFixture.started),alertFixture.model.mask());
    // As with live alerts, MQTT and LCD rendering start from the same new model
    // state independently. Waiting for LCD SPI before publication added latency.
    char message[512];snprintf(message,sizeof(message),
      "{\"kind\":\"alert_fixture\",\"simulated\":true,\"phase\":\"sample\",\"test_id\":%lu,\"sequence\":%lu,\"channel\":\"%s\",\"input_elapsed_ms\":%lu,\"alert_mask\":%u,\"alert_temp_state\":%u,\"alert_iaq_state\":%u,\"firmware\":\"%s\",\"timestamp\":%lu,\"alert_temp_limit\":35,\"alert_iaq_limit\":150}",
      (unsigned long)alertFixture.id,(unsigned long)alertFixture.sequence,alertFixture.air?"IAQ":"TEMP",(unsigned long)(now-alertFixture.started),
      alertFixture.model.mask(),alertFixture.model.temperature.state,alertFixture.model.air.state,WatchExt::VERSION,(unsigned long)time(nullptr));
    LiveNetwork::publishDiagnostic(message);
  }
}
static uint32_t toneAt = 0, toneMs = 0;
static ClockService watchClock;
static bool networkReady=false;
static bool accelLive=false,magLive=false;
static bool sensorBusReady=false;
static unsigned paintedPage=0;
static uint32_t paintedFrames=0;
static uint32_t lastPaintMs=0,maxPaintGapMs=0,motionReads=0,lastMotionMs=0;
static uint32_t renderMicros=0,maxRenderMicros=0;
static bool displayReady=false,lcdRecoveryPending=false;
static uint32_t lcdLowAt=0;
static volatile bool buttonFallingEdge=false;
static RuntimeSettings runtimeSettings;
static EspNowService displayLink;
static OtaService ota;
static SetupService setupPortal;
static bool setupRequested=false,screenAsleep=false;
static uint32_t interactionAt=0;
static bool magCalibrating=false;
static uint32_t magCalibrationAt=0,magCalibrationSamples=0;
static float magMinimum[3]={},magMaximum[3]={};
static void startCompassCalibration() {
  magCalibrating=true;magCalibrationAt=millis();magCalibrationSamples=0;
  for(unsigned i=0;i<3;++i) {magMinimum[i]=32767;magMaximum[i]=-32768;}
  setupPortal.magCalibrationStatus="ROTATE ALL AXES FOR 60 SECONDS";
  Serial.println("MAGCAL START: ROTATE THROUGH ALL AXES FOR 60 SECONDS");
}
static void wakeScreen() {
  interactionAt=millis();
  if(screenAsleep) {screenAsleep=false;lcdRecoveryPending=true;lcdLowAt=millis()-80;dirty=true;}
}

static void IRAM_ATTR onButtonFalling() {
  __atomic_store_n(&buttonFallingEdge,true,__ATOMIC_RELAXED);
}

static void beep(uint32_t frequency, uint32_t duration) {
  if (!SOUND_DRIVER_CONNECTED) return;
  ledcWriteTone(0, frequency);
  toneAt = millis(); toneMs = duration; tonePlaying = true;
}
static void controls() {
  uint32_t now = millis();
  bool down=digitalRead(Pin::BUTTON)==LOW;
  // Also latch short reset pulses occurring while the display driver is waiting.
  if(__atomic_exchange_n(&buttonFallingEdge,false,__ATOMIC_RELAXED) || down || digitalRead(Pin::RST)==LOW) {
    lcdRecoveryPending=true; lcdLowAt=now;
  }
  if (tonePlaying && uint32_t(now-toneAt) >= toneMs) {
    ledcWriteTone(0, 0); tonePlaying = false;
  }
  switch(button.update(down, now)) {
    case ButtonEvent::Down:
      wakeScreen();
      Serial.printf("BUTTON DOWN gpio4=%d lcd_rst5=%d\n",digitalRead(Pin::BUTTON),digitalRead(Pin::RST));
      beep(2400, 45); break;
    case ButtonEvent::Click:
      if(state.page==6) {
        if(mapTaps.click(now)) {
          maps.cycle();state.map=maps.current();state.mapAutomatic=maps.automatic();dirty=true;
        }
        break;
      }
      if(state.page==10) {
        if(robotTaps.click(now)) {robotPlayRequested=true;dirty=true;}
        break;
      }
      state.page = (state.page + 1) % Pin::PAGE_COUNT; dirty = true;
      Serial.printf("PAGE %u\n", state.page + 1); break;
    case ButtonEvent::Home:
      if(state.page==5) {setupRequested=true;dirty=true;break;}
      if(state.page==10) {robotTaps.cancel();robotFeedRequested=true;dirty=true;break;}
      if(state.page==6) {mapTaps.cancel();state.mapZoom=MapZoom::next(state.mapZoom);dirty=true;Serial.printf("MAP ZOOM %u\n",state.mapZoom);break;}
      if(state.page==7) { recordToggleRequested=true; break; }
      state.page = 0; dirty = true; beep(1600, 80);
      Serial.println("HOME"); break;
    default: break;
  }
  if(state.page!=10) robotTaps.cancel();
  if(state.page!=6) mapTaps.cancel();
  if(state.page==6 && mapTaps.leave(now,down)) {
    state.page=7;dirty=true;Serial.println("PAGE 8");
  }
  if(state.page==10 && robotTaps.leave(now,down)) {
    state.page=0;dirty=true;Serial.println("HOME");
  }
}
static void clockTick() {
  watchClock.tick();
  bool changed=state.timeSet!=watchClock.model.live || state.clockSource!=watchClock.model.label();
  state.timeSet=watchClock.model.live;state.clockSource=watchClock.model.label();
  state.timeFromGps=watchClock.model.source==ClockModel::Gps;state.timeFromNet=watchClock.model.source==ClockModel::Network;
  time_t local=time_t(watchClock.utc()+7*3600ULL);
  struct tm t;gmtime_r(&local,&t);
  if(changed || state.second!=t.tm_sec || state.minute!=t.tm_min)dirty=true;
  state.hour=t.tm_hour;state.minute=t.tm_min;state.second=t.tm_sec;
  state.day=t.tm_mday;state.month=t.tm_mon+1;state.weekday=t.tm_wday;
}
static void max30102Tick(uint32_t now);
static void envTick(uint32_t now);
static void consoleTick();
static bool mapRenderService() {
  controls();gps.poll();
  if(sensorBusReady) {max30102Tick(millis());envTick(millis());}
  return !lcdRecoveryPending;
}
static void initializeDisplay() {
  frameCache.invalidate();
  display.begin(DISPLAY_SPI_HZ); display.setRotation(DISPLAY_ROTATION);
  display.invertDisplay(DISPLAY_INVERT); displayReady=true;screenAsleep=false;interactionAt=millis();dirty=true;
}
static void displayRecoveryTick() {
  if(!lcdRecoveryPending || digitalRead(Pin::BUTTON)==LOW || digitalRead(Pin::RST)==LOW ||
     uint32_t(millis()-lcdLowAt)<80) return;
  // LCD initialization blocks button polling. Finish the MAP/ROBOT tap decision
  // first so a quick second tap is not swallowed by the existing reset wiring.
  if((state.page==10 && robotTaps.waiting()) || (state.page==6 && mapTaps.waiting())) return;
  lcdRecoveryPending=false;
  initializeDisplay();
  Serial.println("LCD AUTO RECOVERED AFTER RELEASE");
}
static void paint() {
  if(screenAsleep)return;
  if(!frame || !displayReady || lcdRecoveryPending) {dirty=true;return;}
  dirty = false; const bool testFrame=alertFixture.active;
  const unsigned page=testFrame?(alertFixture.air?8:1):state.page;uint32_t began=micros();
  const uint32_t fixtureId=alertFixture.id,fixtureSequence=alertFixture.sequence,fixtureStarted=alertFixture.started,fixtureInputAt=alertFixture.inputAt;
  const bool fixtureAir=alertFixture.air;
  Face::State visible=state;
  if(alertFixture.active) {
    visible.page=alertFixture.air?8:1;visible.bme=visible.iaqValid=true;
    visible.temp=alertFixture.air?25:36;visible.iaq=alertFixture.air?200:50;
    visible.iaqAccuracy=3;visible.iaqStable=visible.iaqRunIn=true;
    visible.alertMask=alertFixture.model.mask();
    visible.alertTemperature=alertFixture.model.temperature.state;visible.alertAir=alertFixture.model.air.state;
  }
  frame->render(visible);
  if(alertFixture.active){frame->rect(35,61,170,10,Face::BLACK);frame->center(62,"TEST INPUT - NOT SENSOR",1,Face::LIME);}
  renderMicros=uint32_t(micros()-began);if(renderMicros>maxRenderMicros) maxRenderMicros=renderMicros;
  if(lcdRecoveryPending) {dirty=true;return;}
  // Give each strip its own address window and finish SPI before servicing controls.
  // Keep pulse FIFO/GPS service frequent even with a slower display clock.
  if(testFrame || paintedPage!=page)frameCache.invalidate();
  for(int y=0;y<240;y+=8) {
    if(!frameCache.same(frame->pixels,y,8)) {
      display.startWrite(); display.setAddrWindow(0,y,240,8);
      display.writePixels(frame->pixels+y*240,240*8,true);
      display.endWrite();
      frameCache.written(frame->pixels,y,8);
    }
    controls(); gps.poll();
    if(sensorBusReady) { max30102Tick(millis()); envTick(millis()); }
    if(sensorBusReady) consoleTick();
    alertFixtureTick(millis());
    if(lcdRecoveryPending) {dirty=true;return;}
  }
  frameCache.complete();
  paintedPage=page; ++paintedFrames;
  uint32_t completed=millis();if(lastPaintMs)maxPaintGapMs=max(maxPaintGapMs,uint32_t(completed-lastPaintMs));lastPaintMs=completed;
  if(testFrame && alertFixture.active && fixtureId==alertFixture.id && fixtureSequence && alertFixture.painted!=fixtureSequence) {
    unsigned redPixels=0;for(unsigned y=25;y<34;++y)for(unsigned x=40;x<200;++x)if(frame->pixels[y*240+x]==0xf800)++redPixels;
    char proof[512];snprintf(proof,sizeof(proof),
      "{\"kind\":\"alert_fixture\",\"simulated\":true,\"phase\":\"displayed\",\"test_id\":%lu,\"sequence\":%lu,\"channel\":\"%s\",\"input_elapsed_ms\":%lu,\"display_elapsed_ms\":%lu,\"alert_mask\":%u,\"alert_temp_state\":%u,\"alert_iaq_state\":%u,\"alert_pixels\":%u,\"firmware\":\"%s\",\"timestamp\":%lu,\"alert_temp_limit\":35,\"alert_iaq_limit\":150}",
      (unsigned long)fixtureId,(unsigned long)fixtureSequence,fixtureAir?"IAQ":"TEMP",
      (unsigned long)(fixtureInputAt-fixtureStarted),(unsigned long)(completed-fixtureStarted),
      visible.alertMask,visible.alertTemperature,visible.alertAir,redPixels,WatchExt::VERSION,(unsigned long)watchClock.utc());
    Serial.printf("ALERTTEST DISPLAY %s queued=0\n",proof);
    alertFixture.painted=fixtureSequence;
  }
}
static bool ack(uint8_t address) {
  Wire.beginTransmission(address); return Wire.endTransmission() == 0;
}
static bool readSensor(uint8_t address, uint8_t reg, uint8_t *data, uint8_t length) {
  Wire.beginTransmission(address); Wire.write(reg);
  if(Wire.endTransmission(false)!=0 || Wire.requestFrom(address,length)!=length) return false;
  for(uint8_t i=0;i<length;++i) data[i]=Wire.read();
  return true;
}
static bool writeSensor(uint8_t address, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(address); Wire.write(reg); Wire.write(value);
  return Wire.endTransmission()==0;
}
static void gy51Init() {
  if(ack(0x18)) {
    writeSensor(0x18,0x20,0x27); writeSensor(0x18,0x23,0x08);
    state.gy51=true; Serial.println("GY-51 accelerometer initialized 0x18");
  }
  if(ack(0x1e)) {
    writeSensor(0x1e,0x00,0x70); writeSensor(0x1e,0x01,0x20); writeSensor(0x1e,0x02,0x00);
    state.gy51=true; Serial.println("GY-51 magnetometer initialized 0x1E");
  }
}
static void gy51Tick(uint32_t now) {
  static uint32_t next=0;
  if(int32_t(now-next)<0) return;
  next=now+500;
  uint8_t data[6];
  accelLive=readSensor(0x18,0x80|0x28,data,6);
  if(accelLive) {
    state.accX=int16_t((uint16_t(data[1])<<8)|data[0]);
    state.accY=int16_t((uint16_t(data[3])<<8)|data[2]);
    state.accZ=int16_t((uint16_t(data[5])<<8)|data[4]);
    state.gy51=true;
  }
  magLive=readSensor(0x1e,0x03,data,6);
  if(magLive) {
    state.magX=int16_t((uint16_t(data[0])<<8)|data[1]);
    state.magZ=int16_t((uint16_t(data[2])<<8)|data[3]);
    state.magY=int16_t((uint16_t(data[4])<<8)|data[5]);
    state.gy51=true;
    if(state.magX==-4096 || state.magY==-4096 || state.magZ==-4096)magLive=false;
  }
  int16_t raw[3]={state.magX,state.magY,state.magZ};
  state.heading=magLive?WatchExt::heading(raw,runtimeSettings.value):NAN;
  if(magCalibrating && magLive) {
    for(unsigned i=0;i<3;++i) {magMinimum[i]=min(magMinimum[i],float(raw[i]));magMaximum[i]=max(magMaximum[i],float(raw[i]));}
    ++magCalibrationSamples;
  }
  if(magCalibrating && uint32_t(now-magCalibrationAt)>=60000) {
    magCalibrating=false;auto s=runtimeSettings.value;s.magCalibrated=1;
    memcpy(s.magMin,magMinimum,sizeof(s.magMin));memcpy(s.magMax,magMaximum,sizeof(s.magMax));
    bool ok=magCalibrationSamples>=80 && runtimeSettings.save(s);
    setupPortal.magCalibrationStatus=ok?"SAVED - VERIFY DIRECTION WITH WATCH LEVEL":"FAILED - CHECK AXES AND ROTATE AGAIN";
    Serial.println(ok?"MAGCAL SAVED; HEADING IS MAGNETIC AND REQUIRES LEVEL WATCH":"MAGCAL FAILED; INVALID AXIS OR INSUFFICIENT MOTION");
  }
  state.gy51=accelLive || magLive;
  ++motionReads;lastMotionMs=now;
  dirty=true;
}
static String jsonNumber(double value,unsigned places=2) {
  return isfinite(value)?String(value,places):String("null");
}
static void networkTick(uint32_t now) {
  if(!networkReady) return;
  LiveNetwork::Status status{};
  if(xQueuePeek(LiveNetwork::statuses,&status,0)==pdTRUE) {
    state.networkErrors=status.errors;
    if(state.wifi!=status.wifi || state.mqtt!=status.mqtt) {
      state.wifi=status.wifi; state.mqtt=status.mqtt; dirty=true;
      Serial.printf("NETWORK wifi=%u mqtt=%u error=%d sent=%lu heap=%u\n",status.wifi,status.mqtt,status.error,status.sent,ESP.getFreeHeap());
    }
  }
  if(state.networkPending!=status.pending || state.networkDropped!=status.dropped || state.networkStorage!=status.storage) {
    state.networkPending=status.pending;state.networkDropped=status.dropped;state.networkStorage=status.storage;
    if(state.page==5)dirty=true;
  }
  static uint32_t sentAt=0;
  if(uint32_t(now-sentAt)<MQTT_INTERVAL_MS) return;
  // Preserve fixed cadence instead of adding render delay every second.
  // Skip missed slots after long stalls; never invent historical observations.
  sentAt+=uint32_t(now-sentAt)/MQTT_INTERVAL_MS*MQTT_INTERVAL_MS;
  auto g=gps.reading();
  String payload; payload.reserve(2200);
  payload="{\"temp\":"+jsonNumber(state.bme?state.temp:NAN);
  payload+=",\"humidity\":"+jsonNumber(state.bme?state.humidity:NAN);
  payload+=",\"pressure\":"+jsonNumber(state.bme?state.pressure:NAN);
  payload+=",\"bpm\":"+jsonNumber(state.bpm,1);
  payload+=",\"spo2\":"+jsonNumber(state.spo2,0);
  payload+=",\"spo2_status\":"+String(state.spo2Status);
  payload+=",\"spo2_quality\":"+jsonNumber(pulse.spo2Quality,3);
  payload+=",\"spo2_valid\":"+String(isfinite(state.spo2)?"true":"false");
  payload+=",\"gas_ohms\":"+jsonNumber(state.gas,0);
  payload+=",\"iaq\":"+jsonNumber(state.iaq,1);
  payload+=",\"iaq_accuracy\":"+String(state.iaqAccuracy);
  payload+=",\"iaq_valid\":"+String(state.iaqValid?"true":"false");
  payload+=",\"iaq_stable\":"+String(state.iaqStable?"true":"false");
  payload+=",\"iaq_run_in\":"+String(state.iaqRunIn?"true":"false");
  payload+=",\"bsec_status\":"+String(environment.status);
  payload+=",\"alert_temp_state\":"+String(alerts.model.temperature.state);
  payload+=",\"alert_iaq_state\":"+String(alerts.model.air.state);
  payload+=",\"alert_mask\":"+String(alerts.model.mask());
  payload+=",\"alert_battery_state\":"+String(unsigned(batteryAlert));
  payload+=",\"battery_low\":"+String(state.batteryLow?"true":"false");
  payload+=",\"firmware\":\""+String(WatchExt::VERSION)+"\"";
  payload+=",\"alert_temp_limit\":"+jsonNumber(alerts.model.settings.temperature);
  payload+=",\"alert_iaq_limit\":"+jsonNumber(alerts.model.settings.iaq);
  payload+=",\"battery_voltage\":"+jsonNumber(state.batteryVolts,3);
  payload+=",\"battery_percent\":"+jsonNumber(state.batteryPercent,0);
  payload+=",\"battery_valid\":"+String(state.batteryValid?"true":"false");
  payload+=",\"battery_current_ma\":"+jsonNumber(battery.currentMa,2);
  payload+=",\"battery_power_mw\":"+jsonNumber(battery.powerMw,2);
  payload+=",\"current_valid\":"+String(battery.currentValid?"true":"false");
  payload+=",\"heading\":"+jsonNumber(state.heading,1);
  payload+=",\"espnow_online\":"+String(displayLink.online?"true":"false");
  payload+=",\"ina226_detected\":"+String(state.batteryDetected?"true":"false");
  payload+=",\"ir\":"+jsonNumber(state.max30102?double(state.ir):NAN,0);
  payload+=",\"red\":"+jsonNumber(state.max30102?double(state.red):NAN,0);
  payload+=",\"finger\":"+String(state.finger?"true":"false");
  payload+=",\"pulse_live\":"+String(state.max30102?"true":"false");
  payload+=",\"env_live\":"+String(state.bme?"true":"false");
  payload+=",\"acc_live\":"+String(accelLive?"true":"false");
  payload+=",\"mag_live\":"+String(magLive?"true":"false");
  payload+=",\"acc_x\":"+jsonNumber(accelLive?state.accX:NAN,0);
  payload+=",\"acc_y\":"+jsonNumber(accelLive?state.accY:NAN,0);
  payload+=",\"acc_z\":"+jsonNumber(accelLive?state.accZ:NAN,0);
  payload+=",\"mag_x\":"+jsonNumber(magLive?state.magX:NAN,0);
  payload+=",\"mag_y\":"+jsonNumber(magLive?state.magY:NAN,0);
  payload+=",\"mag_z\":"+jsonNumber(magLive?state.magZ:NAN,0);
  payload+=",\"gps_fix\":"+String(g.reliable()?"true":"false");
  payload+=",\"gps_raw_fix\":"+String(g.fix?"true":"false");
  payload+=",\"latitude\":"+jsonNumber(g.reliable()?g.latitude:NAN,7);
  payload+=",\"longitude\":"+jsonNumber(g.reliable()?g.longitude:NAN,7);
  payload+=",\"altitude\":"+jsonNumber(g.reliable()?g.altitude:NAN);
  payload+=",\"speed_kmh\":"+jsonNumber(g.reliable()?g.speed:NAN);
  payload+=",\"satellites\":"+jsonNumber(g.data?double(g.satellites):NAN,0);
  payload+=",\"satellites_view\":"+jsonNumber(g.viewValid?double(g.inView):NAN,0);
  payload+=",\"gps_signal\":"+jsonNumber(g.signalValid?double(g.signal):NAN,0);
  payload+=",\"gps_data\":"+String(g.data?"true":"false");
  payload+=",\"gps_hdop\":"+jsonNumber(g.fix?g.hdop:NAN);
  payload+=",\"gps_age_s\":"+jsonNumber(g.positionAge!=0xffffffffu?double(g.positionAge)/1000:NAN,1);
  payload+=",\"gps_chars\":"+String(gps.receiver.chars());
  payload+=",\"gps_checksum_errors\":"+String(gps.receiver.checksumErrors());
  payload+=",\"recording\":"+String(recorder.active?"true":"false");
  payload+=",\"elapsed_s\":"+String(recorder.elapsedMs/1000);
  payload+=",\"distance_m\":"+jsonNumber(recorder.meters());
  payload+=",\"activity_id\":"+String(recorder.id);
  payload+=",\"uptime_ms\":"+String(now);
  payload+=",\"wifi_rssi\":"+jsonNumber(status.wifi?double(status.rssi):NAN,0);
  payload+=",\"heap_free\":"+String(ESP.getFreeHeap());
  payload+=",\"storage_free\":"+jsonNumber(recorder.ready?double(recorder.freeBytes):NAN,0);
  payload+=",\"record_samples\":"+String(recorder.samples);
  payload+=",\"mqtt_sent\":"+String(status.sent);
  char utc[24]; snprintf(utc,sizeof(utc),"%llu",watchClock.utc());
  payload+=",\"timestamp\":"+String(state.timeSet?utc:"null");
  uint64_t token=(uint64_t(telemetrySession)<<32)|++telemetrySequence;
  char sampleId[24];snprintf(sampleId,sizeof(sampleId),"%08lx-%08lx",(unsigned long)telemetrySession,(unsigned long)telemetrySequence);
  payload+=",\"sample_id\":\""+String(sampleId)+"\"";
  payload+=",\"device\":\"ku-watch-"+String(uint32_t(ESP.getEfuseMac()),HEX)+"\"}";
  LiveNetwork::Sample sample{};sample.token=token;sample.capturedMs=now;
  if(payload.length()<sizeof(sample.json)) {
    payload.toCharArray(sample.json,sizeof(sample.json));LiveNetwork::capture(sample);
  }

}
static void scanTick(uint32_t now) {
  static unsigned index=0; static uint32_t next=0;
  static const uint8_t addresses[]={INA226_I2C_ADDRESS,0x57,0x18,0x19,0x1d,0x1e};
  if(int32_t(now-next)<0) return;
  bool *flags[]={&state.addrIna,&state.addr57,&state.addr18,&state.addr19,&state.addr1d,&state.addr1e};
  bool found=ack(addresses[index]);
  if(*flags[index]!=found) { *flags[index]=found; dirty=true; }
  if(found) Serial.printf("I2C ACK 0x%02X (address only)\n",addresses[index]);
  ++index;
  if(index==sizeof(addresses)) { index=0; next=now+10000; }
  else next=now+150;
}
static void envTick(uint32_t now) {
  environment.tick(now);
  state.bme=environment.live;state.temp=environment.temp;
  state.humidity=environment.humidity;state.pressure=environment.pressure;
  state.gas=environment.gas;state.iaq=environment.iaq;state.iaqAccuracy=environment.accuracy;
  state.iaqValid=environment.iaqValid;state.iaqStable=environment.stable;state.iaqRunIn=environment.runIn;
  auto previousMask=state.alertMask;
  auto previousTemp=state.alertTemperature,previousAir=state.alertAir;
  alerts.model.update(environment.sequence,environment.live,environment.temp,environment.iaqValid,
    environment.iaq,environment.accuracy,environment.stable,environment.runIn);
  state.alertMask=alerts.model.mask();state.alertTemperature=alerts.model.temperature.state;state.alertAir=alerts.model.air.state;
  if(previousMask!=state.alertMask || previousTemp!=state.alertTemperature || previousAir!=state.alertAir) {
    dirty=true;alerts.report();
    if(state.alertMask & ~previousMask)beep(2200,120);
  }
  battery.tick(now);state.batteryDetected=battery.detected;state.batteryValid=battery.valid;
  state.batteryVolts=battery.volts;state.batteryPercent=battery.percent;
  state.batteryCurrent=battery.currentMa;state.batteryPower=battery.powerMw;
  auto previousBattery=batteryAlert;
  batteryAlert=BatteryAlert::update(batteryAlert,state.batteryValid,state.batteryPercent);
  state.batteryLow=batteryAlert==BatteryAlert::Low;
  if(previousBattery!=batteryAlert){dirty=true;if(state.batteryLow)beep(1800,120);}
}
static void max30102Tick(uint32_t now) {
  pulse.tick(now);
  bool changed=state.max30102!=pulse.live || state.finger!=pulse.finger ||
    isfinite(state.bpm)!=isfinite(pulse.bpm);
  state.max30102=pulse.live; state.finger=pulse.finger;
  state.ir=pulse.ir; state.red=pulse.red; state.bpm=pulse.bpm;
  state.spo2=pulse.spo2;state.spo2Status=pulse.spo2Status;
  static uint32_t reportAt=0;
  if(uint32_t(now-reportAt)>=1000) {
    reportAt=now; changed=true;
    Serial.printf("MAX30102 %s IR=%lu RED=%lu finger=%s BPM=",pulse.live?"LIVE":"WAITING",pulse.ir,pulse.red,pulse.finger?"YES":"NO");
    if(isfinite(pulse.bpm)) Serial.printf("%.1f",pulse.bpm); else Serial.print("--");
    Serial.printf(" dropped_batches=%lu gap=%lu fifo=%u/%u/%u\n",pulse.droppedBatches,pulse.lastGap,pulse.lastWrite,pulse.lastOverflow,pulse.lastRead);
  }
  if(changed) dirty=true;
}
static void gpsTick() {
  gps.poll(); auto r=gps.reading();
  bool changed=state.gpsData!=r.data || state.gpsFix!=r.fix;
  state.gpsData=r.data; state.gpsFix=r.fix; state.satellites=r.satellites;
  bool reliable=r.reliable();
  changed=changed || reliable!=state.gpsReliable;state.gpsReliable=reliable;
  state.gpsChars=gps.receiver.chars();
  state.gpsViewValid=r.viewValid; state.gpsSignalValid=r.signalValid;
  state.gpsInView=r.inView; state.gpsSignal=r.signal;
  state.latitude=r.latitude; state.longitude=r.longitude;
  state.altitude=r.altitude; state.speed=r.speed;
  watchClock.gps(r.utc,r.utcAgeMs);
  static uint32_t reportAt=0; uint32_t now=millis();
  if(uint32_t(now-reportAt)>=2000) { reportAt=now; gps.report(); changed=true; }
  if(changed) dirty=true;
}
static void activityTick() {
  if(recordToggleRequested) {
    recordToggleRequested=false;
    if(recorder.active) recorder.stop();
    else if(maps.importing() || ota.busy()) Serial.println("REC ERROR MAP IMPORT OR OTA BUSY");
    else if(!recorder.start(watchClock.utc(),state.timeSet)) recorder.report();
    dirty=true;
  }
  recorder.tick(gps.reading(),state.bpm);
  static uint32_t trailId=0,trailSamples=0;
  if(recorder.id!=trailId) {trailId=recorder.id;trailSamples=0;trail.clear();}
  if(recorder.samples!=trailSamples) {trailSamples=recorder.samples;trail.append(recorder.latestRecord);}
  recorder.exportTick();
  bool was=state.recording;
  state.recording=recorder.active; state.storageReady=recorder.ready;
  state.recordElapsed=recorder.elapsedMs; state.recordDistance=recorder.meters();
  state.recordId=recorder.id; state.recordFree=recorder.freeBytes; state.recordMessage=recorder.message;
  if(was!=state.recording) dirty=true;
}
static const char* robotHelp() {
  switch(state.page) {
    case 0:return state.timeSet && (state.hour>=23 || state.hour<6)?"TIME TO REST":"LET US GO FOR A WALK";
    case 1:return state.bme?"ENVIRONMENT IS LIVE":"SENSOR WARMING UP";
    case 2:return "CHECK DEVICES HERE";
    case 3:return !state.finger?"ALIGN SENSOR ON SKIN":!isfinite(state.bpm)?"KEEP YOUR ARM STILL":"READING YOUR PULSE";
    case 4:return state.gy51?"MOTION SENSOR READY":"MOTION IS WAITING";
    case 5:return state.mqtt?"CLOUD LINK IS ONLINE":state.wifi?"CLOUD IS CONNECTING":"WIFI IS OFFLINE";
    case 6:return state.gpsReliable?"POSITION FOUND":state.gpsFix?"GPS SIGNAL IS WEAK":"WAIT FOR GPS OUTSIDE";
    case 7:return state.recording?"WALK RECORDING ON":state.timeSet?"HOLD TO START A WALK":"SET THE CLOCK FIRST";
    case 8:return state.iaqValid?"AIR ESTIMATE READY":"AIR SENSOR LEARNING";
    case 9:return !state.batteryValid?"CHECK BATTERY SENSE":state.batteryPercent<20?"BATTERY IS LOW":"BATTERY LEVEL READY";
    default:return "DOUBLE TAP TO PLAY";
  }
}
static void robotSay(const char* text,RobotPet::Pose pose,uint32_t duration=4000) {
  robotSpeech=text;robotGesture=pose;robotSpeechAt=millis();robotSpeechMs=duration;dirty=true;
}
static void robotTick() {
  static unsigned page=999;
  static bool recording=false,fix=false,bubble=false;
  uint32_t now=millis();
  if(page!=state.page) {page=state.page;robotSay(robotHelp(),RobotPet::Pose::Wave);}
  bool stopped=recording && !state.recording;
  if(recording!=state.recording) {
    recording=state.recording;
    bool error=!strcmp(state.recordMessage,"WRITE ERROR") || !strcmp(state.recordMessage,"STORAGE ERROR");
    robotSay(recording?"LET US EXPLORE":error?"CHECK WALK STORAGE":"WALK SAVED WELL DONE",error?RobotPet::Pose::Think:RobotPet::Pose::Happy);
  }
  bool playing=uint32_t(now-robotSpeechAt)<robotSpeechMs &&
    (robotGesture==RobotPet::Pose::Dance || robotGesture==RobotPet::Pose::Jump || robotGesture==RobotPet::Pose::Stretch);
  if(fix!=state.gpsReliable) {
    fix=state.gpsReliable;
    // A fluctuating GPS must not repeatedly interrupt the action the user chose.
    if(!playing) robotSay(fix?"GPS POSITION FOUND":"WAIT FOR GPS SIGNAL",fix?RobotPet::Pose::Happy:RobotPet::Pose::Think);
  }
  unsigned before=RobotPet::level(robot.model.saved.xp);
  robot.model.activity(recorder.id,recorder.elapsedMs,recorder.meters());
  uint64_t utc=state.timeSet?watchClock.utc():0;
  robot.model.care(utc);
  if(state.gpsReliable && WatchMap::covers(state.map,state.latitude,state.longitude) && robot.model.visit(maps.selected(),utc))
    robotSay("WE FOUND A NEW PLACE",RobotPet::Pose::Happy);
  if(robotFeedRequested) {
    robotFeedRequested=false;
    bool fed=robot.model.feed(utc);robotSay(fed?"YUMMY THANK YOU":"5 MIN WALK FINDS FOOD",fed?RobotPet::Pose::Happy:RobotPet::Pose::Think,5000);
    robot.tick(true);Serial.println(fed?"ROBOT FED":"ROBOT NO FOOD");
  }
  if(robotPlayRequested) {
    robotPlayRequested=false;static unsigned action=0;
    static const RobotPet::Pose moves[]={RobotPet::Pose::Dance,RobotPet::Pose::Jump,RobotPet::Pose::Stretch};
    static const char* words[]={"LET US DANCE","JUMP WITH ME","STRETCH TOGETHER"};
    unsigned n=action++%3;robot.model.play();robotSay(words[n],moves[n],7000);robot.tick(true);Serial.printf("ROBOT PLAY %u\n",n);
  }
  unsigned current=RobotPet::level(robot.model.saved.xp);
  if(current>before) {robotSay("I GREW THANK YOU",RobotPet::Pose::Happy,6000);robot.tick(true);}
  robot.tick(stopped);
  now=millis();bool speaking=uint32_t(now-robotSpeechAt)<robotSpeechMs;
  uint32_t phase=now/600;
  if(phase!=state.robotPhase || bubble!=speaking) dirty=true;
  bubble=speaking;state.robotBubble=speaking;state.robotMessage=speaking?robotSpeech:robotHelp();
  state.robotPose=speaking?robotGesture:state.recording?RobotPet::Pose::Walk:robot.model.saved.energy<20?RobotPet::Pose::Sleep:
    state.page==6 && !state.gpsReliable?RobotPet::Pose::Think:state.page==1 || state.page==3 || state.page==8?RobotPet::Pose::Scan:
    (state.page==10 || state.page==0) && (phase/8)%4==1?RobotPet::Pose::Dance:
    (state.page==10 || state.page==0) && (phase/8)%4==2?RobotPet::Pose::Stretch:RobotPet::Pose::Idle;
  state.robotPhase=phase;state.robotXp=robot.model.saved.xp;state.robotFood=robot.model.saved.food;
  state.robotMood=robot.model.saved.mood;state.robotEnergy=robot.model.saved.energy;
}
static void consoleTick() {
  static char line[256]; static unsigned length=0; static bool overflow=false;
  unsigned budget=64;
  while(Serial.available() && budget--) {
    char c=Serial.read();
    if(c=='\r') continue;
    if(c=='\n') {
      if(!overflow) {
        line[length]=0;
        if(strcmp(line,"SETUP")==0) {setupRequested=true;state.page=5;dirty=true;}
        else if(strcmp(line,"SETUPAUTH")==0 && setupPortal.active) {
          // USB-only credential retrieval for local setup tools; never part of telemetry.
          Serial.printf("SETUPAUTH %s %s\n",WiFi.localIP().toString().c_str(),runtimeSettings.apPassword.c_str());
        }
        else if(strcmp(line,"LINKINFO")==0)displayLink.report();
        else if(strcmp(line,"LINKFORGET")==0) {displayLink.forget();Serial.println("ESPNOW PEER REMOVED");}
        else if(strcmp(line,"OTAINFO")==0)ota.report();
        else if(strcmp(line,"OTACHECK")==0)ota.check();
        else if(!strncmp(line,"ALERTTEST ",10)) {
          unsigned long identity=0;char channel[8]={},extra;
          if(!strcmp(line,"ALERTTEST STOP")){alertFixture.stop();dirty=true;Serial.println("ALERTTEST STOPPED");}
          else if(sscanf(line,"ALERTTEST START %lu %7s %c",&identity,channel,&extra)==2 && identity &&
                  (!strcmp(channel,"TEMP")||!strcmp(channel,"IAQ")) && !recorder.active && !ota.busy() && !setupPortal.active) {
            wakeScreen();alertFixture.begin(millis(),identity,!strcmp(channel,"IAQ"));dirty=true;
            Serial.printf("ALERTTEST BEGIN id=%lu channel=%s uptime_ms=%lu simulated=1 real_telemetry_unchanged=1\n",identity,channel,(unsigned long)millis());
            alertFixtureTick(millis());
          } else Serial.println("ALERTTEST ERROR USE START ID TEMP/IAQ WHEN IDLE OR STOP");
        }
        else if(!strcmp(line,"RATEINFO")) {
          Serial.printf("RATES uptime_ms=%lu pulse_samples=%lu pulse_sample_ms=%lu pulse_dropped=%lu env_sequence=%lu env_sample_ms=%lu motion_reads=%lu motion_ms=%lu frames=%lu paint_ms=%lu paint_max_gap_ms=%lu\n",
            (unsigned long)millis(),(unsigned long)pulse.acquiredSamples,(unsigned long)pulse.lastSampleMs(),(unsigned long)pulse.droppedBatches,
            (unsigned long)environment.sequence,(unsigned long)environment.lastSampleMs(),(unsigned long)motionReads,(unsigned long)lastMotionMs,
            (unsigned long)paintedFrames,(unsigned long)lastPaintMs,(unsigned long)maxPaintGapMs);
        }
        else if(strcmp(line,"SETTINGSINFO")==0) {
          Serial.printf("SETTINGS restored=%u led=%u red=%u averaging=%u idle=%u csv=%u shunt=%.5f compass=%u\n",runtimeSettings.restored,
            runtimeSettings.value.led,runtimeSettings.value.red,runtimeSettings.value.average,runtimeSettings.value.idleSeconds,
            runtimeSettings.value.logging,double(runtimeSettings.value.shuntOhms),runtimeSettings.value.magCalibrated);
        }
        else if(strcmp(line,"MAGCAL")==0) {
          startCompassCalibration();
        }
        else if(strcmp(line,"WAKE")==0)wakeScreen();
        else if(strcmp(line,"CLOCKINFO")==0)watchClock.report();
        else if(strcmp(line,"POWERINFO")==0)Serial.printf("POWER screen_sleep=%u idle=%u backlight_control=0 sensors_continuous=1\n",screenAsleep,runtimeSettings.value.idleSeconds);
        else if(strcmp(line,"PETSHOW")==0) {state.page=10;dirty=true;}
        else if(strcmp(line,"PETINFO")==0) {
          robot.report();
          Serial.printf("ROBOT ACTION pose=%u phase=%lu speaking=%u\n",unsigned(state.robotPose),(unsigned long)state.robotPhase,state.robotBubble);
        }
        else if(strcmp(line,"PETFEED")==0) {robotFeedRequested=true;}
        else if(strcmp(line,"PETPLAY")==0) {robotPlayRequested=true;}
        else if(strcmp(line,"MAPSHOW")==0) {state.page=6;dirty=true;}
        else if(!strncmp(line,"MAPZOOM ",8)) {
          if(strlen(line)==9 && line[8]>='0' && line[8]<'0'+MapZoom::COUNT) {state.mapZoom=line[8]-'0';dirty=true;Serial.printf("MAP ZOOM %u\n",state.mapZoom);}
          else Serial.printf("MAP ERROR ZOOM USE 0..%u\n",MapZoom::COUNT-1);
        }
        else if(alerts.command(line)) {
          if(!strcmp(line,"ALERTSHOW"))state.page=1;
          dirty=true;
        }
        else if(maps.command(line,recorder.active || recorder.exporting())) {
          state.map=maps.current();state.mapAutomatic=maps.automatic();recorder.refreshFree();
          if(!strcmp(line,"MAPEND") || !strcmp(line,"MAPCYCLE") || !strcmp(line,"MAPAUTO") || !strncmp(line,"MAPAREA ",8)) dirty=true;
        }
        else if(strncmp(line,"TIME ",5)==0) {
          char *end=nullptr; uint64_t value=strtoull(line+5,&end,10);
          if(end!=line+5 && *end==0 && value>=1704067200ULL && value<=4102444799ULL) {
            watchClock.set(value,ClockModel::Manual);clockTick();dirty=true;
            Serial.println("TIME OK");
          } else Serial.println("TIME ERROR: use Unix seconds");
        } else if(strcmp(line,"NEXT")==0) {
          state.page=(state.page+1)%Pin::PAGE_COUNT; dirty=true; beep(2400,45);
        } else if(strcmp(line,"HOME")==0) { state.page=0; dirty=true; }
        else if(strcmp(line,"GPSTRACE")==0) { gps.startTrace(); }
        else if(strcmp(line,"RECSTATUS")==0) { recorder.report(); }
        else if(strcmp(line,"RECLIST")==0) { recorder.list(); }
        else if(strcmp(line,"RECSTART")==0) {
          state.page=7; recordToggleRequested=!recorder.active; dirty=true;
          if(recorder.active) recorder.report();
        }
        else if(strcmp(line,"RECSTOP")==0) { recorder.stop(); dirty=true; }
        else if(strcmp(line,"REBOOT")==0) {
          if(recorder.active || recorder.exporting() || maps.importing()) Serial.println("REBOOT ERROR STOP RECORDING OR TRANSFER FIRST");
          else {robot.tick(true);Serial.println("REBOOT OK");Serial.flush();ESP.restart();}
        }
        else if(strncmp(line,"RECGET ",7)==0 || strncmp(line,"RECDELETE ",10)==0) {
          bool deleting=line[3]=='D'; const char* arg=line+(deleting?10:7); char* end=nullptr;
          unsigned long id=strtoul(arg,&end,10);
          if(end==arg || *end || !id || id>999999) Serial.println("REC ERROR INVALID ID");
          else if(deleting) recorder.remove(id); else recorder.get(id);
        }
        else if(strcmp(line,"NETINFO")==0) {
          LiveNetwork::Status status{};
          if(networkReady && xQueuePeek(LiveNetwork::statuses,&status,0)==pdTRUE)
            Serial.printf("NETWORK cloud=%u wifi=%u mqtt=%u error=%d sent=%lu heap=%u\n",KU_CLOUD_ENABLED,status.wifi,status.mqtt,status.error,status.sent,ESP.getFreeHeap());
          LiveNetwork::report(status);
        }
        else if(strcmp(line,"NETSHOW")==0) {state.page=5;dirty=true;}
        else if(!strncmp(line,"NETPAUSE ",9)) {
          char* end=nullptr;unsigned long seconds=strtoul(line+9,&end,10);
          if(end==line+9 || *end || seconds>900 || !networkReady)Serial.println("NETPAUSE ERROR USE 0..900 SECONDS");
          else {LiveNetwork::pause(seconds);Serial.printf("NETPAUSE OK %lu\n",seconds);}
        }
        else if(strcmp(line,"SENSORINFO")==0) {
          pulse.reportQuality();
          Serial.printf("SENSORS spo2=%.1f status=%u quality=%.3f gas=%.0f iaq=%.1f accuracy=%u stable=%u runin=%u bsec=%d battery=%.3f percent=%.0f ina=%u heap=%u\n",
            state.spo2,state.spo2Status,pulse.spo2Quality,state.gas,state.iaq,state.iaqAccuracy,
            state.iaqStable,state.iaqRunIn,environment.status,state.batteryVolts,state.batteryPercent,state.batteryDetected,ESP.getFreeHeap());
        }
        else if(strcmp(line,"INAINFO")==0) {
          unsigned found=0;
          for(uint8_t addr=0x40;addr<=0x4f;++addr) {
            if(!ack(addr)) continue;
            ++found;Serial.printf("INA CHECK addr=0x%02X",addr);
            for(uint8_t reg:{uint8_t(0xfe),uint8_t(0xff),uint8_t(0x00),uint8_t(0x02),uint8_t(0x06)}) {
              uint8_t data[2];
              if(readSensor(addr,reg,data,2)) {
                uint16_t value=(uint16_t(data[0])<<8)|data[1];
                Serial.printf(" reg%02X=%04X",reg,value);
                if(reg==0x02) Serial.printf(" bus_voltage=%.3f",double(value)*.00125);
              } else Serial.printf(" reg%02X=ERR",reg);
            }
            Serial.println();
          }
          if(!found) Serial.println("INA NONE: no I2C response at 0x40-0x4F");
        }
        else if(strcmp(line,"SCREENINFO")==0) {
          unsigned bodyPixels=0;
          for(int y=65;y<185;++y) for(int x=55;x<185;++x)
            if(frame && frame->pixels[y*240+x]!=Face::BLACK) ++bodyPixels;
          Serial.printf("SCREEN page=%u painted=%u frames=%lu body_pixels=%u button=%d rst=%d spi=%lu render_us=%lu max_render_us=%lu\n",
            state.page+1,paintedPage+1,(unsigned long)paintedFrames,bodyPixels,
            digitalRead(Pin::BUTTON),digitalRead(Pin::RST),(unsigned long)DISPLAY_SPI_HZ,(unsigned long)renderMicros,(unsigned long)maxRenderMicros);
          unsigned alertPixels=0;
          for(unsigned y=25;y<34;++y)for(unsigned x=40;x<200;++x)
            if(frame && frame->pixels[y*240+x]==0xf800)++alertPixels;
          Serial.printf("SCREEN alert_mask=%u alert_pixels=%u\n",state.alertMask,alertPixels);
        }
        else if(strcmp(line,"LCDRESET")==0) {
          lcdRecoveryPending=true; lcdLowAt=millis()-80;
          Serial.println("LCD RECOVERY REQUESTED");
        }
        else if(strncmp(line,"MAXRED ",7)==0) {
          char* end=nullptr;unsigned long level=strtoul(line+7,&end,10);
          auto s=runtimeSettings.value;s.red=uint8_t(level);
          if(end==line+7 || *end || level<1 || level>127 || !runtimeSettings.save(s) || !pulse.setRedCurrent(unsigned(level)))
            Serial.println("MAXRED ERROR use 1..127");
        }
        else if(strcmp(line,"MAXAVG 1")==0 || strcmp(line,"MAXAVG 0")==0) {
          auto s=runtimeSettings.value;s.average=line[7]=='1';
          if(runtimeSettings.save(s))pulse.setAveraging(s.average);else Serial.println("MAXAVG SAVE FAILED");
        }
        else if(strncmp(line,"MAXLED ",7)==0) {
          char* end=nullptr;unsigned long level=strtoul(line+7,&end,10);
          auto s=runtimeSettings.value;s.led=s.red=uint8_t(level);
          if(end==line+7 || *end || level<1 || level>63 || !runtimeSettings.save(s) || !pulse.setLedCurrent(unsigned(level)))
            Serial.println("MAXLED ERROR use 1..63");
        }
        else if(strcmp(line,"PULSETRACE")==0) { pulse.startTrace(); }
        else if(strcmp(line,"PULSEGET")==0) { pulse.reportTrace(); }
        else if(strcmp(line,"MAXINFO")==0) {
          Serial.print("MAX30102 REG");
          for(uint8_t reg:{uint8_t(0xff),uint8_t(0xfe),uint8_t(0x08),uint8_t(0x09),uint8_t(0x0a),uint8_t(0x0c),uint8_t(0x0d),uint8_t(0x04),uint8_t(0x05),uint8_t(0x06)}) {
            uint8_t value;
            if(readSensor(0x57,reg,&value,1)) Serial.printf(" %02X=%02X",reg,value);
            else Serial.printf(" %02X=ERR",reg);
          }
          Serial.println();
        }
        else if(strcmp(line,"INFO")==0) {
          Serial.printf("MEMORY psram=%u free_psram=%u frame_psram=%u heap=%u trail_points=%u\n",ESP.getPsramSize(),ESP.getFreePsram(),frame?esp_ptr_external_ram(frame):0,ESP.getFreeHeap(),trail.count());
          Serial.printf("GPS NAV reliable=%u\n",state.gpsReliable);
          Serial.printf("KU_DISPLAY_FIRST %s CS=%d DC=%d ROT=%u GPIO4=button GPIO2=%s BME=%s\n",
            WatchExt::VERSION,Pin::CS,Pin::DC,unsigned(DISPLAY_ROTATION),SOUND_DRIVER_CONNECTED?"driver tone":"input (no speaker drive)",state.bme?"live":"waiting");
          gps.report();
          recorder.report();
        }
      }
      length=0; overflow=false;
    } else if(length<sizeof(line)-1) line[length++]=c;
    else overflow=true;
  }
}
void setup() {
  // Never wait for Serial or a sensor before bringing up the display.
  pinMode(Pin::SOUND,INPUT); pinMode(Pin::BUTTON,INPUT_PULLUP);
  pinMode(Pin::RST,INPUT_PULLUP);
  attachInterrupt(Pin::BUTTON,onButtonFalling,FALLING);
  if(SOUND_DRIVER_CONNECTED) { ledcSetup(0,2400,8); ledcAttachPin(Pin::SOUND,0); ledcWrite(0,0); }
  state.sound=SOUND_DRIVER_CONNECTED;
  state.firmware=WatchExt::VERSION;
  Serial.begin(115200);
  frame=static_cast<Face::Canvas*>(heap_caps_malloc(sizeof(Face::Canvas),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
  if(!frame) frame=static_cast<Face::Canvas*>(heap_caps_malloc(sizeof(Face::Canvas),MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT));
  // Use only optional PSRAM for the previous image; preserve internal heap for TLS.
  frameCache.attach(static_cast<uint16_t*>(heap_caps_malloc(FrameCache::PIXELS*sizeof(uint16_t),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT)));
  state.trail=&trail;
  state.mapService=mapRenderService;
  pinMode(Pin::CS,OUTPUT); digitalWrite(Pin::CS,HIGH);
  SPI.begin(Pin::SCK,-1,Pin::MOSI,Pin::CS);
  if(digitalRead(Pin::BUTTON)==HIGH && digitalRead(Pin::RST)==HIGH) initializeDisplay();
  else {lcdRecoveryPending=true;lcdLowAt=millis();}
  // Brief primary colors make a lit backlight vs successful pixel transfer distinguishable.
  if(displayReady) for(uint16_t color : {uint16_t(0xf800),uint16_t(0x07e0),uint16_t(0x001f)}) {
    display.fillScreen(color); delay(120);
  }
  watchClock.begin(BUILD_UTC_SECONDS);clockTick();paint();
  Serial.printf("KU_DISPLAY_FIRST %s - screen started CS=%d DC=%d, GPIO4 menu, GPIO2 driver only\n",WatchExt::VERSION,Pin::CS,Pin::DC);
  runtimeSettings.begin();
  setCpuFrequencyMhz(160); // Preserve the 80 MHz APB/SPI clock while reducing CPU power.
  // Persist the accepted wrist settings once; subsequent user changes remain authoritative.
  if(!runtimeSettings.restored)runtimeSettings.save(runtimeSettings.value);
  pulse.setLedCurrent(runtimeSettings.value.led);pulse.setRedCurrent(runtimeSettings.value.red);pulse.setAveraging(runtimeSettings.value.average);
  battery.setShunt(runtimeSettings.value.shuntOhms);
  recorder.begin();
  telemetrySession=esp_random();if(!telemetrySession)telemetrySession=1;
  maps.begin(recorder.ready);state.map=maps.current();state.mapAutomatic=maps.automatic();
  robot.begin();
  alerts.begin();
  Wire.begin(Pin::SDA,Pin::SCL,100000); Wire.setTimeOut(10);
  sensorBusReady=true;
  displayLink.begin();
  setupPortal.begin(runtimeSettings,alerts);
  if(runtimeSettings.value.magCalibrated)setupPortal.magCalibrationStatus="SAVED - VERIFY DIRECTION WITH WATCH LEVEL";
  setupPortal.deleteActivity=[](uint32_t id) {
    if(recorder.active||recorder.exporting()||maps.importing()||ota.busy())return false;
    char path[32];snprintf(path,sizeof(path),"/rec%06lu.kua",(unsigned long)id);
    if(!LittleFS.exists(path))return false;recorder.remove(id);return !LittleFS.exists(path);
  };
  ota.begin(runtimeSettings.value.manifest);
  networkReady=LiveNetwork::begin(recorder.ready,telemetrySession,runtimeSettings.value);
  if(!networkReady) Serial.println("NETWORK disabled or allocation failed");
  gy51Init();
  gps.begin();
  pulse.tick(millis());
}
static void extensionsTick() {
  if(setupRequested) {setupRequested=false;wakeScreen();if(setupPortal.active)setupPortal.stop();else setupPortal.start();dirty=true;}
  setupPortal.canUpdate=!recorder.active && !recorder.exporting() && !maps.importing() && !ota.busy() && ota.confirmed && state.batteryValid && state.batteryPercent>=30;
  setupPortal.activeActivity=recorder.active?recorder.id:0;
  setupPortal.wifiConnected=state.wifi;setupPortal.mqttConnected=state.mqtt;
  setupPortal.pendingSamples=state.networkPending;
  setupPortal.droppedSamples=state.networkDropped;setupPortal.storageErrors=state.networkErrors;
  setupPortal.environmentSequence=environment.sequence;
  setupPortal.clockUtc=state.timeSet?watchClock.utc():0;setupPortal.clockSource=watchClock.model.label();
  setupPortal.tick();state.setupActive=setupPortal.active;state.setupSsid=setupPortal.ssid;state.setupPassword=runtimeSettings.apPassword.c_str();
  if(setupPortal.requestedTime) {
    watchClock.set(setupPortal.requestedTime,ClockModel::Manual);setupPortal.requestedTime=0;clockTick();dirty=true;
  }
  if(setupPortal.magCalibrationRequested) {setupPortal.magCalibrationRequested=false;startCompassCalibration();}
  if(setupPortal.changed) {
    setupPortal.changed=false;LiveNetwork::configure(runtimeSettings.value);
    pulse.setLedCurrent(runtimeSettings.value.led);pulse.setRedCurrent(runtimeSettings.value.red);pulse.setAveraging(runtimeSettings.value.average);
    battery.setShunt(runtimeSettings.value.shuntOhms);ota.configure(runtimeSettings.value.manifest);wakeScreen();dirty=true;
  }
  if(setupPortal.forgetPeer) {setupPortal.forgetPeer=false;displayLink.forget();}
  if(setupPortal.restartRequested) {robot.tick(true);delay(200);ESP.restart();}
  KuLink::CommandPacket command;
  while(displayLink.next(command)) {
    KuLink::Result result=KuLink::Ok;if(command.action!=KuLink::Heartbeat && command.action!=KuLink::ClockSync)wakeScreen();
    switch(command.action) {
      case KuLink::Next:state.page=(state.page+1)%Pin::PAGE_COUNT;break;
      case KuLink::Home:state.page=0;break;
      case KuLink::Page:if(command.argument<0 || command.argument>=Pin::PAGE_COUNT)result=KuLink::Invalid;else state.page=command.argument;break;
      case KuLink::RecordStart:
        if(recorder.active)break;
        if(maps.importing()||recorder.exporting()||ota.busy())result=KuLink::Busy;
        else if(!state.timeSet)result=KuLink::NoClock;
        else if(!recorder.start(watchClock.utc(),state.timeSet))result=KuLink::StorageError;
        break;
      case KuLink::RecordStop:recorder.stop();if(recorder.active)result=KuLink::StorageError;break;
      case KuLink::MapArea:
        if(command.argument<-1||command.argument>1)result=KuLink::Invalid;
        else if(!maps.choose(command.argument))result=KuLink::StorageError;
        break;
      case KuLink::MapZoom:if(command.argument<0||!MapZoom::valid(unsigned(command.argument)))result=KuLink::Invalid;else state.mapZoom=command.argument;break;
      case KuLink::PetFeed:robotFeedRequested=true;break;
      case KuLink::PetPlay:robotPlayRequested=true;break;
      case KuLink::AlertLimits:
        {
        if(!EnvAlert::Settings::valid(command.value,command.value2))result=KuLink::Invalid;
        else if(!alerts.configure(command.value,command.value2))result=KuLink::StorageError;}
        break;
      case KuLink::PulseSettings:
        {auto s=runtimeSettings.value;
        if(command.argument<1||command.argument>63 || (command.value!=0&&command.value!=1))result=KuLink::Invalid;
        else {s.led=s.red=command.argument;s.average=command.value;
          if(!runtimeSettings.save(s))result=KuLink::StorageError;
          else {pulse.setLedCurrent(s.led);pulse.setAveraging(s.average);}}}
        break;
      case KuLink::Heartbeat:break;
      case KuLink::ScreenWake:break;
      case KuLink::Setup:if(!setupPortal.active)setupRequested=true;state.page=5;break;
      case KuLink::CompassCalibration:if(magCalibrating)result=KuLink::Busy;else startCompassCalibration();break;
      case KuLink::ClockSync:
        {uint32_t seconds=0;memcpy(&seconds,&command.argument,sizeof(seconds));
        if(!ClockModel::valid(seconds))result=KuLink::Invalid;
        else if(!watchClock.hub(seconds))result=KuLink::Busy;
        else {clockTick();watchClock.report();}}
        break;
      default:result=KuLink::Invalid;break;
    }
    dirty=true;displayLink.ack(command,result,state.page,recorder.active);
  }
  KuLink::TelemetryPacket p;
  p.utc=state.timeSet?watchClock.utc():0;p.uptime=millis();
  p.flags=(state.timeSet?KuLink::Clock:0)|(state.bme?KuLink::Environment:0)|(state.max30102&&isfinite(state.bpm)?KuLink::Pulse:0)|
    (isfinite(state.spo2)?KuLink::Spo2:0)|(state.iaqValid?KuLink::Iaq:0)|(state.batteryValid?KuLink::Battery:0)|
    (state.gpsReliable?KuLink::Gps:0)|(recorder.active?KuLink::Recording:0)|(state.wifi?KuLink::Wifi:0)|(state.mqtt?KuLink::Mqtt:0)|
    (accelLive?KuLink::Motion:0)|(magLive?KuLink::Mag:0)|(isfinite(state.heading)?KuLink::Heading:0)|(battery.currentValid?KuLink::Current:0)|(state.batteryLow?KuLink::LowBattery:0)|
    (watchClock.model.source==ClockModel::Hub?KuLink::HubClock:0);
  p.temperature=state.temp;p.humidity=state.humidity;p.pressure=state.pressure;p.bpm=state.bpm;p.spo2=state.spo2;
  p.iaq=state.iaq;p.gas=state.gas;p.batteryVolts=state.batteryVolts;p.batteryPercent=state.batteryPercent;
  p.current=battery.currentMa;p.power=battery.powerMw;p.heading=state.heading;
  p.latitude=state.gpsReliable?state.latitude:NAN;p.longitude=state.gpsReliable?state.longitude:NAN;p.speed=state.speed;p.altitude=state.altitude;
  p.distance=recorder.meters();p.elapsed=recorder.elapsedMs;p.activity=recorder.id;p.pending=state.networkPending;
  p.acc[0]=state.accX;p.acc[1]=state.accY;p.acc[2]=state.accZ;p.mag[0]=state.magX;p.mag[1]=state.magY;p.mag[2]=state.magZ;
  p.page=state.page;p.area=maps.selected();p.zoom=state.mapZoom;p.satellites=min(255u,state.satellites);
  p.iaqAccuracy=state.iaqAccuracy;p.alertMask=state.alertMask;p.xp=state.robotXp;p.food=state.robotFood;
  p.mood=state.robotMood;p.energy=state.robotEnergy;p.pose=unsigned(state.robotPose);strlcpy(p.firmware,WatchExt::VERSION,sizeof(p.firmware));
  p.temperatureLimit=alerts.model.settings.temperature;p.iaqLimit=alerts.model.settings.iaq;
  p.spo2Status=state.spo2Status;p.finger=state.finger;p.iaqStable=state.iaqStable;p.iaqRunIn=state.iaqRunIn;
  p.temperatureAlert=state.alertTemperature;p.iaqAlert=state.alertAir;p.robotBubble=state.robotBubble;
  strlcpy(p.robotMessage,state.robotMessage?state.robotMessage:"",sizeof(p.robotMessage));
  p.magCalibration=magCalibrating?1:runtimeSettings.value.magCalibrated?2:0;
  displayLink.tick(p);state.linkOnline=displayLink.online;
  bool transfers=recorder.active||recorder.exporting()||maps.importing()||setupPortal.active||alertFixture.active;
  ota.tick(!transfers,state.batteryValid,state.batteryPercent,frame && displayReady && recorder.ready && networkReady);
  if(!screenAsleep && !setupPortal.active && !lcdRecoveryPending && !ota.busy() && runtimeSettings.value.idleSeconds &&
     uint32_t(millis()-interactionAt)>=uint32_t(runtimeSettings.value.idleSeconds)*1000u) {
    display.sendCommand(0x28);display.sendCommand(0x10);screenAsleep=true;Serial.println("POWER SCREEN ASLEEP; SENSORS KEEP RUNNING");
  }
}
void loop() {
  controls(); consoleTick(); clockTick(); gpsTick();
  displayRecoveryTick();
  uint32_t now=millis();
  alertFixtureTick(now);
  if(now>500) { max30102Tick(now); scanTick(now); envTick(now); gy51Tick(now); networkTick(now); }
  gpsTick(); max30102Tick(millis());
  activityTick();
  if(maps.tick(state.gpsReliable,state.latitude,state.longitude)) dirty=true;
  state.map=maps.current();state.mapAutomatic=maps.automatic();
  robotTick();
  extensionsTick();
  if(dirty) paint();
  max30102Tick(millis());
  delay(1);
}
