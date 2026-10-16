const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const D = require('C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/docx');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'output/progress_update_20261010');
fs.mkdirSync(out, { recursive: true });
const read = p => JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const latest = read('output/presentation_evidence/latest.json');
const snapshotDir = `output/presentation_evidence/${latest.folder}`;
const soak = read(`${snapshotDir}/soak_status.json`);
const snapshotAt = latest.captured_bangkok.replace('2026','2569');
const duration = `${Math.floor(soak.observed_hours)} ชั่วโมง ${Math.floor(soak.observed_hours * 60) % 60} นาที`;
const fmt = x => Number(x).toLocaleString('en-US');
const proofFiles = [
 `${snapshotDir}/soak_status.json`, `${snapshotDir}/01_soak.png`,
 'output/presentation_evidence/20261010212911_running/02_query_latency.png',
 'output/requirements_audit_20261009/live_phone_20261010.json',
 'output/requirements_audit_20261009/phone_drain_database_20261010.json',
 'output/requirements_audit_20261009/grafana_latency_phone_20261010.json',
 'output/requirements_audit_20261009/broker_outage.json',
 'output/requirements_audit_20261009/network_phone_final_20261010.json',
];
const sources = proofFiles.map(p => {const b=fs.readFileSync(path.join(root,p)); return {path:p,sha256:crypto.createHash('sha256').update(b).digest('hex'),bytes:b.length};});
fs.writeFileSync(path.join(out,'sources.json'), JSON.stringify({created_utc:new Date().toISOString(),baseline:'KU Watch ความคืบหน้า 23 ก.ย. 2569 (3).pdf',snapshot_at:snapshotAt,soak,sources},null,2));
fs.copyFileSync(path.join(root,snapshotDir,'soak_status.json'),path.join(out,'soak_status_at_report.json'));
const font='Leelawadee UI';
const run = (text,opt={}) => new D.TextRun({text,font,size:23,color:'000000',...opt});
const p = (text,opt={}) => new D.Paragraph({children:[run(text)],spacing:{after:110,line:276},...opt});
const h = text => new D.Paragraph({text,heading:D.HeadingLevel.HEADING_1,spacing:{before:100,after:150}});
const sub = text => new D.Paragraph({text,heading:D.HeadingLevel.HEADING_2,spacing:{before:130,after:80}});
const bullet = text => p(text,{numbering:{reference:'bullets',level:0},spacing:{after:100,line:276}});
const small = text => new D.Paragraph({children:[run(text,{size:19,color:'424242'})],spacing:{after:100,line:245}});
const breakPage = () => new D.Paragraph({children:[new D.PageBreak()],spacing:{before:0,after:0}});
const table = (headers,rows,widths) => {
 const make=(vals,isHead,index)=> new D.TableRow({tableHeader:isHead,cantSplit:true,children:vals.map((v,i)=>new D.TableCell({
  width:{size:widths[i],type:D.WidthType.DXA},verticalAlign:D.VerticalAlign.CENTER,
  margins:{top:90,bottom:90,left:110,right:110},shading:{type:D.ShadingType.CLEAR,fill:isHead?'243E57':index%2?'F1F5F8':'FFFFFF'},
  children:[new D.Paragraph({children:[run(v,{size:21,color:isHead?'FFFFFF':'000000',bold:isHead})],spacing:{after:0,line:255}})]
 }))});
 const border={style:D.BorderStyle.SINGLE,size:4,color:'D9D9D9'};
 return new D.Table({width:{size:widths.reduce((a,b)=>a+b,0),type:D.WidthType.DXA},columnWidths:widths,
  borders:{top:border,bottom:border,left:border,right:border,insideHorizontal:border,insideVertical:border},
  rows:[make(headers,true,0),...rows.map((r,i)=>make(r,false,i))]});
};
const img=(relative,caption)=>[
 new D.Paragraph({children:[new D.ImageRun({type:'png',data:fs.readFileSync(path.join(root,relative)),transformation:{width:624,height:351},altText:{title:caption,description:caption,name:'ภาพหลักฐาน'}})],alignment:D.AlignmentType.CENTER,spacing:{after:70}}),
 small(caption)
];
const children=[];
children.push(new D.Paragraph({text:'รายงานความคืบหน้าโครงงาน KU Watch',heading:D.HeadingLevel.TITLE,spacing:{after:170}}),
 p('อัปเดต 10 ตุลาคม 2569 ต่อจากรายงานวันที่ 23 กันยายน 2569',{children:[run('อัปเดต 10 ตุลาคม 2569 ต่อจากรายงานวันที่ 23 กันยายน 2569',{bold:true})]}),
 small(`ตัวเล็ก 2.0.8  |  จอใหญ่ HUB 1.0.5  |  สถานะรอบยาว ณ ${snapshotAt} เวลาไทย`),
 p('หลังรายงานเดิม เราพัฒนาจอใหญ่ให้รับข้อมูลและส่งคำสั่งกลับสู่นาฬิกาผ่าน ESP-NOW สองทาง เพิ่มแผนที่และ KU BOT ใช้งานด้วยแบตเตอรี่ได้ และเพิ่มการเก็บข้อมูลช่วงเครือข่ายขัดข้องเพื่อส่งย้อนหลัง ระบบหลักทำงานร่วมกันแล้ว แต่ยังมีข้อกำหนดที่ต้องทดสอบกับฮาร์ดแวร์และเวลาใช้งานจริงก่อนตรวจรับครบทั้งหมด'),
 h('01 ภาพรวมผลงานที่เพิ่มจากวันที่ 23 กันยายน'),
 table(['หัวข้อ','สถานะในรายงานเดิม','ความคืบหน้ารอบนี้'],[
  ['เฟิร์มแวร์และเมนู','รุ่น 1.4.0 และ 8 หน้า','ตัวเล็ก 2.0.8 และเมนู 11 หน้า'],
  ['จอใหญ่ ESP-NOW','กำหนดแนวทาง ยังไม่พัฒนา','HUB 1.0.5 รับข้อมูลและสั่งงานกลับได้'],
  ['GPS และแผนที่','รับข้อมูล แต่ยังไม่มี fix','ผู้ใช้ยืนยัน GPS FIX และจุดสีน้ำเงินบนแผนที่'],
  ['แบตเตอรี่และ INA226','ยังไม่ต่อวงจรไฟและยังไม่วัด','ใช้แบตได้ อ่านแรงดันได้ กระแสยังไม่สอบเทียบ'],
  ['MAX30102','อ่าน BPM และ IR / RED','ปลายนิ้วขึ้น BPM และ SpO2 ตามคำยืนยันผู้ใช้'],
  ['ข้อมูลช่วงเน็ตหลุด','ข้อมูลสดไม่ส่งย้อนหลัง','เพิ่มคิวในแฟลช การส่งย้อนหลัง และสปูล SQLite'],
  ['เวลาเมื่อเปิดใหม่','ยังไม่มีผลตรวจในฉบับเดิม','รับเวลาจาก GPS NTP และ RTC จอใหญ่ได้'],
  ['เอกสารและหลักฐาน','รายงานและแบบประกอบเดิม','เพิ่มตารางตรวจรับ สไลด์ 14 หน้า และภาพผลพร้อมเวลา'],
 ],[1850,2850,5050]),
 small('คำว่า “ทำแล้ว” ในรายงานนี้หมายถึงมีฟังก์ชันหรือหลักฐานในขอบเขตที่ระบุ ส่วน “ยังไม่ตรวจรับ” หมายถึงยังไม่มีผลทดสอบครบตามเกณฑ์ ไม่ใช้ผลจำลองแทนการทดสอบเครื่องจริง'));

children.push(breakPage(),h('02 อุปกรณ์ที่เพิ่มและปรับเปลี่ยน'),
 p('บอร์ดหลักยังเป็น ESP32-S3 Super Mini และจอกลม GC9A01A เพิ่มจอใหญ่ ESP32-S3-Touch-LCD-2.1 ซึ่งทำหน้าที่เป็นจอแสดงข้อมูลและแผงควบคุมร่วมกับนาฬิกา'),
 table(['อุปกรณ์','สถานะล่าสุด','ข้อที่ต้องตรวจต่อ'],[
  ['ESP32-S3 และ GC9A01A','เมนูและปุ่มเดียวใช้งานได้','ทดสอบความต่อเนื่องระยะยาว'],
  ['จอใหญ่ Touch LCD 2.1','ภาพและทัชทำงาน ส่งคำสั่งกลับได้','จับเวลาทัชถึงภาพจริง ≤300 ms'],
  ['ATGM336H','ผู้ใช้เคยยืนยัน GPS FIX กลางแจ้ง','เดินบันทึกเส้นทางและตรวจไฟล์จริง'],
  ['MAX30102','ปลายนิ้วอ่าน BPM และ SpO2 ได้','ตำแหน่งข้อมือและค่าอ้างอิงยังไม่ตรวจรับ'],
  ['BME68x และ BSEC2','อ่านสภาพแวดล้อมและ IAQ พร้อมสถานะ','เทียบอุณหภูมิและทดสอบเกณฑ์เตือน'],
  ['การเคลื่อนไหวและแม่เหล็ก','ส่งค่าขึ้นระบบได้ รอบล่าสุดพร้อมอ่าน','สอบเทียบและตรวจทิศทางภาคสนาม'],
  ['INA226','อ่านแรงดันและแสดงแบตโดยประมาณ','ระบุค่า shunt และสอบเทียบกระแส'],
  ['LiPo 3.7 V 1000 mAh','ผู้ใช้ระบุแบตรุ่นนี้และใช้งานบนแบตแล้ว','ระยะเวลา 6 ชั่วโมง วงจรชาร์จและไฟย้อน'],
 ],[2350,3500,3900]),
 small('รายงานเดิมระบุแบต 582535 ขนาด 600 mAh ส่วนแบตที่ผู้ใช้ระบุภายหลังเป็น 1000 mAh จึงต้องแก้ BOM และตรวจขนาดติดตั้งจริงตามอุปกรณ์ที่ใช้ ไม่ใช้ข้อมูลเดิมเป็นแบบผลิต'),
 h('03 เฟิร์มแวร์และการควบคุมหน้าจอ'),
 bullet('แก้จอกลมดำขณะเปลี่ยนหน้าโดยเพิ่มการกู้การแสดงผล ผู้ใช้ยืนยันว่าภาพกลับมาเองและเปลี่ยนหน้าได้'),
 bullet('ปรับทัชจอใหญ่ให้รับการแตะแล้วปล่อยได้สม่ำเสมอ ผู้ใช้ยืนยันว่าแตะเปลี่ยนหน้าได้ทุกครั้งในการทดสอบที่แจ้ง'),
 bullet('คงการควบคุมตัวเล็กด้วยปุ่มเดียว กดสั้นเปลี่ยนหน้า และใช้การกดค้างตามคำสั่งของหน้าปัจจุบัน จอใหญ่มี PREV HOME NEXT'),
 small('ตรวจคำสั่งและสถานะเมนูจริงครบ 11 หน้าได้ตรงกันระหว่างสองบอร์ด ผลนี้ยืนยันการทำงาน แต่ยังไม่ใช่ผลจับเวลาทัชตาม NFR-03'));

children.push(breakPage(),h('03 แผนที่ กิจกรรม เวลา และ KU BOT'),
 sub('แผนที่และตำแหน่ง GPS'),
 p('เพิ่มหน้าแผนที่บริเวณมหาวิทยาลัยเกษตรศาสตร์ บางเขน และมิตรอินทรีย์เพื่อการเกษตรอัจฉริยะ จังหวัดอำนาจเจริญ แสดงตำแหน่งจาก GPS และบันทึกพื้นที่ที่เลือกไว้ ผู้ใช้เคยพบว่าหลังถอด USB กลับไปบางเขน จึงแก้การจำค่าตั้งและผู้ใช้ยืนยันว่าใช้งานได้แล้ว'),
 p('ผู้ใช้ยืนยันว่าเมื่อออกกลางแจ้งมี GPS FIX และจุดสีน้ำเงินขึ้นบนแผนที่ การยืนยันนี้ยังไม่ครอบคลุมความคลาดเคลื่อนของตำแหน่ง ความต่อเนื่องขณะเดิน หรือความถูกต้องของระยะทาง'),
 sub('กิจกรรม WALK และการส่งออก'),
 p('มีคำสั่งเริ่มและหยุดบันทึกกิจกรรม พร้อมไฟล์ KUA JSON และ TCX ใช้แฟลชภายในแทน SD ตรวจไฟล์กิจกรรมเดิมและค่าตั้งหลังอัปเดตด้วย SHA256 แล้วยังอยู่ครบ จอใหญ่ส่งคำสั่งเกี่ยวกับกิจกรรมกลับไปยังนาฬิกาได้'),
 p('การเดินทดสอบรอบใหม่ถูกข้ามตามคำขอผู้ใช้ จึงยังต้องเดินจริง หยุดบันทึก เปิดเครื่องใหม่ ส่งออกไฟล์ และเทียบเส้นทางก่อนปิดการตรวจรับ การนำ TCX เข้า Strava ยังเป็นการนำเข้าโดยผู้ใช้'),
 sub('การรักษาเวลาเมื่อเปิดเครื่องใหม่'),
 p('เพิ่มแหล่งเวลาจาก GPS และ NTP รวมทั้งรับเวลาจาก RTC จอใหญ่ผ่าน ESP-NOW ที่จับคู่แล้ว ผู้ใช้ทดสอบปิดตัวเล็กประมาณ 15 วินาทีโดยเปิดจอใหญ่ไว้ และยืนยันว่าเปิดกลับมาเวลาตรง'),
 p('เมื่อดับทั้งสองบอร์ด ต้องมีแหล่งเวลาที่กลับมาใช้งานได้หรือแบตสำรอง RTC ที่ถูกต้อง ยังไม่ได้ยืนยันแบตช่อง RTC ของจอใหญ่ การเปิดทั้งระบบโดยไม่มีอินเทอร์เน็ต GPS หรือ RTC ที่เดินต่อได้ยังเป็นข้อทดสอบค้าง'),
 sub('ตัวละคร KU BOT และการแจ้งเตือน'),
 p('เพิ่มหุ่นยนต์ร่วมกับหน้าจอเมนู ปรับตำแหน่งเพื่อไม่บังค่าด้านล่าง เพิ่มท่าทางและระบบกิจกรรมสำหรับดูแลตัวละครตามที่ผู้ใช้ขอ มีส่วนสั่งงานและตั้งค่าที่เกี่ยวข้องจากจอใหญ่ ยังไม่มีผลประเมินการเติบโตของตัวละครจากการใช้งานต่อเนื่องระยะยาว'),
 p('เพิ่มสถานะ WAITING เมื่อข้อมูลไม่พร้อม แสดงเวอร์ชันจริง และเตือนแบตเตอรี่ที่ค่าประมาณ ≤20% โดยยกเลิกเมื่อ ≥22% ค่า SpO2 และแบตเตอรี่เป็นค่าประมาณ ส่วนกระแสไม่แสดงว่าพร้อมเมื่อยังไม่ได้สอบเทียบ'),
 small('การอ่าน IAQ ใช้ BSEC2 รอบ LP ประมาณ 3 วินาที IAQ เป็นดัชนีที่อัลกอริทึมคำนวณ ไม่ใช่ผลตรวจความเข้มข้นของก๊าซแต่ละชนิดหรือการรับรอง AQI ภายนอก'));

children.push(breakPage(),h('04 การรับส่งและเก็บข้อมูล'),
 p('เส้นทางข้อมูลหลักเป็น นาฬิกา → MQTT ผ่าน TLS → HiveMQ Cloud → Node-RED → SQLite spool → InfluxDB 3 → Grafana ส่วน ESP-NOW สองทางเชื่อมตัวเล็กกับจอใหญ่เพื่อส่งสถานะและคำสั่ง'),
 p('เพิ่ม sample_id เพื่อแยกข้อมูลแต่ละการวัดและป้องกันแถวซ้ำเมื่อส่งย้อนหลัง นาฬิกาเก็บคิวในแฟลชและลบเมื่อได้รับ PUBACK จาก broker ฝั่ง Node-RED เก็บลงสปูล SQLite ก่อนเขียน InfluxDB การได้รับ PUBACK ยังไม่ใช่การยืนยันว่าฐานข้อมูลเขียนสำเร็จ'),
 table(['การตรวจ','ผลที่มีหลักฐาน','ขอบเขต'],[
  ['พอร์ต MQTT ใช้ไม่ได้ 10 นาที','รุ่น 2.0.5 คืนการเชื่อมต่อแล้ว DB ครบ 600 captures ในช่วงขาด','Wi-Fi ยังอยู่ ทดสอบพอร์ตแยกจาก Wi-Fi'],
  ['รับสดผ่านฮอตสปอตมือถือ','173 รหัสใน 167.822 s ไม่พบลำดับขาด','ระยะสั้น ไม่แทนผลครบ 24 ชั่วโมง'],
  ['ฐานข้อมูลหลังส่งย้อนหลัง','657 รหัสที่รับ ตรวจพบอย่างละ 1 แถว','ยืนยันเฉพาะชุดรหัสที่รับและนำมาตรวจ'],
  ['ข้อมูลเข้าคิวไม่ได้','26 รายการระหว่างสลับเครือข่ายใน boot 2.0.8','คิวจำกัดด้วยพื้นที่ ไม่รับรองว่าข้อมูลไม่สูญหายทุกกรณี'],
  ['รอบต่อเนื่องที่กำลังรัน',`${duration} รับสด ${fmt(soak.samples)} รายการ gap ${soak.gaps} หลุด ${soak.disconnects}`,`${snapshotAt} สถานะ ${soak.status} ยังไม่ผ่าน 24 ชั่วโมง`],
 ],[2450,3850,3450]),
 small('ช่วงรับที่ห่างที่สุดใน snapshot รอบยาวประมาณ '+(soak.max_receive_gap_ms/1000).toFixed(3)+' วินาที มีความแปรปรวนของการรับข้อมูล แม้ยังไม่พบลำดับขาด ผลรอบ Windows ที่เคยไม่ผ่านและ dropped 64 จาก boot รุ่นก่อนยังเก็บไว้เป็นประวัติ'),
 h('05 แดชบอร์ดและความหน่วง'),
 p('ปรับ Live ให้รีเฟรช 1 วินาที และ Friends View 10 วินาที เพิ่มสถานะเครือข่าย คิว เวลา เวอร์ชัน และความพร้อมของเซ็นเซอร์ แก้เส้นทาง Node-RED หลังย้ายโฟลเดอร์ และจัดวิธีเปิดบริการใหม่หลังเปิดคอม'),
 p('ตรวจ 10 รหัสจริงโดยจับคู่ sample_id และเวลา UTC ในแถวเดียวกัน พบเวลาจากการวัดถึงคำตอบ query ของ Grafana เฉลี่ย 3.091 วินาที สูงสุด 3.275 วินาที หลังชดเชยความคลาดเคลื่อนนาฬิกา ขอบเขตนี้ผ่านเกณฑ์ 5 วินาทีสำหรับ query แต่ยังไม่วัดการรีเฟรชและวาดภาพในเบราว์เซอร์จริง'),
 small('แดชบอร์ดในฉบับเดิมมี 41 ช่องและ 13 กราฟ รายงานนี้ไม่ใช้จำนวนเดิมยืนยันจำนวน panel ปัจจุบัน และไม่ใช้การตั้ง refresh 1s เป็นหลักฐานว่าภาพทุกค่าขึ้นจอภายใน 1s'));

children.push(breakPage(),h('06 แบบวงจรและการเชื่อมต่อ'),
 p('ใช้แบบเชื่อมต่อโมดูลเป็นข้อมูลอ้างอิง การต่อเซ็นเซอร์ใช้ I2C SDA GPIO8 และ SCL GPIO9 GPS ใช้ UART RX12 TX13 ปุ่มเมนูตัวเล็กอยู่ GPIO4 จอกลมใช้ SCK10 MOSI11 CS6 DC7 RST5'),
 p('อุปกรณ์ที่เพิ่มและเปลี่ยนจริงต้องปรับในแบบ ได้แก่ INA226 แบตเตอรี่ สวิตช์ วงจรชาร์จและจ่ายไฟ และจอใหญ่ แบบวงจรฉบับเดิมยังไม่ใช่ PCB พร้อมผลิต ยังไม่มีผลรับรองการจ่ายไฟพร้อม USB และแบตหรือการป้องกันไฟย้อนครบทั้งหมด'),
 h('07 ตัวเรือนและแบบประกอบ'),
 p('มี Assembly Drawing PDF และไฟล์ SOLIDWORKS จากงานเดิม แต่แบบเก่าระบุบอร์ด ESP32-C3 และมีข้อมูลแบตไม่ตรงกันระหว่างแบบกับรายงาน ต้องตรวจอุปกรณ์จริงและปรับตำแหน่ง ESP32-S3 GPS INA226 และช่องเซ็นเซอร์ที่แนบผิวก่อนผลิตหรือประกอบถาวร'),
 p('รอบนี้ยังไม่มีหลักฐานว่าปรับ CAD ครบและทดสอบความพอดีทุกชิ้นแล้ว จึงคงสถานะงานประกอบและวงจรไฟว่า “รอตรวจและปรับแบบตามของจริง” ไม่เปลี่ยนสถานะจากการมีภาพตัวเรือนเพียงอย่างเดียว'),
 h('08 การแชร์ข้อมูลและชุดส่งมอบ'),
 p('Friends View เป็นหน้าอ่านข้อมูลสำหรับผู้ชม รายงานวันที่ 23 ก.ย. เคยยืนยันลิงก์ HTTPS ภายนอกแล้ว แต่ลิงก์ชั่วคราวเดิมไม่ใช่หลักฐานว่าปัจจุบันยังเปิดได้ การดู Grafana ในเครื่องต้องเปิดบริการบนคอม และการแชร์ภายนอกต้องตรวจช่องทางที่ใช้งานอยู่แยกต่างหาก'),
 p('จัดชุดโค้ดตัวเล็ก 2.0.8 และ HUB 1.0.5 คู่มือเริ่มระบบ ตารางความต้องการ รายการตรวจรับ BOM ที่เว้นราคาจริง และสไลด์ตามเกณฑ์ประเมิน 14 หน้า ตรวจแพ็กเกจส่งงานว่าไม่มีไฟล์ private หรือรหัสผ่านที่รู้จัก'),
 p('เพิ่มตัวเก็บภาพสรุปผลจาก JSON ทุก 5 นาที โดยแต่ละชุดมีเวลาไทย UTC ไฟล์ต้นทางและ SHA256 หน้ารวมหลักฐานเปิดภาพเต็มและวิดีโอที่เติมภายหลังได้ ภาพเหล่านี้เป็นรายงานผลจากข้อมูลที่เก็บ ไม่ใช่ภาพถ่ายฮาร์ดแวร์หรือภาพหน้า Grafana จริง'),
 sub('ภาพและวิดีโอทดสอบจริงที่เติมภายหลัง'),
 p('ชื่อไฟล์หรือคลิป ____________________  วันและเวลาที่ถ่าย ____________________'),
 p('รุ่นเฟิร์มแวร์และเงื่อนไขทดสอบ __________________________________________'),
 p('ผลที่สังเกตได้และข้อจำกัด ______________________________________________'),
 small('เว้นชื่อสมาชิก บทบาท ราคาซื้อ และสื่อจริงไว้ตามคำขอผู้ใช้ ไม่ใช้เวลาของไฟล์เป็นเวลาที่ถ่าย และไม่เติมผลทดสอบที่ยังไม่ได้ทำ'));

children.push(breakPage(),h('ภาพหลักฐานพร้อมเวลา'),
 small('สองภาพนี้สร้างจากผลตรวจที่บันทึกจริงใน JSON ตัวเลขเป็น snapshot ตามเวลาในภาพ ไม่เปลี่ยนตามรอบตรวจที่ยังรันอยู่'),
 ...img(`${snapshotDir}/01_soak.png`, `ภาพที่ 1 สรุปรอบต่อเนื่อง ณ ${snapshotAt} รับสด ${fmt(soak.samples)} รายการ ตรวจไป ${duration} สถานะ ${soak.status} ยังไม่ผ่านครบ 24 ชั่วโมง และไม่ใช่การทดสอบแบต 6 ชั่วโมง`),
 ...img('output/presentation_evidence/20261010212911_running/02_query_latency.png','ภาพที่ 2 สรุปความหน่วง query จาก 10 รหัสจริง ภาพบันทึกวันที่ 10 ต.ค. 2569 เวลา 21:29:11 เฉลี่ย 3.091 s สูงสุด 3.275 s ไม่รวม browser refresh และ paint'),
 small('ไฟล์ต้นทางและ hash ของภาพทั้งสองระบุใน sources.json ที่เก็บร่วมกับรายงาน สามารถตรวจสอบย้อนกลับได้โดยไม่ใช้ภาพสรุปแทนผลตรวจฉบับเต็ม'));

children.push(breakPage(),h('09 สถานะรวมและงานลำดับถัดไป'),
 p('ระบบหลักทำงานและจัดชุดส่งมอบแล้ว แต่ยังไม่ผ่านข้อกำหนดทุกข้อ งานที่ข้ามการทดสอบก่อนหน้านี้ยังเป็นงานค้าง ตารางนี้ระบุเงื่อนไขปิดงานต่อจากฉบับวันที่ 23 กันยายน'),
 table(['งานตรวจรับ','สถานะล่าสุด','สิ่งที่ต้องทำต่อ'],[
  ['NFR-01 ต่อเนื่อง 24 ชั่วโมง',`กำลังตรวจ ณ ${snapshotAt}`,'รอครบเวลาจริง และ continuity_pass เป็น true'],
  ['NFR-04 แบต 6 ชั่วโมง','ใช้งานบนแบตได้ ยังไม่จับเวลาจนถึง 20%','ทดสอบจากแบตเต็ม แยกจากรอบ USB'],
  ['INA226 และ NFR-06 ความแม่นยำ','แรงดันอ่านได้ กระแสยังไม่สอบเทียบ','ระบุ shunt เทียบกระแสและค่าเซ็นเซอร์กับอุปกรณ์อ้างอิง'],
  ['FR-06 เตือน ≤5 วินาที','ทดสอบจำลองผ่าน แต่ BSEC LP ใหม่ทุก ~3s','ตรวจ 3 ค่าที่อ่านใหม่จริงและเวลาเตือน ห้ามนับค่าเดิมซ้ำ'],
  ['NFR-03 กราฟและทัช','query ≤5s ผ่านใน 10 ตัวอย่าง','จับเวลา browser paint และทัชถึงภาพ ≤300 ms'],
  ['GPS WALK และเข็มทิศ','GPS FIX ยืนยันแล้ว ยังไม่เดินรอบใหม่','บันทึกจริง หยุด เปิดใหม่ ส่งออก และเทียบเส้นทาง'],
  ['เวลาหลังดับทั้งสองบอร์ด','ทดสอบตัวเล็กโดยจอใหญ่ยังเปิดผ่าน','ตรวจ RTC backup และเริ่มระบบเมื่อไม่มีแหล่งเวลา'],
  ['FR-08 และ NFR-08 OTA','มี A/B SHA256 และเงื่อนไขแบต ≥30%','ปลายทาง HTTPS อัตโนมัติ รุ่นใหม่ และตัดไฟ 3 รอบ'],
  ['แบบประกอบและวงจรไฟ','มีแบบเดิม ยังไม่ยืนยันครบตามอุปกรณ์ใหม่','ตรวจขนาดจริง วงจรชาร์จและไฟย้อน'],
  ['NFR-07 งบและสื่อส่งงาน','BOM ช่องราคาและสื่อจริงยังเว้นไว้','เติมราคาซื้อรวม ตรวจ ≤3000 บาท ชื่อและวิดีโอจริง'],
 ],[2750,3400,3600]),
 small('การเปิด OTA gateway และ HTTPS tunnel ถูกระบบตรวจอนุมัติอัตโนมัติปฏิเสธด้วยเหตุผล blocked by policy จึงยังไม่ได้เปิดปลายทางนั้น การอัปเดตผ่านมือถือที่เคยทำสำเร็จไม่แทนผล OTA อัตโนมัติและตัดไฟ 3 รอบ'),
 sub('ลำดับดำเนินงานหลังรายงานฉบับนี้'),
 p('1 รักษารอบตรวจ 24 ชั่วโมงให้ครบโดยไม่รีบูตหรือเปลี่ยนเครือข่าย  2 เตรียมการทดสอบแบต การสอบเทียบ และเดินจริงแยกจากรอบนี้  3 ปรับแบบตามอุปกรณ์จริง เติมราคาและสื่อ แล้วอัปเดตสถานะตรวจรับจากผลที่ได้'),
 small('เอกสารอ้างอิง: รายงาน KU Watch วันที่ 23 ก.ย. 2569 ฉบับ (3) หน้า 1–14; Smart Environment Watch Requirements Plan V2; ความต้องการ_สถานะล่าสุด.md; เหลืออะไร_ล่าสุด.md; ผลตรวจ_10ตุลาคม2569.md; ผล JSON ตาม sources.json'));

const doc=new D.Document({creator:'KU Watch',title:'รายงานความคืบหน้าโครงงาน KU Watch 10 ตุลาคม 2569',description:'อัปเดตต่อจากรายงานวันที่ 23 กันยายน 2569 พร้อมผลและงานตรวจรับค้าง',
 styles:{default:{document:{run:{font,size:23,color:'000000'},paragraph:{spacing:{after:110,line:276}}}},paragraphStyles:[
  {id:'Title',name:'Title',basedOn:'Normal',next:'Normal',run:{font,size:42,bold:true,color:'000000'},paragraph:{keepNext:true}},
  {id:'Heading1',name:'Heading 1',basedOn:'Normal',next:'Normal',run:{font,size:30,bold:true,color:'000000'},paragraph:{keepNext:true}},
  {id:'Heading2',name:'Heading 2',basedOn:'Normal',next:'Normal',run:{font,size:25,bold:true,color:'000000'},paragraph:{keepNext:true}},
 ]},numbering:{config:[{reference:'bullets',levels:[{level:0,format:D.LevelFormat.BULLET,text:'•',alignment:D.AlignmentType.LEFT,style:{paragraph:{indent:{left:280,hanging:160}}}}]}]},
 sections:[{properties:{page:{size:{width:11906,height:16838},margin:{top:900,bottom:900,left:1080,right:1080,header:420,footer:420}}},
 headers:{default:new D.Header({children:[small('KU Watch    รายงานความคืบหน้าต่อจากวันที่ 23 กันยายน 2569')]})},
 footers:{default:new D.Footer({children:[new D.Paragraph({alignment:D.AlignmentType.RIGHT,children:[run('10 ตุลาคม 2569    หน้า ',{size:18}),new D.TextRun({children:[D.PageNumber.CURRENT],font,size:18}),run(' / ',{size:18}),new D.TextRun({children:[D.PageNumber.TOTAL_PAGES],font,size:18})]})]})},children}]});
D.Packer.toBuffer(doc).then(b=>{const file=path.join(out,'KU_Watch_ความคืบหน้า_10ตุลาคม2569_ต่อจาก23กย.docx');fs.writeFileSync(file,b);console.log(JSON.stringify({docx:file,bytes:b.length,snapshot_at:snapshotAt,samples:soak.samples,status:soak.status}));});
