// Update a copy of the original 14-slide deck. No board or cloud writes.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const runtime=path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies');
process.env.RUNTIME_NODE_MODULES=path.join(runtime,'node/node_modules');
const skill=path.join(process.env.USERPROFILE,'.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations');
const {PresentationFile,FileBlob}=await import(pathToFileURL(path.join(runtime,'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const build=path.join(root,'output/presentation_build_latest'),output=path.join(root,'output/delivery_20261010');
await fs.mkdir(build,{recursive:true});await fs.mkdir(output,{recursive:true});
const source=path.join(root,'output/delivery_20261009/KU_Watch_ตามเกณฑ์ประเมิน_25691009_v2.pptx');
const sourceHash=crypto.createHash('sha256').update(await fs.readFile(source)).digest('hex');
const p=await PresentationFile.importPptx(await FileBlob.load(source));
if(p.slides.items.length!==14)throw Error('Source slide count changed');
const inspection=await p.inspect({select:'$.slides[*]',include:['id','index','elements.id','elements.kind','elements.text']});
const records=inspection.records;
function exact(slide,old){const hits=records[slide-1].elements.filter(e=>e.text===old);if(hits.length!==1)throw Error('Expected one imported element: '+old);return p.resolve(hits[0].id);}
exact(1,'KU Watch 2.0.5 / Hub 1.0.5 · 9 ตุลาคม2569').text.replace('KU Watch 2.0.5 / Hub 1.0.5 · 9 ตุลาคม2569','KU Watch 2.0.8 / Hub 1.0.5 · 10 ตุลาคม2569');
exact(3,'ขั้นต่ำมีครบ: เซ็นเซอร์ + ไร้สาย + จอ/เตือน\nองค์ประกอบเสริม: แบต / Preferences / OTA / RTCจอใหญ่').text.replace('ขั้นต่ำมีครบ','มีองค์ประกอบ');
exact(7,'1Hz = 86,400ข้อความ/วัน · สมมติJSON2kB ≈172.8MB/วัน\nแฟลชเป็นคิวจำกัด768รายการ; DBควรวาง retention30วันตามดิสก์จริง').text.replace('แฟลชเป็นคิวจำกัด768รายการ; DBควรวาง retention30วันตามดิสก์จริง','คิวสูงสุด768รายการขึ้นกับพื้นที่ว่าง · retention30วันเป็นแผน');
exact(11,'เน็ตขาด: queue / backoff / replay\nWi-Fiและพอร์ตMQTTขาด10นาทีผ่าน').text.replace('Wi-Fiและพอร์ตMQTTขาด10นาทีผ่าน','พอร์ตMQTTขาด10นาทีผ่านรอบ9ต.ค.');
const s11=p.slides.items[10];s11.speakerNotes.text += '\nอัปเดต10ตุลาคม: ผลพอร์ตMQTTขาด10นาทีเป็นรุ่น2.0.5 โดยWi-Fiยังเชื่อม ห้ามใช้แทนรอบมือถือ24hหรือกล่าวว่าเครือข่ายปัจจุบันไม่มีข้อมูลตกหล่น ประวัติbootรุ่นเก่า dropped64 และช่วงสลับเครือข่ายรุ่น2.0.8 dropped26 คงไว้ตามจริง';
const gallery=path.join(root,'output/presentation_evidence'),latest=JSON.parse(await fs.readFile(path.join(gallery,'latest.json'),'utf8'));
if(!latest.layout_verified)throw Error('Latest evidence layout was not checked');
const candidates=(await fs.readdir(gallery)).filter(n=>/^\d{14}_/.test(n)).sort().reverse();
let full;
for(const name of candidates){try{const m=JSON.parse(await fs.readFile(path.join(gallery,name,'manifest.json'),'utf8'));if(m.layout_verified&&m.images.some(x=>x.file==='02_query_latency.png')){full={folder:name,meta:m};break;}}catch{}}
if(!full)throw Error('Verified query image missing');
async function verifiedImage(folder,meta,name){const b=await fs.readFile(path.join(gallery,folder,name));const expected=meta.images.find(x=>x.file===name).sha256;if(crypto.createHash('sha256').update(b).digest('hex')!==expected)throw Error('Evidence image changed');return b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength);}
const queryBytes=await verifiedImage(full.folder,full.meta,'02_query_latency.png');
const soakBytes=await verifiedImage(latest.folder,latest,'01_soak.png');
const s=p.slides.items[13];
exact(14,'เกณฑ์ความสำเร็จและหลักฐานปัจจุบัน').text.replace('เกณฑ์ความสำเร็จและหลักฐานปัจจุบัน','ผลล่าสุดและหลักฐานพร้อมเวลา');
const oldImage=records[13].elements.filter(e=>e.kind==='image');if(oldImage.length!==1)throw Error('Original evidence image was ambiguous');
const image=p.resolve(oldImage[0].id);image.replace({blob:queryBytes,contentType:'image/png',alt:'ผล10รหัสจริงถึงGrafana query เฉลี่ย3.091s ยังไม่รวมbrowser paint',fit:'contain'});
image.position={left:72,top:162,width:650,height:366};
exact(14,'DBครบ 600 ข้อมูลช่วงขาด; ลำดับขาด0\nผู้ใช้ยืนยันปิดเปิดแล้วเวลากลับมาตรง').text.replace('DBครบ 600 ข้อมูลช่วงขาด; ลำดับขาด0\nผู้ใช้ยืนยันปิดเปิดแล้วเวลากลับมาตรง','มือถือ: DBครบ657รหัส · queryเฉลี่ย3.091s\n24hยังตรวจไม่ครบ · ช่วงสลับเข้าคิวไม่ได้26');
const videoShape=p.resolve(records[13].elements.find(e=>e.id==='sh/idgvmx8r').id);
videoShape.position={left:758,top:470,width:450,height:150};
const videoText=exact(14,'วิดีโอทดสอบ\nเปลี่ยนหน้า / ค่าจริง / WALK');
videoText.position={left:780,top:499,width:406,height:85};
videoText.text.style={typeface:'Tahoma',fontSize:24,bold:true,color:'#145B43'};
const photoShape=p.resolve(records[13].elements.find(e=>e.id==='sh/kfidonqx').id);
photoShape.position={left:758,top:171,width:450,height:253};
exact(14,'ภาพประกอบ\nผลกราฟหรือCSVจริง').text='';
s.images.add({blob:soakBytes,contentType:'image/png',alt:'ภาพสถานะ24hจริง ณ '+latest.captured_bangkok+' ยังไม่ครบ24ชั่วโมง',fit:'contain',position:{left:758,top:171,width:450,height:253}});
const caption=s.shapes.add({geometry:'textbox',position:{left:758,top:431,width:450,height:32},fill:'none',line:{fill:'none',width:0}});
caption.text='ภาพสถานะ ณ '+latest.captured_bangkok+' UTC+7';caption.text.style={typeface:'Tahoma',fontSize:17,color:'#52645E'};
const footer=exact(14,'ชุดส่งมอบ: source / คู่มือ / รายงาน / เครื่องมือตรวจ / รายการข้าม');
footer.text=[[{run:'เปิดภาพหลักฐานเต็มขนาดและวิดีโอ',link:{uri:'../presentation_evidence/index.html',isExternal:true}},'   ·   ',{run:'เปิด Grafana Live',link:{uri:'http://127.0.0.1:3000/d/ku-watch-live/ku-watch-e280a2-live-and-walk?from=now-15m&to=now&timezone=browser&refresh=1s',isExternal:true}}]];
footer.text.style={typeface:'Tahoma',fontSize:21,bold:true,color:'#145B43'};
s.speakerNotes.text=`เวลาพูด30วินาที\nผลquery10รหัสจับคู่sample_id/UTCตรงแถวเดียว เฉลี่ย3.091sสูงสุด3.275s uncertainty18.7ms ไม่รวมbrowserpaint DB657รหัสคือเฉพาะที่observerรับได้ ไม่ใช้แทนcapturesทั้งboot\nภาพ24h ณ ${latest.captured_bangkok} UTC+7 ตรวจไปแล้ว${(latest.observed_hours*60).toFixed(2)}นาที รับสด${latest.samples} gap${latest.gaps} disconnect${latest.disconnects} status=${latest.status} continuity_pass=${latest.continuity_pass}; ยังไม่ครบ24h\nช่วงสลับเครือข่ายเข้าคิวไม่ได้26 และbootรุ่นก่อน dropped64ไม่ลบผลเดิม\nภาพประกอบเป็นรายงานจากJSON ไม่ใช่ screenshotGrafana/ภาพบอร์ดจริง ช่องวิดีโอยังเว้นไว้ให้ใส่ของจริง ลิงก์หลักฐานใช้โฟลเดอร์ข้างชุดสไลด์; Grafanaต้องbackendทำงานและบัญชีเดิม\nหลักฐาน: presentation_evidence/${full.folder}/02_query_latency.png, presentation_evidence/${latest.folder}/01_soak.png และmanifest/hashของแต่ละโฟลเดอร์\nเกณฑ์ประเมิน: https://github.com/cchantra/IoT-Lab/wiki/Week%E2%80%904%E2%80%90Project%E2%80%90Proposal%E2%80%90Rubric`;
const after=await p.inspect({select:'$.slides[*]',include:['id','index','title','elements.id','elements.kind','elements.text','notes.text']});
await fs.writeFile(path.join(build,'after-inspect.ndjson'),after.ndjson);
const draft=path.join(build,'candidate.pptx');await(await PresentationFile.exportPptx(p)).save(draft);
const final=path.join(output,'KU_Watch_ตามเกณฑ์ประเมิน_25691010_v3.pptx');
await finalizePresentation({workspaceDir:root,candidatePath:draft,finalPath:final,
 pythonExecutable:path.join(runtime,'python/python.exe'),integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...[3,6,7,8,10,12,13].flatMap(n=>['--require-native-table-slide',String(n)])],
 fontPolicy:{basis:'reference',families:['Tahoma'],referencePath:source,referenceSha256:sourceHash},explicitTotalSlideCount:14,requiredNativeTableOwnerSlides:[3,6,7,8,10,12,13],verifyArtifactToolImport:true,receiptPath:path.join(build,'validation.json')});
for(let i=0;i<p.slides.items.length;i++){const png=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(path.join(build,'after-'+String(i+1).padStart(2,'0')+'.png'),new Uint8Array(await png.arrayBuffer()));}
await fs.writeFile(path.join(build,'evidence_used.json'),JSON.stringify({source:sourceHash,latest_soak:latest,query_snapshot:full},null,2));
console.log(JSON.stringify({file:final,slides:14,query_evidence:full.folder,soak_evidence:latest.folder}));
