"""Read-only pixel capture of the foreground authenticated browser pane.

Coordinates were inspected on this workstation. No cookies or credentials are
read. Stop if the app is not the foreground window. Review each PNG before use.
"""
import ctypes, hashlib, json, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from PIL import ImageGrab

root = Path(__file__).resolve().parents[1]
api = ctypes.windll.user32
api.SetProcessDPIAware()
api.GetForegroundWindow.restype = ctypes.c_void_p
window = api.GetForegroundWindow()
process = ctypes.c_uint()
api.GetWindowThreadProcessId(ctypes.c_void_p(window), ctypes.byref(process))
if process.value != 12640:
    raise RuntimeError('Foreground app changed; screenshot skipped')
folder_name = sys.argv[4] if len(sys.argv) > 4 else '20261014_grafana_in_app'
if not folder_name.replace('_', '').replace('-', '').isalnum():
    raise ValueError('Use a simple evidence folder name')
folder = root / 'output/presentation_evidence/actual_tools' / folder_name
folder.mkdir(parents=True, exist_ok=True)
name, url, caption = sys.argv[1:4]
file = folder / (name + '.png')
if file.exists():
    raise FileExistsError('Preserve prior screenshots')
now = datetime.now(timezone.utc)
bbox = (-855, 105, -10, 1030)
capture = ImageGrab.grab(bbox=bbox, all_screens=True)
if not any(high for low, high in capture.convert('RGB').getextrema()):
    raise RuntimeError('All-black pixels; browser capture unavailable, no evidence saved')
capture.save(file)
record = dict(file=file.name, captured_utc=now.isoformat(),
    captured_thai=now.astimezone(timezone(timedelta(hours=7))).isoformat(),
    url=url, caption=caption, sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
    capture_method='Read-only original pixels of authenticated in-app browser pane',
    bbox_screen=list(bbox), foreground_pid=process.value)
manifest = folder / 'manifest.json'
data = json.loads(manifest.read_text(encoding='utf8')) if manifest.exists() else dict(type='ACTUAL_TOOL_SCREENSHOTS', images=[])
data['images'].append(record)
manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')
print(file)
