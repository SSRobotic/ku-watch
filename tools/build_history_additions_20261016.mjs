import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const ROOT='C:/Users/pomma/OneDrive/Desktop/02_Projects/KU_Watch_Display_First';
const runtime='C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES=path.join(runtime,'node/node_modules');
const {FileBlob,Presentation,PresentationFile}=await import(pathToFileURL(path.join(runtime,'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const B=path.join(ROOT,'output/ppt_history_v2_20261016/build');
const source=path.join(ROOT,'สไลด์/พร้อมนำเสนอ/KU_Watch_นำเสนอวิชาการ_18ตุลาคม2569.pptx');
const original=await PresentationFile.importPptx(await FileBlob.load(source));
await fs.writeFile(path.join(B,'source_inspection.json'),JSON.stringify(await original.inspect({kind:'slide,layout',maxChars:6000}),null,2));
if(original.slides.items.length!==66)throw Error('Source count changed; inspect before proceeding');
const m=JSON.parse(await fs.readFile(path.join(B,'history_manifest.json'),'utf8'));
const old=JSON.parse(await fs.readFile(path.join(ROOT,'output/ppt_academic_20261016/build/media_inventory.json'),'utf8'));
const p=Presentation.create({slideSize:{width:1920,height:1080}});
const C={navy:'#1E3A5F',blue:'#2F6FB0',ink:'#222E3A',muted:'#657586',line:'#D5DCE4'};
const font='Leelawadee UI',plan={source,source_slides:66,main_slides:14,replacements:[],append:[],links:[],videos:[]};
const asset=id=>m.images.find(x=>x.id===id);
function text(s,v,x,y,w,h,size=34,bold=false,color=C.ink,name='text'){const q=s.shapes.add({geometry:'textbox',name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});q.text=v;q.text.style={typeface:font,fontSize:size,bold,color};q.text.insets=0;return q;}
function make(title,finalNumber,history=true){const s=p.slides.add();s.background.fill='#FFFFFF';text(s,title,90,52,history?1370:1730,90,history?52:62,true,C.navy);text(s,history?'KU Watch  /  ภาพพัฒนาการและเอกสารออกแบบที่ผู้ใช้ส่งมา':'KU Watch  /  รายงานผลการพัฒนาต้นแบบ  /  16 ตุลาคม 2569',90,1028,1650,28,20,false,C.muted);text(s,String(finalNumber).padStart(2,'0'),1775,1028,80,30,22,false,C.muted);if(history&&finalNumber!==15){text(s,'สารบัญภาคผนวก',1510,44,330,55,26,false,C.blue,'back-to-index');plan.links.push({slide:finalNumber,shapeName:'back-to-index',targetSlide:15});}return s;}
async function image(s,file,x,y,w,h,alt){s.images.add({blob:new Uint8Array(await fs.readFile(file)),contentType:/\.png$/i.test(file)?'image/png':'image/jpeg',fit:'contain',alt,position:{left:x,top:y,width:w,height:h}});}
async function img(s,id,x,y,w,h){const a=asset(id);await image(s,a.display_file,x,y,w,h,a.title);}
function note(s,body,ids=[]){s.speakerNotes.text=body+'\n\nหลักฐาน\n'+ids.map(id=>asset(id)?.source||id).join('\n');}
function label(s,v,x,y,w,size=29){text(s,v,x,y,w,80,size,false,C.muted);}
function add(title,body,ids=[]){const n=66+plan.append.length+1,s=make(title,n);plan.append.push({donor_slide:p.slides.items.length,final_slide:n,title});note(s,body,ids);return s;}

// Replace only source slide 2; keep the problem, target users and project scope.
let s=make('โจทย์และพัฒนาการของต้นแบบ',2,false);
text(s,'ข้อมูล ณ จุดใช้งาน',90,215,500,70,43,true,C.navy);
text(s,'กิจกรรมกลางแจ้ง\nในมหาวิทยาลัย\nและพื้นที่เกษตร',90,320,500,190,39);
text(s,'อ่านค่ารอบตัวได้ทันที\nดูข้อมูลร่วมกันสองจอ\nและตรวจย้อนหลังได้',90,585,500,205,36);
label(s,'ชีพจรและ SpO₂ เป็นค่าทดลอง',90,835,510,27);
text(s,'เปิดภาพพัฒนาการทั้งหมด',90,935,520,60,29,true,C.blue,'open-history');
plan.links.push({slide:2,shapeName:'open-history',targetSlide:67});
const overview=[['cad','ออกแบบตัวเรือน',665,205],['assembly_wide','ประกอบและต่อโมดูล',1265,205],['lcd_issue','ตรวจปัญหาจอและการประกอบ',665,595],['backend_screen','เชื่อมข้อมูลกับ Node-RED',1265,595]];
for(const [id,title,x,y] of overview){await img(s,id,x,y,550,285);text(s,title,x,y+300,550,65,29,true,C.navy);}
note(s,'เวลาพูด 25 วินาที\nสรุปโจทย์เดิมและพัฒนาการตามขั้นตอนงาน ภาพเก่าแสดงทั้งการทำงานและปัญหาระหว่างพัฒนา ไม่ใช้ภาพจอขาวเป็นสถานะปัจจุบัน ภาคผนวกให้เปิดขยายได้ทุกภาพ วันที่บนหน้าจอระยะแรกไม่ใช่หลักฐานเวลาจริง',['cad','assembly_wide','lcd_issue','backend_screen']);
plan.replacements.push({donor_slide:1,final_slide:2,title:'โจทย์และพัฒนาการของต้นแบบ'});

s=make('ภาคผนวก: สื่อสาธิตและหลักฐาน',15);
text(s,'คลิกหัวข้อเพื่อเปิดภาพเต็ม คลิป หรือผลตรวจรับ',90,195,1740,60,34,false,C.muted);
const entries=[['พัฒนาการ: CAD และแบบประกอบ',67],['ประกอบโมดูลและแก้ปัญหา',70],['คลิปต้นแบบระหว่างพัฒนา',80],['ทดสอบนอกอาคารจากชุดเดิม',81],['คลิปเดินและ GPS ฉบับเต็ม',16],['Grafana: คลิปกราฟข้อมูลไหล',17],['Node-RED: คลิปหลังกลับออนไลน์',18],['Node-RED: flow และหน้าระบบ',19],['InfluxDB: จำนวนข้อมูล',28],['InfluxDB: ตัวอย่างข้อมูล',29],['CSV จาก MicroSD',30],['ตาราง Requirements: FR',31],['ตาราง Requirements: NFR',32],['Grafana: ภาพครบ 77 แผง',33],['เอกสารอ้างอิง',66]];
entries.forEach(([title,target],i)=>{const x=i<8?100:1000,y=285+(i<8?i:i-8)*86;const name='index-v2-'+i;text(s,title,x,y,810,75,31,true,C.blue,name);plan.links.push({slide:15,shapeName:name,targetSlide:target});});
note(s,'สารบัญสำหรับเปิดหลักฐานประกอบตอบคำถาม ภาคผนวกซ่อนไว้จากลำดับนำเสนอหลัก 14 หน้า รายการภาพพัฒนาการเป็นประวัติการทำงาน ส่วนตารางตรวจรับยังคงผลจากชุดเดิม');
plan.replacements.push({donor_slide:2,final_slide:15,title:'ภาคผนวก: สื่อสาธิตและหลักฐาน'});

s=add('ออกแบบตัวเรือนและปรับรูปแบบ','ภาพจาก SolidWorks ที่ผู้ใช้เก็บไว้ เปรียบเทียบ V1 กับ V5 ตามข้อความในภาพ ไม่ระบุวันสำเร็จจากชื่อไฟล์ และไม่ใช้ยืนยันขนาดจากการวัดตัวเครื่อง',['cad']);
await img(s,'cad',65,165,1790,770);label(s,'เปรียบเทียบโครงสร้างตัวเรือนและตำแหน่งโมดูลก่อนประกอบ',90,955,1740);

s=add('แบบประกอบเชิงกล: Rev A','เอกสารอ้างอิงออกแบบ 16 กันยายน 2569 ไม่ใช่แบบ As-built รุ่นปัจจุบัน แบบระบุโมเดล ESP32-C3 และบอกเองว่าต้องปรับให้ตรง ESP32-S3 จอใหญ่และ GPS ไม่อยู่ในโมเดลนี้',['C:/Users/pomma/Downloads/KU_Watch_Drawing.PDF']);
await image(s,m.pdfs.find(x=>x.id==='drawing').image,65,155,1790,785,'Drawing Rev A เต็มหน้า');label(s,'แบบอ้างอิงเดิม 16 ก.ย. 2569  /  มีชิ้นส่วนโมเดลที่ต่างจากเครื่องประกอบปัจจุบัน',90,955,1740,27);

s=add('แบบเชื่อมต่อวงจร: Rev A','Schematic เดิม 16 กันยายน 2569 เป็น review draft ระบุ INA226 0x40/ACK only, แบต 600mAh และ GPS/ESP-NOW ยังวางแผนไว้ เครื่องปัจจุบันใช้แบต1000mAhและINA2260x44พร้อมGPS/ESP-NOWที่มีหลักฐานแยกในชุดเดิม จึงคงภาพเดิมและระบุขอบเขต ไม่ใช้เป็นผังต่อสายล่าสุด',['C:/Users/pomma/Downloads/KU_Watch_Schematic.pdf']);
await image(s,m.pdfs.find(x=>x.id==='schematic').image,65,155,1790,785,'Schematic Rev A เต็มหน้า');label(s,'แบบร่างเดิม  /  แบต 600mAh และ INA226 0x40 ในแบบต่างจากชุดปัจจุบัน',90,955,1740,27);

s=add('เลือกบอร์ดและจัดวางโมดูล','ภาพบอร์ดจริง การทดลองจัดวางในถาดเคส และแบตเตอรี่1000mAh พร้อมMAX30102 แสดงงานจัดพื้นที่ก่อนต่อสาย ไม่ใช้แทนผลทดสอบแบตเตอรี่',['mcu','layout','battery']);
for(const [i,id] of ['mcu','layout','battery'].entries()){await img(s,id,80+i*600,185,560,720);label(s,asset(id).title,80+i*600,925,560,28);}

s=add('ประกอบสายและตรวจอุปกรณ์','ภาพต้นแบบเปิดเคสขณะทำงานและหน้าDEVICES แสดงการต่อโมดูลร่วมกัน ค่าหรือสถานะเก่าในภาพไม่ใช่การยืนยันว่าทุกเซ็นเซอร์ผ่านเกณฑ์ครบ',['assembly_wide','devices']);
for(const [i,id] of ['assembly_wide','devices'].entries()){await img(s,id,80+i*920,205,840,600);label(s,asset(id).title,80+i*920,845,840,30);}

s=add('ปัญหาระหว่างประกอบ: จอและปุ่ม','ภาพซ้ายเป็นจอขาวและเส้นที่ผู้ใช้เก็บระหว่างพัฒนา ภาพขวาแสดงตำแหน่งปุ่มกด ภาพเหล่านี้เป็นหลักฐานพบปัญหา ไม่สรุปสาเหตุทางไฟฟ้าจากภาพเพียงอย่างเดียว',['lcd_issue','button']);
await img(s,'lcd_issue',80,190,840,635);await img(s,'button',1000,190,840,635);label(s,'ตรวจอาการจอขาวและเส้นระหว่างทดสอบ',80,865,840,30);label(s,'จัดตำแหน่งปุ่มกดบนตัวเรือน',1000,865,840,30);

s=add('ตรวจความพอดีของช่องและจุดยึด','ภาพวงสีแดงเป็นคำอธิบายเดิมจากผู้ใช้ คงไว้ตามต้นฉบับ ใช้บันทึกจุดตรวจทางกลและระยะเสียบสาย ไม่อ้างว่าแก้ช่องทุกจุดเสร็จจากภาพนี้',['usb_small','slot','usb_hub']);
for(const [i,id] of ['usb_small','slot','usb_hub'].entries()){await img(s,id,80+i*600,175,560,735);label(s,asset(id).title,80+i*600,930,560,28);}

s=add('จัดวางจอใหญ่ในตัวเรือน','ภาพจอใหญ่ESP32-S3-Touch-LCD-2.1ในตัวเรือนและด้านหลังบอร์ด เห็นช่องMicroSDและRTC ขอบเขตนี้คือการประกอบทางกล หลักฐานการบันทึกCSVใช้ผลจากชุดเดิม',['hub_marked','hub_board']);
await img(s,'hub_marked',90,175,830,760);await img(s,'hub_board',1000,175,830,760);label(s,'ตรวจตำแหน่งบอร์ดและขอบตัวเรือน',90,950,830,28);label(s,'ตรวจการเข้าถึง MicroSD และช่องเชื่อมต่อ',1000,950,830,28);

s=add('พัฒนาเมนูของจอสัมผัส','หน้าหลัก หน้าSYSTEM และหน้าปรับความสว่างจากการพัฒนาระยะแรก ค่าจำนวนก้าวและวันที่ในภาพไม่ใช้เป็นผลตรวจความแม่นยำของกิจกรรมหรือRTC',['hub_home','hub_system','hub_brightness']);
for(const [i,id] of ['hub_home','hub_system','hub_brightness'].entries()){await img(s,id,80+i*600,175,560,735);label(s,asset(id).title,80+i*600,930,560,28);}

s=add('ตรวจสายพร้อมทดสอบการแสดงผล','ภาพเปิดเคสแสดงการทดสอบหน้าหลักและหน้าสภาพแวดล้อมขณะยังเข้าถึงสายได้ คงการวางแนวภาพตามต้นฉบับ ไม่หมุนเฉพาะตัวเลขให้ดูเหมือนจออยู่ทิศอื่น',['open_home','open_env']);
await img(s,'open_home',90,175,830,760);await img(s,'open_env',1000,175,830,760);label(s,'หน้าหลักพร้อมตรวจวงจรภายใน',90,950,830,28);label(s,'หน้าสภาพแวดล้อมพร้อมตรวจสายโมดูล',1000,950,830,28);

s=add('อ่านค่าสภาพแวดล้อมบนตัวเครื่อง','ภาพแสดงอุณหภูมิ ความชื้น และความดันบนตัวเล็กในมุมและช่วงทดสอบต่างกัน ไม่ใช้เป็นหลักฐานสอบเทียบกับเครื่องอ้างอิง',['environment','env_angle','env_wide']);
await img(s,'environment',75,180,515,760);await img(s,'env_angle',650,180,515,760);await img(s,'env_wide',1230,210,600,445);text(s,'อุณหภูมิ\nความชื้น\nความดันอากาศ',1250,720,550,165,36,true,C.navy);label(s,'ภาพอ่านค่าจริงระหว่างพัฒนา  /  ความแม่นยำยังต้องมีเครื่องอ้างอิง',90,960,1740,27);

s=add('เชื่อมข้อมูลกับ Node-RED ระยะแรก','ภาพหน้าจอจริงที่ผู้ใช้เก็บไว้ แสดงMQTTเข้าfunctionแล้วแยกไปกราฟและเครื่องวัด เป็นโครงสร้างbackendระยะแรก ไม่เท่ากับflowและtopiccanonicalในผลตรวจรับปัจจุบัน',['backend_screen']);
await img(s,'backend_screen',65,170,1790,780);label(s,'เห็น dashboard และ flow ในภาพเดียวกัน  /  โครงสร้างระยะแรก',90,965,1740,28);

s=add('ทดสอบนาฬิกาควบคู่คอมพิวเตอร์','ภาพต้นแบบและNodeREDทำงานร่วมกันที่ผู้ใช้ถ่ายไว้ เป็นหลักฐานการบูรณาการระยะแรก ค่าวันเวลาที่จอเก่าไม่ใช้แทนเวลารับข้อมูลจริง',['backend_photo']);
await img(s,'backend_photo',90,175,1740,780);label(s,'ตรวจค่าบนอุปกรณ์ควบคู่กราฟและข้อความในคอมพิวเตอร์',90,965,1740,28);

s=add('คลิปต้นแบบระหว่างพัฒนา','คลิปผู้ใช้ส่งมา ความยาวจริง30.233วินาที แสดงโมดูล หน้าDEVICES และNodeREDตามที่ถ่าย ไม่เปลี่ยนความเร็ว ไม่แทนผลสอบเทียบหรือผลผ่านทั้งระบบ',[m.video.source]);
await image(s,m.video.frames[1].file,100,175,620,790,'ภาพตัวอย่างคลิปต้นแบบระหว่างพัฒนา');
text(s,'บันทึกการทดสอบจริง',880,250,900,75,46,true,C.navy);text(s,'สำรวจการต่อโมดูล\nเปิดหน้า DEVICES\nตรวจค่าที่รับบน Node-RED',880,375,900,225,42);label(s,'คลิปเต็มประมาณ 30 วินาที\nคลิกวิดีโอเพื่อเล่นระหว่างตอบคำถาม',880,720,900,32);
plan.videos.push({slide:80,id:'history_development',file:m.video.source,poster:m.video.frames[1].file,left:100,top:175,width:620,height:790,posterName:null});

s=add('ทดสอบนอกอาคารจากชุดเดิม','ภาพสถานที่ทดสอบนอกอาคารและต้นแบบจากชุดสื่อเดิม ผู้ใช้ยืนยันGPSFIXก่อนถ่ายคลิปเดิน แต่ภาพนี้ไม่ระบุสถานที่หรือความแม่นยำระยะทางจากภาพเพียงอย่างเดียว',[path.join(ROOT,old.photos[1].source)]);
await image(s,path.join(ROOT,old.photos[1].display_file),90,175,650,790,'ภาพต้นแบบและคอมพิวเตอร์ในพื้นที่ทดสอบนอกอาคาร');text(s,'ขั้นต่อจากการประกอบ',900,250,900,75,46,true,C.navy);text(s,'ตรวจการรับ GPS\nบันทึกกิจกรรมเดิน\nดูผลบนจอใหญ่และ Backend',900,375,900,225,42);text(s,'เปิดคลิปเดินและ GPS ฉบับเต็ม',900,740,900,70,32,true,C.blue,'history-walk');plan.links.push({slide:81,shapeName:'history-walk',targetSlide:16});text(s,'เปิดสถานะตรวจรับ Requirements',900,845,900,70,32,true,C.blue,'history-requirements');plan.links.push({slide:81,shapeName:'history-requirements',targetSlide:13});

plan.total_slides=66+plan.append.length;
await fs.writeFile(path.join(B,'additions_plan.json'),JSON.stringify(plan,null,2));
await (await PresentationFile.exportPptx(p)).save(path.join(B,'history_additions.pptx'));
console.log(JSON.stringify({source_slides:66,authored_slides:p.slides.items.length,appendix_added:plan.append.length,total:plan.total_slides,replacements:plan.replacements.length,new_videos:plan.videos.length}));
