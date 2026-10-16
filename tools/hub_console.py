"""Read large-display diagnostics without asserting USB DTR/RTS."""
import argparse,time,json
from pathlib import Path
import serial
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',default='COM8');parser.add_argument('--seconds',type=float,default=15);parser.add_argument('--command',action='append',default=[]);parser.add_argument('--output',default='output/large_live.json');args=parser.parse_args()
    connection=serial.Serial();connection.port=args.port;connection.baudrate=115200;connection.timeout=.1;connection.dtr=False;connection.rts=False;connection.open()
    started=time.monotonic();lines=[];sent=False
    while time.monotonic()-started<args.seconds:
        if not sent and time.monotonic()-started>.8:
            for command in args.command or ['HUBINFO']:connection.write((command+'\n').encode())
            sent=True
        raw=connection.readline()
        if raw:
            line=raw.decode('utf8','replace').strip();lines.append({'at':round(time.monotonic()-started,2),'text':line})
            if line.startswith(('HUB','KU HUB','ESP-ROM','rst:')):print(line)
    connection.close();Path(args.output).write_text(json.dumps({'port':args.port,'seconds':args.seconds,'commands':args.command,'lines':lines},ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':main()
