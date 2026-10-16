const assert=require('assert'),{Coverage,continuityPass}=require('../tools/telemetry_audit_coverage.cjs');
const normal=new Coverage();
for(let ms=1000;ms<=3600000;ms+=1000)normal.receive(ms);
const base={status:'completed',observed_hours:1,target_hours:1,sessions:1,samples:3600,
  gaps:0,malformed:0,disconnects:0,...normal.snapshot(3600000)};
assert(continuityPass(base));
// More than 99% of samples does not excuse a gap at the end of the run.
const trailing=new Coverage();for(let ms=1000;ms<=3589000;ms+=1000)trailing.receive(ms);
assert(!continuityPass({...base,samples:3589,...trailing.snapshot(3600000)}));
assert.equal(trailing.snapshot(3600000).trailing_receive_gap_ms,11000);
const leading=new Coverage();for(let ms=11000;ms<=3600000;ms+=1000)leading.receive(ms);
assert(!continuityPass({...base,samples:3590,...leading.snapshot(3600000)}));
assert.equal(leading.snapshot(3600000).leading_receive_gap_ms,11000);
const middle=new Coverage();middle.receive(1000);middle.receive(12000);middle.receive(13000);
assert.equal(middle.snapshot(14000).max_receive_gap_ms,11000);
assert.equal(new Coverage().snapshot(3600000).max_receive_gap_ms,3600000);
assert(!continuityPass({...base,status:'running'}));
assert(!continuityPass({...base,observed_hours:.99}));
assert(!continuityPass({...base,sessions:2}));
assert(!continuityPass({...base,gaps:1}));
assert(!continuityPass({...base,disconnects:1}));
assert(!continuityPass({...base,malformed:1}));
assert.throws(()=>normal.receive(0));
console.log('Monotonic coverage, quiet boundaries and completion conditions passed');
