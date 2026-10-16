// Only adjacent live captures with unchanged boot, sequence and connection earn time.
class AccumulatedCoverage {
  constructor(saved={}) {
    this.creditedMs=saved.credited_ms||0;this.longestMs=saved.longest_continuous_ms||0;
    this.breaks=saved.breaks||0;this.last=null;this.start=null;this.seen=new Set();
  }
  interrupt() {
    if(this.last!==null){this.breaks++;this.longestMs=Math.max(this.longestMs,this.last.ms-this.start);}
    this.last=null;this.start=null;
  }
  receive(id,ms) {
    if(!/^[a-f0-9]{8}-[a-f0-9]{8}$/i.test(id)||!Number.isFinite(ms)||ms<0)throw Error('Invalid capture');
    if(this.seen.has(id))return false;
    if(this.last&&ms<this.last.ms)throw Error('Non-monotonic time');
    this.seen.add(id);
    const [boot,hex]=id.toLowerCase().split('-'),seq=parseInt(hex,16),previous=this.last;
    if(previous&&boot===previous.boot&&seq===previous.seq+1&&ms-previous.ms<=10000) {
      this.creditedMs+=ms-previous.ms;
    } else {
      this.interrupt();this.start=ms;
    }
    this.last={boot,seq,ms};this.longestMs=Math.max(this.longestMs,ms-this.start);return true;
  }
  snapshot(ms) {
    if(this.last&&ms-this.last.ms>10000)this.interrupt();
    return {credited_ms:this.creditedMs,longest_continuous_ms:this.longestMs,
      current_continuous_ms:this.last?this.last.ms-this.start:0,breaks:this.breaks};
  }
}
module.exports={AccumulatedCoverage};
