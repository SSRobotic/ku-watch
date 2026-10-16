"""Prepare an isolated localhost Grafana demonstration using its built-in TestData."""
from pathlib import Path
import csv
import hashlib
import io
import json
import secrets

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/grafana_tool_demo_20261011'
PROVISION = OUT / 'provisioning'
for name in ['data', 'logs', 'plugins', 'dashboards', 'provisioning/datasources', 'provisioning/dashboards']:
    (OUT / name).mkdir(parents=True, exist_ok=True)
SOURCE_UID = 'ku-watch-demo-testdata'
DS = {'type': 'grafana-testdata-datasource', 'uid': SOURCE_UID}

def target(value, alias='DEMO', ref='A'):
    return {'refId': ref, 'datasource': DS, 'scenarioId': 'csv_metric_values',
            'stringInput': str(value), 'alias': alias, 'hide': False}

def base(number, title, kind, x, y, w, h):
    return {'id': number, 'title': title + ' · SIMULATED', 'type': kind,
            'description': 'Grafana TestData demonstration. Simulated data, not a completed hardware test.',
            'gridPos': {'x': x, 'y': y, 'w': w, 'h': h}, 'datasource': DS,
            'fieldConfig': {'defaults': {'color': {'mode': 'fixed', 'fixedColor': 'green'},
                'mappings': [], 'thresholds': {'mode': 'absolute', 'steps': [{'color': 'green', 'value': None}]}}, 'overrides': []}}

def stat(number, title, value, x, unit='none', mappings=None):
    p = base(number, title, 'stat', x, 3, 4, 5)
    p['targets'] = [target(value, title + ' (simulated)')]
    p['fieldConfig']['defaults'].update({'unit': unit, 'decimals': 0})
    if mappings:
        p['fieldConfig']['defaults']['mappings'] = mappings
    p['options'] = {'reduceOptions': {'values': False, 'calcs': ['lastNotNull'], 'fields': ''},
                    'orientation': 'auto', 'textMode': 'auto', 'colorMode': 'value',
                    'graphMode': 'none', 'justifyMode': 'auto'}
    return p

banner = {'id': 1, 'type': 'text', 'title': 'ข้อมูลจำลองจาก Grafana TestData',
          'gridPos': {'x': 0, 'y': 0, 'w': 24, 'h': 3},
          'options': {'mode': 'markdown', 'content':
            '## DEMO / SIMULATED — ตัวอย่างเมื่อผ่านการทดสอบ 24 ชั่วโมง\n'
            'กราฟและค่าทุกช่องสร้างด้วย **Grafana TestData** สำหรับสาธิตรูปแบบรายงาน '
            '**ไม่ใช่ผลทดสอบฮาร์ดแวร์จริง** เปิดเมนูแต่ละช่อง → Inspect → Data เพื่อดูข้อมูลต้นทางหรือ Download CSV ได้'}}
panels = [banner,
    stat(2, 'เวลาสมมติ', 86400, 0, 'dtdurations'),
    stat(3, 'ข้อมูลสดสมมติ', 86400, 4, 'short'),
    stat(4, 'รอบบูตสมมติ', 1, 8),
    stat(5, 'ลำดับขาดสมมติ', 0, 12),
    stat(6, 'ตัวรับหลุดสมมติ', 0, 16),
    stat(7, 'ผลตัวอย่าง', 1, 20, mappings=[{'type': 'value', 'options': {'1': {'text': 'PASS (DEMO)', 'color': 'green', 'index': 0}}}]),
]
count_values = [i * 900 for i in range(97)]
gap_values = [1000, 1110, 990, 1250, 1020, 1840, 1070, 960, 1300, 1050, 2500, 1010,
              1120, 1090, 1020, 980, 1210, 1050, 1100, 990, 1180, 1010, 1230, 1080, 1000]
for number, title, values, unit, x in [
        (8, 'ข้อมูลสะสมสมมติ', count_values, 'short', 0),
        (9, 'ช่วงรับข้อมูลห่างสมมติ', gap_values, 'ms', 12)]:
    p = base(number, title, 'timeseries', x, 8, 12, 9)
    p['targets'] = [target(','.join(map(str, values)), title)]
    p['fieldConfig']['defaults'].update({'unit': unit, 'min': 0,
        'custom': {'drawStyle': 'line', 'lineInterpolation': 'linear', 'lineWidth': 2,
                   'fillOpacity': 12, 'showPoints': 'auto', 'spanNulls': False,
                   'axisLabel': 'จำนวนรายการ (DEMO)' if number == 8 else 'ช่วงรับห่าง ms (DEMO)',
                   'axisPlacement': 'auto'}})
    p['options'] = {'legend': {'displayMode': 'list', 'placement': 'bottom', 'calcs': ['lastNotNull', 'max']},
                    'tooltip': {'mode': 'single', 'sort': 'none'}}
    panels.append(p)

criteria = [
    ['ระยะเวลา', '24 ชั่วโมง (สมมติ)', 'อย่างน้อย 24 ชั่วโมง'],
    ['ข้อมูลสด', '86400 รายการ (สมมติ)', 'อย่างน้อย 99% ของ 1 Hz'],
    ['รอบบูต', '1 รอบ (สมมติ)', '1 รอบ'],
    ['ลำดับข้อมูลขาด', '0 รายการ (สมมติ)', '0 รายการ'],
    ['ตัวรับ MQTT หลุด', '0 ครั้ง (สมมติ)', '0 ครั้ง'],
    ['ช่วงรับห่างสูงสุด', '2.5 วินาที (สมมติ)', 'ไม่เกิน 10 วินาที'],
    ['ข้อมูลผิดรูปแบบ', '0 รายการ (สมมติ)', '0 รายการ'],
]
stream = io.StringIO(newline='')
writer = csv.writer(stream, lineterminator='\n')
writer.writerow(['รายการ', 'ค่าจำลอง', 'เกณฑ์ของรอบตรวจ'])
writer.writerows(criteria)
criteria_csv = stream.getvalue()
table = base(10, 'เกณฑ์ตัวอย่างผ่าน', 'table', 0, 17, 24, 8)
table['targets'] = [{'refId': 'A', 'datasource': DS, 'scenarioId': 'csv_content', 'csvContent': criteria_csv}]
table['options'] = {'showHeader': True, 'cellHeight': 'md', 'footer': {'show': False}}
table['fieldConfig']['defaults']['custom'] = {'align': 'auto', 'cellOptions': {'type': 'auto'}, 'filterable': True}
panels.append(table)
dashboard = {
    'uid': 'ku-watch-demo-pass', 'title': 'KU Watch · PASS DEMO · ข้อมูลจำลอง',
    'description': 'Demonstration in the actual Grafana application using built-in TestData; not hardware acceptance evidence.',
    'tags': ['KU Watch', 'DEMO', 'SIMULATED'], 'schemaVersion': 39, 'version': 1,
    'editable': True, 'timezone': 'Asia/Bangkok', 'time': {'from': 'now-24h', 'to': 'now'},
    'refresh': '', 'panels': panels, 'templating': {'list': []},
    'annotations': {'list': []}, 'links': [],
}
dash_path = OUT / 'dashboards/ku-watch-demo-pass.json'
dash_path.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding='utf-8')
(OUT / 'demo_criteria.csv').write_text(criteria_csv, encoding='utf-8-sig')
(PROVISION / 'datasources/ku-watch-demo.yaml').write_text(
    'apiVersion: 1\ndatasources:\n  - name: KU Watch DEMO TestData\n    type: grafana-testdata-datasource\n'
    f'    uid: {SOURCE_UID}\n    orgId: 1\n    access: proxy\n    isDefault: true\n    editable: false\n', encoding='utf-8')
(PROVISION / 'dashboards/ku-watch-demo.yaml').write_text(
    'apiVersion: 1\nproviders:\n  - name: KU Watch Demo\n    orgId: 1\n    folder: KU Watch Demo\n'
    '    type: file\n    disableDeletion: true\n    allowUiUpdates: true\n    updateIntervalSeconds: 10\n'
    f'    options:\n      path: {(OUT / "dashboards").as_posix()}\n', encoding='utf-8')
config = OUT / 'grafana-demo.local.ini'
if not config.exists():
    password = secrets.token_hex(24)
    config.write_text(
        '[server]\nhttp_addr = 127.0.0.1\nhttp_port = 3001\ndomain = 127.0.0.1\nroot_url = http://127.0.0.1:3001/\n'
        '[paths]\n' + ''.join(f'{key} = {(OUT / value).as_posix()}\n' for key, value in
                               [('data', 'data'), ('logs', 'logs'), ('plugins', 'plugins'), ('provisioning', 'provisioning')]) +
        '[database]\ntype = sqlite\npath = grafana.db\n'
        '[auth.anonymous]\nenabled = true\norg_name = Main Org.\norg_role = Viewer\n'
        '[security]\nadmin_user = ku-demo-admin\nadmin_password = ' + password + '\n'
        '[users]\nallow_sign_up = false\n'
        '[analytics]\nreporting_enabled = false\ncheck_for_updates = false\ncheck_for_plugin_updates = false\n', encoding='utf-8')
manifest = {'data_type': 'SIMULATED', 'engine': 'Grafana built-in TestData',
            'listen': '127.0.0.1:3001', 'dashboard_uid': dashboard['uid'],
            'dashboard_sha256': hashlib.sha256(dash_path.read_bytes()).hexdigest(),
            'actual_evidence_modified': False, 'panels': len(panels),
            'note': '97 cumulative points are simulated 15-minute summaries, not 86400 actual captured messages.'}
(OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'prepared': True, 'panels': len(panels), 'listen': manifest['listen'], 'dashboard_uid': dashboard['uid']}))
