#pragma once
#include <Arduino.h>
#include <WebServer.h>
#include <Update.h>
#include <LittleFS.h>
#include "runtime_settings.h"
#include "alert_service.h"

class SetupService {
  WebServer server{80};RuntimeSettings* settings=nullptr;
  AlertService* alerts=nullptr;
  uint32_t at=0;bool uploadOk=false,uploadStarted=false;
  bool authorized() {return server.authenticate("admin",settings->apPassword.c_str())||server.authenticate("ADMIN",settings->apPassword.c_str());}
  bool authenticate() {if(authorized())return true;server.requestAuthentication();return false;}
  static String escape(const char* value) {String s(value);s.replace("&","&amp;");s.replace("\"","&quot;");s.replace("<","&lt;");s.replace(">","&gt;");return s;}
  String input(const char* name,const char* label,const char* value,const char* type="text") {
    return String("<label>")+label+"<input name='"+name+"' type='"+type+"' step='any' value=\""+escape(value)+"\"></label>";
  }
  bool csrf() {return server.hasArg("token") && server.arg("token")==settings->apPassword;}
public:
  bool active=false,changed=false,forgetPeer=false,restartRequested=false,closeRequested=false;
  bool canUpdate=false;
  uint32_t activeActivity=0;
  bool wifiConnected=false,mqttConnected=false;
  uint32_t pendingSamples=0,droppedSamples=0,storageErrors=0,environmentSequence=0;
  uint64_t clockUtc=0;
  const char* clockSource="WAIT GPS/WIFI";
  uint64_t requestedTime=0;
  bool (*deleteActivity)(uint32_t)=nullptr;
  bool magCalibrationRequested=false;
  const char* magCalibrationStatus="NOT CALIBRATED";
  char ssid[25]={};
  void begin(RuntimeSettings& runtime,AlertService& alarm) {
    settings=&runtime;alerts=&alarm;snprintf(ssid,sizeof(ssid),"KU-WATCH-%04X",unsigned(ESP.getEfuseMac()&0xffff));
    // WebServer sends non-multipart bodies through the same upload callback.
    // Its upload() pointer is null for those requests, so inspect the header first.
    const char* headers[]={"Content-Type"};server.collectHeaders(headers,1);
    server.on("/status",HTTP_GET,[this] {
      if(!authenticate())return;
      server.sendHeader("Cache-Control","no-store");
      server.send(200,"application/json",String("{\"firmware\":\"")+WatchExt::VERSION+"\",\"uptime_ms\":"+String(millis())+
        ",\"recording\":"+String(activeActivity)+",\"ota_allowed\":"+String(canUpdate?"true":"false")+
        ",\"wifi\":"+String(wifiConnected?"true":"false")+",\"mqtt\":"+String(mqttConnected?"true":"false")+
        ",\"pending\":"+String(pendingSamples)+",\"dropped\":"+String(droppedSamples)+",\"storage_errors\":"+String(storageErrors)+
        ",\"environment_sequence\":"+String(environmentSequence)+",\"clock_source\":\""+clockSource+"\",\"utc\":"+String((unsigned long)clockUtc)+"}");
    });
    server.on("/close",HTTP_POST,[this] {
      if(!authenticate())return;if(!csrf()) {server.send(403,"text/plain","Invalid token");return;}
      closeRequested=true;server.send(200,"text/html; charset=utf-8","ปิดหน้าตั้งค่าแล้ว นาฬิกายังทำงานต่อได้");
    });
    server.on("/",HTTP_GET,[this] {
      if(!authenticate())return;
      auto& s=settings->value;
      String html="<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>KU Watch</title><style>body{font:16px sans-serif;max-width:600px;margin:24px auto;padding:16px}label{display:block;margin:12px 0}input{display:block;width:95%;padding:8px}button{padding:12px}</style><h1>KU Watch "+String(WatchExt::VERSION)+"</h1><p>ตั้งค่าแล้วจำหลังปิดเครื่อง ช่องรหัสผ่านว่าง = ใช้ค่าเดิม</p><form method='post' action='/save'>";
      html+="<input type='hidden' name='token' value='"+settings->apPassword+"'>";
      html+=input("ssid","Wi-Fi SSID",s.ssid)+input("password","Wi-Fi password","","password");
      html+=input("host","MQTT host",s.host)+input("port","MQTT port",String(s.port).c_str(),"number");
      html+=input("tls","MQTT TLS: 1=เปิด, 0=ปิด",String(s.tls).c_str(),"number");
      html+=input("user","MQTT user",s.user)+input("mqtt_password","MQTT password","","password")+input("topic","MQTT topic",s.topic);
      html+=input("led","Pulse LED 1–63",String(s.led).c_str(),"number")+input("average","Pulse averaging 0/1",String(s.average).c_str(),"number");
      html+=input("idle","พักจอหลังไม่ได้กด (วินาที; 0=ไม่พัก)",String(s.idleSeconds).c_str(),"number");
      html+=input("logging","CSV ทุก 5 วินาที: 0/1",String(s.logging).c_str(),"number");
      html+=input("shunt","Shunt Ω (0=ยังไม่ได้สอบเทียบกระแส)",String(s.shuntOhms,5).c_str(),"number");
      html+=input("manifest","OTA manifest HTTPS URL",s.manifest);
      html+=input("temperature_limit","เตือนอุณหภูมิเกิน °C",String(alerts->model.settings.temperature,2).c_str(),"number");
      html+=input("iaq_limit","เตือน IAQ เกิน",String(alerts->model.settings.iaq,2).c_str(),"number");
      html+="<button>บันทึก</button></form><h2>ข้อมูลเซ็นเซอร์</h2>";
      for(unsigned i=0;i<4;++i)html+="<p><a href='/csv?slot="+String(i)+"'>CSV "+String(i)+"</a></p>";
      html+="<h2>กิจกรรม WALK</h2><p><a href='/activities'>รายการกิจกรรม</a> · ดาวน์โหลดและแปลง TCX ผ่านตัวส่งออกบนคอมได้ทั้ง USB และ Wi-Fi</p>";
      html+="<h2>เวลา</h2><p>GPS หรืออินเทอร์เน็ตซิงค์เวลาเองได้ หากเปิดใหม่หลังปิดสวิตช์แล้วไม่มีสัญญาณ ให้ตั้งจากมือถือได้</p><form method='post' action='/clock' onsubmit=\"this.utc.value=Math.floor(Date.now()/1000)\"><input type='hidden' name='token' value='"+settings->apPassword+"'><input type='hidden' name='utc'><button>ตั้งเวลาจากมือถือ</button></form>";
      html+="<h2>อัปเดตเฟิร์มแวร์</h2><p>หยุด WALK และรอแบต ≥30% ก่อนอัปเดต</p><form method='post' action='/update?token="+settings->apPassword+"' enctype='multipart/form-data'><input name='firmware' type='file' accept='.bin'><button>อัปเดต</button></form>";
      html+="<form method='post' action='/unpair'><input type='hidden' name='token' value='"+settings->apPassword+"'><button>ล้างการจับคู่จอใหญ่</button></form>";
      html+="<h2>เข็มทิศ</h2><p>"+String(magCalibrationStatus)+"</p><form method='post' action='/magcal'><input type='hidden' name='token' value='"+settings->apPassword+"'><button>เริ่มสอบเทียบ 60 วินาที</button></form><p>หมุนผ่านทุกแกน แล้วกลับมาหน้านี้เพื่อตรวจผล</p>";
      html+="<form method='post' action='/close'><input type='hidden' name='token' value='"+settings->apPassword+"'><button>ปิดหน้าตั้งค่า</button></form>";
      server.send(200,"text/html; charset=utf-8",html);
    });
    server.on("/save",HTTP_POST,[this] {
      if(!authenticate())return;if(!csrf()) {server.send(403,"text/plain","Invalid token");return;}
      auto s=settings->value;bool ok=true;
      auto copy=[&](const char* name,char* out,size_t size,bool secret=false) {
        if(!server.hasArg(name)) {ok=false;return;}
        String v=server.arg(name);if(secret && !v.length())return;
        if(v.length()>=size) {ok=false;return;}strlcpy(out,v.c_str(),size);
      };
      copy("ssid",s.ssid,sizeof(s.ssid));copy("password",s.password,sizeof(s.password),true);
      copy("host",s.host,sizeof(s.host));copy("user",s.user,sizeof(s.user));copy("mqtt_password",s.mqttPassword,sizeof(s.mqttPassword),true);
      copy("topic",s.topic,sizeof(s.topic));copy("manifest",s.manifest,sizeof(s.manifest));
      auto integer=[&](const char* name,long low,long high)->long {String a=server.arg(name);char* end;long v=strtol(a.c_str(),&end,10);
        if(!a.length()||*end||v<low||v>high)ok=false;return v;};
      s.port=integer("port",1,65535);s.tls=integer("tls",0,1);s.led=integer("led",1,63);s.red=s.led;
      s.average=integer("average",0,1);s.idleSeconds=integer("idle",0,3600);s.logging=integer("logging",0,1);
      String raw=server.arg("shunt");char* end;s.shuntOhms=strtof(raw.c_str(),&end);if(!raw.length()||*end)ok=false;
      String t=server.arg("temperature_limit"),q=server.arg("iaq_limit");char *te,*qe;
      float temperature=strtof(t.c_str(),&te),iaq=strtof(q.c_str(),&qe);
      if(!t.length()||*te||!q.length()||*qe||!EnvAlert::Settings::valid(temperature,iaq))ok=false;
      if(!ok || !WatchExt::valid(s)) {server.send(400,"text/plain","Invalid settings");return;}
      if(!settings->save(s) || !alerts->configure(temperature,iaq)) {server.send(500,"text/plain","Storage error; review saved settings");return;}
      changed=true;server.send(200,"text/html; charset=utf-8","บันทึกแล้ว <a href='/'>กลับ</a>");
    });
    server.on("/csv",HTTP_GET,[this] {
      if(!authenticate())return;String v=server.arg("slot");
      if(v.length()!=1 || v[0]<'0'||v[0]>'3') {server.send(400,"text/plain","Invalid slot");return;}
      String path="/sensors"+v+".csv";File f=LittleFS.open(path,FILE_READ);
      if(!f) {server.send(404,"text/plain","No log in this slot");return;}
      server.sendHeader("Content-Disposition","attachment; filename=sensors"+v+".csv");server.streamFile(f,"text/csv");f.close();
    });
    server.on("/unpair",HTTP_POST,[this] {if(!authenticate())return;if(!csrf()) {server.send(403,"text/plain","Invalid token");return;}
      forgetPeer=true;server.send(200,"text/plain","Peer removed; display can pair again");});
    server.on("/activities",HTTP_GET,[this] {
      if(!authenticate())return;String json="{\"active\":"+String(activeActivity)+",\"files\":[";File root=LittleFS.open("/");bool comma=false;
      for(File f=root.openNextFile();f;f=root.openNextFile()) {
        const char* name=f.name();if(*name=='/')++name;unsigned long id;char extra;
        if(sscanf(name,"rec%6lu.kua%c",&id,&extra)==1 && id && id<=999999) {
          if(comma)json+=',';comma=true;json+="{\"id\":"+String(id)+",\"size\":"+String(f.size())+"}";
        }
        f.close();
      }
      root.close();json+="]}";server.send(200,"application/json",json);
    });
    server.on("/activity",HTTP_GET,[this] {
      if(!authenticate())return;String value=server.arg("id");char* end;unsigned long id=strtoul(value.c_str(),&end,10);
      if(!value.length()||*end||!id||id>999999) {server.send(400,"text/plain","Invalid activity ID");return;}
      if(activeActivity) {server.send(409,"text/plain","Stop recording before downloading");return;}
      char path[32];snprintf(path,sizeof(path),"/rec%06lu.kua",id);File f=LittleFS.open(path,FILE_READ);
      if(!f) {server.send(404,"text/plain","No activity");return;}
      server.sendHeader("Content-Disposition","attachment; filename="+String(path+1));server.streamFile(f,"application/octet-stream");f.close();
    });
    server.on("/clock",HTTP_POST,[this] {
      if(!authenticate())return;if(!csrf()) {server.send(403,"text/plain","Invalid token");return;}
      String value=server.arg("utc");char* end;uint64_t utc=strtoull(value.c_str(),&end,10);
      if(!value.length()||*end||utc<1704067200ULL||utc>4102444799ULL) {server.send(400,"text/plain","Invalid UTC");return;}
      requestedTime=utc;server.send(200,"text/plain","Clock accepted");
    });
    server.on("/delete",HTTP_POST,[this] {
      if(!authenticate())return;if(!csrf()) {server.send(403,"text/plain","Invalid token");return;}
      String value=server.arg("id");char* end;unsigned long id=strtoul(value.c_str(),&end,10);
      if(!value.length()||*end||!id||id>999999) {server.send(400,"text/plain","Invalid activity ID");return;}
      bool ok=deleteActivity && deleteActivity(id);server.send(ok?200:409,"text/plain",ok?"Deleted":"Busy, missing file, or storage error");
    });
    server.on("/magcal",HTTP_POST,[this] {if(!authenticate())return;if(!csrf()) {server.send(403,"text/plain","Invalid token");return;}
      magCalibrationRequested=true;server.send(200,"text/html; charset=utf-8","เริ่มสอบเทียบ หมุนครบทุกแกน 60 วินาที แล้ว <a href='/'>กลับไปตรวจผล</a>");});
    server.on("/update",HTTP_POST,[this] {
      if(!authenticate())return;
      bool ok=csrf()&&uploadOk;server.send(ok?200:400,"text/plain",ok?"Verified. Restarting":"Update refused or failed");
      uploadOk=false;
      if(ok)restartRequested=true;
    },[this] {
      if(!server.header("Content-Type").startsWith("multipart/form-data")) {uploadOk=false;return;}
      auto& upload=server.upload();
      if(upload.status==UPLOAD_FILE_START) {
        uploadOk=false;uploadStarted=false;
        if(!authorized() || !csrf() || !canUpdate)return;
        uploadStarted=Update.begin(UPDATE_SIZE_UNKNOWN,U_FLASH);
      } else if(upload.status==UPLOAD_FILE_WRITE && uploadStarted) {
        if(!canUpdate || Update.write(upload.buf,upload.currentSize)!=upload.currentSize) {Update.abort();uploadStarted=false;}
      } else if(upload.status==UPLOAD_FILE_END && uploadStarted) {uploadOk=Update.end(true);uploadStarted=false;}
      else if(upload.status==UPLOAD_FILE_ABORTED && uploadStarted) {Update.abort();uploadStarted=false;}
    });
  }
  void start() {
    if(active)return;WiFi.mode(WIFI_AP_STA);WiFi.softAP(ssid,settings->apPassword.c_str(),WiFi.channel()?WiFi.channel():1,0,1);
    server.begin();active=true;at=millis();Serial.println("SETUP ACTIVE http://192.168.4.1 admin; password shown on watch");
  }
  void stop() {if(!active)return;server.stop();WiFi.softAPdisconnect(true);WiFi.mode(WIFI_STA);active=false;Serial.println("SETUP CLOSED");}
  void tick() {if(active) {server.handleClient();if(closeRequested || uint32_t(millis()-at)>600000) {closeRequested=false;stop();}}}
};
