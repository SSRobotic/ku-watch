const fs=require('fs'),path=require('path'),crypto=require('crypto');
const D=require('C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/docx');
const root=path.resolve(__dirname,'..'),out=path.join(root,'output/progress_update_20261014');fs.mkdirSync(out,{recursive:true});
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const s=read('output/accumulated_soak/status.json'),db=read('output/reconnect_20261014/database_check.json'),sensor=read('output/reconnect_20261014/sensors_65s.json');
const audit=fs.readFileSync(path.join(root,'output/soak_audit/status.json'));
if(crypto.createHash('sha256').update(audit).digest('hex')!==s.prior_audit_sha256)throw Error('Prior audit changed');
if(Date.now()-Date.parse(s.updated_utc)>30000)throw Error('Current status is stale');
const fmtMs=ms=>{let sec=Math.floor(ms/1000);return `${Math.floor(sec/3600)} ชั่วโมง ${Math.floor(sec%3600/60)} นาที ${sec%60} วินาที`;};
const at=new Intl.DateTimeFormat('th-TH',{timeZone:'Asia/Bangkok',dateStyle:'long',timeStyle:'medium'}).format(new Date(s.updated_utc));
const font='Leelawadee UI',width=10140;
const run=(text,opt={})=>new D.TextRun({text,font,size:23,...opt});
const p=(text,opt={})=>new D.Paragraph({children:[run(text)],spacing:{after:110,line:280},...opt});
const small=text=>new D.Paragraph({children:[run(text,{size:19,color:'4B5563'})],spacing:{after:90,line:240}});
const h=text=>new D.Paragraph({text,heading:D.HeadingLevel.HEADING_1,spacing:{before:150,after:120}});
const page=()=>new D.Paragraph({children:[new D.PageBreak()]});
function table(headers,rows,widths){
 const row=(values,head,index)=>new D.TableRow({tableHeader:head,cantSplit:true,children:values.map((v,i)=>new D.TableCell({width:{size:widths[i],type:D.WidthType.DXA},verticalAlign:D.VerticalAlign.CENTER,margins:{top:90,bottom:90,left:110,right:110},shading:{type:D.ShadingType.CLEAR,fill:head?'243E57':index%2?'F1F5F8':'FFFFFF'},children:[new D.Paragraph({children:[run(v,{size:22,bold:head,color:head?'FFFFFF':'111827'})],spacing:{after:0,line:260}})]}))});
 const border={style:D.BorderStyle.SINGLE,size:4,color:'D4DCE4'};
 return new D.Table({layout:D.TableLayoutType.FIXED,width:{size:width,type:D.WidthType.DXA},columnWidths:widths,borders:{top:border,bottom:border,left:border,right:border,insideHorizontal:border,insideVertical:border},rows:[row(headers,true,0),...rows.map((r,i)=>row(r,false,i))]});
}
const children=[
 new D.Paragraph({text:'รายงานความคืบหน้า KU Watch',heading:D.HeadingLevel.TITLE}),
 p('ฉบับอัปเดต 14 ตุลาคม 2569',{children:[run('ฉบับอัปเดต 14 ตุลาคม 2569',{bold:true})]}),
 small('ต่อจากรายงานวันที่ 23 กันยายน และฉบับวันที่ 10 ตุลาคม 2569'),
 small(`ข้อมูลรอบยาว ณ ${at}  |  ตัวเล็ก 2.0.8  |  จอใหญ่ HUB 1.0.5`),
 p('ระบบนาฬิกา จอใหญ่ และระบบรับข้อมูลบนคอมกลับมาทำงานร่วมกันแล้ว ผู้ใช้ยืนยันว่าทั้งสองจอแสดงภาพและเวลาปัจจุบัน การตรวจรหัสที่รับจริงพบว่าข้อมูลเข้า DB ครบตามชุดที่ตรวจ แต่การตรวจรับระยะยาวและความแม่นยำของเซ็นเซอร์ยังไม่ครบ'),
 h('ความคืบหน้าของระบบ'),
 table(['ส่วนงาน','สิ่งที่ทำแล้ว','ผลและงานที่ยังค้าง'],[
  ['จอเล็กและเมนู','เฟิร์มแวร์ 2.0.8 มี 11 หน้า แก้หมุนจอและกู้ภาพจอดำ','ผู้ใช้ยืนยันใช้งานเปลี่ยนหน้าได้ ยังไม่วัดเวลาทัชถึงภาพ'],
  ['จอใหญ่และ ESP-NOW','HUB 1.0.5 รับข้อมูลและส่งคำสั่งกลับ จับคู่และเชื่อมต่อได้','รอบ 14 ต.ค. TX/RX เพิ่มขึ้น ผู้ใช้ยืนยันภาพและเวลา'],
  ['สิ่งแวดล้อมและการเคลื่อนไหว','BME68x/BSEC IAQ และข้อมูลการเคลื่อนไหวส่งขึ้นระบบ','สถานะพร้อม 65/65 รายการ ยังต้องเทียบเครื่องมืออ้างอิง'],
  ['BPM และ SpO₂','เพิ่มการกรองและแสดงค่าประมาณ ผู้ใช้เคยยืนยันปลายนิ้วอ่านได้','รอบ 14 ต.ค. ยังไม่มีข้อมูล PPG สด ไม่ใช่ผลเทียบความแม่นยำ'],
  ['GPS แผนที่และ WALK','มีแผนที่บางเขนและพื้นที่อำนาจเจริญ บันทึกกิจกรรมและส่งออก TCX','ผู้ใช้เคยยืนยัน GPS FIX แต่ยังข้ามการเดินทดสอบเส้นทางจริง'],
  ['แบตเตอรี่และ INA226','ใช้งานแบต 1000 mAh และอ่านแรงดันได้','กระแสยังไม่สอบเทียบ ยังไม่ทดสอบแบตเต็ม 6 ชั่วโมง'],
  ['เวลาและ RTC','ใช้เวลา GPS/NTP จอใหญ่ RTC และตั้งผ่านคอมได้','รอบล่าสุดตั้งจากคอม ต้องยืนยันแบตสำรอง RTC เมื่อดับทั้งสองบอร์ด'],
  ['KU BOT และการตั้งค่า','มีท่าทาง การเติบโตตามกิจกรรม และบันทึกค่าหลังปิดเครื่อง','มีแจ้งเตือนและ OTA ในโค้ด ยังต้องตรวจเงื่อนไขเตือนและ OTA อัตโนมัติ'],
  ['ระบบข้อมูลและ Grafana','MQTT TLS คิวเก็บข้อมูลย้อนหลัง Node-RED InfluxDB และ Grafana','กลับมารับข้อมูลสดแล้ว คงผลขาดช่วงและ dropped ตามจริง'],
 ],[1900,4100,4140]),
 page(),h('ผลทดสอบที่มีหลักฐาน'),
 p('ผลแต่ละชุดยืนยันเฉพาะขอบเขตที่ระบุ จำนวนรหัสที่เข้า DB ครบไม่แทนผลว่าข้อมูลทุกช่วงไม่สูญหาย และเวลาหลายช่วงรวมกันไม่แทนการใช้งานต่อเนื่อง 24 ชั่วโมง'),
 table(['ผลตรวจ','ผลที่บันทึกได้','ขอบเขต'],[
  ['เวลารับสดสะสม',fmtMs(s.credited_ms),'นับช่วงรับสดที่รหัสต่อกันและห่างไม่เกิน 10 วินาที ไม่รวม backfill หรือช่วงเงียบ'],
  ['ช่วงต่อเนื่องยาวที่สุด',fmtMs(s.longest_continuous_ms),'ยังไม่ครบ 24 ชั่วโมง ช่วงต่อเนื่องปัจจุบัน '+fmtMs(s.current_continuous_ms)],
  ['จำนวนข้อมูลสดสะสม',s.samples.toLocaleString('en-US')+' รายการ','พบการขาดช่วงสะสม '+s.breaks+' ครั้ง ช่วงเก่าที่ไม่ผ่านยังเก็บแยก'],
  ['รับสดหลังต่อระบบ 14 ต.ค.',sensor.live+' รายการ / '+sensor.observed_s.toFixed(3)+' วินาที','reader disconnect 0 / malformed 0 ช่วงรับสูงสุด '+(sensor.max_interval_ms/1000).toFixed(3)+' วินาที'],
  ['DB ชุดที่รับ 14 ต.ค.',db.stored_once+' / '+db.observed_trusted_ids+' รหัส อยู่รหัสละหนึ่งแถว','มีสด '+db.observed_live+' รหัส ที่เหลือย้อนหลัง ไม่รวมข้อมูลที่ไม่ได้รับหรือเวลาเก่าไม่ถูกต้อง'],
  ['การระบายคิว','จาก 758 เหลือ 1 รายการที่กำลังส่ง','บอร์ดแจ้ง dropped=24 ในบูตรอบนี้ ไม่สรุปว่าทุกช่วงครบ'],
  ['ความหน่วง query 10 ต.ค.','เฉลี่ย 3.091 s สูงสุด 3.275 s / 10 รหัส','capture UTC ถึงผล query ไม่รวมเวลาวาดหน้าจอเบราว์เซอร์'],
  ['การตรวจ 24 ชั่วโมงรอบเดิม','ไม่ผ่าน หยุดที่ 1 ชั่วโมง 30 นาที 24 วินาที','พบ 2 รอบบูต และช่วงรับห่าง 12.097 s ไม่รวมรอบนี้เข้าผลต่อเนื่อง'],
 ],[2350,3400,4390]),
 h('ข้อสรุปของการตรวจระยะยาว'),
 p('ตัวเก็บยังรับ MQTT จริงและบันทึกเวลา รหัสข้อมูล และเหตุการณ์การเชื่อมต่อไว้ตรวจย้อนหลัง เมื่อตรวจพบช่วงขาดจะหยุดนับช่วงนั้นและเริ่มช่วงต่อเนื่องใหม่ โดยรักษายอดสะสมที่บันทึกแล้ว การเสียบ USB ในรอบนี้ไม่ใช่ผลทดสอบอายุแบตเตอรี่'),
 small('หลักฐานสำคัญอยู่ใน output/accumulated_soak/ และ output/reconnect_20261014/ โดยฉบับนี้แนบ snapshot และรายการ SHA-256 ใน sources.json ผลจำลองในแดชบอร์ด DEMO ไม่ถูกนำมาใช้เป็นผลผ่าน'),
 page(),h('งานค้างและขั้นถัดไป'),
 table(['งานตรวจรับ','สิ่งที่ต้องทำต่อ'],[
  ['ต่อเนื่อง 24 ชั่วโมง','เก็บรอบที่รับต่อเนื่องครบจริง โดยคอม บอร์ด และอินเทอร์เน็ตยังเปิด ไม่ใช้เวลาสะสมแทน'],
  ['แบตเตอรี่ 6 ชั่วโมงและวงจรไฟ','ทดสอบด้วยแบตเต็มโดยถอด USB ตรวจแบตสำรอง RTC และการป้องกันไฟย้อนของวงจรจริง'],
  ['สอบเทียบเซ็นเซอร์','ระบุค่าตัวต้านทาน shunt ของ INA226 เทียบกระแส อุณหภูมิ และ PPG กับเครื่องมืออ้างอิง'],
  ['WALK GPS และเข็มทิศ','เดินกลางแจ้ง บันทึก หยุด เปิดใหม่ ส่งออก TCX และตรวจเส้นทางจริง'],
  ['เวลาเตือนและความหน่วงหน้าจอ','จับเวลาเตือนจากข้อมูลใหม่ 3 รอบ BSEC LP ใช้ราว 3 s ต่อรอบ ตรวจ browser paint และทัช ≤300 ms'],
  ['OTA อัตโนมัติและ rollback','เตรียม HTTPS ที่ใช้ได้กับเฟิร์มแวร์ใหม่ แล้วตรวจดาวน์โหลดอัตโนมัติและตัดไฟ 3 ครั้ง ยังไม่ดำเนินการในรอบนี้'],
  ['BOM แบบเคส และสื่อส่งงาน','เติมราคาซื้อจริงให้ตรวจงบ ≤3,000 บาท ยืนยันแบบเคสล่าสุด และใส่ชื่อสมาชิก ภาพ/วิดีโอทดสอบ'],
 ],[2850,7290]),
 h('แผนงานระหว่างรอผลระยะยาว'),
 p('ให้ตัวเก็บทำงานต่อและเก็บหลักฐานเมื่อมีเหตุการณ์ ระหว่างนี้เตรียมภาพอุปกรณ์จริง วิดีโอเปลี่ยนหน้าและสั่งงานสองทาง รวมถึงรายการราคา แล้วทดสอบเซ็นเซอร์และเส้นทางเมื่อมีเครื่องมือและพื้นที่พร้อม ขั้นที่ยังทำไม่ได้คงสถานะรอทดสอบไว้'),
 p('ชื่อสมาชิกและบทบาท __________________________________________'),
 p('ภาพจอเล็กและจอใหญ่ __________________________________________'),
 p('ลิงก์วิดีโอทดสอบจริง ___________________________________________'),
 small('อ้างอิงรายงาน 23 ก.ย. 2569 และฉบับ 10 ต.ค. 2569 ข้อกำหนด Plan V2 ความต้องการ_สถานะล่าสุด.md และผล JSON จริงตาม sources.json ไม่มีการสรุปว่าผ่านข้อกำหนดทั้งหมด'),
];
const doc=new D.Document({creator:'KU Watch',title:'รายงานความคืบหน้า KU Watch 14 ตุลาคม 2569',styles:{default:{document:{run:{font,size:23},paragraph:{spacing:{after:110,line:280}}}},paragraphStyles:[{id:'Title',name:'Title',basedOn:'Normal',next:'Normal',run:{font,size:38,bold:true,color:'243E57'},paragraph:{keepNext:true,spacing:{after:150}}},{id:'Heading1',name:'Heading 1',basedOn:'Normal',next:'Normal',run:{font,size:28,bold:true,color:'243E57'},paragraph:{keepNext:true}}]},sections:[{properties:{page:{size:{width:12240,height:15840},margin:{top:850,bottom:850,left:1050,right:1050,header:400,footer:400}}},headers:{default:new D.Header({children:[small('KU Watch    ความคืบหน้าต่อจากวันที่ 23 กันยายน 2569')]})},footers:{default:new D.Footer({children:[new D.Paragraph({alignment:D.AlignmentType.RIGHT,children:[run('14 ตุลาคม 2569    หน้า ',{size:18}),new D.TextRun({children:[D.PageNumber.CURRENT],font,size:18})]})]})},children}]});
const files=['output/accumulated_soak/status.json','output/soak_audit/status.json','output/reconnect_20261014/database_check.json','output/reconnect_20261014/mqtt_receipts.json','output/reconnect_20261014/sensors_65s.json','output/reconnect_20261014/watch_final_status.json','output/requirements_audit_20261009/grafana_latency_phone_20261010.json'];
const sources=files.map(p=>{const b=p==='output/accumulated_soak/status.json'?Buffer.from(JSON.stringify(s,null,2)):fs.readFileSync(path.join(root,p));return {path:p==='output/accumulated_soak/status.json'?'output/progress_update_20261014/soak_status_at_report.json':p,bytes:b.length,sha256:crypto.createHash('sha256').update(b).digest('hex')};});
fs.writeFileSync(path.join(out,'soak_status_at_report.json'),JSON.stringify(s,null,2));
fs.writeFileSync(path.join(out,'sources.json'),JSON.stringify({snapshot_utc:s.updated_utc,snapshot_thai:at,soak:s,sources},null,2));
D.Packer.toBuffer(doc).then(b=>{const file=path.join(out,'KU_Watch_รายงานความคืบหน้า_14ตุลาคม2569.docx');fs.writeFileSync(file,b);console.log(JSON.stringify({docx:file,snapshot_utc:s.updated_utc,cumulative:fmtMs(s.credited_ms),longest:fmtMs(s.longest_continuous_ms),current:fmtMs(s.current_continuous_ms),samples:s.samples}));});
