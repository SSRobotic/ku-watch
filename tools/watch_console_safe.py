"""Observe small-watch diagnostics without reset lines, credentials or raw sensor data."""
import argparse,json,re,time
from pathlib import Path
import serial
from package_delivery import known_secrets
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=15);p.add_argument('--output',default='output/requirements_audit_20261009/watch_network_20261010.json');p.add_argument('--command',action='append',default=[]);p.add_argument('--interval',type=float,default=0);a=p.parse_args()
port=serial.Serial();port.port='COM15';port.baudrate=115200;port.timeout=.1;port.dtr=False;port.rts=False;port.open()
start=time.monotonic();sent=False;lines=[];secrets=known_secrets();next_query=0
while time.monotonic()-start<a.seconds:
    if not sent and time.monotonic()-start>.8:
        for command in a.command or ['NETINFO','CLOCKINFO','LINKINFO']:port.write((command+'\n').encode())
        sent=True
        next_query=time.monotonic()+a.interval
    if sent and a.interval>0 and time.monotonic()>=next_query:
        for command in ['NETINFO','CLOCKINFO','LINKINFO']:port.write((command+'\n').encode())
        next_query=time.monotonic()+a.interval
    line=port.readline().decode('utf8','replace').strip()
    if not line:continue
    if not (line.startswith(('OTA','NET','MQTT','QUEUE','CLOCK','ESPNOW','ESP-ROM','rst:','Guru Meditation','Backtrace','Rebooting','abort','WIFI')) or re.search('esp-tls|esp_mqtt|mqtt_client|OUTBOX|watchdog|panic',line,re.I)):continue
    for secret in sorted(secrets,key=len,reverse=True):line=line.replace(secret.decode(),'[REDACTED]')
    if line.startswith('NET ') and 'ssid=' in line:line=re.sub(r'ssid=.*? (?=ip=)','ssid=[configured] ',line)
    lines.append({'at':round(time.monotonic()-start,2),'text':line});print(line,flush=True)
port.close();(ROOT/a.output).write_text(json.dumps({'port':'COM15','seconds':a.seconds,'lines':lines},indent=2))
