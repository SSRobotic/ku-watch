const fs=require('fs'),path=require('path'),cp=require('child_process');
const root=path.resolve(__dirname,'..'),out=path.join(root,'output/final_acceptance_20261016');
const files=['mqtt_topic.cjs','accumulated_soak.cjs','capture_sensor_comparison.cjs','observe_outdoor_link.cjs','observe_replay.cjs','requirements_sensor_audit.cjs','soak_audit.cjs','requirements_grafana_latency.cjs','requirements_mqtt_audit.cjs','test_cloud_connection.cjs','verify_capture_storage.cjs','wait_configured_topic.cjs'];
const report={boundary:'Syntax checks for changed observer scripts and existing production-flow regression checks; not hardware acceptance',checks:[]};
for(const n of files){const r=cp.spawnSync(process.execPath,['--check',path.join(root,'tools',n)],{encoding:'utf8'});report.checks.push({name:n,passed:r.status===0});}
for(const n of ['test_influx_flow.cjs','test_telemetry_audit_coverage.cjs']){const r=cp.spawnSync(process.execPath,[path.join(root,'tests',n)],{cwd:root,encoding:'utf8'});report.checks.push({name:n,passed:r.status===0});if(r.status!==0)fs.writeFileSync(path.join(out,n+'.log'),r.stdout+r.stderr);}
report.passed=report.checks.every(x=>x.passed);fs.writeFileSync(path.join(out,'script_checks.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));process.exitCode=report.passed?0:1;
