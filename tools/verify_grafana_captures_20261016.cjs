// Read-only recapture after the actual Grafana query finishes, with refresh off.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),dir=path.join(root,'output/ppt_academic_20261016/build/dashboard_verified');fs.mkdirSync(dir,{recursive:true});
const original=JSON.parse(fs.readFileSync(path.join(root,'output/ppt_academic_20261016/build/dashboard/manifest.json'),'utf8'));
const report=process.argv.length===2&&fs.existsSync(path.join(dir,'manifest.json'))?JSON.parse(fs.readFileSync(path.join(dir,'manifest.json'),'utf8')):{started_utc:new Date().toISOString(),boundary:'Real browser capture of every panel. Refresh disabled for the capture only; dashboard definition and data unchanged. Capture waits for the actual query to finish.',panels:[],pages:original.pages};
(async()=>{const ctx=await chromium.launchPersistentContext(path.join(root,'output/presentation_evidence/actual_tools/.capture-private'),{executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,viewport:{width:1600,height:1000}});try{
const page=ctx.pages()[0]||await ctx.newPage();
const selected=process.argv.slice(2).map(Number);
for(const panel of original.panels.filter(p=>(!selected.length||selected.includes(p.panel_id))&&!report.panels.some(x=>x.panel_id===p.panel_id))){
 await page.setViewportSize(panel.type==='timeseries'?{width:1600,height:1000}:{width:900,height:510});
 const url=panel.url.replace(/&kiosk.*$/,'')+'&refresh=&kiosk';
 const queries=[];page.on('response',response=>{if(response.url().includes('/api/ds/query'))queries.push({status:response.status(),at:new Date().toISOString()});});
 const done=page.waitForResponse(r=>r.url().includes('/api/ds/query'),{timeout:20000}).catch(()=>null);
 await page.goto(url,{waitUntil:'domcontentloaded',timeout:25000});
 const response=await done;if(response)await response.finished();
 const refresh=page.getByRole('button',{name:/Choose refresh time interval/});
 if(await refresh.count()){
   await refresh.click();
   const off=page.getByText('Off',{exact:true});
   if(await off.count())await off.last().dispatchEvent('click');else if(selected.length)console.log('No Off option');
 }else if(selected.length)console.log(JSON.stringify(await page.getByRole('button').evaluateAll(xs=>xs.map(x=>({label:x.getAttribute('aria-label'),text:x.innerText})))));
 await page.waitForTimeout(1800);
 await page.getByRole('button',{name:'Cancel',exact:true}).waitFor({state:'hidden',timeout:15000}).catch(()=>{});
 const body=await page.locator('body').innerText();if(/Sign in to Grafana/.test(body))throw Error('Grafana login required');
 await page.screenshot({path:path.join(dir,panel.file),fullPage:false});
 report.panels.push({...panel,url:page.url(),captured_utc:new Date().toISOString(),viewport:page.viewportSize(),query_responses:queries,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(dir,panel.file))).digest('hex'),visual_review:'pending'});
 page.removeAllListeners('response');
 fs.writeFileSync(path.join(dir,'manifest.json'),JSON.stringify(report,null,2));
 if(report.panels.length%10===0)console.log(JSON.stringify({captured:report.panels.length}));
}
report.status='completed';report.finished_utc=new Date().toISOString();fs.writeFileSync(path.join(dir,'manifest.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({status:report.status,count:report.panels.length}));
}finally{await ctx.close();}})().catch(e=>{console.error(e.message);process.exitCode=1;});
