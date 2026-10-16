// Actual device -> diagnostic MQTT -> Node-RED -> browser paint. No host fake telemetry.
const fs=require('fs'),path=require('path'),crypto=require('crypto'),{spawn}=require('child_process');
const {performance}=require('node:perf_hooks');
const {chromium}=require('C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const mqtt=require(path.join(process.env.APPDATA,'npm/node_modules/node-red/node_modules/mqtt'));
const root=path.resolve(__dirname,'..'),baseOut=path.join(root,'output/fr_completion_20261016'),out=path.join(baseOut,'fr06_runs',new Date().toISOString().replace(/[:.]/g,'-')),cfg=JSON.parse(fs.readFileSync(path.join(root,'config/cloud.local.json'))),topic=require('./mqtt_topic.cjs').topic;fs.mkdirSync(out,{recursive:true});
const python='C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const channels=process.argv.slice(2).length?process.argv.slice(2):['TEMP','IAQ'];
const proof={started_utc:new Date().toISOString(),timing_clock:'Calibrated browser/Node monotonic clocks; conservative time from before starting the USB trigger process',boundary:'Explicit 1-Hz diagnostic inputs on real watch, through production alert model and physical display SPI writes; separate MQTT test topic, same alert UI template. Browser DOM + two animation frames measured. Does not establish physical BSEC three-reading latency or optical LCD latency.',tests:[],normal_data_samples:0,normal_data_simulated:0};
let client,browser,context;
(async()=>{try{
 client=mqtt.connect('mqtts://'+cfg.host+':8883',{username:cfg.reader_user,password:cfg.reader_password,clientId:'ku-fr06-proof-'+crypto.randomBytes(5).toString('hex'),rejectUnauthorized:true,reconnectPeriod:0});
 await new Promise((res,rej)=>{client.once('connect',()=>client.subscribe([topic,topic+'/test/alerts'],{qos:1},err=>err?rej(err):res()));client.once('error',()=>rej(Error('MQTT read connection failed')));});
 client.on('message',(t,raw,packet)=>{if(packet.retain)return;let p;try{p=JSON.parse(raw);}catch{return;}const now=Date.now();if(t===topic){if(!p.backfill){proof.normal_data_samples++;if(p.simulated===true)proof.normal_data_simulated++;}return;}const test=proof.tests.find(x=>x.id===p.test_id);if(test)test.mqtt.push({received_epoch_ms:now,payload:p});});
 browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 context=await browser.newContext({viewport:{width:1440,height:1000},recordVideo:{dir:path.join(out,'fr06_browser_video'),size:{width:1440,height:1000}}});
 const page=await context.newPage();
 await page.goto('http://127.0.0.1:1880/dashboard/fr06-test',{waitUntil:'networkidle',timeout:25000});
 await page.locator('.ku-alerts').waitFor({state:'visible',timeout:15000});
 await page.evaluate(()=>{window.fr06Paints=[];let pending=false;const check=()=>{if(pending)return;pending=true;requestAnimationFrame(()=>requestAnimationFrame(()=>{pending=false;const card=document.querySelector('.ku-alerts');if(!card)return;const id=Number(card.dataset.testId),seq=Number(card.dataset.sequence);if(!id||!seq||window.fr06Paints.some(x=>x.id===id&&x.seq===seq))return;const high=card.querySelector('div.high strong'),rect=card.getBoundingClientRect();window.fr06Paints.push({id,seq,high:!!high,visible:rect.width>0&&rect.height>0,epoch_ms:Date.now(),monotonic_ms:performance.now(),text:card.innerText});}));};new MutationObserver(check).observe(document.body,{subtree:true,childList:true,attributes:true,characterData:true});check();});
 for(const channel of channels){
  const id=(Date.now()%2000000000)+1,test={id,channel,serial:[],mqtt:[],browser:[]};proof.tests.push(test);
  const calibrationBefore=performance.now(),browserClock=await page.evaluate(()=>performance.now()),calibrationAfter=performance.now();
  test.clock_calibration={node_before_ms:calibrationBefore,node_after_ms:calibrationAfter,browser_ms:browserClock,uncertainty_ms:calibrationAfter-calibrationBefore};
  test.trigger_process_start_monotonic_ms=performance.now();
  const proc=spawn(python,[path.join(root,'tools/fr06_serial_trigger.py'),String(id),channel],{cwd:root,windowsHide:true});let buffer='',error='';
  proc.stdout.on('data',chunk=>{buffer+=chunk.toString();let at;while((at=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,at);buffer=buffer.slice(at+1);if(line.trim())test.serial.push(JSON.parse(line));}});proc.stderr.on('data',x=>error+=x.toString());
  await new Promise((res,rej)=>{proc.on('error',rej);proc.on('close',code=>code?rej(Error('USB test process failed: '+error.split('\n').slice(-2).join(' '))):res());});
  test.browser=await page.evaluate(id=>window.fr06Paints.filter(x=>x.id===id),id);
  const sent=test.serial.find(x=>x.kind==='host_sent');const display=test.serial.filter(x=>x.text?.startsWith('ALERTTEST DISPLAY ')).map(x=>({...x,payload:JSON.parse(x.text.slice('ALERTTEST DISPLAY '.length).replace(/ queued=\d+$/,''))}));
  const trigger=display.find(x=>x.payload.sequence===3&&x.payload.alert_mask===(channel==='TEMP'?1:2)&&x.payload.alert_pixels>0);
  const painted=test.browser.find(x=>x.seq===3&&x.high&&x.visible);
  test.display_elapsed_ms=trigger?.payload.display_elapsed_ms??null;
  test.browser_elapsed_ms=painted?painted.monotonic_ms+(calibrationAfter-browserClock)-test.trigger_process_start_monotonic_ms:null;
  test.passed=display.length===3&&display.slice(0,2).every(x=>x.payload.alert_mask===0)&&!!trigger&&test.display_elapsed_ms<=5000&&test.browser_elapsed_ms!==null&&test.browser_elapsed_ms<=5000&&test.mqtt.some(x=>x.payload.sequence===3&&x.payload.simulated===true);
  test.screenshot='FR06_'+channel+'_'+id+'.png';await page.screenshot({path:path.join(out,test.screenshot)});test.screenshot_sha256=crypto.createHash('sha256').update(fs.readFileSync(path.join(out,test.screenshot))).digest('hex');
  fs.writeFileSync(path.join(out,'fr06_hardware_browser.json'),JSON.stringify(proof,null,2));
  console.log(JSON.stringify({channel,id,display_ms:test.display_elapsed_ms,browser_ms:test.browser_elapsed_ms,device_messages:test.mqtt.length,passed:test.passed}));
 }
 proof.passed=proof.tests.every(t=>t.passed)&&proof.normal_data_samples>0&&proof.normal_data_simulated===0;
 }catch(e){proof.passed=false;proof.error=e.message;console.error(e.message);}finally{if(context)await context.close().catch(()=>{});if(browser)await browser.close().catch(()=>{});if(client)client.end(true);proof.completed_utc=new Date().toISOString();fs.writeFileSync(path.join(out,'fr06_hardware_browser.json'),JSON.stringify(proof,null,2));console.log(JSON.stringify({passed:proof.passed,normal_data_samples:proof.normal_data_samples,normal_data_simulated:proof.normal_data_simulated,error:proof.error}));process.exitCode=proof.passed?0:1;}})();
