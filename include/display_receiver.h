#pragma once
#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <esp_idf_version.h>
#include "espnow_auth.h"

// Board-independent display-side bridge. The future large-screen UI consumes
// snapshot + freshness and sends commands; it never owns sensors or recording.
class DisplayReceiver {
  struct Incoming {uint8_t mac[6],bytes[250];uint16_t size;};
  inline static DisplayReceiver* owner=nullptr;
  QueueHandle_t queue=nullptr;uint8_t watch[6]={};bool paired=false,sessionConfirmed=false;
  uint32_t session=0,sequence=0,watchSession=0,watchSequence=0,channelAt=0,helloAt=0,heartbeatAt=0;
  uint32_t pendingAt=0;unsigned attempts=0;KuLink::CommandPacket pending;
  static void receive(const uint8_t* mac,const uint8_t* bytes,int size) {
    if(!owner || !owner->queue || size<20 || size>250)return;
    Incoming p{};memcpy(p.mac,mac,6);memcpy(p.bytes,bytes,size);p.size=size;xQueueSend(owner->queue,&p,0);
  }
#if ESP_IDF_VERSION_MAJOR >= 5
  static void callback(const esp_now_recv_info_t* info,const uint8_t* bytes,int size) {receive(info->src_addr,bytes,size);}
#else
  static void callback(const uint8_t* mac,const uint8_t* bytes,int size) {receive(mac,bytes,size);}
#endif
public:
  KuLink::TelemetryPacket snapshot;
  bool ready=false,waiting=false;uint8_t lastResult=KuLink::Invalid;
  uint32_t receivedAt=0,acks=0,timeouts=0,incoming=0,hellos=0,rejected=0;bool lastTimedOut=false;
  uint8_t channel() const {uint8_t c=1;wifi_second_chan_t secondary;esp_wifi_get_channel(&c,&secondary);return c;}
  bool fresh() const {return receivedAt && uint32_t(millis()-receivedAt)<3000;}
  void begin(const uint8_t expectedWatch[6]) {
    owner=this;memcpy(watch,expectedWatch,6);session=esp_random();if(!session)session=1;
    WiFi.mode(WIFI_STA);WiFi.setAutoReconnect(false);WiFi.setSleep(false);
    queue=xQueueCreate(12,sizeof(Incoming));ready=queue && esp_now_init()==ESP_OK;
    if(!ready)return;esp_now_set_pmk(KU_LINK_KEY);esp_now_register_recv_cb(callback);
    esp_now_peer_info_t peer{};const uint8_t broadcast[6]={255,255,255,255,255,255};
    memcpy(peer.peer_addr,broadcast,6);peer.channel=0;peer.ifidx=WIFI_IF_STA;esp_now_add_peer(&peer);
  }
  bool send(KuLink::Action action,int32_t argument=0,float value=0,float value2=0) {
    if(!fresh() || waiting || !paired)return false;
    pending={};pending.action=action;pending.argument=argument;pending.value=value;pending.value2=value2;pending.receiverSession=watchSession;
    KuLink::sign(pending,KuLink::Command,session,++sequence);waiting=true;lastTimedOut=false;attempts=1;pendingAt=millis();
    esp_now_send(watch,reinterpret_cast<uint8_t*>(&pending),sizeof(pending));return true;
  }
  void tick() {
    if(!ready)return;Incoming p;uint32_t now=millis();
    while(xQueueReceive(queue,&p,0)==pdTRUE) {
      ++incoming;if(memcmp(p.mac,watch,6)){++rejected;continue;}
      if(p.size==sizeof(KuLink::HelloPacket)) {
        KuLink::HelloPacket hello;memcpy(&hello,p.bytes,sizeof(hello));
        if(!KuLink::authentic(hello,KuLink::Hello)||hello.role!=1){++rejected;continue;}++hellos;
        if(!paired || watchSession!=hello.h.session || !fresh()) {
          if(esp_now_is_peer_exist(watch))esp_now_del_peer(watch);
          esp_now_peer_info_t peer{};memcpy(peer.peer_addr,watch,6);peer.channel=0;peer.ifidx=WIFI_IF_STA;peer.encrypt=true;memcpy(peer.lmk,KU_LINK_KEY,16);
          paired=esp_now_add_peer(&peer)==ESP_OK;if(!paired)continue;
          if(watchSession!=hello.h.session) {watchSequence=0;waiting=false;sessionConfirmed=false;}
          watchSession=hello.h.session;
        }
        // Encrypted telemetry can still arrive using the persisted MAC/key
        // before the watch accepts this hub's new boot session. Only an ACK
        // addressed to this session proves the reverse path. Keep answering
        // the watch challenge until then, even when telemetry is fresh.
        if(paired && !sessionConfirmed && uint32_t(now-helloAt)>=500) {
            helloAt=now;KuLink::HelloPacket response;response.role=2;response.channel=hello.channel;response.challenge=hello.challenge;
            KuLink::sign(response,KuLink::Hello,session,++sequence);
            const uint8_t broadcast[6]={255,255,255,255,255,255};esp_now_send(broadcast,reinterpret_cast<uint8_t*>(&response),sizeof(response));
        }
        channelAt=now;
      } else if(p.size==sizeof(KuLink::TelemetryPacket)) {
        KuLink::TelemetryPacket t;memcpy(&t,p.bytes,sizeof(t));
        if(!KuLink::authentic(t,KuLink::Telemetry) || t.h.session!=watchSession || int32_t(t.h.sequence-watchSequence)<=0){++rejected;continue;}
        snapshot=t;watchSequence=t.h.sequence;receivedAt=now;channelAt=now;
      } else if(p.size==sizeof(KuLink::AckPacket)) {
        KuLink::AckPacket ack;memcpy(&ack,p.bytes,sizeof(ack));
        if(KuLink::authentic(ack,KuLink::Ack) && ack.h.session==watchSession && waiting &&
           ack.commandSession==session && ack.commandSequence==pending.h.sequence) {waiting=false;sessionConfirmed=true;lastTimedOut=false;lastResult=ack.result;++acks;}
      }
    }
    // Watch broadcasts Hello once per second. Stay longer than that on each
    // candidate channel so boot discovery cannot repeatedly hop past Hello.
    if(!fresh() && uint32_t(now-channelAt)>=1200) {
      channelAt=now;uint8_t next=channel();
      // Some country profiles reject channels 12/13. Skip unsupported channels
      // instead of remaining stuck trying the same rejected channel forever.
      for(unsigned i=0;i<13;++i){next=next==13?1:next+1;if(esp_wifi_set_channel(next,WIFI_SECOND_CHAN_NONE)==ESP_OK)break;}
    }
    if(waiting && uint32_t(now-pendingAt)>=350) {
      pendingAt=now;if(attempts++>=5) {waiting=false;sessionConfirmed=false;lastTimedOut=true;++timeouts;lastResult=KuLink::Busy;}
      else esp_now_send(watch,reinterpret_cast<uint8_t*>(&pending),sizeof(pending));
    }
    if(fresh() && !waiting && uint32_t(now-heartbeatAt)>=5000) {heartbeatAt=now;send(KuLink::Heartbeat);}
  }
};
