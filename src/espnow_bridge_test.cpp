#include <Arduino.h>
#include "display_receiver.h"
static DisplayReceiver receiver;
// This is a receiver reference build, NOT the Super Mini watch firmware.
static const uint8_t WATCH_MAC[6]={0xd4,0x05,0x92,0x44,0x51,0xac};
void setup() {Serial.begin(115200);receiver.begin(WATCH_MAC);}
void loop() {
  receiver.tick();static uint32_t at=0;
  if(uint32_t(millis()-at)>=1000) {at=millis();Serial.printf("DISPLAY ready=%u fresh=%u page=%u recording=%u acked=%lu\n",receiver.ready,receiver.fresh(),receiver.snapshot.page,!!(receiver.snapshot.flags&KuLink::Recording),receiver.acks);}
  static char line[96];static unsigned used=0;
  while(Serial.available()) {char c=Serial.read();if(c=='\n') {
    line[used]=0;unsigned action;long arg;float a,b;char extra;
    if(sscanf(line,"LINKCMD %u %ld %f %f %c",&action,&arg,&a,&b,&extra)==4 && action>=1 && action<=15)
      Serial.println(receiver.send(KuLink::Action(action),arg,a,b)?"COMMAND QUEUED":"COMMAND WAIT FOR FRESH LINK");
    used=0;
  } else if(c!='\r'&&used<sizeof(line)-1)line[used++]=c;}
  delay(1);
}
