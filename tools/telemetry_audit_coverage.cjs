// Monotonic elapsed times only. Include leading/trailing silence as well as
// gaps between samples, so a quiet start or finish cannot pass unnoticed.
class Coverage {
  constructor(){this.first=null;this.last=null;this.maxGap=0;}
  receive(elapsedMs){
    if(!Number.isFinite(elapsedMs)||elapsedMs<0||(this.last!==null&&elapsedMs<this.last))throw Error('Invalid monotonic capture time');
    const gap=elapsedMs-(this.last??0);
    this.maxGap=Math.max(this.maxGap,gap);
    if(this.first===null)this.first=elapsedMs;
    this.last=elapsedMs;
  }
  snapshot(elapsedMs){
    if(!Number.isFinite(elapsedMs)||elapsedMs<0||(this.last!==null&&elapsedMs<this.last))throw Error('Invalid monotonic observation time');
    const trailing=elapsedMs-(this.last??0);
    return {leading_receive_gap_ms:this.first??elapsedMs,trailing_receive_gap_ms:trailing,
            max_receive_gap_ms:Math.max(this.maxGap,trailing)};
  }
}
function continuityPass(report){
  return report.status==='completed'&&report.observed_hours>=report.target_hours&&report.sessions===1&&
    report.samples>=report.target_hours*3600*.99&&report.gaps===0&&report.malformed===0&&
    report.disconnects===0&&report.max_receive_gap_ms<=10000;
}
module.exports={Coverage,continuityPass};
