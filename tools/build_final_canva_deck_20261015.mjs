import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const runtime='C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES=path.join(runtime,'node/node_modules');
const skill='C:/Users/pomma/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(runtime,'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const base=path.join(root,'output/canva_presentation_20261015');
const build=path.join(base,'build_v2'),out=path.join(base,'deliverable');
await fs.mkdir(build,{recursive:true});await fs.mkdir(out,{recursive:true});
const p=Presentation.create({slideSize:{width:1920,height:1080}});
const C={ink:'#28353B',green:'#40A98D',blue:'#7393AE',gold:'#C59130',muted:'#68787D',line:'#D9E2E3',pale:'#F3F8F6',white:'#FFFFFF'};
const font='Tahoma';
const times=[20,25,25,40,35,30,40,30,35,25,45,35,25,10];
const rubric='https://github.com/cchantra/IoT-Lab/wiki/Week%E2%80%904%E2%80%90Project%E2%80%90Proposal%E2%80%90Rubric';
const sourceReq=path.join(root,'output/deadline_20261018/requirements_original.json');
function text(s,v,x,y,w,h,size=32,bold=false,color=C.ink){
 const q=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 q.text=v;q.text.style={typeface:font,fontSize:size,bold,color};q.text.insets=0;return q;
}
function box(s,x,y,w,h,fill=C.white,line=C.line,name){return s.shapes.add({geometry:'rect',name,position:{left:x,top:y,width:w,height:h},fill,line:{fill:line,width:2}});}
function slide(title,subtitle=''){
 const s=p.slides.add();s.background.fill=C.white;
 text(s,title,110,67,1700,95,62,true);box(s,110,178,135,5,C.green,C.green);
 if(subtitle)text(s,subtitle,110,204,1700,57,29,false,C.muted);
 text(s,'KU WATCH  /  15 ตุลาคม 2569',110,1025,1450,32,21,false,C.muted);
 text(s,String(p.slides.items.length).padStart(2,'0'),1748,1025,70,32,22,false,C.green);
 return s;
}
function note(s,n,body,sources=[]){s.speakerNotes.text=`เวลาพูด ${times[n-1]} วินาที (รวม 7 นาที)\n${body}\nแหล่งข้อมูล: ${[sourceReq,...sources].join('\n')}\nเกณฑ์ประเมิน: ${rubric}\nชุดนี้รายงานสถานะ ณ 15 ตุลาคม 2569 ภาพหลักฐานเป็นข้อมูลจริงที่บันทึก 14 ตุลาคม ไม่ใช่ค่าปัจจุบัน และไม่ใช่ผลผ่านทุกข้อ`;}
function table(s,rows,{y=285,h=620,widths=[210,670,820],size=31}={}){
 const t=s.tables.add({rows:rows.length,columns:rows[0].length,left:110,top:y,width:1700,height:h,values:rows,columnWidths:widths});
 t.borders.assign({fill:C.line,width:1.5,style:'solid'});
 for(let r=0;r<rows.length;r++)for(let c=0;c<rows[0].length;c++){
  const cell=t.getCell(r,c);cell.fill=r===0?C.pale:C.white;
  cell.text.style={typeface:font,fontSize:size,color:r>0&&c===0?C.green:C.ink,bold:r===0||c===0};
 }
 return t;
}
function node(s,label,x,y,w,h,{main=false,size=31}={}){
 const q=box(s,x,y,w,h,main?C.green:C.white,main?C.green:C.line);q.text=label;
 q.text.style={typeface:font,fontSize:size,bold:main,color:main?C.white:C.ink,alignment:'center',verticalAlignment:'middle'};return q;
}
function edge(s,a,b,from='right',to='left',two=false){return s.shapes.connect(a,b,{kind:'elbow',fromSide:from,toSide:to,line:{fill:C.green,width:3},tail:{type:'arrow'},head:{type:two?'arrow':'none'}});}
async function pic(s,f,x,y,w,h,alt){s.images.add({blob:new Uint8Array(await fs.readFile(f)),contentType:/\.jpe?g$/i.test(f)?'image/jpeg':'image/png',alt,fit:'contain',position:{left:x,top:y,width:w,height:h}});}
function caption(s,v,x,y,w,size=25){text(s,v,x,y,w,70,size,false,C.muted);}
const ev=path.join(root,'output/presentation_evidence/slide_evidence_20261014/images');
let s=slide('Smart Environment Watch');
box(s,112,300,7,430,C.green,C.green);
text(s,'นาฬิกาตรวจสภาพแวดล้อม\nเชื่อมข้อมูลจากข้อมือถึงแดชบอร์ด',155,310,1135,200,60,true);
text(s,'ต้นแบบ 2 จอ · MQTT · ESP-NOW สองทาง\nบันทึกข้อมูลบนแฟลชและ MicroSD',155,535,1300,120,35,false,C.muted);
text(s,'สมาชิก / บทบาท: __________________________________\nสมาชิก / บทบาท: __________________________________',155,740,1330,125,31);
text(s,'WATCH 2.0.9\nHUB 1.0.8',1490,360,300,160,43,true,C.green);
text(s,'รายงานเพื่อการนำเสนอ\n18 ตุลาคม 2569',1490,565,300,115,31,false,C.muted);
note(s,1,'เปิดด้วยแนวคิดดูค่าที่จุดใช้งานจริง เชื่อมสองหน้าจอและเก็บย้อนหลัง สมาชิกและบทบาทเว้นให้ผู้ใช้เติม ไม่อ้างว่าตรวจรับครบทุกข้อ',['output/map_zoom_20261014/manifest.json']);

s=slide('ที่มาและวัตถุประสงค์','กลุ่มเป้าหมาย: ผู้ทำกิจกรรมกลางแจ้งในมหาวิทยาลัยและพื้นที่เกษตร');
box(s,110,300,820,640);box(s,990,300,820,640);
text(s,'ปัญหาที่ต้องการแก้',150,345,740,65,43,true,C.green);
text(s,'สภาพอากาศเปลี่ยนตามจุดใช้งาน\nต้องการดูค่าที่ข้อมือได้ทันที\nข้อมูลจากอุปกรณ์กระจายหลายส่วน\nต้องการเก็บย้อนหลังเพื่ออธิบายผล',150,450,740,280,37);
caption(s,'พื้นที่เป้าหมาย: ม.เกษตรฯ บางเขน\nและพื้นที่เกษตรในจังหวัดอำนาจเจริญ',150,800,740,28);
text(s,'ผลลัพธ์ที่ออกแบบไว้',1030,345,740,65,43,true,C.green);
text(s,'อ่านเซ็นเซอร์และแสดงค่าล่าสุด\nดูข้อมูลร่วมกันบนจอใหญ่และเว็บ\nเก็บ CSV พร้อมเวลาและส่งย้อนหลัง\nแจ้งเตือนเมื่อค่าเกินเกณฑ์',1030,450,740,280,37);
caption(s,'ชีพจร / SpO₂ เป็นข้อมูลเบื้องต้น\nไม่ใช่อุปกรณ์วินิจฉัยทางการแพทย์',1030,800,740,28);
note(s,2,'อธิบายบริบทการใช้ ยังไม่มีผลสำรวจผู้ใช้หรือข้อสรุปทางการแพทย์');

s=slide('ขอบเขตงานตามเอกสารความต้องการ','จัดลำดับตาม MoSCoW เดิม และระบุส่วนที่เพิ่มภายหลัง');
const scope=[['MUST','FR-01 อ่านเซ็นเซอร์\nFR-02 แสดงผล / ทัช\nFR-03 ส่ง MQTT\nFR-04 บันทึก CSV',C.green],['SHOULD','FR-05 เก็บออฟไลน์\nและส่งย้อนหลัง\nFR-06 แจ้งเตือน',C.blue],['COULD','FR-07 ตั้งค่าผ่าน NVS\nFR-08 อัปเดต OTA\nอัตโนมัติ',C.gold],['นอกขอบเขต','การวินิจฉัยโรค\nการรับรองทางแพทย์\nผลิตภัณฑ์เชิงพาณิชย์',C.muted]];
scope.forEach(([head,body,color],i)=>{const x=110+i*435;box(s,x,320,395,565);text(s,head,x+30,355,335,65,42,true,color);box(s,x+30,444,65,4,color,color);text(s,body,x+30,485,335,330,32);});
text(s,'ขอบเขตที่ปรับแล้ว: แฟลชตัวเล็ก + MicroSD จอใหญ่ / ใช้ GY-51 แทน QMI8658 (ไม่มีไจโร)',110,935,1700,58,28,false,C.muted);
note(s,3,'ผู้ใช้ยืนยันว่าผู้สอนยอมรับการปรับอุปกรณ์ ไม่เปลี่ยนหมายเลข FR ให้ผิดจากเอกสาร จอใหญ่มี SD จริงแล้ว');

s=slide('Workflow: จากการเปิดเครื่องถึงการใช้งาน','setup(): GPIO / จอ / NVS / LittleFS / เซ็นเซอร์ / เวลา / เครือข่าย');
const stages=[['SENSE','อ่าน MAX30102 / BME68x\nGY-51 / INA226 / GPS','แยกจังหวะอ่านแต่ละเซ็นเซอร์'],['THINK','กรองค่า / ตรวจความพร้อม\nประเมินเกณฑ์เตือน / เวลา','ข้อมูลไม่พร้อมแสดง -- ไม่แทนด้วย 0'],['ACT','แสดงจอ / ส่ง MQTT\nบันทึก / รับคำสั่งจากจอใหญ่','บริการปุ่ม ทัช และงานเครือข่าย']];
const ns=stages.map(([h,b,c],i)=>{let x=110+i*590;const q=node(s,h,x,330,520,125,{main:i===1,size:42});box(s,x,510,520,330);text(s,b,x+32,550,456,155,35);caption(s,c,x+32,750,456,26);return q;});edge(s,ns[0],ns[1]);edge(s,ns[1],ns[2]);
text(s,'จังหวะหลัก: MQTT 1 วินาที / CSV 5 วินาที / IAQ ประมาณ 3 วินาที',110,900,1700,60,34,true,C.green);
note(s,4,'แยกงานเครือข่ายและทัชเพื่อให้ UI ยังตอบสนอง ออฟไลน์ใช้ journal จำกัดความจุและ replay ไม่อ้างว่าไม่มี blocking เลยทั้งระบบ',['src/main.cpp','include/network_worker.h','large_display/KU_Hub/touch_sampler.h']);

s=slide('สถาปัตยกรรมระบบ','สัญญาณ 3.3V · ตัวเล็กเก็บข้อมูลเอง · จอใหญ่รับคำสั่งและบันทึก MicroSD');
const a=node(s,'เซ็นเซอร์ I²C\nSDA8 / SCL9\nGPS UART RX12 / TX13',110,310,410,205,{size:31});
const b=node(s,'ESP32-S3 SuperMini\nLittleFS / NVS\nปุ่มเดียว GPIO4',690,310,480,205,{main:true,size:33});
const c=node(s,'จอเล็ก GC9A01A / SPI\nSCK10 MOSI11\nCS6 DC7 RST5',1370,310,440,205,{size:31});
edge(s,a,b);edge(s,b,c);
const hub=node(s,'จอใหญ่ 480 × 480\nทัช / RTC / MicroSD',690,610,480,145,{size:32});edge(s,b,hub,'bottom','top',true);
text(s,'ESP-NOW สองทาง',1205,625,575,55,30,true,C.green);
text(s,'MQTT: TLS / QoS 1 / LWT',110,810,1700,55,33,true,C.green);
text(s,'ตัวเล็ก → HiveMQ Cloud → Node-RED → SQLite queue → InfluxDB → Grafana',110,880,1700,60,32);
caption(s,'Topic ปัจจุบัน: ku_watch/live และ /status · JSON: device / sample_id / timestamp / temp / iaq_valid / backfill',110,955,1700,24);
note(s,5,'Wi-Fi เชื่อม cloud MQTT ส่วน ESP-NOW เป็นการเชื่อมใกล้กัน ไม่ส่งข้ามอินเทอร์เน็ตแทน MQTT ข้อมูล device เป็น tag เวลา UTC ค่าเซ็นเซอร์ number และ validity เป็นสถานะ sample_id ช่วยจัดการการส่งซ้ำ 1Hz เท่ากับ 86400 ข้อความต่อวัน PUBACK ยืนยันถึง broker ไม่ใช่ถึง DB Topic ปัจจุบันต่างจากรูปแบบใน FR-03 ต้องระบุไว้',['include/config.h (เฉพาะ pin map ไม่แนบ credentials)','integration/node-red','tools/influx_queue.py']);

s=slide('ฮาร์ดแวร์และการแบ่งงาน','เหตุผลเลือก: แยกจอสวมใส่กับจอแสดงผลร่วม และใช้บัสมาตรฐาน');
table(s,[['อุปกรณ์ / Interface','หน้าที่และเหตุผล','ราคา / ผู้รับผิดชอบ'],['ESP32-S3 + GC9A01A / SPI','ตัวเล็กสวมใส่ / ปุ่มเดียว / Wi-Fi','________________'],['MAX30102 + BME68x + GY-51 / I²C','ชีพจร / อากาศ / การเคลื่อนไหว','________________'],['INA226 / I²C + GPS / UART','แรงดันแบต / ตำแหน่งกลางแจ้ง','________________'],['Touch-LCD-2.1 + RTC + MicroSD','จอใหญ่ / ทัช / CSV พร้อมเวลา','________________'],['LiPo 3.7V 1000mAh + สวิตช์','ใช้แบตนอกสถานที่ / ทดสอบในห้องด้วย USB','________________']],{y:285,h:485,widths:[650,700,350],size:28});
await pic(s,'C:/Users/pomma/Downloads/06_รูปภาพ_วิดีโอ/รูปภาพ/836500246_2011153689545983_660703057889593406_n.jpg',110,800,330,190,'ภาพต้นแบบจริงระหว่างพัฒนา');
text(s,'ต้นแบบจริงระหว่างพัฒนา\nมีการเปลี่ยนเลย์เอาต์และเฟิร์มแวร์ภายหลัง',480,815,700,95,28,false,C.muted);
text(s,'งบเป้าหมาย ≤ 3,000 บาท\nยังรอเติมราคาซื้อจริง',1250,820,560,100,31,true,C.green);
note(s,6,'สมาชิก ราคา และบทบาทเว้นตามผู้ใช้สั่ง ไม่มีชาร์จเจอร์แบตในชุดตามผู้ใช้ INA กระแสยังไม่สอบเทียบ ไม่รับรอง power path หรืออายุแบตจากการทดสอบ USB');

s=slide('ผลการดำเนินงาน: ข้อกำหนดหลัก','FR-01 ถึง FR-04 · แยกผลใช้งานจริงออกจากเกณฑ์ที่ยังรอทดสอบ');
table(s,[['ข้อกำหนด','สิ่งที่ต้องทำ','ผลและขอบเขตหลักฐาน'],['FR-01','อ่านเซ็นเซอร์ / ชีพจร / SpO₂\nอัปเดตต่อเนื่องตามเกณฑ์','อ่านค่าจริงได้; ปลายนิ้วขึ้น BPM / SpO₂\nรอทดสอบทุกค่าครบ 1 นาทีในรุ่นล่าสุด'],['FR-02','แสดงค่า เวลา แบต และสถานะ\nเปลี่ยนหน้าด้วยทัช','✓ ผู้ใช้ยืนยันแสดงครบ สถานะตรง\nจอใหญ่แตะเปลี่ยนหน้าได้ตามปกติ'],['FR-03','MQTT JSON ทุก 1 วินาที\nQoS 1 / LWT / ตรวจรับ 5 นาที','ส่งข้อมูลเข้า backend ได้จริง\nรอตรวจครบ 5 นาที; topic ต่างจากเอกสาร'],['FR-04','MicroSD CSV ทุก 5 วินาที\nเวลา RTC / เปิดใน Excel ได้','✓ ชุดหลักฐาน 1,408 แถว เปิดใน Excel ได้\nช่วงที่ตรวจ 1 ชม. 57 นาที 32 วินาที']],{y:285,h:635,widths:[200,655,845],size:30});
caption(s,'✓ หมายถึงมีหลักฐานตามขอบเขตที่ระบุในช่องผล ไม่ใช่การรับรองผ่านทั้งระบบ',110,949,1700,26);
note(s,7,'FR-02 ยืนยันโดยผู้ใช้ หน้าหลักและ NETWORK แสดงครบ FR-04 อ้างไฟล์ตรวจรับ 1408 แถว 26 คอลัมน์ RTC ต่าง watch ไม่เกิน2s interval4–6s ไม่มีgap>6sในไฟล์นี้ ไฟล์ถัดมา125แถวมีgapจริงจึงไม่รวมผลผ่านแบบเหมารวม',['output/deadline_20261018/sd_acceptance_longer/env_1791956522_e47806b1.csv.audit.json','output/deadline_20261018/sd_acceptance_longer/excel_open.json']);

s=slide('ผลการดำเนินงาน: ข้อกำหนดรอง','FR-05 ถึง FR-08 · มีส่วนที่พัฒนาแล้ว แต่ยังไม่ปิดเกณฑ์ตรวจรับทั้งหมด');
table(s,[['ข้อกำหนด','สิ่งที่ต้องทำ','สถานะปัจจุบัน'],['FR-05','เก็บออฟไลน์ / ส่งย้อนหลังครบ\nตัด Wi-Fi 10 นาทีแล้วต่อกลับ','มี LittleFS journal + replay\nรอทดสอบตัดเน็ต 10 นาทีบนรุ่นล่าสุด'],['FR-06','IAQ > 150 หรือ T > 35°C\n3 รอบ; เตือนภายใน 5 วินาที','มี logic และภาพแจ้งเตือนจริง\nรอวัดเวลาจริง; IAQ อ่านราว 3 วินาที/รอบ'],['FR-07','แก้ Wi-Fi / broker / threshold\nเก็บ NVS และมีผลหลังรีบูต','มีหน้าตั้งค่าและคงค่าหลังอัปเดต\nรอตรวจครบทุกช่องหลังรีบูต'],['FR-08','ตรวจเวอร์ชัน / ดาวน์โหลด OTA\nอัตโนมัติภายใน 24 ชั่วโมง','ติดตั้ง WATCH 2.0.9 / HUB 1.0.8 ผ่าน USB\nยังไม่ผ่านทดสอบ OTA อัตโนมัติ']],{y:285,h:635,widths:[200,655,845],size:30});
caption(s,'การอัปโหลดผ่าน USB ยืนยันเวอร์ชันที่ติดตั้ง ไม่ใช้แทนผลทดสอบ OTA อัตโนมัติ',110,949,1700,26);
note(s,8,'รุ่นเก่ามีผล outage 10 นาที แต่รุ่นล่าสุดยังต้องทำซ้ำ คิวแฟลชมีขนาดจำกัด768records ไม่รับรอง offline ไม่จำกัดเวลา บทสนทนาผู้ใช้ยืนยันการคงแผนที่และตั้งค่าบางรายการ ส่วนเตือน 3 รอบกับ IAQ3s ต้องยืนยัน latency จริง ไม่ใช้ fixture1Hzแทนเซ็นเซอร์จริง');

s=slide('ผลการทดสอบคุณภาพระบบ','NFR-01 ถึง NFR-04 · รายงานค่าที่วัดได้พร้อมข้อจำกัด');
table(s,[['ข้อกำหนด','เกณฑ์ในเอกสาร','หลักฐาน / รายการที่ยังรอ'],['NFR-01','ทำงานต่อเนื่อง 24 ชั่วโมง\nไม่ต้องรีบูตด้วยมือ','รับ MQTT สะสม 22 ชม. 12 นาที\nต่อเนื่องยาวสุด 8 ชม. 10 นาที; ยังไม่ครบ'],['NFR-02','เน็ตหรือ broker ล่ม 10 นาที\nทำงานต่อและต่อกลับอัตโนมัติ','มี backoff และส่งย้อนหลัง\nรอทดสอบควบคุม 10 นาทีบนรุ่นล่าสุด'],['NFR-03','Grafana ≤ 5 วินาที\nทัช ≤ 300 มิลลิวินาที','query เดิมเฉลี่ย 3.091 วินาที / 10 ครั้ง\nยังไม่รวมเวลาวาดเว็บและทัชจริง'],['NFR-04','แบต 1000mAh ใช้งาน 6 ชั่วโมง\nจนเหลือ 20%','ใช้ USB ทดสอบระบบ / แบตใช้กลางแจ้ง\nยังไม่มีผลทดสอบอายุแบต 6 ชั่วโมง']],{y:285,h:635,widths:[230,625,845],size:30});
caption(s,'ตัวเก็บหลักฐานหยุดพักตามคำขอผู้ใช้ · เวลาสะสมไม่ใช่เวลาทำงานต่อเนื่อง และไม่ใช่อายุแบต',110,949,1700,25);
note(s,9,'ตัวเลขสะสมอ่านจาก status.json ที่หยุด14Oct11:16:30Z credited79937713.6927993ms longest29421707.857400004ms ขอบเขตคือ MQTT reception เท่านั้น ไม่สรุปผ่านNFR-01จากตัวเลขนี้ กราฟqueryไม่ใช่ sensor-to-browser-painted latency',['output/accumulated_soak/status.json']);

s=slide('สิ่งที่พัฒนาเพิ่มเติมจากขอบเขตเดิม','ฟังก์ชันเสริมที่ใช้ในการสาธิต ไม่ใช้ทดแทนข้อกำหนดหลัก');
const extra=[['จอใหญ่สองทาง','ทัชสั่งเปลี่ยนหน้าตัวเล็ก\nสื่อสารด้วย ESP-NOW'],['แผนที่และ GPS','GPS FIX / ตำแหน่งจริง\nเลือกซูมได้ถึงระดับ 25 เมตร'],['WALK / Activity','เริ่ม–หยุดด้วยปุ่มเดียว\nบันทึกกิจกรรมและส่งออก TCX'],['แฟลช + MicroSD','journal / activity บนตัวเล็ก\nCSV พร้อม RTC บนจอใหญ่'],['เวลาเมื่อเปิดเครื่อง','รับเวลาจาก GPS / NTP / Hub\nเมื่อมีแหล่งเวลาที่พร้อมใช้งาน'],['KU BOT','ตัวละครคู่กับนาฬิกา\nแสดงท่าทางและกิจกรรม']];
extra.forEach(([h,b],i)=>{const x=110+(i%3)*590,y=300+Math.floor(i/3)*335;box(s,x,y,520,285);text(s,h,x+32,y+30,456,65,37,true,i%3===0?C.green:i%3===1?C.blue:C.gold);text(s,b,x+32,y+120,456,130,32);});
note(s,10,'MAP เป็นแผนที่บนอุปกรณ์ ไม่ใช่กราฟ Grafana WALK .kua อยู่ LittleFS และต้องหยุดให้ SAVED ก่อนดึงออกแปลง TCX Hub SD บันทึกเฉพาะรับค่าล่าสุดได้ ไม่มี flash replay ฝั่ง hub เพื่อเติม CSV gap ทุกช่วง',['output/map_zoom_20261014/manifest.json','tools/activity_export.py']);

s=slide('คลิปสาธิตและทดสอบ','แทนที่กรอบด้วยคลิปจริงของคุณ · กดเล่นระหว่างนำเสนอได้');
const clips=[['01  การใช้งานสองจอ','เปลี่ยนหน้า / ทัช / เวลาและสถานะ','ผู้ใช้แจ้งว่าถ่ายแล้ว'],['02  เซ็นเซอร์และ GPS','ค่าจริง / GPS FIX / ซูมแผนที่','ผู้ใช้แจ้งว่าถ่ายแล้ว'],['03  บันทึกข้อมูล CSV','บันทึก MicroSD → เปิด Excel','มีไฟล์จริงพร้อมใช้ประกอบคลิป'],['04  ออฟไลน์แล้วต่อกลับ','ตัดเน็ต 10 นาที → ส่งย้อนหลัง','รอทดสอบรุ่นล่าสุดและถ่ายคลิป']];
clips.forEach(([h,b,status],i)=>{const x=110+(i%2)*875,y=290+Math.floor(i/2)*350;box(s,x,y,825,300,C.pale,C.green,'VIDEO_INSERT_HERE_'+(i+1));text(s,h,x+30,y+24,765,48,34,true,C.green);text(s,'วางคลิปที่นี่',x+30,y+103,765,65,42,true);text(s,b,x+30,y+181,765,50,29);text(s,status,x+30,y+242,765,40,25,false,C.muted);});
note(s,11,'กรอบทั้ง4เป็น placeholder ที่แก้ไขได้ ไม่มีการสร้างคลิปหรือผลผ่านขึ้นเอง ผู้ใช้เพิ่มคลิปด้วย Canva Uploads แล้วลากเข้าหน้า11 จัดในกรอบเดิม อธิบาย 45วินาทีและเลือกเปิดคลิปสั้น ไม่เล่นเต็มทุกคลิปในเวลา7นาที Clip03ไฟล์CSVใหม่125แถวมีgapจริง ต่างจากไฟล์ตรวจรับ1408แถว ต้องบอกตามไฟล์ที่เปิด',['output/clip03_csv_25691014T111238Z','output/deadline_20261018/ทำต่อพรุ่งนี้_15ตุลาคม2569.md']);

s=slide('สรุปผลและหลักฐานที่เก็บแล้ว','ภาพจากเครื่องมือจริง วันที่ 14 ตุลาคม 2569 · ไม่ใช่ข้อมูลจำลอง');
await pic(s,path.join(ev,'01_temperature.png'),110,285,600,650,'ภาพ Grafana จริงที่บันทึก14ตุลาคม2569');
caption(s,'Grafana: อุณหภูมิย้อนหลังจากข้อมูลจริง\nยังไม่ได้สอบเทียบกับเทอร์โมมิเตอร์',110,941,600,25);
await pic(s,path.join(ev,'01_influx_count.png'),780,285,1030,255,'ผล query InfluxDB จริง896แถวและ896sample_idในช่วง15นาทีที่ตรวจ');
text(s,'896 แถว / 896 sample_id',780,565,1030,60,42,true,C.green);
caption(s,'InfluxDB: ช่วง 15 นาทีที่ตรวจเมื่อ 14 ตุลาคม\nตรวจจำนวนแถวและข้อมูลซ้ำจากฐานข้อมูลจริง',780,640,1030,29);
text(s,'1,408 แถว CSV',780,760,1030,65,46,true,C.green);
text(s,'เวลาในไฟล์ 1 ชม. 57 นาที 32 วินาที\nเปิดด้วย Excel และตรวจโครงสร้าง 26 คอลัมน์',780,840,1030,105,31);
note(s,12,'ภาพGrafanaและInfluxจากmanifest14Oct ไม่แก้ตัวเลขในภาพ ผล896records/896uniqueช่วง15นาทีมีไว้ยืนยันชุดข้อมูลที่ตรวจ ไม่อนุมานทุกช่วงไม่มีข้อมูลขาด ภาพอุณหภูมิมีความร้อนบอร์ดไม่ใช่อุณหภูมิอ้างอิงที่สอบเทียบ SD1408fileมีSHAและExcelเปิดread-only hashไม่เปลี่ยน',['output/presentation_evidence/slide_evidence_20261014/manifest.json','output/deadline_20261018/sd_acceptance_longer/env_1791956522_e47806b1.csv.audit.json','output/deadline_20261018/sd_acceptance_longer/excel_open.json']);

s=slide('บทเรียนและรายการก่อนตรวจรับครบ','สาธิตเส้นทางข้อมูลจริงได้แล้ว พร้อมระบุข้อจำกัดให้ตรวจซ้ำได้');
box(s,110,300,820,660);box(s,990,300,820,660);
text(s,'บทเรียนจากการพัฒนา',150,340,740,60,42,true,C.green);
text(s,'แยกงานทัช / เครือข่ายลดอาการหน่วง\nกู้จอหลังการกดปุ่มจากซอฟต์แวร์\nข้อมูลต้องมีเวลาและ sample_id\nเก็บไฟล์ดิบและภาพพร้อมเวลาเสมอ',150,450,740,285,33);
caption(s,'รอบสาธิต: ใช้ USB / เตรียมคลิปสำรอง\nค่าชีพจรข้อมือขึ้นกับการแนบเซ็นเซอร์',150,820,740,27);
text(s,'รายการที่ยังไม่ปิด',1030,340,740,60,42,true,C.gold);
text(s,'NFR-05 ตรวจ credentials ใน repo ที่ส่ง\nNFR-06 เทียบอุณหภูมิ 10 จุด ±3°C\nNFR-07 เติม BOM จริง เทียบงบ 3,000\nNFR-08 OTA ตัดไฟ / rollback 3 ครั้ง',1030,450,740,285,32);
caption(s,'รวมถึงทดสอบ 24 ชั่วโมงต่อเนื่อง\nออฟไลน์ 10 นาที / latency / แบต 6 ชั่วโมง',1030,820,740,27);
note(s,13,'ไม่กล่าวว่าครบrequirementsแล้ว การตรวจZIPsourceไม่แทนตรวจrepoทุกประวัติ INA กระแสยังไม่สอบเทียบ ไม่มีเทอร์โมมิเตอร์สำหรับ10จุด Garminเทียบได้เป็นconsumercomparisonแต่ไม่แทนเครื่องมาตรฐานอุณหภูมิ โค้ดแยกโมดูลและgateOTA30%มีแล้ว แต่ตัดไฟ3ครั้งยังไม่มีหลักฐาน');

s=slide('ขอบคุณครับ');
text(s,'Smart Environment Watch',320,355,1280,100,66,true,C.green);
text(s,'ข้อมูลจากอุปกรณ์จริง → บันทึกตรวจสอบได้ → แสดงผลร่วมกัน',320,500,1280,85,38);
text(s,'คำถามและข้อเสนอแนะ',320,650,1280,85,46,true);
text(s,'สมาชิก / บทบาท: __________________________________\nสมาชิก / บทบาท: __________________________________',320,820,1280,105,29,false,C.muted);
note(s,14,'จบและเปิดคำถาม เตรียมตอบเรื่องpin/bus QoS1 LWT offlineการส่งซ้ำ ขอบเขตSD และผลที่ยังไม่ผ่าน เปิดแหล่งหลักฐานได้จากไฟล์ในproject ไม่ใส่รหัสผ่านหรือพิกัดดิบลงสไลด์');

const candidate=path.join(build,'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
console.log('Exported candidate');
const final=path.join(out,'KU_Watch_พร้อมนำเสนอ_15ตุลาคม2569_v2.pptx');
await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:final,pythonExecutable:path.join(runtime,'python/python.exe'),integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','18288000,10287000','--validate-heading-fit',...[6,7,8,9].flatMap(n=>['--require-native-table-slide',String(n)])],fontPolicy:{basis:'design',families:[font]},explicitTotalSlideCount:14,requiredNativeTableOwnerSlides:[6,7,8,9],verifyArtifactToolImport:true,receiptPath:path.join(build,'validation.json')});
console.log('Finalized',final);
for(let i=0;i<p.slides.items.length;i++){
 const png=await p.export({slide:p.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(build,'slide-'+String(i+1).padStart(2,'0')+'.png'),new Uint8Array(await png.arrayBuffer()));
 console.log('Rendered',i+1);
}
await fs.writeFile(path.join(out,'วิธีเติมคลิปในCanva.txt'),'หน้า 11 มีช่องคลิป 4 ช่องที่แก้ไขได้\n1 สองจอ / ทัช / เวลา\n2 เซ็นเซอร์ / GPS FIX / ซูมแผนที่\n3 MicroSD CSV → Excel\n4 ออฟไลน์ 10 นาที → ส่งย้อนหลัง (รอทดสอบรุ่นล่าสุด)\n\nCanva: อัปโหลดคลิปจริงของคุณ แล้วลากลงหน้า 11 ปรับขนาดให้ตรงกรอบ ลบข้อความ วางคลิปที่นี่ ตั้งให้เล่นเมื่อคลิก และทดลอง Present ก่อนวันพรีเซ็นต์\nชื่อสมาชิก บทบาท และราคายังเว้นไว้ให้เติม\nตัวเลขผลทดสอบเป็นหลักฐานที่มีอยู่ ไม่ใช่การรับรองว่าทุกข้อผ่าน\n','utf8');
console.log('DONE');
