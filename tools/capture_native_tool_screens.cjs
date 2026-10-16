// Screenshots of the actual localhost tools, not generated report pages.
// Browser automation fallback: this session has no Windows node_repl / sky tool.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),base=path.join(root,'output/presentation_evidence/actual_tools');
const at=new Date(),stamp=at.toISOString().replace(/[-:]/g,'').replace(/\.\d{3}Z$/,'Z');
const folder=path.join(base,stamp);fs.mkdirSync(folder,{recursive:true});
const manifest={started_utc:at.toISOString(),type:'ACTUAL_TOOL_SCREENSHOTS',boundary:'Native Node-RED editor and Grafana pages, plus actual InfluxDB SQL API response in a browser. No image generation, fake data or changed backend settings. Images do not prove all requirements passed.',images:[],results:{}};
const thai=utc=>new Intl.DateTimeFormat('th-TH',{timeZone:'Asia/Bangkok',dateStyle:'long',timeStyle:'medium'}).format(new Date(utc));
function save(){fs.writeFileSync(path.join(folder,'manifest.json'),JSON.stringify(manifest,null,2));fs.writeFileSync(path.join(base,'active.json'),JSON.stringify({pid:process.pid,folder:stamp,status:manifest.status,updated_utc:new Date().toISOString()},null,2));}
async function shot(page,name,caption,extra={}){
 const captured=new Date().toISOString(),file=name+'.png';await page.screenshot({path:path.join(folder,file),fullPage:false});
 manifest.images.push({file,captured_utc:captured,captured_thai:thai(captured),url:page.url(),title:await page.title(),caption,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(folder,file))).digest('hex'),...extra});save();
}
async function main(){
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1600,height:1000},deviceScaleFactor:1});
  const page=await context.newPage();await page.goto('http://127.0.0.1:1880/',{waitUntil:'networkidle',timeout:20000});
  const response=await page.request.get('http://127.0.0.1:1880/flows');
  if(response.ok()){
   const value=await response.json(),flows=Array.isArray(value)?value:value.flows;
   const tabs=flows.filter(n=>n.type==='tab').map(n=>({id:n.id,label:n.label}));manifest.results.node_red_tabs=tabs;
   const watch=tabs.filter(t=>/ku.?watch|hivemq|influx|sensor/i.test(t.label));
   if(watch.length===1){await page.goto('http://127.0.0.1:1880/#flow/'+watch[0].id);await page.waitForTimeout(1500);}
  }
  console.log(JSON.stringify({node_red_tabs:manifest.results.node_red_tabs,page:page.url()}));
  await shot(page,'01_nodered','Node-RED editor จริง แสดง flow และสถานะ node ขณะรับข้อมูล ไม่ได้กด Deploy หรือเปลี่ยน flow');
  await context.close();
  const config=fs.readFileSync(path.join(root,'include/config.h'),'utf8');const token=/INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"/.exec(config)?.[1];
  if(!token)throw Error('InfluxDB credential not configured');
  const influx=await browser.newContext({viewport:{width:1600,height:1000},extraHTTPHeaders:{Authorization:'Bearer '+token}});
  await influx.route('**/*',route=>new URL(route.request().url()).origin==='http://127.0.0.1:8181'?route.continue():route.abort());
  const p=await influx.newPage();
  const queries=[
   ['02_influx_counts',"SELECT COUNT(*) AS stored_rows, COUNT(DISTINCT sample_id) AS unique_samples, MIN(time) AS first_utc, MAX(time) AS last_utc FROM ku_watch WHERE time >= now() - INTERVAL '15 minutes'",'ผล SELECT จริงจาก InfluxDB 3 Core ในช่วง 15 นาที แสดงจำนวนแถวและรหัสไม่ซ้ำ Core นี้ใช้ SQL API ไม่ได้ติดตั้ง Explorer UI'],
   ['03_influx_records',"SELECT time, sample_id, temp, humidity, iaq, battery_voltage FROM ku_watch ORDER BY time DESC LIMIT 3",'ตัวอย่าง 3 แถวล่าสุดจาก InfluxDB จริง พร้อมเวลาและ sample_id ไม่รวมพิกัดหรือ PPG ดิบ'],
  ];
  for(const [name,query,caption] of queries){
   const url='http://127.0.0.1:8181/api/v3/query_sql?'+new URLSearchParams({db:'iot',q:query,format:'json'});
   const result=await p.goto(url,{waitUntil:'domcontentloaded',timeout:20000});if(!result.ok())throw Error('Influx query HTTP '+result.status());
   const body=await result.text();const parsed=JSON.parse(body);fs.writeFileSync(path.join(folder,name+'.json'),JSON.stringify(parsed,null,2));fs.writeFileSync(path.join(folder,name+'.sql'),query+'\n');
   // Browser zoom only, with all response bytes retained unchanged above.
   await p.locator('body').evaluate(el=>{el.style.zoom='150%';});
   await shot(p,name,caption,{sql:query,response_file:name+'.json',response_sha256:crypto.createHash('sha256').update(body).digest('hex')});
  }
  await influx.close();
 }finally{await browser.close();}
 const profile=path.join(base,'.browser-private');
 const grafana=await chromium.launchPersistentContext(profile,{executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:false,viewport:{width:1600,height:1000},args:['--window-size=1640,1100']});
 try{
  const page=grafana.pages()[0]||await grafana.newPage();
  const live='http://127.0.0.1:3000/d/ku-watch-live?from=now-15m&to=now&timezone=Asia%2FBangkok&refresh=1s';
  await page.goto(live,{waitUntil:'domcontentloaded',timeout:20000});
  if(new URL(page.url()).pathname.startsWith('/login')){
   manifest.status='waiting_for_user_grafana_login';save();console.log(JSON.stringify({status:manifest.status,folder,login_window_open:true}));
   const deadline=Date.now()+10*60*1000;
   while(new URL(page.url()).pathname.startsWith('/login') && Date.now()<deadline)await page.waitForTimeout(1000);
   if(new URL(page.url()).pathname.startsWith('/login')){manifest.status='needs_login';save();return;}
   await page.goto(live,{waitUntil:'domcontentloaded',timeout:20000});
  }
  await page.waitForTimeout(6000);
  manifest.results.grafana_live_title=await page.title();
  manifest.results.grafana_panel_titles=await page.locator('[data-testid*="panel-header"]').allTextContents();
  await shot(page,'04_grafana_live','Grafana dashboard สดจากระบบจริง ณ เวลาจับภาพ ไม่ใช่ dashboard DEMO และไม่ใช้ภาพนี้รับรอง latency หรือ 24 ชั่วโมง');
  const rootScroll=page.locator('[data-testid="data-testid Dashboard page"]');
  await page.evaluate(()=>{const roots=[document.scrollingElement,...document.querySelectorAll('div')].filter(e=>e&&e.scrollHeight>e.clientHeight+200&&e.clientHeight>300);for(const e of roots)e.scrollTop=e.scrollHeight;});
  await page.waitForTimeout(1200);await shot(page,'05_grafana_live_lower','ส่วนล่างของ Grafana สดจากข้อมูลจริง ไม่ได้เปลี่ยนค่าหรือข้อมูล');
  await page.goto('http://127.0.0.1:3000/d/ku-watch-real-evidence?from=now-24h&to=now&timezone=Asia%2FBangkok',{waitUntil:'domcontentloaded',timeout:20000});
  await page.waitForTimeout(4000);
  await shot(page,'06_grafana_recorded_evidence','Grafana แสดงหลักฐานชุดจริงที่บันทึกไว้วันที่ 10 ต.ค. ขอบเขต 657 รหัสและ query latency 10 รหัส เป็นผลเก่าของชุดที่ระบุ ไม่ใช่ผลสดครบ 24 ชั่วโมง');
  manifest.status='captured';save();
 }finally{await grafana.close();}
 fs.writeFileSync(path.join(folder,'คำอธิบายภาพ.md'),'# ภาพหน้าจอโปรแกรมจริง\n\n'+manifest.images.map(i=>`- ${i.file}\n  เวลาไทย ${i.captured_thai}\n  ${i.caption}\n  URL ${i.url}\n`).join('\n')+'\nไฟล์ .browser-private เป็น profile สำหรับลงชื่อเข้าใช้ ไม่ใช่ไฟล์ส่งมอบและห้ามใส่ในชุดภาพ\n');
 console.log(JSON.stringify({status:manifest.status,folder,images:manifest.images.length}));
}
main().catch(e=>{manifest.status='capture_error';manifest.error=e.message;save();console.error(e.message);process.exitCode=1;});
