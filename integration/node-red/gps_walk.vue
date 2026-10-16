<template>
  <div class="ku-gps-walk">
    <div><small>ตำแหน่ง GPS</small><strong>{{ p.gps_fix ? 'รับตำแหน่งแล้ว' : 'รอสัญญาณดาวเทียม' }}</strong>
      <span>{{ p.gps_fix && Number.isFinite(p.latitude) && Number.isFinite(p.longitude) ? p.latitude.toFixed(6)+', '+p.longitude.toFixed(6) : '—' }}</span></div>
    <div><small>ดาวเทียม / สัญญาณ</small><strong>{{ formatReading(p.satellites_view) }} ดวง</strong><span>C/N0 {{ formatReading(p.gps_signal) }}</span></div>
    <div><small>การเดิน</small><strong>{{ p.recording ? 'กำลังบันทึก' : 'หยุดบันทึก' }}</strong><span>{{ formatReading(p.elapsed_s) }} วินาที</span></div>
    <div><small>ระยะทาง</small><strong>{{ Number.isFinite(p.distance_m) ? (p.distance_m/1000).toFixed(3) : '—' }} กม.</strong><span>{{ formatReading(p.speed_kmh) }} กม./ชม.</span></div>
  </div>
</template>
<script>
export default {
  computed: { p() { return this.msg?.payload||{}; } },
  methods: { formatReading(v) { return typeof v==='number' && Number.isFinite(v) ? v : '—'; } }
};
</script>
<style>
.ku-gps-walk { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:20px; padding:20px; }
.ku-gps-walk div { display:flex; flex-direction:column; gap:8px; border-left:3px solid #087f8c; padding-left:14px; }
.ku-gps-walk small { color:#64748b; font-size:13px; }
.ku-gps-walk strong { font-size:20px; color:#0f172a; }
.ku-gps-walk span { font-size:14px; color:#475569; }
</style>
