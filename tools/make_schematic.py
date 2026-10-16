"""Build a module-level, editable KiCad schematic from the documented wiring.

Symbols use functional terminal IDs, not guessed physical header pin numbers.
This is an interconnect draft; battery power design and footprints are pending.
"""
from pathlib import Path
import json
import uuid
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'hardware' / 'KU_Watch'
OUT.mkdir(parents=True, exist_ok=True)
NAME = 'KU_Watch'
NS = uuid.UUID('699a6c52-9c90-473c-8b66-3b484295b367')
counter = 0
def uid(key=None):
    global counter
    counter += 1
    return str(uuid.uuid5(NS, str(key) if key else f'item-{counter}'))
def q(s): return json.dumps(str(s), ensure_ascii=False)
def n(v): return f'{v:.4f}'.rstrip('0').rstrip('.')
def xy(x,y): return f'{n(x)} {n(y)}'
def effects(size=1.27, justify='', hide=False, bold=False):
    if size == 1.016: size = 1.27
    return f'(effects (font (size {n(size)} {n(size)})' + (' (bold yes)' if bold else '') + ')' + (f' (justify {justify})' if justify else '') + (' (hide yes)' if hide else '') + ')'

root_id = uid('root')
lib = {}
objects = []
instances = {}
native_lib = {}
power_count = 0

def balanced_block(source, start):
    depth=0; quoted=False; escape=False
    for i in range(start,len(source)):
        c=source[i]
        if escape: escape=False; continue
        if c=='\\' and quoted: escape=True; continue
        if c=='"': quoted=not quoted
        if not quoted:
            if c=='(': depth+=1
            if c==')': depth-=1
            if depth==0: return source[start:i+1]
    raise ValueError('Unclosed symbol')

def native(lib_id,ref,value,x,y,fields=None,bom=True):
    """Embed the installed KiCad 10 symbol without approximating its graphics."""
    category,name=lib_id.split(':',1)
    if lib_id not in native_lib:
        source=(Path('D:/KiCad/share/kicad/symbols')/(category+'.kicad_sym')).read_text(encoding='utf8')
        block=balanced_block(source,source.index(f'(symbol {q(name)}'))
        native_lib[lib_id]=block.replace(f'(symbol {q(name)}',f'(symbol {q(lib_id)}',1)
    definition=native_lib[lib_id]
    power=ref.startswith('#PWR')
    s=f'(symbol (lib_id {q(lib_id)}) (at {xy(x,y)} 0) (unit 1) (exclude_from_sim yes) (in_bom {"yes" if bom else "no"}) (on_board no) (dnp no) (uuid {q(uid(ref))})'
    rx,ry,vx,vy=fields or (x,y-10.16,x,y-6.35)
    s+=prop('Reference',ref,rx,ry,1.27,hide=power)
    s+=prop('Value',value,vx,vy,1.27,hide=(lib_id=='power:GND'))
    s+=prop('Footprint','',x,y,hide=True)+prop('Datasheet','',x,y,hide=True)
    terms={}
    for match in re.finditer(r'\(pin\s+(?:input|output|bidirectional|passive|power_in|power_out|open_collector)\s+\w+',definition):
        pin=balanced_block(definition,match.start())
        at=re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)',pin)
        px,py,angle=map(float,at.groups())
        number=re.search(r'\(number\s+"([^"]+)"',pin).group(1)
        side={0:'L',180:'R',90:'B',270:'T'}[int(angle)]
        terms[number]=(round(x+px,4),round(y-py,4),side)
        s+=f'(pin {q(number)} (uuid {q(uid(ref+number))}))'
    s+=f'(instances (project {q(NAME)} (path {q("/"+root_id)} (reference {q(ref)}) (unit 1)))))'
    objects.append(s); instances[ref]=terms
    return terms

def power_at(net,x,y):
    global power_count
    power_count+=1
    lib_id='power:GND' if net=='GND' else 'power:+3V3'
    value='GND' if net=='GND' else '+3V3'
    native(lib_id,f'#PWR{power_count:03}',value,x,y,fields=(x,y,x,y-4.572),bom=False)

def graphic_path(points):
    return '(polyline (pts '+' '.join(f'(xy {xy(*p)})' for p in points)+') (stroke (width 0.254) (type default)) (fill (type none)))'

def graphic_circle(x,y,r):
    return f'(circle (center {xy(x,y)}) (radius {n(r)}) (stroke (width 0.254) (type default)) (fill (type none)))'
def prop(name,value,x,y,size=1.27,hide=False):
    return f'(property {q(name)} {q(value)} (at {xy(x,y)} 0) {effects(size,hide=hide)})'
def module(name,width,height,pins,description,shape=None):
    # pins: (functional terminal ID, visible name, side, screen y offset, type)
    half=width/2
    hidden_names=' (hide yes)' if shape=='switch' else ''
    s = f'(symbol {q(name)} (pin_numbers (hide yes)) (pin_names (offset 1.016){hidden_names}) (exclude_from_sim yes) (in_bom yes) (on_board no)'
    s += prop('Reference','U',0,height/2+5.08)+prop('Value',name,0,height/2+2.54)
    s += prop('Footprint','',0,0,hide=True)+prop('Datasheet','',0,0,hide=True)+prop('Description',description,0,0,hide=True)
    s += f'(symbol {q(name+"_0_1")} '
    if shape=='switch':
        for cx in [-half,half]:
            s += f'(circle (center {xy(cx,0)}) (radius 0.762) (stroke (width 0.254) (type default)) (fill (type none)))'
        s += f'(polyline (pts (xy {xy(-half,0)}) (xy {xy(half-1.27,3.81)})) (stroke (width 0.254) (type default)) (fill (type none)))'
    else:
        s += f'(rectangle (start {xy(-half,height/2)}) (end {xy(half,-height/2)}) (stroke (width 0.254) (type default)) (fill (type background)))'
    # Small graphics identify the function of a complete board, not a guessed IC circuit.
    if shape=='display':
        s+=graphic_circle(0,-14,7.2)
        s+=graphic_path([(0,-9),(0,-14),(4,-16)])
        for dx,dy in [(0,1),(1,0),(0,-1),(-1,0)]:
            s+=graphic_path([(dx*5.8,-14+dy*5.8),(dx*6.7,-14+dy*6.7)])
    elif shape=='mcu':
        s+=graphic_path([(-5,29),(-5,35),(5,35),(5,29),(-5,29)])
        for xx in [-3,0,3]:
            s+=graphic_path([(xx,35),(xx,36.8)])+graphic_path([(xx,29),(xx,27.2)])
        s+=graphic_path([(-7,31),(-5,31)])+graphic_path([(5,31),(7,31)])
    elif shape=='remote':
        s+=graphic_circle(-25,0,9)
        s+=graphic_path([(-25,6),(-25,0),(-21,-3)])
    s += ')'
    s += f'(symbol {q(name+"_1_1")} '
    for number,label,side,dy,kind in pins:
        x = -half-5.08 if side=='L' else half+5.08
        angle = 0 if side=='L' else 180
        s += f'(pin {kind} line (at {xy(x,-dy)} {angle}) (length 5.08) (name {q(label)} {effects(1.016)}) (number {q(number)} {effects(0.762)}))'
    s += '))'
    lib[name]=(s,width,height,pins,description)

def place(name,ref,value,x,y,bom=True):
    sym,width,height,pins,desc=lib[name]
    symbol_id=uid(ref)
    s=f'(symbol (lib_id {q("KU_Watch:"+name)}) (at {xy(x,y)} 0) (unit 1) (exclude_from_sim yes) (in_bom {"yes" if bom else "no"}) (on_board no) (dnp no) (uuid {q(symbol_id)})'
    s+=prop('Reference',ref,x,y-height/2-6.35,1.27)
    s+=prop('Value',value,x,y-height/2-3.175,1.016)
    s+=prop('Footprint','',x,y,hide=True)+prop('Datasheet','',x,y,hide=True)+prop('Description',desc,x,y,hide=True)
    terms={}
    for number,label,side,dy,kind in pins:
        terms[number]=(round(x+(-width/2-5.08 if side=='L' else width/2+5.08),4), round(y+dy,4), side)
        s+=f'(pin {q(number)} (uuid {q(uid(ref+number))}))'
    s+=f'(instances (project {q(NAME)} (path {q("/"+root_id)} (reference {q(ref)}) (unit 1)))))'
    objects.append(s)
    instances[ref]=terms
    return terms
def wire(a,b):
    if a==b: return
    objects.append(f'(wire (pts (xy {xy(*a)}) (xy {xy(*b)})) (stroke (width 0) (type default)) (uuid {q(uid())}))')
def junction(x,y):
    objects.append(f'(junction (at {xy(x,y)}) (diameter 0) (color 0 0 0 0) (uuid {q(uid())}))')
def label(name,x,y,angle=0):
    objects.append(f'(label {q(name)} (at {xy(x,y)} {angle}) {effects(1.016,"left bottom")} (uuid {q(uid())}))')
def stub(ref,pin,net,length=10.16):
    x,y,side=instances[ref][pin]
    if net in ['3V3_MINI','GND','+3V3']:
        end=(round(x-7.62 if side=='L' else x+7.62,4),y)
        wire((x,y),end); power_at(net,*end)
        return
    end=(round(x-length if side=='L' else x+length,4),y)
    wire((x,y),end)
    # Place labels above the stub, growing away from the symbol for left pins.
    label(net,end[0],y)
def nc(ref,pin):
    x,y,_=instances[ref][pin]
    objects.append(f'(no_connect (at {xy(x,y)}) (uuid {q(uid())}))')
def text(s,x,y,size=1.27,bold=False):
    objects.append(f'(text {q(s)} (at {xy(x,y)} 0) {effects(size,"left",bold=bold)} (uuid {q(uid())}))')
def line(points,dash=False):
    p=' '.join(f'(xy {xy(*v)})' for v in points)
    objects.append(f'(polyline (pts {p}) (stroke (width 0.254) (type {"dash" if dash else "default"})) (fill (type none)) (uuid {q(uid())}))')
def box(x1,y1,x2,y2): line([(x1,y1),(x2,y1),(x2,y2),(x1,y2),(x1,y1)],True)

module('SuperMini_Functional',50.8,76.2,[
 ('3V3','3V3 (USB regulator)','L',-25.4,'power_out'),('GND','GND','L',-20.32,'power_out'),
 ('GPIO4','GPIO4 / MENU','L',-5.08,'input'),('GPIO2','GPIO2 / AUDIO','L',5.08,'output'),
 ('GPIO12','GPIO12 / GPS_RX*','L',20.32,'input'),('GPIO13','GPIO13 / GPS_TX*','L',25.4,'output'),
 ('GPIO10','GPIO10 / SCK','R',-25.4,'output'),('GPIO11','GPIO11 / MOSI','R',-20.32,'output'),
 ('GPIO6','GPIO6 / CS','R',-15.24,'output'),('GPIO7','GPIO7 / DC','R',-10.16,'output'),('GPIO5','GPIO5 / RST','R',-5.08,'output'),
 ('GPIO8','GPIO8 / SDA','R',10.16,'bidirectional'),('GPIO9','GPIO9 / SCL','R',15.24,'output')
], 'Module-level ESP32-S3 Super Mini. Functional GPIO IDs, not package/header numbers. Powered by its existing USB-C regulator in this draft. Only used terminals shown. GPS pins are proposed.',shape='mcu')
module('GC9A01_Module',40.64,50.8,[
 ('SCK','SCL / SCK','L',-20.32,'input'),('MOSI','SDA / DIN','L',-15.24,'input'),('CS','CS','L',-10.16,'input'),('DC','DC','L',-5.08,'input'),('RST','RST','L',0,'input'),
 ('VCC','VCC','R',-10.16,'power_in'),('GND','GND','R',-5.08,'power_in'),('BL','BL / BLK*','R',5.08,'passive')
], 'Round 1.28-inch GC9A01(A) 240x240 SPI breakout; verify VIN rating and optional BL header on actual module.',shape='display')
common=[('VCC','VCC / VIN','L',-10.16,'power_in'),('GND','GND','L',-5.08,'power_in'),('SDA','SDA','L',0,'bidirectional'),('SCL','SCL','L',5.08,'input')]
module('BME680_Module',30.48,27.94,common+[
 ('CS','CS / CSB','R',-10.16,'input'),('SDO','SDO','R',-5.08,'input')
], 'BME680 breakout in I2C mode: CS to 3V3; SDO to GND selects 0x76.')
module('MAX30102_Module',30.48,27.94,common+[
 ('INT','INT','R',5.08,'output')
], 'MAX30102 breakout with onboard regulator/level interface. Bare IC is not represented; verify breakout accepts 3.3V supply and logic.')
module('GY51_Module',30.48,27.94,common,
 'GY-51 as named by firmware. Reads accelerometer 0x18 and magnetometer 0x1E. Actual silicon/module variant unverified.')
module('INA226_Module',30.48,27.94,common+[
 ('IN+','IN+','R',-10.16,'passive'),('IN-','IN-','R',-5.08,'passive'),('ALERT','ALERT','R',5.08,'open_collector')
], 'INA226 candidate at 0x40. Firmware checks ACK only. Current path/shunt and address strap must be confirmed; sense terminals not connected.')
module('ATGM336H_Module',40.64,35.56,[
 ('VCC','VCC / VIN*','L',-10.16,'power_in'),('GND','GND','L',-5.08,'power_in'),
 ('TXD','TXD','L',0,'output'),('RXD','RXD','L',5.08,'input'),('PPS','PPS*','R',-5.08,'output'),('ANT','ANT socket','R',5.08,'passive')
], 'ATGM336H GPS/BeiDou breakout with supplied antenna. UART pins proposed; header order, exact variant and VIN range pending verification.')
module('Menu_Button',15.24,12.7,[('1','A','L',0,'passive'),('2','B','R',0,'passive')], 'Normally-open momentary menu button; GPIO4 uses internal pull-up.',shape='switch')
module('Audio_Reserved',25.4,15.24,[('IN','AMP_IN','L',-2.54,'passive'),('GND','GND','L',2.54,'passive')], 'Reserved logic-level interface only; driver/amplifier not selected.',None)
module('Speaker_2Wire',20.32,15.24,[('1','SPK_A','L',-2.54,'passive'),('2','SPK_B','L',2.54,'passive')], 'Existing bare speaker: impedance/power rating and amplifier not specified; both wires isolated.')
module('Battery_3Wire',35.56,20.32,[('A','WIRE A','R',-5.08,'passive'),('B','WIRE B','R',0,'passive'),('C','WIRE C','R',5.08,'passive')], 'Battery 582535, 3.7V nominal, 600mAh, three leads. A/B/C are placeholders, not physical order or polarity. All disconnected pending identification.')
module('Waveshare_Remote',78.74,25.4,[], 'Complete ESP32-S3-Touch-LCD-2.1 board with own USB-C power. Wireless peer only; no wired net to Super Mini. Internal circuits are not reproduced.',shape='remote')

text('KU WATCH  /  SYSTEM SCHEMATIC',20.32,20.32,2.54,True)
text('REV B    |    KiCad 10.0    |    16 SEP 2026',20.32,27.94,1.524)
text('Module wiring + standard electrical symbols. * Proposed connection; confirm on hardware.',20.32,34.29,1.27)
text('01  SUPER MINI + LOCAL DISPLAY',20.32,41.91,1.524,True)
text('02  I2C SENSOR MODULES',259.08,41.91,1.524,True)
place('SuperMini_Functional','U1','ESP32-S3 Super Mini',81.28,88.9)
place('GC9A01_Module','DS1','GC9A01(A) 240x240',193.04,83.82)
for gpio,pin,net in [('GPIO10','SCK','LCD_SCK'),('GPIO11','MOSI','LCD_MOSI'),('GPIO6','CS','LCD_CS'),('GPIO7','DC','LCD_DC'),('GPIO5','RST','LCD_RST')]:
    a=instances['U1'][gpio][:2]; b=instances['DS1'][pin][:2]
    wire(a,b); label(net,a[0]+8.89,a[1])
for pin,net in [('3V3','3V3_MINI'),('GND','GND'),('GPIO4','MENU'),('GPIO2','AUDIO_OFF'),('GPIO12','GPS_TX_TO_RX12'),('GPIO13','GPS_RX_FROM_TX13')]: stub('U1',pin,net,20.32)
for pin,net in [('VCC','3V3_MINI'),('GND','GND')]: stub('DS1',pin,net)
nc('DS1','BL')
text('BL/BLK: module-dependent; held open.',166.37,116.84,1.016)
text('Connect only after checking backlight input.',166.37,121.92,1.016)
text('USB-C powers U1 for this draft.',55.88,134.62,1.016)
text('Only used GPIOs shown; no SD module.',55.88,139.7,1.016)

for name,ref,value,x,y in [
 ('BME680_Module','U2','BME680',294.64,73.66),('MAX30102_Module','U3','MAX30102 breakout',375.92,73.66),
 ('GY51_Module','U4','GY-51 (variant TBD)',294.64,134.62),('INA226_Module','U5','INA226 (ACK only)',375.92,134.62)]:
    place(name,ref,value,x,y)
    for p,net in [('VCC','3V3_MINI'),('GND','GND')]: stub(ref,p,net,12.7)
# Continuous two-wire bus from U1 to all four modules; junctions show real taps.
bus_taps={'SDA':[],'SCL':[]}
for upper,lower in [('U2','U4'),('U3','U5')]:
    for p,offset in [('SDA',20.32),('SCL',15.24)]:
        ax,ay,_=instances[upper][p]; bx,by,_=instances[lower][p]
        trunk=round(ax-offset,4)
        wire((ax,ay),(trunk,ay)); wire((trunk,ay),(trunk,by)); wire((trunk,by),(bx,by))
        rail_y=153.67 if p=='SDA' else 158.75
        wire((trunk,by),(trunk,rail_y)); junction(trunk,by)
        bus_taps[p].append(trunk)
for p,gpio,bend,rail_y in [('SDA','GPIO8',142.24,153.67),('SCL','GPIO9',147.32,158.75)]:
    x,y,_=instances['U1'][gpio]
    wire((x,y),(bend,y)); label('I2C_'+p,x+7.62,y)
    wire((bend,y),(bend,rail_y))
    previous=bend
    for i,tap in enumerate(bus_taps[p]):
        wire((previous,rail_y),(tap,rail_y))
        if i<len(bus_taps[p])-1: junction(tap,rail_y)
        previous=tap
    label('I2C_'+p,175.26,rail_y)
stub('U2','CS','3V3_MINI',7.62); stub('U2','SDO','GND',7.62)
nc('U3','INT')
for p in ['IN+','IN-','ALERT']: nc('U5',p)
text('0x76 (CS high, SDO low)',269.24,99.06,1.016)
text('Temp / humidity / pressure',269.24,104.14,1.016)
text('0x57; IR + BPM',350.52,99.06,1.016)
text('Regulated breakout, not bare IC.',350.52,104.14,1.016)
text('0x18 ACC + 0x1E MAG',269.24,165.1,1.016)
text('Confirm chip / header markings.',269.24,170.18,1.016)
text('0x40; sense path unassigned.',350.52,165.1,1.016)
text('No voltage/current readout yet.',350.52,170.18,1.016)

text('03  CONTROLS / GPS ON SUPER MINI',20.32,153.67,1.524,True)
native('Switch:SW_Push','SW1','MENU',43.18,171.45)
stub('SW1','1','MENU',10.16); stub('SW1','2','GND',10.16)
text('GPIO4 -> switch -> GND',20.32,183.515,1.016)
text('Internal pull-up in firmware.',20.32,188.595,1.016)
native('Connector_Generic:Conn_01x02','J1','AMP INPUT (reserved)',114.3,173.99,bom=False)
stub('J1','1','AUDIO_OFF',20.32); stub('J1','2','GND',10.16)
native('Device:Speaker','LS1','Speaker',114.3,203.2)
nc('LS1','1');nc('LS1','2')
text('GPIO2 disabled in firmware.',88.9,218.44,1.016)
text('Amplifier/driver required.',88.9,223.52,1.016)
place('ATGM336H_Module','U6','ATGM336H + antenna',200.66,186.69)
for p,net in [('VCC','3V3_MINI'),('GND','GND'),('TXD','GPS_TX_TO_RX12'),('RXD','GPS_RX_FROM_TX13')]: stub('U6',p,net,25.4)
nc('U6','PPS')
native('Device:Antenna','AE1','GNSS antenna',243.84,177.8,fields=(244,169.545,244,172.72))
rf=instances['U6']['ANT'][:2]; ant=instances['AE1']['1'][:2]
wire(rf,(ant[0],rf[1])); wire((ant[0],rf[1]),ant); label('GNSS_RF',rf[0]+1.27,rf[1])
text('* Proposed UART: TXD -> GPIO12; RXD <- GPIO13.',149.86,214.63,1.016)
text('Confirm exposed GPIOs, module VIN and header order.',149.86,219.71,1.016)
text('Firmware UART/GPS not implemented. Antenna supplied.',149.86,224.79,1.016)

text('04  WIRELESS REMOTE DISPLAY',269.24,179.07,1.524,True)
text('Super Mini  < - - ESP-NOW TWO-WAY - - >  Remote',269.24,187.96,1.016)
place('Waveshare_Remote','U7','ESP32-S3-Touch-LCD-2.1',332.74,215.9)
text('480x480 touch LCD',320.04,211.455,1.27)
text('Own USB-C supply',320.04,217.805,1.27)
text('Telemetry -> / <- commands + ACK (planned)',279.4,232.41,1.27)
text('No physical signal/ground wire between boards.',279.4,237.49,1.016)
text('Same radio channel; ESP-NOW firmware pending.',279.4,242.57,1.016)

text('05  BATTERY FOR SUPER MINI - POWER DESIGN PENDING',20.32,237.49,1.524,True)
native('Device:Battery_Cell','BT1','3.7V / 600mAh',33.02,260.35,fields=(33.02,246.38,33.02,249.555))
for pin in ['1','2']: nc('BT1',pin)
native('Connector_Generic:Conn_01x03','J2','3-wire pack',68.58,259.08,fields=(68.58,246.38,68.58,249.555),bom=False)
for pin in ['1','2','3']: nc('J2',pin)
text('582535',25.4,269.24,1.27)
text('Mapping TBD',54.61,269.24,1.27)
box(88.9,246.38,193.04,273.05)
text('REQUIRED POWER STAGE - PARTS NOT SELECTED',93.98,252.73,1.016,True)
text('Charge / protection / regulated output / USB power sharing',93.98,260.35,1.016)
text('Battery is isolated. Do not connect raw cell to 3V3.',93.98,267.97,1.016)
text('J2 lead order / polarity unknown. Cell + / - are conceptual only.',20.32,280.67,1.016)

text('BUILD NOTES',203.2,239.395,1.27,True)
text('Module-level assembly draft, not a PCB.',203.2,245.11,1.016)
text('Terminal IDs are functions, not header positions.',203.2,250.19,1.016)
text('Verify 3.3V-compatible VIN / logic on breakouts.',203.2,255.27,1.016)
text('I2C pull-ups: check installed module resistors.',203.2,260.35,1.016)
text('No added pull-ups until bus loading is checked.',203.2,265.43,1.016)
text('No footprints assigned. See README_TH.md.',203.2,270.51,1.016)

embedded=list(native_lib.values())
for name,(sym,*_) in lib.items(): embedded.append(sym.replace(f'(symbol {q(name)}',f'(symbol {q("KU_Watch:"+name)}',1))
head=f'''(kicad_sch (version 20260306) (generator "ku_watch_schematic") (generator_version "2.0")
(uuid {q(root_id)}) (paper "A3")
(title_block (title "KU Watch - system schematic") (date "2026-09-16") (rev "B")
 (company "ESP32-S3 Super Mini + wireless touch display")
 (comment 1 "GPIOs from firmware; GPS proposed; battery power stage pending"))
(lib_symbols {''.join(embedded)})
'''
schematic=head+'\n'.join(objects)+f'\n(sheet_instances (path "/" (page "1"))))\n'
(OUT/f'{NAME}.kicad_sch').write_text(schematic,encoding='utf-8')
library='(kicad_symbol_lib (version 20241209) (generator "ku_watch_schematic")\n'+'\n'.join(v[0] for v in lib.values())+')\n'
(OUT/f'{NAME}.kicad_sym').write_text(library,encoding='utf-8')
(OUT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "KU_Watch") (type "KiCad") (uri "${KIPRJMOD}/KU_Watch.kicad_sym") (options "") (descr "Module-level functional terminals; no physical footprints")))\n',encoding='utf-8')
project={'meta':{'filename':NAME+'.kicad_pro','version':1},'net_settings':{'classes':[{'name':'Default','clearance':0.2,'track_width':0.25,'via_diameter':0.8,'via_drill':0.4,'wire_width':6,'bus_width':12}],'meta':{'version':3}},'schematic':{'drawing':{'default_line_thickness':6,'default_text_size':50,'pin_symbol_size':25,'label_size_ratio':0.375},'meta':{'version':1}},'text_variables':{}}
(OUT/f'{NAME}.kicad_pro').write_text(json.dumps(project,indent=2)+'\n',encoding='utf-8')
print(OUT/f'{NAME}.kicad_sch')
