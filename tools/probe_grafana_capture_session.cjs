const {chromium}=require('C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path=require('path'),fs=require('fs');
const root=path.resolve(__dirname,'..');
const base=path.join(root,'output/presentation_media_20261016');
(async()=>{for(const name of ['.capture-private','.browser-private']){
 const profile=path.join(root,'output/presentation_evidence/actual_tools',name);if(!fs.existsSync(profile))continue;
 let ctx;try{ctx=await chromium.launchPersistentContext(profile,{executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,viewport:{width:1600,height:1000}});
 const pg=ctx.pages()[0]||await ctx.newPage();await pg.goto('http://127.0.0.1:3000/d/ku-watch-live?from=now-5m&to=now&timezone=Asia%2FBangkok&refresh=1s',{waitUntil:'domcontentloaded',timeout:20000});await pg.waitForTimeout(3500);
 const logged=!new URL(pg.url()).pathname.startsWith('/login');console.log(JSON.stringify({profile:name,authenticated:logged}));
 if(logged){const dest=path.join(base,'Grafana_actual_16Oct.png');await pg.screenshot({path:dest,fullPage:false});fs.writeFileSync(path.join(base,'grafana_session_probe.json'),JSON.stringify({authenticated:true,profile:name,file:dest,captured_utc:new Date().toISOString()},null,2));return;}
 }catch(e){console.log(JSON.stringify({profile:name,error:e.message.split('\n')[0]}));}finally{if(ctx)await ctx.close().catch(()=>{});}
 }fs.writeFileSync(path.join(base,'grafana_session_probe.json'),JSON.stringify({authenticated:false,reason:'Dedicated capture profiles require user login. No credentials or browser data extracted.'},null,2));
})().catch(e=>{console.error(e.message);process.exitCode=1;});
