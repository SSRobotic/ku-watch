"""Build the provisioned live dashboard. No simulated sensor data is used."""
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'integration/grafana/ku-watch-live.json'
DS = {'type': 'influxdb', 'uid': 'efwpjfdzlacqoc'}
SHARED = {'type': 'dashboard', 'uid': '-- Dashboard --'}
panels = []
ident = 0

def add(kind, title, x, y, w, h, description=''):
    global ident
    ident += 1
    p = dict(id=ident, type=kind, title=title, description=description,
             gridPos=dict(x=x, y=y, w=w, h=h))
    panels.append(p)
    return p

def row(title, y):
    p=add('row',title,0,y,24,1)
    p.update(collapsed=False,panels=[])

def series_fields(p, fields, empty=False):
    p['datasource']=SHARED
    p['targets']=[dict(refId='A',datasource=SHARED,panelId=1,withTransforms=False)]
    p['transformations']=[dict(id='filterFieldsByName',options=dict(include=dict(names=['time']+fields+(['_empty'] if empty else []))))]
    p['fieldConfig']={'defaults':{'unit':'none','noValue':'—','color':{'mode':'palette-classic'}},'overrides':[]}
    if empty:
        p['fieldConfig']['overrides'].append({'matcher':{'id':'byName','options':'_empty'},'properties':[
            {'id':'custom.hideFrom','value':{'legend':True,'tooltip':True,'viz':False}},
            {'id':'displayName','value':'รอข้อมูลจากเซ็นเซอร์'}]})

def override(p, field, **values):
    p['fieldConfig']['overrides'].append({'matcher':{'id':'byName','options':field},
        'properties':[{'id':k,'value':v} for k,v in values.items()]})

def stat(title, field, x,y,w=4,unit='none',color='#56D9CA',decimals=0,description='',mapping=None):
    p=add('stat',title,x,y,w,4,description)
    series_fields(p,[field])
    p['fieldConfig']['defaults'].update(unit=unit,decimals=decimals,color={'mode':'fixed','fixedColor':color})
    p['options']=dict(reduceOptions=dict(calcs=['last'],fields='',values=False),
        colorMode='value',graphMode='area',textMode='value',wideLayout=True,
        justifyMode='auto',orientation='auto',showPercentChange=False)
    if mapping:
        if set(mapping)=={'false','true'}:
            # Stats reduce numeric fields; convert optional booleans locally,
            # preserving null and avoiding references to absent SQL columns.
            p['transformations'].append(dict(id='convertFieldType',options=dict(
                conversions=[dict(targetField=field,destinationType='number')])))
            mapping={'0':mapping['false'],'1':mapping['true']}
        p['fieldConfig']['defaults']['mappings']=[{'type':'value','options':mapping}]
        p['options']['graphMode']='none'
    return p

def chart(title,fields,x,y,w=12,h=7,unit='none',description='',colors=None,decimals=1):
    p=add('timeseries',title,x,y,w,h,description)
    series_fields(p,fields,True)
    p['fieldConfig']['defaults'].update(unit=unit,decimals=decimals,custom={
        'drawStyle':'line','lineInterpolation':'linear','lineWidth':2,'fillOpacity':12,
        'gradientMode':'opacity','showPoints':'never','spanNulls':False,
        'axisBorderShow':False,'axisColorMode':'text','axisLabel':'','axisPlacement':'auto',
        'scaleDistribution':{'type':'linear'},'stacking':{'mode':'none','group':'A'},
        'hideFrom':{'legend':False,'tooltip':False,'viz':False}})
    p['options']={'legend':{'displayMode':'table','placement':'bottom','calcs':['lastNotNull','min','max']},
        'tooltip':{'mode':'multi','sort':'none'}}
    if colors:
        for name,color in zip(fields,colors): override(p,name,color={'mode':'fixed','fixedColor':color})
    return p

YES={'0':{'text':'รอข้อมูล','color':'orange'},'1':{'text':'อ่านได้','color':'green'}}
FINGER={'0':{'text':'วางนิ้วบนเซ็นเซอร์','color':'orange'},'1':{'text':'ตรวจพบนิ้ว','color':'green'}}
FIX={'0':{'text':'รอสัญญาณดาวเทียม','color':'orange'},'1':{'text':'มีตำแหน่งแล้ว','color':'green'}}
RECORD={'0':{'text':'พร้อมเริ่มเดิน','color':'blue'},'1':{'text':'กำลังบันทึก','color':'green'}}

# Panel 1 supplies one shared query to all other panels, before transformations.
p=stat('อุณหภูมิ', 'temp',0,0,unit='celsius',color='#FFB86C',decimals=2,
       description='อุณหภูมิบริเวณบอร์ดจาก BME68x ไม่ใช่อุณหภูมิร่างกาย')
flags=['finger','pulse_live','env_live','acc_live','mag_live','gps_data','gps_fix','recording']
sql='SELECT *, CAST(NULL AS DOUBLE) AS _empty, uptime_ms / 1000.0 AS uptime_s, '
sql+=', '.join(f'CASE WHEN {f} THEN 1 WHEN {f}=false THEN 0 ELSE NULL END AS {f}_value' for f in flags)
sql+=", date_part('epoch', now())-date_part('epoch', time) AS sample_age_s "
sql+='FROM (SELECT * FROM "ku_watch" WHERE $__timeFilter(time) ORDER BY time DESC LIMIT 18000) ORDER BY time ASC'
p['datasource']=DS
p['targets']=[dict(datasource=DS,refId='A',editorMode='code',rawQuery=True,rawSql=sql,format='table')]
stat('ความชื้น','humidity',4,0,unit='percent',color='#73BFFF',decimals=2)
stat('ความดันอากาศ','pressure',8,0,unit='pressurehpa',color='#B794F6',decimals=2)
stat('ชีพจร','bpm',12,0,unit='bpm',color='#FF6D95',decimals=1,description='แสดงเมื่อวางนิ้วและตรวจจับจังหวะได้ต่อเนื่อง')
stat('ดาวเทียม','satellites_view',16,0,color='#F9D46B')
p=stat('ข้อมูลล่าสุด','sample_age_s',20,0,unit='s',description='อายุข้อมูลล่าสุด: เขียวต่ำกว่า 15 วินาที / แดงเมื่อไม่มีข้อมูลใหม่ 30 วินาที')
p['options']['graphMode']='none'
p['fieldConfig']['defaults'].update(color={'mode':'thresholds'},thresholds={'mode':'absolute','steps':[
    {'color':'green','value':None},{'color':'orange','value':15},{'color':'red','value':30}]})

for card in panels:
    card['options'].update(graphMode='none',text={'valueSize':26})

row('01  ชีพจรและสัญญาณแสง  ·  MAX30102',4)
stat('แสงอินฟราเรด • IR','ir',0,5,6,color='#FF7EA5',description='ค่าดิบล่าสุดที่ส่งทุก 1 วินาที ไม่ใช่กราฟคลื่นชีพจร 100 Hz')
stat('แสงสีแดง • RED','red',6,5,6,color='#FFB86C',description='ค่าดิบจากช่องแสงสีแดง ไม่ใช่ค่าออกซิเจนในเลือด')
stat('การวางนิ้ว','finger_value',12,5,6,mapping=FINGER)
stat('เซ็นเซอร์ชีพจร','pulse_live_value',18,5,6,mapping=YES)
chart('ชีพจรย้อนหลัง',['bpm'],0,9,unit='bpm',colors=['#FF6D95'],description='ช่องว่างคือช่วงที่ยังอ่านชีพจรไม่ได้ ไม่มีการเติมค่า 0')
p=chart('การเปลี่ยนแปลงแสง IR / RED',['ir','red'],12,9,colors=['#FF7EA5','#FFB86C'],decimals=0,
    description='ส่งค่าดิบล่าสุด 1 จุด/วินาที ใช้ดูการวางนิ้วและระดับแสง ไม่ใช่รูปคลื่นชีพจรเต็มความถี่')
override(p,'ir',displayName='IR');override(p,'red',displayName='RED')

row('02  สภาพแวดล้อม  ·  BME68x',16)
chart('อุณหภูมิย้อนหลัง',['temp'],0,17,8,unit='celsius',colors=['#FFB86C'],decimals=2)
chart('ความชื้นย้อนหลัง',['humidity'],8,17,8,unit='percent',colors=['#73BFFF'],decimals=2)
chart('ความกดอากาศย้อนหลัง',['pressure'],16,17,8,unit='pressurehpa',colors=['#B794F6'],decimals=2)

row('03  การเคลื่อนไหวและสนามแม่เหล็ก  ·  GY-51',24)
for i,(field,title,color) in enumerate([
    ('acc_x','เคลื่อนไหว X','#56D9CA'),('acc_y','เคลื่อนไหว Y','#73BFFF'),('acc_z','เคลื่อนไหว Z','#FFB86C'),
    ('mag_x','แม่เหล็ก X','#56D9CA'),('mag_y','แม่เหล็ก Y','#73BFFF'),('mag_z','แม่เหล็ก Z','#B794F6')]):
    p=stat(title,field,i*4,25,color=color,description='ค่าดิบจากรีจิสเตอร์ ยังไม่ได้แปลงหน่วยหรือสอบเทียบเป็นทิศเข็มทิศ')
    if field.startswith('mag_'):
        p['fieldConfig']['defaults']['mappings']=[{'type':'value','options':{'-4096':{'text':'ตรวจเซ็นเซอร์','color':'orange'}}}]
for x,fields,title in [(0,['acc_x','acc_y','acc_z'],'การเคลื่อนไหว 3 แกน • ค่าดิบ'),(12,['mag_x','mag_y','mag_z'],'สนามแม่เหล็ก 3 แกน • ค่าดิบ')]:
    p=chart(title,fields,x,29,colors=['#56D9CA','#73BFFF','#FFB86C'],decimals=0,
        description='ค่าจากรีจิสเตอร์เซ็นเซอร์ ยังไม่ใช่ g หรือ µT; ค่าแม่เหล็ก -4096 ค้าง ควรตรวจการอิ่มตัวของเซ็นเซอร์และสนามแม่เหล็กใกล้บอร์ด')
    for f in fields: override(p,f,displayName=f[-1].upper())

row('04  ตำแหน่งและสัญญาณดาวเทียม  ·  ATGM336H',36)
stat('สถานะตำแหน่ง','gps_fix_value',0,37,6,mapping=FIX)
stat('การรับข้อมูล GPS','gps_data_value',6,37,6,mapping=YES)
stat('ดาวเทียมที่ใช้คำนวณ','satellites',12,37,6,color='#F9D46B')
stat('สัญญาณดาวเทียมสูงสุด','gps_signal',18,37,6,unit='suffix:dB-Hz',color='#56D9CA',description='C/N0 สูงสุดของดาวเทียมที่รายงานสัญญาณ ไม่ใช่ความแม่นยำพิกัด')
stat('ละติจูด','latitude',0,41,6,decimals=6,color='#73BFFF')
stat('ลองจิจูด','longitude',6,41,6,decimals=6,color='#73BFFF')
stat('ความสูงจาก GPS','altitude',12,41,6,unit='lengthm',decimals=1,color='#B794F6')
stat('ความเร็วจาก GPS','speed_kmh',18,41,6,unit='velocitykmh',decimals=2,color='#FFB86C')
p=chart('จำนวนดาวเทียม • มองเห็น / ใช้คำนวณ',['satellites_view','satellites'],0,45,colors=['#F9D46B','#56D9CA'],decimals=0)
override(p,'satellites_view',displayName='มองเห็น');override(p,'satellites',displayName='ใช้คำนวณ')
chart('ระดับสัญญาณดาวเทียม',['gps_signal'],12,45,unit='suffix:dB-Hz',colors=['#56D9CA'],decimals=0)
stat('HDOP • ยิ่งต่ำยิ่งดี','gps_hdop',0,52,6,decimals=2,color='#B794F6',description='แสดงเฉพาะตอนมี GPS fix ไม่ใช่ระยะคลาดเคลื่อนเป็นเมตร')
stat('อายุตำแหน่งล่าสุด','gps_age_s',6,52,6,unit='s',decimals=1,description='ขีดหมายถึงยังไม่เคยได้ตำแหน่งที่ใช้ได้')
stat('ข้อมูล GPS ที่รับแล้ว','gps_chars',12,52,6,unit='suffix:ตัวอักษร',color='#73BFFF')
stat('ประโยค GPS ที่ตรวจไม่ผ่าน','gps_checksum_errors',18,52,6,color='#FFB86C')

row('05  การเดินและบันทึกกิจกรรม',56)
stat('สถานะกิจกรรม','recording_value',0,57,6,mapping=RECORD)
stat('ระยะทางสะสม','distance_m',6,57,6,unit='lengthm',decimals=1,color='#56D9CA')
stat('เวลาที่เดิน','elapsed_s',12,57,6,unit='s',color='#73BFFF')
stat('จุดที่บันทึกแล้ว','record_samples',18,57,6,color='#B794F6')
chart('ระยะทางสะสมย้อนหลัง',['distance_m'],0,61,unit='lengthm',colors=['#56D9CA'])
chart('ความเร็วระหว่างเดิน',['speed_kmh'],12,61,unit='velocitykmh',colors=['#FFB86C'])

row('06  สถานะบอร์ดและการส่งข้อมูล',68)
stat('Wi-Fi','wifi_rssi',0,69,unit='suffix:dBm',color='#73BFFF')
stat('เวลาทำงาน','uptime_s',4,69,unit='s',color='#56D9CA')
stat('แรมว่าง','heap_free',8,69,unit='bytes',color='#B794F6')
stat('พื้นที่ว่าง','storage_free',12,69,unit='bytes',color='#F9D46B')
stat('ส่งสำเร็จ','mqtt_sent',16,69,color='#56D9CA')
stat('กิจกรรม #','activity_id',20,69,color='#73BFFF',description='0 หมายถึงยังไม่ได้เริ่มกิจกรรมหลังเปิดบอร์ด')
chart('สัญญาณ Wi-Fi ย้อนหลัง',['wifi_rssi'],0,73,unit='suffix:dBm',colors=['#73BFFF'],decimals=0)
chart('หน่วยความจำบอร์ดที่เหลือ',['heap_free'],12,73,unit='bytes',colors=['#B794F6'],decimals=0)
for i,(field,title) in enumerate([('env_live_value','BME68x'),('acc_live_value','Accelerometer'),('mag_live_value','Magnetometer')]):
    stat(title,field,i*8,80,8,mapping=YES)
# Keep original panel IDs (including the footer) stable for the friends link.
p=add('text','เกี่ยวกับข้อมูล',0,128,24,3)
p['options']={'mode':'markdown','content':'**KU Watch • เซ็นเซอร์สด**  ·  บอร์ดส่งทุก 1 วินาที / หน้ารีเฟรชทุก 5 วินาที\n\nSpO₂ เป็นค่าทดลองจากสัญญาณแสง ไม่ใช้วินิจฉัยโรค • IAQ ของ Bosch ต้องรออุ่นและเรียนรู้สภาพอากาศ ไม่ใช่ PM2.5 หรือ AQI ของกรมควบคุมมลพิษ • เปอร์เซ็นต์แบตประมาณจากแรงดัน LiPo 1 เซลล์ และแสดงเมื่อ INA226 อ่านได้ • ขีด/ช่องว่างคือยังไม่มีค่าที่ผ่านการตรวจ • กราฟแต่ละช่วงแสดงข้อมูลล่าสุดสูงสุด 18,000 จุด'}

row('07  ออกซิเจนจากสัญญาณแสง  ·  SpO₂ ทดลอง',84)
stat('SpO₂ • ค่าทดลอง','spo2',0,85,8,unit='percent',color='#FF7EA5',
     description='ประมาณจาก RED/IR ที่ 25 Hz ด้วยอัลกอริทึมอ้างอิง Maxim; รออย่างน้อย 5 วินาทีและผ่านการคัดกรองสัญญาณ ไม่ใช่อุปกรณ์การแพทย์')
stat('สถานะการคำนวณ SpO₂','spo2_status',8,85,8,mapping={
    '0':{'text':'วางนิ้ว','color':'orange'},'1':{'text':'กำลังเก็บสัญญาณ','color':'blue'},
    '2':{'text':'สัญญาณอ่อน / เคลื่อนไหว','color':'orange'},'3':{'text':'ค่าทดลองพร้อม','color':'green'},
    '4':{'text':'นอกช่วงประมาณ','color':'orange'}})
stat('ความสอดคล้อง RED / IR','spo2_quality',16,85,8,unit='percentunit',decimals=1,
     description='ความสัมพันธ์ของรูปคลื่นสองช่องแสง 0–1 ใช้คัดกรองสัญญาณ ไม่ใช่ความแม่นยำของ SpO₂')
chart('SpO₂ ย้อนหลัง • ค่าทดลอง',['spo2'],0,89,24,unit='percent',colors=['#FF7EA5'],
      description='เว้นช่องว่างเมื่อถอดนิ้ว สัญญาณไม่ผ่าน หรือยังเก็บข้อมูลไม่ครบ')

row('08  คุณภาพอากาศภายใน  ·  Bosch BSEC',96)
p=stat('IAQ • Bosch','iaq',0,97,6,color='#56D9CA',decimals=1,
       description='ดัชนี 0–500: ค่าต่ำหมายถึงอากาศดีกว่าตามแบบจำลอง BSEC; ไม่ใช่ค่าฝุ่น PM2.5')
stat('ระดับการเรียนรู้ IAQ','iaq_accuracy',6,97,6,unit='suffix:/ 3',description='0 ยังไม่พร้อม / 1 ต่ำ / 2 กลาง / 3 สูง เป็นสถานะอัลกอริทึม')
BOOL={'false':{'text':'กำลังเตรียม','color':'orange'},'true':{'text':'พร้อม','color':'green'}}
stat('ฮีตเตอร์พร้อม','iaq_stable',12,97,6,mapping=BOOL)
stat('เซ็นเซอร์ผ่านช่วงเริ่มต้น','iaq_run_in',18,97,6,mapping=BOOL)
stat('ความต้านทานก๊าซ','gas_ohms',0,101,12,unit='ohm',decimals=0,
     description='ความต้านทานก๊าซที่เซ็นเซอร์วัดได้ ไม่ใช่ความเข้มข้นก๊าซชนิดใดในหน่วย ppm')
stat('IAQ ผ่านเงื่อนไขแสดงผล','iaq_valid',12,101,12,mapping=BOOL)
chart('IAQ ย้อนหลัง',['iaq'],0,105,12,colors=['#56D9CA'],description='เริ่มแสดงเมื่อฮีตเตอร์พร้อม ผ่าน run-in และ accuracy อย่างน้อย 1')
chart('ความต้านทานก๊าซย้อนหลัง',['gas_ohms'],12,105,12,unit='ohm',colors=['#B794F6'],decimals=0)

row('09  แบตเตอรี่  ·  INA226',112)
stat('แบตเตอรี่ • ประมาณ','battery_percent',0,113,6,unit='percent',color='#56D9CA',
     description='ประมาณจากแรงดัน LiPo 1S ชาร์จเต็ม 4.20 V; ไม่ได้วัดปริมาณประจุจริงหรือระยะเวลาใช้งานที่เหลือ')
stat('แรงดันแบตเตอรี่','battery_voltage',6,113,6,unit='volt',decimals=3,color='#F9D46B')
stat('ตรวจพบ INA226','ina226_detected',12,113,6,mapping={'false':{'text':'ยังไม่พบ','color':'orange'},'true':{'text':'พบชิปแล้ว','color':'green'}})
stat('การอ่านแบตเตอรี่','battery_valid',18,113,6,mapping={'false':{'text':'รอต่อจุดวัด','color':'orange'},'true':{'text':'อ่านได้','color':'green'}})
chart('เปอร์เซ็นต์แบตย้อนหลัง • ประมาณ',['battery_percent'],0,117,12,unit='percent',colors=['#56D9CA'])
chart('แรงดันแบตเตอรี่ย้อนหลัง',['battery_voltage'],12,117,12,unit='volt',colors=['#F9D46B'],decimals=3)

row('10  แจ้งเตือนสิ่งแวดล้อมจากนาฬิกา',134)
ALERT_STATES={'0':{'text':'รอเซ็นเซอร์พร้อม','color':'orange'},
              '1':{'text':'ยังไม่ถึงเงื่อนไขเตือน','color':'green'},
              '2':{'text':'เกินเกณฑ์','color':'red'},
              '3':{'text':'รอข้อมูลล่าสุด','color':'orange'}}
for x,title,field in [(0,'แจ้งเตือนอุณหภูมิ','alert_temp_state'),(12,'แจ้งเตือน IAQ','alert_iaq_state')]:
    p=stat(title,field,x,135,12,mapping=ALERT_STATES,
           description='เกินเกณฑ์ 3 รอบการอ่านใหม่ตามนาฬิกา; 0=ยังไม่พร้อม; เกิน 15 วินาทีแสดงรอข้อมูลล่าสุด')
    p['datasource']=DS;p['transformations']=[]
    # A separate latest-row query avoids replaying old alerts as current, and
    # leaves the original shared sensor query unchanged.
    p['targets']=[dict(datasource=DS,refId='A',editorMode='code',rawQuery=True,
        rawSql=f"SELECT time, CASE WHEN time < now() - INTERVAL '15 seconds' THEN 3 ELSE {field} END AS {field} FROM ku_watch ORDER BY time DESC LIMIT 1",format='table')]
    p['options']['graphMode']='none';p['fieldConfig']['defaults']['noValue']='รอข้อมูล'

row('10  เวอร์ชันและการเตือนแบตเตอรี่',131)
stat('เวอร์ชันเฟิร์มแวร์','firmware',0,132,8,description='เวอร์ชันจากนาฬิกาที่ส่งข้อมูลจริง')
p=stat('เตือนแบตเตอรี่','alert_battery_state',8,132,8,mapping={
    '0':{'text':'รอค่าแบตเตอรี่','color':'orange'},'1':{'text':'ระดับแบตปกติ','color':'green'},
    '2':{'text':'แบตเตอรี่ต่ำ','color':'red'},'3':{'text':'รอข้อมูลล่าสุด','color':'orange'}})
p['datasource']=DS;p['transformations']=[]
p['targets']=[dict(datasource=DS,refId='A',editorMode='code',rawQuery=True,
    rawSql="SELECT time, CASE WHEN time < now() - INTERVAL '15 seconds' THEN 3 ELSE alert_battery_state END AS alert_battery_state FROM ku_watch ORDER BY time DESC LIMIT 1",format='table')]
p['options']['graphMode']='none';p['fieldConfig']['defaults']['noValue']='รอข้อมูล'

dashboard=dict(id=None,uid='ku-watch-live',title='KU Watch • Live & Walk',
    description='KU Watch 1.9: environmental alerts, optical SpO2 estimate, Bosch IAQ, battery, live sensors and walking activities.',
    tags=['KU Watch','HiveMQ','All sensors'],timezone='browser',schemaVersion=39,version=3,
    refresh='1s',time={'from':'now-15m','to':'now'},timepicker={'refresh_intervals':['1s','5s','10s','30s','1m']},
    graphTooltip=1,editable=True,panels=panels)
DEST.write_text(json.dumps(dashboard,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Public dashboards cannot use the shared-dashboard datasource. Preserve all
# existing direct queries and add the new optional fields via SELECT *, so a
# sensor that has never reported yet does not cause an unknown-column error.
friend_path=DEST.with_name('ku-watch-friends.json')
friends=json.loads(friend_path.read_text(encoding='utf-8')) if friend_path.exists() else deepcopy(dashboard)
old={p['id']:p for p in friends['panels']}
friends.update(uid='ku-watch-friends',title='KU Watch • Friends View',editable=False,
               description=dashboard['description'],version=3,refresh='10s',
               timepicker={'refresh_intervals':['10s','30s','1m']})
friends['panels']=[]
for panel in panels:
    fp=deepcopy(panel)
    if panel['type'] in ('stat','timeseries'):
        fp['datasource']=DS
        previous=old.get(panel['id'],{})
        if panel['datasource']['type']=='influxdb' and panel['id']!=1:
            fp['targets']=deepcopy(panel['targets'])
        elif previous.get('datasource',{}).get('type')=='influxdb':
            fp['targets']=previous['targets']
        else:
            fp['targets']=[dict(datasource=DS,refId='A',editorMode='code',rawQuery=True,
                                rawSql=sql,format='table')]
    friends['panels'].append(fp)
friend_path.write_text(json.dumps(friends,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'panels':len(panels),'stats':sum(p['type']=='stat' for p in panels),
                  'charts':sum(p['type']=='timeseries' for p in panels),'source_queries':1}))
