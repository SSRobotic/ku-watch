#pragma once
#include <SD_MMC.h>
#include "hub_csv.h"

// Only this worker touches the card. The UI, touch sampler and radio never
// wait for FAT writes. Card failures remain visible; no format is attempted.
class HubSdLogger {
  QueueHandle_t queue=nullptr;SemaphoreHandle_t lock=nullptr;
  HubCsv::Cadence cadence;
  struct Job {uint8_t kind=0;uint32_t offset=0;HubCsv::Sample sample;};
  static void taskEntry(void* value){static_cast<HubSdLogger*>(value)->worker();}
  void worker() {
    bool mounted=SD_MMC.setPins(SD_SCLK_PIN,SD_MOSI_PIN,SD_MISO_PIN) && SD_MMC.begin("/sdcard",true,false,10000,5);
    xSemaphoreTake(lock,portMAX_DELAY);stats.ready=mounted;stats.mountDone=true;stats.cardMB=mounted?SD_MMC.cardSize()/1024/1024:0;xSemaphoreGive(lock);
    if(mounted && !SD_MMC.exists("/KU_Watch") && !SD_MMC.mkdir("/KU_Watch")){fail();mounted=false;}
    Job job;
    for(;;){if(xQueueReceive(queue,&job,pdMS_TO_TICKS(100))!=pdTRUE)continue;
      if(job.kind==1){readChunk(job.offset);continue;}
      if(!mounted)continue;
      uint32_t began=micros();char line[640];
      if(!HubCsv::format(job.sample,line,sizeof(line),"1.0.8")){fail();continue;}
      if(!path[0]){
        for(unsigned tries=0;tries<10;++tries){snprintf(path,sizeof(path),"/KU_Watch/env_%llu_%08lx.csv",(unsigned long long)job.sample.rtcUtc,(unsigned long)esp_random());if(!SD_MMC.exists(path))break;path[0]=0;}
        if(!path[0]){fail();continue;}
        File f=SD_MMC.open(path,FILE_APPEND);bool ok=f && f.print(HubCsv::HEADER)==strlen(HubCsv::HEADER);if(f){f.flush();f.close();}
        if(!ok){fail();path[0]=0;continue;}
        xSemaphoreTake(lock,portMAX_DELAY);strlcpy(stats.file,path,sizeof(stats.file));stats.bytes=strlen(HubCsv::HEADER);xSemaphoreGive(lock);
      }
      File file=SD_MMC.open(path,FILE_APPEND);bool ok=file && file.print(line)==strlen(line);uint32_t bytes=0;
      if(file){file.flush();bytes=file.size();file.close();}
      xSemaphoreTake(lock,portMAX_DELAY);
      if(ok){++stats.rows;stats.bytes=bytes;stats.lastUtc=job.sample.rtcUtc;}else{++stats.errors;stats.ready=false;mounted=false;}
      uint32_t duration=micros()-began;if(duration>stats.maxWriteUs)stats.maxWriteUs=duration;xSemaphoreGive(lock);
    }
  }
  void fail(){xSemaphoreTake(lock,portMAX_DELAY);++stats.errors;stats.ready=false;xSemaphoreGive(lock);}
  void readChunk(uint32_t offset){
    uint8_t bytes[64];int n=-1;File f=path[0]?SD_MMC.open(path,FILE_READ):File();
    if(f && offset<=f.size() && f.seek(offset)){n=f.read(bytes,sizeof(bytes));}if(f)f.close();
    xSemaphoreTake(lock,portMAX_DELAY);replyOffset=offset;replySize=n;
    for(int i=0;i<n;++i)snprintf(replyHex+i*2,3,"%02x",bytes[i]);if(n<=0)replyHex[0]=0;replyReady=true;xSemaphoreGive(lock);
  }
  char path[88]{};uint32_t replyOffset=0;int replySize=0;bool replyReady=false;char replyHex[257]{};
public:
  struct Stats {bool mountDone=false,ready=false;uint32_t rows=0,bytes=0,errors=0,dropped=0,skipped=0,maxWriteUs=0;uint64_t lastUtc=0,cardMB=0;char file[88]{};} stats;
  bool begin(){
    lock=xSemaphoreCreateMutex();queue=xQueueCreate(16,sizeof(Job));if(!lock||!queue)return false;
    // Native one-bit SD uses CLK/CMD/D0. DAT3 (EXIO4) must stay high during
    // initialization; the LCD command bus has already been released.
    if(!IOExpander::setPin(EXIO_SD_CS,true))return false;
    return xTaskCreatePinnedToCore(taskEntry,"hub-sd",6144,this,1,nullptr,0)==pdPASS;
  }
  Stats status(){if(lock)xSemaphoreTake(lock,portMAX_DELAY);auto copy=stats;if(lock)xSemaphoreGive(lock);return copy;}
  void tick(const KuLink::TelemetryPacket& p,uint32_t receivedAt,uint64_t rtc,uint32_t rtcAt){
    if(!queue)return;uint32_t now=millis();if(!cadence.due(now))return;
    if(!cadence.accept(p,now,receivedAt,rtc,rtcAt)){xSemaphoreTake(lock,portMAX_DELAY);++stats.skipped;xSemaphoreGive(lock);return;}
    if(!status().ready)return;Job j;j.sample.packet=p;j.sample.rtcUtc=rtc+uint32_t(now-rtcAt)/1000;
    if(xQueueSend(queue,&j,0)!=pdTRUE){xSemaphoreTake(lock,portMAX_DELAY);++stats.dropped;xSemaphoreGive(lock);}
  }
  void info(){auto s=status();hubLog("HUB SD ready=%u mount_done=%u card_mb=%llu rows=%lu bytes=%lu errors=%lu dropped=%lu skipped=%lu max_write_us=%lu last_utc=%llu file=%s\n",s.ready,s.mountDone,(unsigned long long)s.cardMB,(unsigned long)s.rows,(unsigned long)s.bytes,(unsigned long)s.errors,(unsigned long)s.dropped,(unsigned long)s.skipped,(unsigned long)s.maxWriteUs,(unsigned long long)s.lastUtc,s.file);}
  void read(uint32_t offset){if(!queue)return;Job j;j.kind=1;j.offset=offset;xQueueSend(queue,&j,0);}
  void replyTick(){
    if(!lock||!Serial)return;xSemaphoreTake(lock,portMAX_DELAY);
    if(replyReady){char line[330];int n=snprintf(line,sizeof(line),"HUB SDCHUNK offset=%lu size=%d hex=%s\n",(unsigned long)replyOffset,replySize,replyHex);
      if(n>0 && n<int(sizeof(line)) && Serial.availableForWrite()>=n){Serial.write((const uint8_t*)line,n);replyReady=false;}}
    xSemaphoreGive(lock);
  }
};
