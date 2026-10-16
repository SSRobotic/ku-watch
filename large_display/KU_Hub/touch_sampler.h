#pragma once
#include "display_hardware.h"
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>
#include <freertos/semphr.h>

// Capture contact and release history independently of the 90+ ms RGB draw.
// Only this task reads the touch controller. RTC shares the same I2C mutex.
class TouchSampler {
public:
  struct Sample {uint32_t at;uint16_t x,y;uint8_t gesture;bool valid,down,tap;};
  bool started=false;
  volatile uint32_t samples=0,dropped=0,maxGap=0;
private:
  HubDisplay* display=nullptr;QueueHandle_t queue=nullptr;SemaphoreHandle_t bus=nullptr;
  TaskHandle_t task=nullptr;
  static void run(void* argument){static_cast<TouchSampler*>(argument)->capture();}
  void capture(){
    TickType_t wake=xTaskGetTickCount();uint32_t previous=millis();
    for(;;){Sample s{};unsigned x=0,y=0;bool down=false;
      if(take(20)){s.valid=display->touch(down,x,y);s.gesture=display->touchGesture;s.tap=display->completedTap;give();}
      s.at=millis();s.x=x;s.y=y;s.down=down;
      uint32_t gap=s.at-previous;previous=s.at;if(gap>maxGap)maxGap=gap;++samples;
      if(xQueueSend(queue,&s,0)!=pdTRUE)++dropped;
      vTaskDelayUntil(&wake,pdMS_TO_TICKS(4));
    }
  }
public:
  bool begin(HubDisplay& d){
    display=&d;bus=xSemaphoreCreateMutex();queue=xQueueCreate(144,sizeof(Sample));
    if(!bus || !queue || !d.touchReady)return false;
    started=xTaskCreatePinnedToCore(run,"ku-touch",4096,this,2,&task,0)==pdPASS;return started;
  }
  bool take(uint32_t timeout){return !bus || xSemaphoreTake(bus,pdMS_TO_TICKS(timeout))==pdTRUE;}
  void give(){if(bus)xSemaphoreGive(bus);}
  bool next(Sample& s){return queue && xQueueReceive(queue,&s,0)==pdTRUE;}
  void discard(){if(queue)xQueueReset(queue);}
};
