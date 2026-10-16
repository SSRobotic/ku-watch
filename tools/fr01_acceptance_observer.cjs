// Wait for real contact, then require a full real minute. No substitute measurements.
const fs=require('fs'),path=require('path'),crypto=require('crypto'),{spawn}=require('child_process'),{performance}=require('node:perf_hooks');
const mqtt=require(path.join(process.env.APPDATA,'npm/node_modules/node-red/node_modules/mqtt'));
const root=path.resolve(__dirname,'..'),out=path.join(root,'output/fr_completion_20261016'),cfg=JSON.parse(fs.readFileSync(path.join(root,'config/cloud.local.json'))),topic=require('./mqtt_topic.cjs').topic;
const runId=new Date().toISOString().replace(/[:.]/g,'-'),dir=path.join(out,'fr01_runs',runId);fs.mkdirSync(dir,{recursive:true});
const resultPath=path.join(dir,'result.json'),statusPath=path.join(out,'fr01_active_status.json');
const report={run_id:runId,pid:process.pid,started_utc:new Date().toISOString(),status:'waiting_for_real_sensor_readiness',passed:false,boundary:'Real device estimates/readiness and post-SPI frame counters only. A pass is a one-minute functional display/conversion check, not clinical accuracy, battery endurance or 24-hour continuity.',source_firmware:'2.0.12',longest_ready_ms:0,samples_seen:0,serial:[],candidate:[],reasons:{},errors:[]};
const python='C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
let child,client,done=false,candidate=[],serial=[],buffer='',lastSession='',lastId='',lastPacketMono=0;
const parse=line=>Object.fromEntries([...line.matchAll(/([A-Za-z0-9_]+)=([^ ]+)/g)].map(m=>[m[1],Number(m[2])]));
function save(){fs.writeFileSync(resultPath,JSON.stringify(report,null,2));fs.writeFileSync(statusPath,JSON.stringify({pid:process.pid,run_id:runId,status:report.status,passed:report.passed,started_utc:report.started_utc,updated_utc:new Date().toISOString(),longest_ready_ms:report.longest_ready_ms,candidate_samples:candidate.length,result:resultPath,reasons:report.reasons},null,2));}
function clear(reason){if(candidate.length)report.longest_ready_ms=Math.max(report.longest_ready_ms,candidate.at(-1).source_ms-candidate[0].source_ms);candidate=[];report.reasons[reason]=(report.reasons[reason]||0)+1;report.status='waiting_for_real_sensor_readiness';}
function assess(){
 if(candidate.length<61)return;
 const first=candidate[0],last=candidate.at(-1),sourceSpan=last.source_ms-first.source_ms,observedSpan=last.received_monotonic_ms-first.received_monotonic_ms;
 report.longest_ready_ms=Math.max(report.longest_ready_ms,sourceSpan);
 if(sourceSpan<60000||observedSpan<60000)return;
 const rows=serial.filter(x=>x.device==='watch'&&x.line.startsWith('RATES ')&&x.data.uptime_ms>=first.source_ms&&x.data.uptime_ms<=last.source_ms);
 if(rows.length<60)return;
 const a=rows[0].data,b=rows.at(-1).data,seconds=(b.uptime_ms-a.uptime_ms)/1000;
 if(seconds<59)return;
 const paintTimes=[...new Set(rows.map(x=>x.data.paint_ms))].sort((a,b)=>a-b);
 const paintGaps=paintTimes.slice(1).map((x,i)=>x-paintTimes[i]);
 const coverage=serial.filter(x=>x.received_monotonic_ms>=first.received_monotonic_ms&&x.received_monotonic_ms<=last.received_monotonic_ms);
 const screens=coverage.filter(x=>x.device==='watch'&&x.line.startsWith('SCREEN page='));
 const hubs=coverage.filter(x=>x.device==='hub'&&x.line.startsWith('HUBINFO '));
 const metric={source_window_ms:sourceSpan,host_monotonic_window_ms:observedSpan,live_messages:candidate.length,serial_source_window_s:seconds,pulse_sample_hz:(b.pulse_samples-a.pulse_samples)/seconds,pulse_resets_during_window:b.pulse_dropped-a.pulse_dropped,environment_conversions:b.env_sequence-a.env_sequence,motion_read_hz:(b.motion_reads-a.motion_reads)/seconds,watch_display_hz:(b.frames-a.frames)/seconds,observed_max_watch_frame_interval_ms:Math.max(...paintGaps),watch_pulse_page_verified:screens.length>=50&&screens.every(x=>x.data.page===4&&x.data.painted===4&&x.data.body_pixels>0),hub_pulse_page_verified:hubs.length>=50&&hubs.every(x=>x.data.page===3&&x.data.watchpage===3&&x.data.receiver===1&&x.data.ready===1&&(x.data.flags&12)===12)};
 const passed=metric.pulse_sample_hz>=20&&metric.pulse_resets_during_window===0&&metric.environment_conversions>=Math.floor(seconds/3)-1&&metric.motion_read_hz>=1&&metric.watch_display_hz>=1&&metric.observed_max_watch_frame_interval_ms<=1000&&metric.watch_pulse_page_verified&&metric.hub_pulse_page_verified;
 report.last_window_metrics=metric;
 if(passed){report.accepted_window={samples:candidate,serial:coverage,metrics:metric};report.passed=true;report.status='functional_one_minute_passed';finish();}
 else {report.last_failed_window={samples:candidate,metrics:metric};clear('display_or_conversion_window_did_not_meet_criteria');}
}
function finish(error){if(done)return;done=true;clearInterval(timer);if(error){report.errors.push(error);report.status='stopped_without_acceptance';}report.completed_utc=new Date().toISOString();report.candidate=candidate;report.serial=serial;save();if(child?.stdin.writable)child.stdin.end('STOP\n');if(client)client.end(true);console.log(JSON.stringify({status:report.status,passed:report.passed,result:resultPath,metrics:report.last_window_metrics,error}));}
child=spawn(python,[path.join(root,'tools/fr01_serial_observer.py')],{cwd:root,windowsHide:true});
child.stdout.on('data',chunk=>{buffer+=chunk;let index;while((index=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,index);buffer=buffer.slice(index+1);if(!line.trim())continue;let event;try{event=JSON.parse(line);}catch{continue;}if(event.error){finish('Serial '+event.device+' '+event.error);continue;}event.received_monotonic_ms=performance.now();event.data=parse(event.line);serial.push(event);serial=serial.filter(x=>performance.now()-x.received_monotonic_ms<100000);assess();}});
child.on('error',()=>finish('USB observer could not start'));child.on('exit',code=>{if(!done)finish('USB observer exited '+code);});child.stderr.on('data',()=>{});
client=mqtt.connect('mqtts://'+cfg.host+':8883',{username:cfg.reader_user,password:cfg.reader_password,clientId:'ku-fr01-'+crypto.randomBytes(5).toString('hex'),rejectUnauthorized:true,reconnectPeriod:1000});
client.on('connect',()=>client.subscribe(topic,{qos:1},error=>{if(error)finish('MQTT subscription rejected');}));client.on('error',()=>{});client.on('offline',()=>clear('reader_disconnected'));
client.on('message',(_,raw,packet)=>{if(done||packet.retain)return;let p;try{p=JSON.parse(raw);}catch{return;}if(p.backfill||p.simulated===true||p.sample_id===lastId)return;lastId=p.sample_id;report.samples_seen++;
 const mono=performance.now(),session=String(p.sample_id||'').split('-')[0];if(session!==lastSession||lastPacketMono&&mono-lastPacketMono>3500)clear('session_change_or_live_gap');lastSession=session;lastPacketMono=mono;
 const required=['env_live','pulse_live','acc_live','mag_live','iaq_valid','spo2_valid','finger'];
 const missing=required.filter(key=>p[key]!==true);if(p.firmware!=='2.0.12')missing.push('expected_firmware');if(!Number.isFinite(p.bpm)||!Number.isFinite(p.spo2))missing.push('pulse_estimates');if(Number(p.bsec_status)<0)missing.push('bsec_error');
 if(missing.length){clear(missing.join(','));return;}
 candidate.push({received_utc:new Date().toISOString(),received_monotonic_ms:mono,source_ms:p.uptime_ms,sample_id:p.sample_id,firmware:p.firmware,all_required_readiness_true:true});report.status='observing_real_ready_minute';assess();
});
const timer=setInterval(()=>{if(done)return;const thai=new Date(Date.now()+7*3600000);if(thai.getUTCDate()!==16||thai.getUTCMonth()!==9||thai.getUTCFullYear()!==2026){finish('End of requested test day');return;}if(fs.existsSync(path.join(out,'fr01_STOP'))){finish('Stop marker requested');return;}if(lastPacketMono&&performance.now()-lastPacketMono>10000)clear('no_fresh_live_data');report.candidate=candidate;report.serial=serial;save();},5000);
save();console.log(JSON.stringify({status:report.status,pid:process.pid,result:resultPath,read_only:true,raw_ppg_or_coordinates_saved:false}));
process.on('SIGINT',()=>finish('Interrupted'));process.on('SIGTERM',()=>finish('Terminated'));
