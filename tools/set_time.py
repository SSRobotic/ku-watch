"""Set the watch clock from this computer. Close the Serial Monitor first."""
import argparse
import time
import serial

p=argparse.ArgumentParser()
p.add_argument('--port', required=True, help='For example COM5; use the small Super Mini port')
a=p.parse_args()
connection=serial.Serial(port=None, baudrate=115200, timeout=0.2)
connection.dtr=False
connection.rts=False
connection.port=a.port
with connection:
    deadline=time.monotonic()+8
    last=0
    while time.monotonic()<deadline:
        if time.monotonic()-last>=1:
            connection.write(('TIME '+str(int(time.time()))+'\n').encode('ascii'))
            last=time.monotonic()
        if connection.readline().strip()==b'TIME OK':
            print('Clock set from PC; display uses Thailand UTC+7.')
            break
    else:
        raise SystemExit('No TIME OK reply. Check port, firmware and close Serial Monitor.')
