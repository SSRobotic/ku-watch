<template>
  <div class="ku-alerts">
    <h3>แจ้งเตือนและสถานะนาฬิกา</h3>
    <div :class="level('alert_temp_state')"><strong>อุณหภูมิ: {{ text('alert_temp_state') }}</strong>
      <span>เกิน {{ number(p.alert_temp_limit) }} °C ติดต่อกัน 3 รอบ</span></div>
    <div :class="level('alert_iaq_state')"><strong>IAQ: {{ text('alert_iaq_state') }}</strong>
      <span>เกิน {{ number(p.alert_iaq_limit) }} ติดต่อกัน 3 รอบ · รอ BSEC พร้อมก่อน</span></div>
    <div :class="level('alert_battery_state')"><strong>แบตเตอรี่: {{ batteryText }}</strong>
      <span>{{ number(p.battery_percent) }}% โดยประมาณ · เตือนที่ ≤20% · ยกเลิกที่ ≥22%</span></div>
    <small>เฟิร์มแวร์ {{ fresh && typeof p.firmware === 'string' ? p.firmware : '—' }}</small>
    <small>สถานะจากนาฬิกา · อุณหภูมิบริเวณบอร์ด · ข้อมูลย้อนหลังไม่เปลี่ยนสถานะสด</small>
  </div>
</template>
<script>
export default {
  data(){return {now:Date.now(),timer:null};},
  mounted(){this.timer=setInterval(()=>{this.now=Date.now();},1000);},
  unmounted(){clearInterval(this.timer);},
  computed:{p(){return this.msg?.payload||{};},fresh(){return this.p.backfill!==true && typeof this.p.timestamp==='number' && Math.abs(this.now/1000-this.p.timestamp)<=15;},batteryText(){return !this.fresh?'รอข้อมูลล่าสุด':['รอค่าแบตเตอรี่','ระดับแบตปกติ','แบตเตอรี่ต่ำ'][this.p.alert_battery_state]||'รอข้อมูล';}},
  methods:{
    text(key){if(!this.fresh)return 'รอข้อมูลล่าสุด';return ['รอเซ็นเซอร์พร้อม','ยังไม่ถึงเงื่อนไขเตือน','เกินเกณฑ์'][this.p[key]]||'รอข้อมูล';},
    level(key){return this.fresh && this.p[key]===2?'high':this.fresh && this.p[key]===1?'normal':'waiting';},
    number(v){return typeof v==='number' && Number.isFinite(v)?v:'—';}
  }
};
</script>
<style>
.ku-alerts {padding:18px;display:grid;gap:12px;}
.ku-alerts h3 {margin:0;}
.ku-alerts div {padding:12px;border-left:4px solid #94a3b8;display:flex;flex-direction:column;gap:6px;}
.ku-alerts .high {border-color:#ef4444;background:#ef44441a;}
.ku-alerts .high strong {color:#ef4444;}
.ku-alerts .normal {border-color:#22c55e;}
.ku-alerts .waiting {border-color:#eab308;}
.ku-alerts span,.ku-alerts small {font-size:13px;opacity:.85;}
</style>
