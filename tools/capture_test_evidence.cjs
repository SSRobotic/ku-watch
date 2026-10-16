// Render local evidence reports from real JSON. No browser session or sensor state is changed.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');
const {performance}=require('node:perf_hooks');
const root=path.resolve(__dirname,'..'),args=process.argv.slice(2);
const option=(name,fallback)=>args.includes(name)?args[args.indexOf(name)+1]:fallback;
const follow=args.includes('--follow'),interval=Number(option('--interval','300'));
const auditPid=Number(option('--audit-pid','0'));
if(!Number.isFinite(interval)||interval<30||interval>3600)throw Error('Interval must be 30..3600 seconds');
if(follow&&(!Number.isSafeInteger(auditPid)||auditPid<=0))throw Error('An audit PID is required');
const out=path.join(root,'output/presentation_evidence'),audit=path.join(root,'output/soak_audit/status.json');
const evidence=path.join(root,'output/requirements_audit_20261009');
fs.mkdirSync(out,{recursive:true});
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const digest=b=>crypto.createHash('sha256').update(b).digest('hex');
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const thaiTime=t=>new Intl.DateTimeFormat('th-TH-u-ca-gregory',{timeZone:'Asia/Bangkok',year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).format(new Date(t));
const elapsed=s=>{s=Math.max(0,Math.floor(s));return [Math.floor(s/3600),Math.floor(s%3600/60),s%60].map(v=>String(v).padStart(2,'0')).join(':');};
const stamp=t=>{const p=new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Bangkok',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).format(new Date(t));return p.replace(/[^\d]/g,'');};
const atomic=(p,data)=>{fs.writeFileSync(p+'.tmp',data);fs.renameSync(p+'.tmp',p);};
const loadPlaywright=()=>{
 try{return require('playwright');}catch{}
 const bundled=path.join(process.env.USERPROFILE||'','\.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
 return require(bundled);
};
const style=`*{box-sizing:border-box}body{margin:0;background:#eff3f8;color:#16324b;font-family:Tahoma,Arial,sans-serif}.slide{width:1600px;height:900px;padding:54px 64px;position:relative;background:#eff3f8}.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:15px}.brand{font-weight:bold;letter-spacing:3px;font-size:23px;color:#166f62}.stamp{font-size:21px}.title{font-size:43px;font-weight:bold;margin:14px 0 9px;line-height:1.3}.sub{font-size:22px;color:#526b7f;margin-bottom:25px;line-height:1.6}.banner{border-radius:14px;padding:15px 22px;font-size:25px;background:#fff0c2;color:#70531a;margin-bottom:23px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}.metric{background:white;border-radius:16px;padding:22px 23px;box-shadow:0 3px 10px #18334b09}.value{font-size:46px;font-weight:bold;margin-bottom:8px}.label{font-size:21px;line-height:1.5;color:#526b7f}.panel{background:white;border-radius:16px;padding:24px;margin-top:20px;font-size:24px;line-height:1.7}.bar{height:22px;background:#dce5ed;border-radius:12px;overflow:hidden;margin:18px 0}.fill{height:100%;background:#166f62}.foot{position:absolute;left:64px;right:64px;bottom:28px;font-size:17px;line-height:1.6;color:#536a7f;border-top:1px solid #ced9e3;padding-top:11px}.green{color:#166f62}.red{color:#a03129}.split{display:grid;grid-template-columns:1.5fr 1fr;gap:20px}.rows{display:grid;gap:14px}.row{background:white;padding:17px 22px;border-radius:12px;font-size:23px;display:flex;justify-content:space-between;gap:20px}.row small{font-size:18px;color:#536a7f}.small{font-size:21px}.nowrap{white-space:nowrap}`;
const layout=`.panel{padding:22px;font-size:23px;line-height:1.55;overflow-wrap:anywhere}.split{grid-template-columns:minmax(0,1.5fr) minmax(0,1fr)}.split .panel{padding:20px;font-size:20px;line-height:1.5;min-width:0}.rows{gap:12px}.row{padding:15px 22px}`;
function shell(title,sub,body,now,source){return `<!doctype html><html lang="th"><meta charset="utf-8"><style>${style}${layout}</style><body><main class="slide"><div class="top"><div class="brand">KU WATCH · TEST EVIDENCE</div><div class="stamp">สร้างภาพ ${escape(thaiTime(now))} · UTC+7</div></div><h1 class="title">${escape(title)}</h1><div class="sub">${sub}</div>${body}<footer class="foot">ภาพสรุปจากผล JSON จริง ไม่ใช่ภาพหน้าจอ Grafana หรือภาพถ่ายบอร์ด<br>${source}</footer></main></body></html>`;}
const metric=(value,label,cls='')=>`<div class="metric"><div class="value ${cls}">${escape(value)}</div><div class="label">${escape(label)}</div></div>`;
const sourceLabel=(name,snapshot)=>`${escape(name)} · SHA256 ${snapshot.sources[name].sha256.slice(0,16)}…`;
function soakPage(s,now,snapshot){
 const seconds=s.observed_hours*3600,remaining=Math.max(0,s.target_hours*3600-seconds);
 const badge=s.status==='running'?'กำลังตรวจ · ยังไม่ผ่าน 24 ชั่วโมง':s.continuity_pass?'ครบเวลาและผ่านเงื่อนไขความต่อเนื่อง':'รอบจบแล้ว · ยังไม่ผ่านเงื่อนไขความต่อเนื่อง';
 const stale=(now-Date.parse(s.last_sample_utc||s.started_utc))/1000;
 const body=`<div class="banner">${escape(badge)} · สถานะ ${escape(s.status)}${stale>20?' · ข้อมูลล่าสุดเก่า '+Math.floor(stale)+' วินาที':''}</div><div class="grid">${metric(elapsed(seconds),'ตรวจไปแล้ว (ชั่วโมง:นาที:วินาที)')}${metric(elapsed(remaining),'เหลือถึงเป้าหมาย 24 ชั่วโมง')}${metric(s.samples.toLocaleString('en-US'),'รายการสดที่รับจริง')}${metric(s.gaps,'เหตุการณ์ลำดับสดขาด',s.gaps?'red':'green')}</div><div class="panel"><b>เริ่ม ${escape(thaiTime(s.started_utc))} · เป้าหมาย ${s.target_hours} ชั่วโมง</b><div class="bar"><div class="fill" style="width:${Math.min(100,s.observed_hours/s.target_hours*100)}%"></div></div>ช่วงรับสูงสุด ${(s.max_receive_gap_ms/1000).toFixed(3)} วินาที · reader disconnect ${s.disconnects} · malformed ${s.malformed}<br>MQTT ส่งซ้ำที่ข้ามแล้ว ${s.duplicates} · ข้อมูลย้อนหลังในรอบนี้ ${s.backfill_samples}<br><span class="small">หนึ่ง boot = ${s.sessions} session · ข้อมูลล่าสุด ${escape(thaiTime(s.last_sample_utc||s.started_utc))}<br>ฮอตสปอตมือถือ SS / 2.4 GHz · Windows hotspot ปิดตามผลตรวจล่าสุด · Watch 2.0.8 / Hub 1.0.5<br>ช่วงสลับเครือข่ายเข้าคิวไม่ได้ 26 รายการเป็น baseline แยก · USB ไม่แทนผลแบต 6 ชั่วโมง</span></div>`;
 return shell('ความต่อเนื่อง MQTT — รอบมือถือ 24 ชั่วโมง','เวลาที่ตรวจใช้ monotonic clock · วันเวลาแสดง Asia/Bangkok · ภาพแต่ละรอบเก็บแยก',body,now,sourceLabel('soak_status.json',snapshot));
}
function latencyPage(d,now,snapshot,window){
 const uncertainty=d.reference_uncertainty_ms;
 const max=Math.max(...d.samples.map(s=>s.reference_corrected_delay_ms));
 const rows=d.samples.map((s,i)=>{const v=s.reference_corrected_delay_ms/1000,y=16+i*24;return `<text x="0" y="${y+17}" font-size="18" fill="#526b7f">${escape(s.sample_id.slice(-8))}</text><rect x="115" y="${y}" width="${v/6*570}" height="20" rx="5" fill="#166f62"/><text x="${125+v/6*570}" y="${y+17}" font-size="18" fill="#16324b">${v.toFixed(3)}s</text>`;}).join('');
 const plot=`<svg width="100%" height="285" viewBox="0 0 820 285"><line x1="590" y1="15" x2="590" y2="260" stroke="#a03129" stroke-dasharray="5 5" stroke-width="2"/><text x="600" y="17" fill="#a03129" font-size="18">เกณฑ์ 5s</text>${rows}<text x="115" y="280" font-size="18">0</text><text x="580" y="280" font-size="18">5 วินาที</text></svg>`;
 const body=`<div class="banner">${d.within_5s?'ผ่าน ≤5 วินาที เฉพาะถึงผลตอบกลับ query':'ยังไม่ผ่านเกณฑ์ query'} · ยังไม่ได้วัดภาพปรากฏบน browser</div><div class="grid">${metric((d.corrected_mean_ms/1000).toFixed(3)+'s','เฉลี่ยหลังชดเชยเวลาคอม')}${metric((max/1000).toFixed(3)+'s','สูงสุดจากตัวอย่างจริง')}${metric(d.measured,'รหัสที่จับคู่ตรงทั้ง ID และ UTC')}${metric(uncertainty.toFixed(1)+'ms','ความไม่แน่นอน clock reference')}</div><div class="split"><div class="panel" style="padding:12px 20px">${plot}</div><div class="panel small">ช่วงเวลาวัด ${escape(window)}<br><br>ทุกแท่งมาจากรหัส capture จริง<br>UTC ต้นทางละเอียด 1 วินาที<br><br>รวม clock uncertainty ก่อนเทียบเกณฑ์<br>ไม่รวม browser refresh / paint<br>จึงยังไม่ปิดข้อ NFR-03 ทั้งข้อ</div></div>`;
 return shell('ความหน่วงถึง Grafana query — 10 ตัวอย่างจริง','ผลรอบมือถือที่บันทึกไว้ · กราฟนี้ไม่ได้สร้างข้อมูลทดสอบในระบบ',body,now,sourceLabel('grafana_latency_phone_20261010.json',snapshot));
}
function dbPage(d,live,now,snapshot,window){
 const body=`<div class="banner">${d.passed?'รหัสในชุดที่ตรวจ พบในฐานข้อมูลครบอย่างละหนึ่งแถว':'ชุดที่ตรวจยังไม่ครบ'} · ช่วงทดสอบ ${escape(window)}</div><div class="grid">${metric(d.observed,'รหัสรับจริงที่นำไปตรวจ')}${metric(d.stored_once,'พบในฐานข้อมูลหนึ่งแถวต่อรหัส','green')}${metric(d.missing.length,'รหัสในชุดที่ตรวจแล้วยังไม่พบ')}${metric(d.duplicates.length,'รหัสซ้ำในฐานข้อมูล')}</div><div class="panel"><b>ข้อมูลสดใน observer รอบเดียวกัน</b><br>${live.live} รหัส · ${(live.observed_s/60).toFixed(2)} นาที · sequence gaps ${live.sequence_gaps.length}<br>ช่วงรับสูงสุด ${(live.max_receive_gap_ms/1000).toFixed(3)} วินาที · หนึ่ง boot = ${live.sessions} session<br><br><span class="small">657 รหัสรวมทั้งข้อมูลสดและย้อนหลัง เป็นขอบเขตที่ observer รับได้จริง<br>ไม่แทนหลักฐานว่าทุก capture ตลอด boot ไม่หาย ช่วงสลับเครือข่ายเข้าคิวไม่ได้ 26 รายการ<br>ผล DB นี้เป็นรอบสั้นที่บันทึกไว้ ไม่ใช่ผลครบ 24 ชั่วโมง</span></div>`;
 return shell('MQTT → InfluxDB — ตรวจรหัสจริงครบชุด','ตรวจ actual sample_id และเวลาวัดเดิม · การส่งซ้ำใช้จุดเดิมในฐานข้อมูล',body,now,sourceLabel('phone_drain_database_20261010.json',snapshot)+'<br>'+sourceLabel('live_phone_20261010.json',snapshot));
}
function pendingPage(s,now,snapshot){
 const rows=[['MQTT ต่อเนื่อง 24 ชั่วโมง',s.status==='running'?'กำลังตรวจ '+elapsed(s.observed_hours*3600):s.status+' · '+elapsed(s.observed_hours*3600)],['กราฟแสดงบน browser / ทัช ≤300ms','ยังไม่ได้วัดภาพจริงและเวลาแตะ'],['INA226 / ความแม่นยำเซ็นเซอร์','กระแสยังไม่สอบเทียบ · ต้องเทียบเครื่องมือ'],['แบตเต็ม 6 ชั่วโมง / RTC backup','ยังไม่ได้ทดสอบครบ · RTC backup ยังไม่ยืนยัน'],['WALK / GPS / เข็มทิศ','ต้องเดินบันทึกและเทียบเส้นทางจริง'],['FR-06 เตือนจากค่าใหม่ 3 รอบ ≤5s','fixture ผ่าน · ฮาร์ดแวร์จริงยังไม่ผ่านข้อทั้งหมด'],['OTA อัตโนมัติ / ตัดไฟ 3 ครั้ง','ไฟล์เตรียมแล้ว · ปลายทางถูกปฏิเสธในรอบก่อน'],['ชื่อสมาชิก / ราคา / ภาพและวิดีโอบอร์ด','เว้นช่องไว้ให้เติมตามผู้ใช้ร้องขอ']];
 return shell('งานที่ยังต้องมีหลักฐานตอนนำเสนอ','แยกผลโค้ด ผลตรวจจริง และการทดสอบที่ยังข้ามไว้ · ไม่เติมผลผ่านให้ขั้นที่ยังไม่ได้ทำ',`<div class="rows">${rows.map(([a,b])=>`<div class="row"><b>${escape(a)}</b><span>${escape(b)}</span></div>`).join('')}</div>`,now,sourceLabel('soak_status.json',snapshot)+' · รายการคงเหลือตามเอกสารส่งมอบ');
}
async function capture(browser,allPages){
 const now=Date.now(),s=read(audit);
 if(auditPid&&s.pid!==auditPid)throw Error('Audit PID changed; old evidence collector will not attach to a new run');
 const folderName=stamp(now)+'_'+s.status,folder=path.join(out,folderName);fs.mkdirSync(folder);
 const snapshot={captured_utc:new Date(now).toISOString(),captured_bangkok:thaiTime(now),timezone:'Asia/Bangkok',audit_pid:s.pid,status:s.status,observed_hours:s.observed_hours,samples:s.samples,gaps:s.gaps,disconnects:s.disconnects,continuity_pass:s.continuity_pass,baseline_dropped:26,sources:{},images:[],boundary:'Rendered evidence reports from saved real JSON; not hardware photographs, Grafana screenshots, or browser-paint measurements'};
 function copy(name,source){const b=fs.readFileSync(source);fs.writeFileSync(path.join(folder,name),b);snapshot.sources[name]={sha256:digest(b),bytes:b.length,source:path.relative(root,source).replaceAll('\\','/'),file_saved_utc:fs.statSync(source).mtime.toISOString()};}
 copy('soak_status.json',audit);
 // Use the exact bytes copied into this snapshot, so the displayed status and hash cannot race.
 const copied=read(path.join(folder,'soak_status.json'));
 Object.assign(snapshot,{status:copied.status,observed_hours:copied.observed_hours,samples:copied.samples,gaps:copied.gaps,disconnects:copied.disconnects,continuity_pass:copied.continuity_pass});
 const pages=[['01_soak',soakPage(copied,now,snapshot)]];
 if(allPages){
  for(const n of ['grafana_latency_phone_20261010.json','clock_reference_phone_20261010.json','phone_drain_database_20261010.json','live_phone_20261010.json','replay_phone_drain_20261010.json','network_phone_evidence_20261010.json','phone_network_transition_20261010.json'])copy(n,path.join(evidence,n));
  const latency=read(path.join(folder,'grafana_latency_phone_20261010.json')),db=read(path.join(folder,'phone_drain_database_20261010.json')),live=read(path.join(folder,'live_phone_20261010.json'));
  const replay=read(path.join(folder,'replay_phone_drain_20261010.json')),byId=new Map(replay.samples.map(x=>[x.id,x.timestamp]));
  const latTimes=latency.samples.map(x=>byId.get(x.sample_id));
  const window=latTimes.every(Number.isFinite)?thaiTime(Math.min(...latTimes)*1000)+' – '+thaiTime(Math.max(...latTimes)*1000):'ดูไฟล์ผลตรวจประกอบ';
  const replayWindow=thaiTime(Math.min(...replay.samples.map(x=>x.at)))+' – '+thaiTime(Math.max(...replay.samples.map(x=>x.at)));
  pages.push(['02_query_latency',latencyPage(latency,now,snapshot,window)],['03_database',dbPage(db,live,now,snapshot,replayWindow)],['04_remaining',pendingPage(copied,now,snapshot)]);
 }
 const context=await browser.newContext({viewport:{width:1600,height:900},deviceScaleFactor:1});
 // Only our local generated report files are rendered. No cloud or logged-in page is visited.
 await context.route('**/*',route=>{const url=route.request().url();return url.startsWith(pathToFileURL(folder).href)||url.startsWith('data:')?route.continue():route.abort();});
 try{for(const [name,html] of pages){
  const page=await context.newPage(),p=path.join(folder,name+'.html');fs.writeFileSync(p,html);
  await page.goto(pathToFileURL(p).href);await page.evaluate(()=>document.fonts.ready);
  if(await page.evaluate(()=>{const foot=document.querySelector('.foot').getBoundingClientRect();return document.body.scrollWidth>1600||foot.bottom>900||[...document.querySelectorAll('.panel,.rows,.grid,.banner')].some(e=>{const b=e.getBoundingClientRect();return b.right>1536.5||b.bottom>foot.top-5;});}))throw Error('Evidence image layout exceeded the canvas or overlapped the source footer');
  const image=path.join(folder,name+'.png');await page.screenshot({path:image});
  snapshot.images.push({file:name+'.png',sha256:digest(fs.readFileSync(image))});await page.close();
 }}finally{await context.close();}
 snapshot.layout_verified=true;
 fs.writeFileSync(path.join(folder,'manifest.json'),JSON.stringify(snapshot,null,2));
 fs.appendFileSync(path.join(out,'timeline.jsonl'),JSON.stringify({folder:folderName,...snapshot})+'\n');
 const image=fs.readFileSync(path.join(folder,'01_soak.png'));atomic(path.join(out,'latest_soak.png'),image);
 atomic(path.join(out,'latest.json'),JSON.stringify({folder:folderName,...snapshot},null,2));
 const history=fs.readFileSync(path.join(out,'timeline.jsonl'),'utf8').trim().split('\n').map(JSON.parse).filter(x=>x.layout_verified).reverse();
 const firstFull=history.find(x=>x.images.length>1);
 const links=firstFull?firstFull.images.map(x=>`<a href="${firstFull.folder}/${x.file}">${escape(x.file)}</a>`).join(' · '):'';
 const gallery=firstFull?firstFull.images.slice(1).map(x=>`<article><h2>${escape(x.file)}</h2><p>ภาพผลรอบที่บันทึกไว้ ณ ${escape(firstFull.captured_bangkok)} · UTC+7</p><img src="${firstFull.folder}/${x.file}"></article>`).join(''):'';
 const mediaDir=path.join(out,'media');fs.mkdirSync(mediaDir,{recursive:true});
 const media=fs.readdirSync(mediaDir).filter(n=>/\.(png|jpe?g|mp4|webm|mov)$/i.test(n)).map(n=>`<article><p>${escape(n)} · เวลาและเงื่อนไขทดสอบให้ดูบันทึกภาพจริงประกอบ</p>${/\.(png|jpe?g)$/i.test(n)?`<img src="media/${encodeURIComponent(n)}">`:`<video controls style="max-width:100%" src="media/${encodeURIComponent(n)}"></video>`}</article>`).join('')||'<p>ยังไม่มีภาพ/วิดีโอบอร์ดจริงในโฟลเดอร์ media</p>';
 atomic(path.join(out,'index.html'),`<!doctype html><html lang="th"><meta charset="utf-8"><meta http-equiv="refresh" content="60"><title>KU Watch — หลักฐานพร้อมเวลา</title><style>body{font-family:Tahoma,Arial;margin:35px auto;max-width:1200px;background:#eff3f8;color:#16324b}a{color:#166f62}img{max-width:100%;border-radius:12px}article{background:white;padding:22px;margin:22px 0;border-radius:14px}p{line-height:1.7}table{width:100%;border-collapse:collapse}td,th{padding:10px;text-align:left;border-bottom:1px solid #ddd}</style><h1>KU Watch — หลักฐานพร้อมเวลาไทย</h1><p>ภาพสรุปจากผล JSON จริง ไม่ใช่ภาพหน้าจอ Grafana/ภาพบอร์ดจริง รอบที่กำลังตรวจยังไม่ถือว่าผ่าน 24 ชั่วโมง<br>ตัวเก็บภาพโหมด follow ตั้งทุก ${interval/60} นาทีขณะโปรแกรมและคอมทำงาน หยุดเมื่อ audit รอบนี้จบ ไม่เริ่ม audit ใหม่เอง<br>ไฟล์แต่ละภาพมี JSON ต้นทางและ SHA256 ใน manifest ประกอบ ${links}</p><img src="${folderName}/01_soak.png">${gallery}<h2>ประวัติภาพ</h2><table><tr><th>เวลาเก็บ (UTC+7)</th><th>ตรวจไปแล้ว</th><th>รายการสด</th><th>สถานะ</th><th>หลักฐาน</th></tr>${history.map(x=>`<tr><td>${escape(x.captured_bangkok)}</td><td>${elapsed(x.observed_hours*3600)}</td><td>${x.samples}</td><td>${escape(x.status)} / gaps ${x.gaps}</td><td><a href="${x.folder}/01_soak.png">ภาพ</a> · <a href="${x.folder}/manifest.json">JSON/hash</a></td></tr>`).join('')}</table><h2>ภาพและวิดีโอบอร์ดจริง</h2>${media}<p>เก็บไว้ใน media/ และเติมคำอธิบายวันเวลาใน media/บันทึกภาพจริง.md · โปรแกรมไม่อ้างเวลาแก้ไฟล์ว่าเป็นเวลาถ่าย</p></html>`);
 console.log(JSON.stringify({folder:folderName,status:copied.status,samples:copied.samples,observed_hours:copied.observed_hours,images:snapshot.images.length}));
 return copied;
}
async function main(){
 const lock=path.join(out,'collector.json');
 if(follow&&fs.existsSync(lock)){const previous=read(lock);let alive=true;try{process.kill(previous.pid,0);}catch(e){if(e.code==='ESRCH')alive=false;else throw e;}if(alive)throw Error('An evidence collector is already running');}
 const initial=read(audit);if(auditPid&&initial.pid!==auditPid)throw Error('Requested audit PID does not match');
 if(follow){if(initial.status!=='running')throw Error('Audit is not running');fs.writeFileSync(lock,JSON.stringify({pid:process.pid,audit_pid:auditPid,interval_seconds:interval,started_utc:new Date().toISOString()}));}
 const {chromium}=loadPlaywright(),edge=option('--browser','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe');
 let browser;
 try{
  browser=await chromium.launch({executablePath:edge,headless:true});
  let s=await capture(browser,true);
  const followDeadline=performance.now()+Math.max(60,(s.target_hours-s.observed_hours)*3600+60)*1000;
  while(follow&&s.status==='running'){
   // A bounded follower of this specific audit; no reboot, serial port, or audit restart.
   const until=performance.now()+interval*1000;
   while(performance.now()<until){
    await new Promise(r=>setTimeout(r,Math.max(1,Math.min(10000,until-performance.now()))));
    const next=read(audit);if(next.pid!==auditPid)throw Error('Audit changed');if(next.status!=='running')break;
    if(performance.now()>followDeadline)throw Error('Evidence collector reached the original audit time limit; no audit result was changed');
    try{process.kill(auditPid,0);}catch(e){if(e.code==='ESRCH')throw Error('Audit process disappeared while status was still running; collector stopped without inventing a final result');throw e;}
   }
   s=await capture(browser,false);
  }
 }finally{if(browser)await browser.close();if(follow&&fs.existsSync(lock)&&read(lock).pid===process.pid)fs.unlinkSync(lock);}
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
