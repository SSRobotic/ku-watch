"""Validate exported connectivity against firmware pins and the draft's limits."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[1]
out=root/'hardware'/'KU_Watch'
tree=ET.parse(out/'KU_Watch.net.xml')
nets={x.attrib['name'].lstrip('/'): {(n.attrib['ref'], n.attrib['pin']) for n in x.findall('node')} for x in tree.findall('./nets/net')}
pin_block=(root/'include'/'config.h').read_text(encoding='utf8').split('namespace Pin {',1)[1].split('}',1)[0]
pins={k:int(v) for k,v in re.findall(r'\b(SCK|MOSI|CS|DC|RST|SDA|SCL|BUTTON|SOUND)\s*=\s*(\d+)',pin_block)}
checks=[]
def exact(net,expected):
    assert nets[net]==set(expected), (net,nets[net],set(expected))
    checks.append(f'PASS {net}: {sorted(expected)}')
for key,term in [('SCK','SCK'),('MOSI','MOSI'),('CS','CS'),('DC','DC'),('RST','RST')]:
    exact('LCD_'+key,[('U1',f'GPIO{pins[key]}'),('DS1',term)])
for key in ['SDA','SCL']:
    exact('I2C_'+key,[('U1',f'GPIO{pins[key]}')]+[(ref,key) for ref in ['U2','U3','U4','U5']])
exact('MENU',[('U1',f'GPIO{pins["BUTTON"]}'),('SW1','1')])
exact('AUDIO_OFF',[('U1',f'GPIO{pins["SOUND"]}'),('J1','1')])
assert not ({12,13} & set(pins.values())), 'Proposed GPS GPIO conflicts with firmware'
exact('GPS_TX_TO_RX12',[('U6','TXD'),('U1','GPIO12')])
exact('GPS_RX_FROM_TX13',[('U6','RXD'),('U1','GPIO13')])
exact('+3V3',[('U1','3V3'),('DS1','VCC'),('U2','CS')]+[(ref,'VCC') for ref in ['U2','U3','U4','U5','U6']])
exact('GND',[('U1','GND'),('DS1','GND'),('U2','SDO'),('SW1','2'),('J1','2')]+[(ref,'GND') for ref in ['U2','U3','U4','U5','U6']])
exact('GNSS_RF',[('U6','ANT'),('AE1','1')])
for ref,expected_pins in [('BT1',{'1','2'}),('J2',{'1','2','3'}),('LS1',{'1','2'})]:
    actual=set()
    for name,members in nets.items():
        for r,p in members:
            if r==ref:
                assert name.startswith('unconnected-') and len(members)==1, (ref,p,name)
                actual.add(p)
    assert actual==expected_pins
    checks.append(f'PASS {ref}: every lead isolated')
assert all(r!='U7' for members in nets.values() for r,p in members)
checks.append('PASS remote board has no wired connection to Super Mini')
values=[x.text for x in tree.findall('./components/comp/value')]
assert len(values)==14, values
assert not any('SD module' in v for v in values)
checks.append('PASS 14 schematic items plus power symbols; old SD module absent')
report='Connectivity checks against firmware + explicit draft constraints\n\n'+'\n'.join(checks)+'\n\nPASS. Hardware identities, VIN ratings, footprints and battery power stage remain unverified.\n'
(out/'validation.txt').write_text(report,encoding='utf8')
print(report)
