// Local editable presentation from actual project evidence; no cloud publishing.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const runtime=path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies');
process.env.RUNTIME_NODE_MODULES=path.join(runtime,'node/node_modules');
const skill=path.join(process.env.USERPROFILE,'.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations');
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(runtime,'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const build=path.join(root,'output/presentation_build_v2_final');
const output=path.join(root,'output/delivery_20261009');
await fs.mkdir(build,{recursive:true});await fs.mkdir(output,{recursive:true});
const p=Presentation.create({slideSize:{width:1280,height:720}});
const green='#145B43',ink='#152E27',muted='#52645E',font='Tahoma';
function text(s,value,x,y,w,h,size=26,bold=false,color=ink){
 const q=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 q.text=value;q.text.style={typeface:font,fontSize:size,bold,color};return q;
}
function slide(title,notes=''){
 const s=p.slides.add();s.background.fill='#FFFFFF';text(s,title,72,48,1136,78,44,true,green);
 text(s,String(p.slides.items.length),1160,654,48,26,16,false,muted);
 s.speakerNotes.text=notes;return s;
}
function table(s,values,y=165,height=420,widths=[290,450,396]){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:72,top:y,width:1136,height,values,columnWidths:widths});
 t.borders.assign({fill:'#D7E2DB',width:1,style:'solid'});
 for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
  const cell=t.getCell(r,c);cell.fill=r===0?green:r%2?'#F1F6F2':'#FFFFFF';
  cell.text.style={typeface:font,fontSize:22,color:r===0?'#FFFFFF':ink,bold:r===0};
 }
 return t;
}
const rubric='https://github.com/cchantra/IoT-Lab/wiki/Week%E2%80%904%E2%80%90Project%E2%80%90Proposal%E2%80%90Rubric';
function node(s,label,x,y,w,h,main=false){const q=s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:main?green:'#F1F6F2',line:{fill:green,width:1.5}});q.text=label;q.text.style={typeface:font,fontSize:23,bold:main,color:main?'#FFFFFF':ink};return q;}
function edge(s,a,b,from='right',to='left',two=false){s.shapes.connect(a,b,{kind:'elbow',fromSide:from,toSide:to,line:{fill:green,width:2},tail:{type:'arrow'},head:{type:two?'arrow':'none'}});}
function media(s,label,x,y,w,h,video=false){
 const q=s.shapes.add({geometry:'rect',name:video?'VIDEO_INSERT_HERE':'PHOTO_INSERT_HERE',position:{left:x,top:y,width:w,height:h},fill:'#F1F6F2',line:{fill:green,width:2,style:'dashed'}});
 text(s,(video?'วิดีโอทดสอบ':'ภาพประกอบ')+'\n'+label,x+22,y+h/2-45,w-44,90,25,true,green);
 return q;
}
const times=[10,30,25,45,35,35,30,30,40,25,35,25,25,30];
function notes(s,index,source,explain){s.speakerNotes.text=`เวลาพูด ${times[index-1]} วินาที\n${explain}\nหลักฐาน: ${source}\nเกณฑ์ประเมิน: ${rubric}`;}
let s=slide('Smart Environment Watch');
text(s,'นาฬิกาตรวจสภาพแวดล้อม\nและข้อมูลสุขภาพเบื้องต้น',72,180,745,145,44,true);
text(s,'สมาชิก: ____________ บทบาท: ____________\nสมาชิก: ____________ บทบาท: ____________',72,378,745,110,27);
media(s,'ตัวเล็ก + จอใหญ่',865,173,343,350);
text(s,'KU Watch 2.0.5 / Hub 1.0.5 · 9 ตุลาคม2569',72,565,1136,55,26,false,green);
notes(s,1,'เอกสารRequirements v2 / รายงานผลระบบล่าสุด','ชื่อสมาชิกและบทบาทเว้นตามคำขอผู้ใช้ โครงการรับต่อทั้งระบบ ไม่อ้างว่าผ่านตรวจรับทุกข้อ');
s=slide('ปัญหาและกลุ่มผู้ใช้');
text(s,'ผู้ทำกิจกรรมกลางแจ้งในมหาวิทยาลัย\nและพื้นที่เกษตร ต้องการดูข้อมูล ณ จุดใช้งาน\nทั้งสภาพแวดล้อมและสุขภาพเบื้องต้น',72,168,720,170,31,true);
text(s,'เป้าหมาย: บางเขนและอำนาจเจริญ\nค่าทั่วไปไม่ใช่ค่าที่วัด ณ จุดที่ยืน\nจอข้อมือดูทันที จอใหญ่/เว็บดูร่วมกัน',72,375,710,185,28);
media(s,'การใช้งานจริงในพื้นที่',850,180,358,370);
text(s,'ยังไม่ได้เก็บแบบสอบถามหรือพิสูจน์ผลกับกลุ่มผู้ใช้จริง',72,605,1136,35,21,false,muted);
notes(s,2,'สถานที่/การใช้งานที่ผู้ใช้ยืนยันในบทสนทนา','นี่คือบริบทเป้าหมายของโครงการ ไม่อ้างว่ามีการสำรวจความต้องการผู้ใช้แล้ว');
s=slide('เป้าหมายและขอบเขต');
table(s,[['เป้าหมาย','ขอบเขตปัจจุบัน','ไม่ทำในรอบนี้'],['วัดและแสดงข้อมูล','MAX30102 / BME68x / GY-51 / INA226','การวินิจฉัยทางการแพทย์'],['สื่อสารและเก็บย้อนหลัง','Wi-Fi MQTT / ESP-NOW / LittleFS','เพิ่มSD/RTCสำรองกลับตัวเล็ก'],['ใช้งานและดูแลระบบ','MAP / WALK / NVS / OTAมือถือ','GrafanaภาพบนจอESP32']],165,295,[290,465,381]);
text(s,'ขั้นต่ำมีครบ: เซ็นเซอร์ + ไร้สาย + จอ/เตือน\nองค์ประกอบเสริม: แบต / Preferences / OTA / RTCจอใหญ่',72,515,1136,105,29,true,green);
notes(s,3,'ความต้องการ_สถานะล่าสุด.md','ขอบเขตอุปกรณ์เปลี่ยนตามผู้ใช้ GPS/WALK/MAP/KU-BOTได้รับอนุญาตภายหลัง SDยกเลิกแล้ว');
s=slide('สถาปัตยกรรมฝั่งอุปกรณ์');
const sensors=node(s,'I²C · SDA8 / SCL9\nMAX 0x57 / BME 0x76–77\nGY 0x18,1E / INA 0x44',72,155,342,145);
const esp=node(s,'ESP32-S3\nSuper Mini',506,294,250,100,true);
const timeNode=node(s,'GPS / NTP / HUB RTC\nเปิดใหม่รับเวลาที่พร้อม',506,148,250,90);
const gpsNode=node(s,'GPS UART 9600\nTX→RX12 / RX←TX13\nปุ่ม GPIO4 / reset GPIO5',72,424,342,138);
const lcd=node(s,'GC9A01A · SPI\nSCK10 MOSI11 CS6 DC7 RST5',884,155,324,103);
const hub=node(s,'จอใหญ่480×480 / ทัช\nESP-NOWสองทาง / RTC',884,301,324,105);
const store=node(s,'LittleFS: CSV / queue / WALK\nPreferences: ตั้งค่า / จับคู่',472,488,366,105);
const power=node(s,'LiPo3.7V 1000mAh\nสวิตช์ / ทางไฟยังรอตรวจ',884,476,324,112);
edge(s,sensors,esp);edge(s,gpsNode,esp);edge(s,timeNode,esp,'bottom','top');edge(s,esp,lcd);edge(s,esp,hub,'right','left',true);edge(s,esp,store,'bottom','top');edge(s,power,esp,'left','right');
text(s,'สัญญาณ3.3V · GPIO4/RST5มีผลร่วมจริง · แยกบัสI²Cจอใหญ่จากตัวเล็ก',72,631,1136,34,20,false,muted);
notes(s,4,'include/config.h,src/main.cpp; https://docs.waveshare.com/ESP32-S3-Touch-LCD-2.1','ESP32กลางผังมีอินพุต เอาต์พุต เวลา ที่เก็บ สื่อสารและไฟครบ INA226ยืนยัน0x44; โมดูล/แรงดันจ่ายและการกันไฟย้อนยังต้องตรวจจริง ห้ามต่อตรงLiPoเข้าขา3V3โดยเดา');
s=slide('Data flow ถึงเซิร์ฟเวอร์และฐานข้อมูล');
const watch=node(s,'ตัวเล็ก\nLittleFS journal',72,205,240,105,true);
const broker=node(s,'HiveMQ Cloud\nMQTT TLS / QoS1',427,205,250,105);
const nr=node(s,'Node-RED · คอม\nรับJSON / readiness',792,205,330,105);
const spool=node(s,'SQLite spool · คอม\nยืนยันเข้าคิวก่อนส่งDB',792,408,330,105);
const db=node(s,'InfluxDB · คอม\nฐาน iot / ตาราง ku_watch',427,408,250,105);
const graf=node(s,'Grafana · คอม/เว็บ\nข้อมูลล่าสุด / กราฟ / ผู้ใช้',72,408,240,105);
edge(s,watch,broker);edge(s,broker,nr);edge(s,nr,spool,'bottom','top');edge(s,spool,db,'left','right');edge(s,db,graf,'left','right');
text(s,'PUBACKยืนยันbroker · SQLiteช่วยหลังเข้าคิว · ช่วงก่อนเข้าคิวยังมีข้อจำกัด',72,588,1136,65,24,false,muted);
notes(s,5,'include/network_worker.h / tools/influx_queue.py / integration/node-red','เลือกNode-REDเพราะดูflow/สถานะง่าย Influxเก็บtime-series Grafanaทำกราฟ; localbackendต้องเปิดคอม brokercloudอยู่ภายนอก ไม่อ้างว่าACKถึงฐานข้อมูล');
s=slide('การออกแบบการเชื่อมต่อ');
table(s,[['ช่องทาง','เหตุผล / ทางเลือก','รายละเอียดจริง'],['MQTTผ่านWi-Fi','pub/sub / QoS1 เทียบHTTPต้องpollเอง','ku_watch/live + /status(LWT)'],['ข้อมูล / สถานะ','JSONอ่านง่าย / แยกข้อมูลใหม่กับย้อนหลัง','data retain=false / status=true'],['ESP-NOWสองทาง','สื่อสารจอใกล้กันไม่ต้องมีbroker','จับคู่ / auth / ACK / retry'],['ความปลอดภัย','TLS + รหัสผ่าน / ตั้งค่าในNVS','clientIDจากMAC / backoff1–60s']],155,370,[300,465,371]);
text(s,'โครง payload: device / sample_id / timestamp / temp / iaq_valid / battery_percent / backfill',72,568,1136,75,23);
notes(s,6,'network_worker.h / espnow_auth.h / runtime_settings.h','privateclusterแยกกลุ่มในปัจจุบัน หากใช้brokerรวมให้ตั้งtopicชื่อกลุ่ม+deviceและเปลี่ยนreceiverพร้อมกัน HTTPใช้เฉพาะsetup/localAPI BLEต้องมีgatewayเพิ่มเติม topicตัวอย่างไม่ส่งค่าจำลอง credentialsไม่นำเข้าZIP');
s=slide('สคีมาข้อมูลและปริมาณที่คาด');
table(s,[['กลุ่มข้อมูล','ชนิด / ตัวอย่าง','การจัดการ'],['device / timestamp','tag:string / UTCวินาที','เวลาเชื่อถือได้; ไม่มีเวลาใช้รับเข้า'],['ค่าที่วัด','number: temp, humidity, bpm','เขียนเฉพาะfinite/พร้อมใช้'],['สถานะ','bool / state0–2 / firmware:string','WAITINGไม่แทนด้วยค่าศูนย์'],['ตัวระบุข้อความ','sample_id: session-sequence / tag','แยกcapture; ส่งซ้ำใช้จุดเดิม']],160,345,[300,465,371]);
text(s,'1Hz = 86,400ข้อความ/วัน · สมมติJSON2kB ≈172.8MB/วัน\nแฟลชเป็นคิวจำกัด768รายการ; DBควรวาง retention30วันตามดิสก์จริง',72,543,1136,90,27,true,green);
notes(s,7,'src/main.cpp / integration/node-red/to_influx.js / capture_storage.json','172.8MBเป็นpayloadสมมติ ไม่ใช่ขนาดฐานข้อมูลบนดิสก์หรือผลวัดcompression Retention30วันเป็นแผน ยังไม่ตั้งTTL sample_idเป็นtagแยกcapturesเวลาวินาทีเดียว ทดสอบ5capturesจริงและส่งcaptureแรกซ้ำ2ครั้ง พบหนึ่งรายการต่อcapture');
s=slide('BOM และเหตุผลเลือกอุปกรณ์');
table(s,[['รายการ / Interface','เหตุผล / ทางเลือก','ราคา: ผู้ใช้เติมภายหลัง'],['Super Mini + GC9A01A / SPI','แยกจอเล็กสวมใส่จากจอใหญ่','________________'],['Touch-LCD-2.1 / ESP-NOW','ดูง่าย/ทัช/RTCในบอร์ด เทียบจอเดียว','________________'],['MAX30102 + BME68x / I²C','PPG+IAQ เทียบsensorอากาศอย่างเดียว','________________'],['GY-51 + INA226 / I²C','motion+แรงดัน เทียบADCเฉพาะV','________________'],['GPS / UART + LiPo1000mAh','ตำแหน่ง / ไฟเคลื่อนที่ / สายและเคส','________________']],160,425,[330,485,321]);
text(s,'จำนวนและราคาทุกรายการ: BOM_ราคาจริง.csv · งบ≤3,000บาทยังไม่ตรวจรับ',72,616,1136,38,21,false,muted);
notes(s,8,'BOM_ราคาจริง.csv / ผู้ใช้สั่งเว้นราคาไว้','ไม่ใส่ราคาเดาเป็นราคาซื้อจริง ต้องรวมทั้งสองบอร์ด แบต ทางไฟ สายและเคสก่อนเทียบงบ และตรวจVINของโมดูลจริง');
s=slide('Workflow: setup() และ loop()');
const init1=node(s,'GPIOปลอดภัย\nจอ / เวลา',72,170,240,100);
const init2=node(s,'NVS / LittleFS\nเซ็นเซอร์ / บัส',402,170,280,100);
const init3=node(s,'Wi-Fi / worker\nESP-NOW / OTA',792,170,330,100,true);
edge(s,init1,init2);edge(s,init2,init3);
text(s,'setup()',72,132,240,30,23,true,green);
const sense=node(s,'Sense\nFIFO/ GPS / I²C',72,398,240,110);
const think=node(s,'Think\nfilter / readiness / alert',402,398,280,110);
const act=node(s,'Act\nจอ / capture / คำสั่ง',792,398,330,110,true);
edge(s,sense,think);edge(s,think,act);edge(s,act,sense,'bottom','bottom');
text(s,'loop() + worker: MQTT1s / CSV5s / BSEC3s / GY-51~0.5s\nจอเล็กส่งภาพเป็นstripและบริการFIFO/GPSระหว่างส่ง',72,585,1136,70,24);
notes(s,9,'src/main.cpp setup/loop/networkTick/paint / environment_sensor.h','จุดbootมีdelayสั้นสีทดสอบจอ ไม่กล่าวว่าไม่มีdelayทั้งโปรแกรม ในrunแยกtaskเครือข่ายและทัชจอใหญ่ millisแยกจังหวะ ไม่มีรอsensorก่อนเปิดจอ');
s=slide('Design patterns ในโค้ด');
table(s,[['แนวทาง','ใช้ที่ไหน','พฤติกรรม'],['Offline-first','telemetry_store / influx_queue','journal + PUBACK / durable spool'],['Non-blocking','network_worker / touch_sampler','แยกtask / ไม่รอUSB log'],['Config / Preferences','runtime_settings / setup_service','ตั้งค่าเว็บ / CRC / NVS'],['Health / modules','sensor classes / battery_alert / ota','stale→WAITING / battery gate / health']],160,390,[300,465,371]);
text(s,'LittleFSใช้แทนSDตามขอบเขตใหม่ · ไม่ถือว่าofflineปลอดภัยถึงDBทุกช่วง',72,601,1136,44,23,false,muted);
notes(s,10,'include/*.h / large_display/KU_Hub/touch_sampler.h','อธิบายpatternจากโมดูลจริง ไม่ใส่ชื่อpatternที่โค้ดไม่ได้ใช้ แต่ละsensorแยกหน้าที่ lifecycleและvalidity; privateheadersไม่เข้าส่งงาน');
s=slide('กรณีผิดปกติและการตอบสนอง');
text(s,'เน็ตขาด: queue / backoff / replay\nWi-Fiและพอร์ตMQTTขาด10นาทีผ่าน',72,163,650,85,27,true);
text(s,'แบต≤20%: เตือนจอ / OTAต้อง≥30%\nยังไม่ทดสอบแบต6ชั่วโมง',72,290,650,85,27);
text(s,'sensorขาด: WAITING / retry\nจอดำ: กู้หลังปล่อยปุ่ม\nPOSTผิดรูปแบบ: reject / ไม่รีสตาร์ต',72,415,650,145,27);
media(s,'เน็ตหลุด → ส่งย้อนหลัง',765,175,443,300,true);
text(s,'แทรก → วิดีโอ → อุปกรณ์นี้\nเลือกเล่นเมื่อคลิกหรืออัตโนมัติ',765,506,443,85,21,false,muted);
text(s,'CSV/queueมีขอบเขตและสำรองพื้นที่ · ไม่ใช้ค่าปลอมแทนข้อมูลขาด',72,621,1136,35,22,true,green);
notes(s,11,'portal_acceptance.json / battery_alert.h / environment_sensor.h / telemetry_store.h','แบตต่ำเตือนแต่ไม่ได้ปิดเครื่องเอง/หรี่GPIObacklightที่ไม่มี เปิดตัวเล็กใหม่รับGPS/NTPหรือRTCจอใหญ่ที่เชื่อถือได้ กรณีดับทั้งสองบอร์ดยังต้องตรวจRTCbackup ไม่ซ่อนความเสียหายด้วยค่าคงที่');
s=slide('แผนงานและการแบ่งงาน');
table(s,[['ช่วง','งาน / สิ่งส่งมอบ','ผู้รับผิดชอบ: เติมภายหลัง'],['W1–2','ขอบเขต / BOM / pin / sensor / จอ','________________'],['W3–4','Sense–Think–Act / MQTT / DB / Grafana','________________'],['W5–6','CSV / offline / NVS / alerts / OTA','________________'],['W7–8','24h / แบต / เทียบค่า / คู่มือ / นำเสนอ','________________']],160,385,[260,555,321]);
text(s,'แผนเดิมเป็นW1–W8 · ปัจจุบันรับต่อทั้งระบบ\nเหลือการทดสอบจริงและราคาซื้อ ไม่ระบุสัปดาห์ว่างว่าทำสำเร็จแล้ว',72,587,1136,70,25);
notes(s,12,'Requirements v2แผนเดิม / userรับต่อทั้งระบบ','เว้นผู้รับผิดชอบตามคำขอ หัวเอกสารกับtimelineเดิมบทบาทขัดกันจึงไม่ยกชื่อสมาชิกไปผูกกับงานเอง นำเสนอควรแบ่งทั้งdevice/network/backend');
s=slide('ความเสี่ยงและแผนสำรอง');
table(s,[['ความเสี่ยง','รับมือที่ทำได้','รายการข้าม'],['PPGข้อมือ / GPSในอาคาร','จัดตำแหน่ง/ทดสอบนิ้ว; รอGPSกลางแจ้ง','ค่าเทียบอ้างอิง / routeจริง'],['ไฟ / แบต / จอมีRSTร่วม','สำรอง/softreset/ตรวจpowerpathจริง','6h / RTCbackup / กันไฟย้อน'],['คิว / OTA / captureชนเวลา','boundedjournal / A-B / sample_id tag','HTTPSauto / ตัดไฟ3ครั้ง']],160,340,[315,490,331]);
text(s,'FR-06: คง3รอบตามเกณฑ์ ผลจำลอง1Hzเตือนประมาณ2วินาที\nBSECจริง~3s/รอบ; ยังต้องวัดจอและแดชบอร์ดจริงภายใน5s',72,549,1136,90,27,true,green);
notes(s,13,'ตรวจรับ_ที่ข้ามไว้.md / environment_alert.h / to_influx.js','OTAhostingคำสั่งgateway/tunnelถูกautomaticapproval reviewปฏิเสธblocked by policy จึงไม่อ้างautoOTAผ่าน การกู้ด้วยA/Bมีโค้ดแต่ยังไม่physicalpowercut3ครั้ง');
s=slide('เกณฑ์ความสำเร็จและหลักฐานปัจจุบัน');
const outage=JSON.parse(await fs.readFile(path.join(root,'output/requirements_audit_20261009/broker_outage.json'),'utf8'));
if(!outage.passed)throw Error('Completed real outage evidence is required');
s.images.add({blob:new Uint8Array(await fs.readFile(path.join(output,'ผลทดสอบ_MQTT_10นาที.png'))),contentType:'image/png',alt:'กราฟคิวส่งจริงระหว่างพอร์ต MQTT ใช้ไม่ได้ 10 นาที',fit:'contain',position:{left:72,top:162,width:650,height:366}});
text(s,`DBครบ ${outage.database_outage_captures} ข้อมูลช่วงขาด; ลำดับขาด0\nผู้ใช้ยืนยันปิดเปิดแล้วเวลากลับมาตรง`,72,548,650,75,23,true,green);
media(s,'เปลี่ยนหน้า / ค่าจริง / WALK',758,171,450,257,true);
media(s,'ผลกราฟหรือCSVจริง',758,470,450,150);
text(s,'ชุดส่งมอบ: source / คู่มือ / รายงาน / เครื่องมือตรวจ / รายการข้าม',72,641,1136,32,21,true,green);
notes(s,14,'รายงานผลระบบล่าสุด / output/requirements_audit_20261009 / output/acceptance/report.json','วัดอะไรต้องบอกboundary: Grafanaผลถึงqueryไม่รวมbrowserpaint touchpageACKไม่แทนphysicallatency สมาชิกซ้อมร่วมและเตรียมคำถามGPIO/topic/QoS/database/offline');
const draft=path.join(build,'candidate.pptx');await (await PresentationFile.exportPptx(p)).save(draft);
const final=path.join(output,'KU_Watch_ตามเกณฑ์ประเมิน_25691009_v2.pptx');
await finalizePresentation({workspaceDir:root,candidatePath:draft,finalPath:final,
 pythonExecutable:path.join(runtime,'python/python.exe'),
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...[3,6,7,8,10,12,13].flatMap(n=>['--require-native-table-slide',String(n)])],
 fontPolicy:{basis:'design',families:[font]},explicitTotalSlideCount:14,
 requiredNativeTableOwnerSlides:[3,6,7,8,10,12,13],verifyArtifactToolImport:true,
 receiptPath:path.join(build,'validation.json')});
for(let i=0;i<p.slides.items.length;i++){
 const png=await p.export({slide:p.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(build,'slide-'+String(i+1).padStart(2,'0')+'.png'),new Uint8Array(await png.arrayBuffer()));
}
console.log('Editable handoff deck finalized:',final);
