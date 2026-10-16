<template>
  <div class="ku-live-status">
    <strong>KU WATCH</strong>
    <span :class="fresh ? 'fresh' : 'stale'">{{ fresh ? '● MQTT มีข้อมูลใหม่' : '○ รอข้อมูลล่าสุด' }}</span>
    <span>อัปเดต {{ stamp }}</span>
  </div>
</template>
<script>
export default {
  data() { return { now: Date.now(), timer: null }; },
  mounted() { this.timer=setInterval(()=>{ this.now=Date.now(); },1000); },
  unmounted() { clearInterval(this.timer); },
  computed: {
    fresh() { return typeof this.msg?.payload?.timestamp==='number' && Math.abs(this.now/1000-this.msg.payload.timestamp)<10; },
    stamp() { return this.msg?.payload?.timestamp ? new Date(this.msg.payload.timestamp*1000).toLocaleTimeString('th-TH') : '—'; }
  }
};
</script>
<style>
.ku-live-status { display:flex; flex-wrap:wrap; gap:24px; align-items:center; padding:16px 24px; }
.ku-live-status strong { font-size:24px; color:#087f8c; }
.ku-live-status .fresh { color:#15803d; }
.ku-live-status .stale { color:#a16207; }
</style>
