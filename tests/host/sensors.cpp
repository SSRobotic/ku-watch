#include <cstdio>
#include <cstdlib>
#include <string>
#include "pulse_sensor.h"
#include "gps_receiver.h"
#include "face.h"
#include "activity_format.h"
#include "battery_sensor.h"
static uint32_t clockMs=0;
unsigned long millis() { return clockMs; }
HostSerial Serial;
TwoWire Wire;
static unsigned checks=0;
#define CHECK(x) do { ++checks; if(!(x)) { std::fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x); std::exit(1); } } while(0)
static uint32_t wave(unsigned i,double bpm) {
  return uint32_t(50000+1000*std::sin(TWO_PI*bpm/60*i/100));
}
static void send(GpsReceiver& gps,const std::string& body,bool corrupt=false) {
  uint8_t sum=0; for(char c:body) sum^=c;
  char tail[8]; std::snprintf(tail,sizeof(tail),"*%02X\r\n",sum^(corrupt?1:0));
  for(char c:std::string("$")+body+tail) gps.encode(c,clockMs);
}
static void preview(const char* path,const Face::State& state) {
  Face::Canvas c; c.render(state); FILE* f=std::fopen(path,"wb"); CHECK(f);
  std::fprintf(f,"P6\n240 240\n255\n");
  for(auto v:c.pixels) {
    uint8_t rgb[]={uint8_t(((v>>11)&31)*255/31),uint8_t(((v>>5)&63)*255/63),uint8_t((v&31)*255/31)};
    std::fwrite(rgb,1,3,f);
  }
  std::fclose(f);
}
int main() {
  // Real Maxim reference algorithm, ordered 100 Hz input -> 25 Hz windows.
  Spo2Tracker oxygen;
  for(unsigned i=0;i<499;++i) {
    double w=std::sin(TWO_PI*1.2*i/100);
    oxygen.sample(uint32_t(50000+1000*w),uint32_t(30000+300*w),10000,72);
    CHECK(!std::isfinite(oxygen.value)); // Two full windows required (5 seconds).
  }
  for(unsigned i=499;i<1200;++i) {
    double w=std::sin(TWO_PI*1.2*i/100);
    oxygen.sample(uint32_t(50000+1000*w),uint32_t(30000+300*w),10000,72);
  }
  CHECK(oxygen.status==3 && oxygen.value>=90 && oxygen.value<=100 && oxygen.quality>.99f);
  oxygen.sample(500,200,10000,72);CHECK(!std::isfinite(oxygen.value) && oxygen.status==0);
  for(unsigned i=0;i<800;++i) oxygen.sample(50000,30000,10000,72);
  CHECK(!std::isfinite(oxygen.value) && oxygen.status==2);
  oxygen.reset();
  for(unsigned i=0;i<800;++i) {
    double w=std::sin(TWO_PI*1.2*i/100);
    oxygen.sample(uint32_t(50000+1000*w),uint32_t(30000-300*w),10000,72);
  }
  CHECK(!std::isfinite(oxygen.value) && oxygen.quality<.01);
  oxygen.reset();
  for(unsigned i=0;i<800;++i) {
    double w=std::sin(TWO_PI*1.2*i/100);
    oxygen.sample(uint32_t(50000+1000*w),uint32_t(30000+300*w),10000,150);
  }
  // The optical period is now the displayed BPM. An unrelated peak counter
  // must neither override the true 72 BPM nor force a valid window to NAN.
  CHECK(std::isfinite(oxygen.value) && std::fabs(oxygen.pulseBpm-72)<3);
  // A low-amplitude periodic two-channel signal can pass only after four
  // matching windows. Correlated slow drift alone must still be rejected.
  oxygen.reset();
  for(unsigned i=0;i<650;++i) {
    double w=std::sin(TWO_PI*1.2*i/100);
    oxygen.sample(uint32_t(180000+150*w),uint32_t(80000+40*w),10000,72);
    CHECK(!std::isfinite(oxygen.value));
  }
  for(unsigned i=650;i<1200;++i) {
    double w=std::sin(TWO_PI*1.2*i/100);
    oxygen.sample(uint32_t(180000+150*w),uint32_t(80000+40*w),10000,72);
  }
  CHECK(oxygen.status==3 && std::isfinite(oxygen.value));
  oxygen.reset();
  for(unsigned i=0;i<1200;++i) oxygen.sample(180000+i,80000+i/3,10000,72);
  CHECK(!std::isfinite(oxygen.value));
  oxygen.sample(260001,30000,10000,72);CHECK(oxygen.status==0);
  CHECK(!std::isfinite(batteryPercent(NAN)) && !std::isfinite(batteryPercent(0)));
  CHECK(!std::isfinite(batteryPercent(5)) && !std::isfinite(batteryPercent(4.35f)));
  CHECK(batteryPercent(4.2f)==100 && batteryPercent(3.3f)==0 && batteryPercent(3.0f)==0);
  CHECK(std::fabs(batteryPercent(3.8f)-50)<.01);
  for(float v=2.5;v<4.24;v+=.01f) CHECK(batteryPercent(v+.005f)>=batteryPercent(v));
  BatterySensor battery; battery.tick(0);
  CHECK(battery.detected && !battery.valid && Wire.inaConfig==0x4526);
  battery.tick(1000);CHECK(battery.valid && battery.volts==4.0f && battery.percent==80);
  Wire.inaVoltage=0;battery.tick(2000);CHECK(!battery.valid && !std::isfinite(battery.percent));
  Wire.inaVoltage=4000;battery.tick(3000);CHECK(!battery.valid); // 5 V is not a 1S battery.
  Wire.inaVoltage=3200;Wire.inaMask=0;battery.tick(4000);CHECK(!battery.valid);
  Wire.inaMask=8;battery.tick(5000);CHECK(battery.valid);
  Wire.inaConnected=false;battery.tick(6000);CHECK(!battery.detected && !battery.valid);
  Wire.inaConnected=true;Wire.inaDie=0x2190;battery.tick(7000);CHECK(!battery.detected);
  Wire.inaDie=0x2260;Wire.inaManufacturer=0;battery.tick(8000);CHECK(!battery.detected);
  Wire.inaManufacturer=0x5449;battery.tick(9000);CHECK(battery.detected && !battery.valid);
  battery.tick(10000);CHECK(battery.valid);
  for(double rate:{45.,60.,90.,120.,150.}) {
    PulseTracker p;
    for(unsigned i=0;i<1500;++i) p.sample(wave(i,rate),10000);
    CHECK(p.finger && std::isfinite(p.bpm) && std::fabs(p.bpm-rate)<3);
    for(unsigned i=0;i<800;++i) p.sample(50000,10000);
    CHECK(p.finger && !std::isfinite(p.bpm));
    p.sample(500,10000); CHECK(!p.finger && !std::isfinite(p.bpm));
    p.sample(261000,10000); CHECK(!p.finger);
  }
  // Replay a real 100 Hz, 10-second skin-contact capture. The old detector counted
  // secondary maxima and jumped above 100 BPM although the main period is
  // about 87 samples. This fixture verifies filtering, not medical accuracy.
  {
    FILE* capture=std::fopen("tests/fixtures/ppg_skin_20261008.csv","r");CHECK(capture);
    char headerLine[80];CHECK(std::fgets(headerLine,sizeof(headerLine),capture));
    unsigned sample,ir,red,seen=0,ready=0;float low=200,high=0;
    PulseTracker p;Spo2Tracker o;
    while(std::fscanf(capture,"%u,%u,%u\n",&sample,&ir,&red)==3) {
      CHECK(sample==seen++);p.sample(ir,10000);o.sample(ir,red,10000,p.bpm);
      if(sample>=500) {
        CHECK(std::isfinite(p.bpm) && p.bpm>60 && p.bpm<80);
        low=std::min(low,p.bpm);high=std::max(high,p.bpm);
      }
      if(o.status==3) ++ready;
    }
    std::fclose(capture);CHECK(seen==1000 && high-low<5);
    CHECK(ready>=100); // Stable BPM must allow the existing SpO2 gate to pass.
    std::printf("PPG replay BPM %.1f..%.1f SpO2 ready samples=%u\n",low,high,ready);
  }
  {
    FILE* capture=std::fopen("tests/fixtures/ppg_wrist_average4_20261008.csv","r");CHECK(capture);
    char headerLine[80];CHECK(std::fgets(headerLine,sizeof(headerLine),capture));
    unsigned sample,ir,red,seen=0,ready=0;PulseTracker p;Spo2Tracker o;
    while(std::fscanf(capture,"%u,%u,%u\n",&sample,&ir,&red)==3) {
      CHECK(sample==seen++);p.sample(ir,10000);o.sample(ir,red,10000,p.bpm);
      if(o.status==3) ++ready;
    }
    std::fclose(capture);CHECK(seen==1000);
    std::printf("Wrist replay BPM %.1f SpO2 %.1f status=%u ready samples=%u\n",p.bpm,o.value,o.status,ready);
  }
  // Drain 12 records per poll: exceeds the library's four-slot ring buffer.
  PulseSensor sensor; clockMs=0; sensor.tick(clockMs);
  for(unsigned i=0;i<1500;i+=12) {
    for(unsigned j=0;j<12;++j) Wire.samples.push_back(wave(i+j,90));
    clockMs+=120; sensor.tick(clockMs);
  }
  CHECK(sensor.live && sensor.finger && std::fabs(sensor.bpm-90)<3);
  CHECK(Wire.samples.empty() && sensor.ir==wave(1499,90));
  CHECK(sensor.red==sensor.ir/2);
  for(unsigned batch:Wire.batches) CHECK(batch<=5);
  CHECK(!sensor.setLedCurrent(0) && !sensor.setLedCurrent(64));
  CHECK(sensor.setLedCurrent(63) && Wire.redLed==63 && Wire.irLed==63);
  CHECK(!sensor.live && !sensor.finger && !std::isfinite(sensor.bpm) && !std::isfinite(sensor.spo2));
  CHECK(sensor.setLedCurrent(31) && Wire.redLed==31 && Wire.irLed==31);
  sensor.setAveraging(true);CHECK(Wire.average==16 && Wire.adcRate==400 && sensor.sampleRate()==25);
  CHECK(!sensor.live && !sensor.finger && !std::isfinite(sensor.spo2));
  sensor.setAveraging(false);CHECK(Wire.average==1 && Wire.adcRate==100);
  CHECK(!sensor.setRedCurrent(0) && !sensor.setRedCurrent(128));
  CHECK(sensor.setRedCurrent(127) && Wire.redLed==127 && Wire.irLed==31);
  sensor.setAveraging(true);CHECK(Wire.redLed==127 && Wire.irLed==31);
  sensor.setAveraging(false);CHECK(sensor.setLedCurrent(31));
  Wire.stickyOverflow=true; Wire.overflow=31; Wire.samples.push_back(50000);
  clockMs+=20; sensor.tick(clockMs);
  CHECK(!std::isfinite(sensor.bpm) && !sensor.live && sensor.droppedBatches==1);
  CHECK(Wire.overflow==0);
  Wire.samples.push_back(50001); clockMs+=10; sensor.tick(clockMs);
  CHECK(sensor.live && sensor.ir==50001 && sensor.droppedBatches==1);
  Wire.samples.push_back(50000); clockMs+=300; sensor.tick(clockMs);
  CHECK(!std::isfinite(sensor.bpm) && Wire.samples.empty() && sensor.droppedBatches==2);
  Wire.samples.push_back(50000); clockMs+=10; sensor.tick(clockMs); CHECK(sensor.live);
  Wire.connected=false; clockMs+=10; sensor.tick(clockMs); CHECK(!sensor.live && !sensor.finger && sensor.ir==0);
  Wire.connected=true; clockMs+=5000; sensor.tick(clockMs);
  Wire.samples.push_back(50000); clockMs+=10; sensor.tick(clockMs); CHECK(sensor.live);
  for(unsigned i=0;i<102;++i) { clockMs+=10; sensor.tick(clockMs); }
  CHECK(!sensor.live && !std::isfinite(sensor.bpm));
  // Use the real pinned TinyGPSPlus parser with valid and invalid NMEA checksums.
  clockMs=100; GpsReceiver gps;
  CHECK(!gps.reading(clockMs,5000).data);
  send(gps,"GPRMC,123519,A,1345.000,N,10030.000,E,1.0,0.0,230926,,,A");
  auto r=gps.reading(clockMs,5000);
  CHECK(r.data && r.fix && std::fabs(r.latitude-13.75)<1e-6 && std::fabs(r.longitude-100.5)<1e-6);
  CHECK(r.utc==1790166919ULL); // 2026-09-23 12:35:19 UTC, independent of host timezone.
  CHECK(std::fabs(r.speed-1.852)<.001);
  clockMs+=1000; send(gps,"GNGGA,123520,1345.000,N,10030.000,E,1,08,0.9,12.3,M,0.0,M,,");
  r=gps.reading(clockMs,5000); CHECK(r.fix && r.satellites==8 && std::fabs(r.altitude-12.3)<.001);
  CHECK(r.reliable());
  auto quality=r;quality.hdop=25.5;CHECK(!quality.reliable());quality.hdop=5;CHECK(quality.reliable());
  quality.hdop=5.01;CHECK(!quality.reliable());quality.hdop=NAN;CHECK(!quality.reliable());quality.hdop=0;CHECK(!quality.reliable());
  quality=r;quality.satellites=3;CHECK(!quality.reliable());quality=r;quality.positionAge=2000;CHECK(!quality.reliable());
  quality=r;quality.latitude=NAN;CHECK(!quality.reliable());quality=r;quality.longitude=181;CHECK(!quality.reliable());
  clockMs+=1000; send(gps,"GNRMC,123521,V,,,,,,,230926,,,N");
  r=gps.reading(clockMs,5000); CHECK(r.data && !r.fix && !std::isfinite(r.latitude));
  CHECK(r.utc==0);
  send(gps,"GBRMC,123522,A,3345.000,S,15130.000,W,0.0,0.0,230926,,,A");
  r=gps.reading(clockMs,5000); CHECK(r.fix && r.latitude==-33.75 && r.longitude==-151.5);
  send(gps,"GPGGA,123522,3345.000,S,15130.000,W,0,00,99.9,0.0,M,0.0,M,,");
  CHECK(!gps.reading(clockMs,5000).fix);
  send(gps,"GPRMC,123523,A,0000.000,N,00000.000,E,0.0,0.0,230926,,,A",true);
  CHECK(!gps.reading(clockMs,5000).fix && gps.checksumErrors()==1);
  send(gps,"GPRMC,123523,A,0000.000,N,00000.000,E,0.0,0.0,230926,,,A");
  r=gps.reading(clockMs,5000); CHECK(r.fix && r.latitude==0 && r.longitude==0);
  clockMs+=5000; r=gps.reading(clockMs,5000); CHECK(!r.data && !r.fix && !std::isfinite(r.longitude));
  GpsReceiver wrap; clockMs=0xffffff00u;
  send(wrap,"GPRMC,123519,A,1345.000,N,10030.000,E,1.0,0.0,230926,,,A");
  clockMs+=1000; CHECK(wrap.reading(clockMs,5000).fix);
  clockMs+=4000; CHECK(!wrap.reading(clockMs,5000).fix);
  // Replay the GSV shapes observed on this ATGM336H before it has a fix.
  GpsReceiver sky; clockMs=100;
  send(sky,"GPGSV,1,1,01,28,,,08,0");
  send(sky,"BDGSV,1,1,01,01,,,32,0");
  r=sky.reading(clockMs,5000);
  CHECK(r.data && !r.fix && r.viewValid && r.inView==2 && r.signalValid && r.signal==32);
  send(sky,"GPGSV,1,1,00,0");
  r=sky.reading(clockMs,5000); CHECK(r.inView==1 && r.signal==32);
  send(sky,"GBGSV,1,1,01,01,,,24,0");
  r=sky.reading(clockMs,5000); CHECK(r.inView==1 && r.signal==24); // GB/BD alias, not two satellites.
  send(sky,"GPGSV,2,1,05,01,40,020,12,02,50,030,45,03,60,040,20,04,70,050,18,0");
  CHECK(sky.reading(clockMs,5000).inView==1); // Incomplete group is not published.
  send(sky,"GPGSV,2,2,05,05,20,030,25,0");
  r=sky.reading(clockMs,5000); CHECK(r.inView==6 && r.signal==45);
  send(sky,"GPGSV,1,1,01,28,,,08,0");
  r=sky.reading(clockMs,5000); CHECK(r.inView==2 && r.signal==24); // Old slots must not retain 45.
  send(sky,"GPGSV,1,1,01,28,,,99,0",true);
  CHECK(sky.reading(clockMs,5000).signal==24);
  send(sky,"GNGSV,1,1,02,28,,,40,01,,,42,0");
  CHECK(sky.reading(clockMs,5000).inView==2); // GN total does not duplicate GP+BD.
  clockMs+=5000; r=sky.reading(clockMs,5000);
  CHECK(!r.data && !r.viewValid && !r.signalValid && r.inView==0);
  send(sky,"GNGSV,1,1,02,28,,,40,01,,,42,0");
  r=sky.reading(clockMs,5000); CHECK(r.inView==2 && r.signal==42);
  clockMs+=5000;
  send(sky,"GPGSV,1,1,01,28,,");
  r=sky.reading(clockMs,5000); CHECK(r.inView==1 && !r.signalValid);
  send(sky,"GPGSV,1,1,00,0");
  r=sky.reading(clockMs,5000); CHECK(r.viewValid && r.inView==0 && !r.signalValid);
  Face::State state; state.page=6; state.second=35;
  preview("output/gps_no_data.ppm",state);
  state.gpsData=true; state.satellites=0; state.gpsChars=12345;
  state.gpsViewValid=state.gpsSignalValid=true; state.gpsInView=2; state.gpsSignal=32;
  preview("output/gps_wait.ppm",state);
  state.gpsFix=true; state.gpsReliable=true; state.satellites=12; state.latitude=13.756331; state.longitude=100.501762; state.speed=4.2;
  preview("output/gps_fix.ppm",state);
  state.latitude=-89.123456; state.longitude=-179.123456; preview("output/gps_negative.ppm",state);
  state.page=3; state.max30102=true; state.finger=true; state.bpm=120; state.ir=50000;
  preview("output/heart_live.ppm",state);
  state.spo2=98;state.spo2Status=3;preview("output/heart_spo2.ppm",state);
  state.spo2=NAN;state.spo2Status=1;
  state.bpm=NAN; preview("output/heart_reading.ppm",state);
  state.page=7; state.recording=true; state.recordElapsed=754000; state.recordDistance=856;
  state.recordId=1;state.recordFree=850000;state.bpm=86;
  preview("output/walk_recording.ppm",state);
  state.recording=false;state.timeSet=true;state.recordMessage="SAVED";
  preview("output/walk_saved.ppm",state);
  state.page=8;state.bme=true;state.iaq=42;state.iaqAccuracy=2;state.iaqValid=true;state.gas=85000;
  preview("output/iaq_ready.ppm",state);
  state.iaqValid=false;state.iaqStable=false;preview("output/iaq_warmup.ppm",state);
  state.page=9;state.batteryDetected=true;state.batteryValid=true;state.batteryVolts=3.8;state.batteryPercent=50;
  preview("output/battery_ready.ppm",state);
  state.batteryValid=false;preview("output/battery_wait.ppm",state);
  state.page=0;state.batteryValid=true;state.temp=30.5;state.humidity=57;preview("output/home_battery.ppm",state);
  Activity::Track track;
  CHECK(track.point(0,13.75,100.5,true));
  CHECK(track.point(1000,13.750001,100.5,true) && track.meters==0); // Small drift.
  CHECK(track.point(4000,13.75004,100.5,true) && track.meters>4 && track.meters<5);
  double traveled=track.meters;
  CHECK(!track.point(5000,0,0,true) && track.meters==traveled); // GPS jump rejected.
  CHECK(!track.point(6000,NAN,NAN,false));
  CHECK(track.point(7000,13.76,100.5,true) && track.meters==traveled); // No gap distance.
  CHECK(Activity::crc32("\x31\x32\x33\x34\x35\x36\x37\x38\x39",9)==0xcbf43926u);
  auto header=Activity::header(1790166919ULL);
  FILE* activityFile=std::fopen("output/activity_format_fixture.kua","wb");CHECK(activityFile);
  std::fwrite(&header,1,sizeof(header),activityFile);
  for(unsigned i=0;i<4;++i) {
    Activity::Record record={};record.elapsedMs=i*1000;
    if(i<2) {record.flags=Activity::GPS|Activity::ALTITUDE;record.latitudeE7=137500000+i*100;record.longitudeE7=1005000000;record.altitudeCm=1200;}
    if(i!=2) {record.flags|=Activity::HEART;record.bpm10=800+i*10;}
    record.distanceCm=i?111:0;Activity::seal(record);std::fwrite(&record,1,sizeof(record),activityFile);
  }
  Activity::Record stop={};stop.elapsedMs=4100;stop.flags=Activity::STOP;stop.distanceCm=111;
  Activity::seal(stop);std::fwrite(&stop,1,sizeof(stop),activityFile);std::fclose(activityFile);
  std::printf("PASS: %u checks (pulse rates, FIFO batches, loss/recovery, NMEA fix/checksum/staleness/wrap, previews)\n",checks);
}
