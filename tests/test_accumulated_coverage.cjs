const assert=require('node:assert/strict');
const {AccumulatedCoverage}=require('../tools/accumulated_coverage.cjs');
const c=new AccumulatedCoverage();
c.receive('aaaaaaaa-00000001',100000);c.receive('aaaaaaaa-00000002',101000);
assert.equal(c.snapshot(101000).credited_ms,1000); // quiet startup earns nothing
assert.equal(c.receive('aaaaaaaa-00000002',102000),false); // redelivery earns nothing
c.receive('aaaaaaaa-00000003',112000); // long silence starts a new segment
assert.equal(c.snapshot(112000).credited_ms,1000);
c.receive('aaaaaaaa-00000005',113000); // missing sequence earns nothing
c.receive('bbbbbbbb-00000001',114000); // reboot earns nothing
c.receive('bbbbbbbb-00000002',115000);
assert.equal(c.snapshot(115000).credited_ms,2000);
assert.equal(c.snapshot(126000).current_continuous_ms,0); // quiet tail earns nothing
const restarted=new AccumulatedCoverage(c.snapshot(126000));
restarted.receive('bbbbbbbb-00000003',100);restarted.receive('bbbbbbbb-00000004',1100);
assert.equal(restarted.snapshot(1100).credited_ms,3000); // restart retains credit but does not bridge downtime
restarted.interrupt();restarted.receive('bbbbbbbb-00000005',2100);
assert.equal(restarted.snapshot(2100).credited_ms,3000); // reader outage earns nothing
assert.equal(restarted.snapshot(2100).longest_continuous_ms,1000);
assert.throws(()=>restarted.receive('invalid',2200));
console.log('Cumulative capture coverage: outages, restarts, boot changes, missing IDs and duplicate deliveries verified');
