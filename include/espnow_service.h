#pragma once
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <mbedtls/md.h>
#include <Preferences.h>
#include "espnow_protocol.h"
#include "espnow_private.h"
#include "espnow_auth.h"

class EspNowService {
  struct Incoming {uint8_t mac[6],data[250];uint16_t length;};
  inline static EspNowService* owner=nullptr;
  QueueHandle_t inbox=nullptr;
  Preferences prefs;
  KuLink::Commands commands;
  uint32_t sequence=0,helloAt=0,sentAt=0,remoteSession=0,challenge=0;
  uint8_t peer[6]={};bool paired=false;
  KuLink::AckPacket lastAck;
  static void receive(const uint8_t* mac,const uint8_t* data,int length) {
    if(!owner || !owner->inbox || length<20 || length>250)return;
    Incoming p{};memcpy(p.mac,mac,6);memcpy(p.data,data,length);p.length=length;
    if(xQueueSend(owner->inbox,&p,0)!=pdTRUE)++owner->dropped;
  }
  bool addPeer(const uint8_t* mac,bool encrypt) {
    if(esp_now_is_peer_exist(mac))esp_now_del_peer(mac);
    esp_now_peer_info_t info{};memcpy(info.peer_addr,mac,6);info.channel=0;info.ifidx=WIFI_IF_STA;info.encrypt=encrypt;
    if(encrypt)memcpy(info.lmk,KU_LINK_KEY,16);
    return esp_now_add_peer(&info)==ESP_OK;
  }
  template<class P> void sign(P& p,KuLink::Type type) {
    KuLink::sign(p,type,session,++sequence);
  }
  template<class P> bool authentic(const P& p,KuLink::Type type) {
    return KuLink::authentic(p,type);
  }
public:
  bool ready=false,online=false;
  uint32_t session=0,receivedAt=0,sent=0,received=0,dropped=0,rejected=0;
  uint8_t channel() const {uint8_t p=1;wifi_second_chan_t secondary;esp_wifi_get_channel(&p,&secondary);return p;}
  void begin() {
    owner=this;session=esp_random();if(!session)session=1;challenge=esp_random();
    WiFi.mode(WIFI_STA); // network worker is started afterwards and preserves this interface
    inbox=xQueueCreate(12,sizeof(Incoming));
    ready=inbox && esp_now_init()==ESP_OK;
    if(!ready)return;
    esp_now_set_pmk(KU_LINK_KEY);esp_now_register_recv_cb(receive);
    const uint8_t broadcast[6]={255,255,255,255,255,255};addPeer(broadcast,false);
    if(prefs.begin("ku-link2",false) && prefs.getBytesLength("peer")==6) {
      prefs.getBytes("peer",peer,6);paired=addPeer(peer,true);
    }
    Serial.printf("ESPNOW ready=%u paired=%u channel=%u mac=%s\n",ready,paired,channel(),WiFi.macAddress().c_str());
  }
  bool next(KuLink::CommandPacket& command) {
    if(!ready)return false;
    Incoming p;
    while(xQueueReceive(inbox,&p,0)==pdTRUE) {
      if(p.length==sizeof(KuLink::HelloPacket)) {
        KuLink::HelloPacket hello;memcpy(&hello,p.data,sizeof(hello));
        if(!authentic(hello,KuLink::Hello)||hello.role!=2||hello.challenge!=challenge || (paired && memcmp(peer,p.mac,6))) {++rejected;continue;}
        if(!paired) {
          if(!addPeer(p.mac,true) || prefs.putBytes("peer",p.mac,6)!=6) {++rejected;continue;}
          memcpy(peer,p.mac,6);paired=true;
        }
        if(remoteSession!=hello.h.session) {remoteSession=hello.h.session;commands.reset();}
        challenge=esp_random();receivedAt=millis();online=true;
        // The next encrypted telemetry proves pairing and supplies the receiver boot session.
        sentAt=millis()-500;Serial.println("ESPNOW DISPLAY AUTHENTICATED");continue;
      }
      if(p.length==sizeof(KuLink::CommandPacket) && paired && !memcmp(peer,p.mac,6)) {
        memcpy(&command,p.data,sizeof(command));
        if(!authentic(command,KuLink::Command)||command.receiverSession!=session||command.h.session!=remoteSession) {++rejected;continue;}
        receivedAt=millis();online=true;++received;
        if(!commands.accept(command.h.session,command.h.sequence)) {
          if(lastAck.commandSession==command.h.session && lastAck.commandSequence==command.h.sequence)
            esp_now_send(peer,reinterpret_cast<uint8_t*>(&lastAck),sizeof(lastAck));
          continue;
        }
        return true;
      }
      // A signed display Hello doubles as heartbeat without re-opening its session.
      ++rejected;
    }
    return false;
  }
  void ack(const KuLink::CommandPacket& c,KuLink::Result result,uint8_t page,bool recording) {
    lastAck={};lastAck.commandSession=c.h.session;lastAck.commandSequence=c.h.sequence;
    lastAck.result=result;lastAck.page=page;lastAck.recording=recording;sign(lastAck,KuLink::Ack);
    esp_now_send(peer,reinterpret_cast<uint8_t*>(&lastAck),sizeof(lastAck));
  }
  void tick(KuLink::TelemetryPacket& packet) {
    if(!ready)return;uint32_t now=millis();online=paired && receivedAt && uint32_t(now-receivedAt)<15000;
    if(uint32_t(now-helloAt)>=1000) {
      helloAt=now;KuLink::HelloPacket hello;hello.role=1;hello.channel=channel();hello.challenge=challenge;sign(hello,KuLink::Hello);
      const uint8_t broadcast[6]={255,255,255,255,255,255};esp_now_send(broadcast,reinterpret_cast<uint8_t*>(&hello),sizeof(hello));
    }
    if(paired && remoteSession && uint32_t(now-sentAt)>=500) {
      sentAt=now;packet.channel=channel();sign(packet,KuLink::Telemetry);
      if(esp_now_send(peer,reinterpret_cast<uint8_t*>(&packet),sizeof(packet))==ESP_OK)++sent;
    }
  }
  void forget() {if(paired)esp_now_del_peer(peer);paired=false;online=false;remoteSession=0;prefs.remove("peer");commands.reset();}
  void report() const {Serial.printf("ESPNOW ready=%u paired=%u online=%u tx=%lu rx=%lu rejected=%lu dropped=%lu\n",ready,paired,online,sent,received,rejected,dropped);}
};
