"""Prepare bounded ODbL OpenStreetMap vector packs; upload without erasing activities.

Uses raw Overpass geometry, not the public raster tile service. Cached source JSON,
metadata and .kum are redistributable under ODbL: https://opendatacommons.org/licenses/odbl/.
"""
import argparse
import datetime
import json
import math
from pathlib import Path
import struct
import sys
import time
import urllib.parse
import urllib.request
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "vendor"))
HEADER = struct.Struct("<8sIiiIHHI24sII")
FEATURE = struct.Struct("<HHBB")
POINT = struct.Struct("<ii")
MAX_FEATURES, MAX_POINTS = 4096, 32768
USER_AGENT = "KUWatchMap/1.6 (local university wearable prototype; single-area preparation)"

def simplify(points, tolerance):
    if len(points) < 3:
        return points
    a, b = points[0], points[-1]
    dx, dy = b[0]-a[0], b[1]-a[1]
    denominator = dx*dx+dy*dy
    best, index = 0, 0
    for i, p in enumerate(points[1:-1], 1):
        t = max(0, min(1, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/denominator)) if denominator else 0
        distance = math.hypot(p[0]-a[0]-t*dx, p[1]-a[1]-t*dy)
        if distance > best:
            best, index = distance, i
    if best <= tolerance:
        return [a, b]
    return simplify(points[:index+1], tolerance)[:-1] + simplify(points[index:], tolerance)

def clip_segment(a, b, radius):
    dx, dy = b[0]-a[0], b[1]-a[1]
    low, high = 0, 1
    for p, q in ((-dx,a[0]+radius),(dx,radius-a[0]),(-dy,a[1]+radius),(dy,radius-a[1])):
        if p == 0:
            if q < 0:
                return None
        else:
            t = q/p
            if p < 0:
                low = max(low, t)
            else:
                high = min(high, t)
            if low > high:
                return None
    return ((a[0]+low*dx,a[1]+low*dy), (a[0]+high*dx,a[1]+high*dy))

def clip_line(points, radius):
    result, current = [], []
    for a,b in zip(points,points[1:]):
        segment = clip_segment(a,b,radius)
        if segment is None:
            if len(current)>1: result.append(current)
            current=[]
            continue
        c,d=segment
        if current and math.dist(current[-1],c)<.01:
            current.append(d)
        else:
            if len(current)>1: result.append(current)
            current=[c,d]
    if len(current)>1: result.append(current)
    return result

def clip_polygon(points, radius):
    if points and points[0]==points[-1]: points=points[:-1]
    for axis,sign in ((0,1),(0,-1),(1,1),(1,-1)):
        output=[]
        if not points: break
        previous=points[-1]
        for p in points:
            inside=p[axis]*sign<=radius
            was_inside=previous[axis]*sign<=radius
            if inside != was_inside:
                t=(sign*radius-previous[axis])/(p[axis]-previous[axis])
                output.append((previous[0]+t*(p[0]-previous[0]),previous[1]+t*(p[1]-previous[1])))
            if inside: output.append(p)
            previous=p
        points=output
    return points+[points[0]] if len(points)>=3 else []

def prepare(source, lat, lon, radius, name):
    if not (-85<lat<85 and -180<=lon<=180 and 100<=radius<=10000):
        raise ValueError("Invalid map center or radius")
    name_bytes=name.encode("ascii")
    if not name_bytes or len(name_bytes)>23 or any(x<32 or x>126 for x in name_bytes):
        raise ValueError("Area name must be 1..23 printable ASCII characters")
    longitude_scale=111319.490793*math.cos(math.radians(lat))
    candidates=[]
    for element in source.get("elements",[]):
        tags=element.get("tags",{})
        raw=element.get("geometry",[])
        if len(raw)<2: continue
        highway=tags.get("highway")
        if highway and highway not in ("construction","proposed"):
            kind=4
            style=0 if highway in ("motorway","trunk","primary","secondary","tertiary","motorway_link","trunk_link","primary_link") else 2 if highway in ("footway","path","steps","cycleway","pedestrian") else 1
            priority=style
        elif tags.get("building") and tags["building"]!="no": kind,style,priority=3,0,5
        elif tags.get("natural")=="water" or tags.get("landuse")=="basin": kind,style,priority=2,0,3
        elif tags.get("waterway") and tags["waterway"] not in ("riverbank",): kind,style,priority=5,0,3
        elif tags.get("leisure") in ("park","garden","pitch","golf_course") or tags.get("landuse") in ("grass","forest","meadow","farmland","orchard"):
            kind,style,priority=1,0,4
        else: continue
        points=[((p["lon"]-lon)*longitude_scale,(p["lat"]-lat)*111319.490793) for p in raw]
        groups=clip_line(points,radius) if kind in (4,5) else [clip_polygon(points,radius)]
        for points in groups:
            if len(points)<2: continue
            points=simplify(points,1.5)
            if kind not in (4,5) and len(points)>128:
                points=simplify(points,4)
            if len(points)>128 and kind not in (4,5): continue
            distance=min(math.hypot(*p) for p in points)
            candidates.append((priority,distance,kind,style,points,element.get("id")))
    candidates.sort(key=lambda x:(x[0],x[1],x[5] or 0))
    features, vertices, selected_ids=[],[],[]
    dropped={"roads":0,"other":0}
    for _,_,kind,style,points,identifier in candidates:
        converted=[(round((lat+y/111319.490793)*1e7),round((lon+x/longitude_scale)*1e7)) for x,y in points]
        converted=[p for i,p in enumerate(converted) if i==0 or p!=converted[i-1]]
        if len(converted)<2: continue
        if len(features)>=MAX_FEATURES or len(vertices)+len(converted)>MAX_POINTS:
            dropped["roads" if kind==4 else "other"]+=1
            continue
        features.append((len(vertices),len(converted),kind,style))
        vertices.extend(converted)
        selected_ids.append(identifier)
    if not features: raise ValueError("No usable map features found")
    if dropped["roads"]: raise ValueError(f"Area exceeds road capacity ({dropped}); reduce --radius")
    payload=b"".join(FEATURE.pack(*f) for f in features)+b"".join(POINT.pack(*p) for p in vertices)
    header=HEADER.pack(b"KUMAP1\0\0",1,round(lat*1e7),round(lon*1e7),radius,len(features),len(vertices),zlib.crc32(payload),name_bytes.ljust(24,b"\0"),0,0)
    header=header[:-4]+struct.pack("<I",zlib.crc32(header[:-4]))
    meta={"name":name,"latitude":lat,"longitude":lon,"radius_m":radius,"features":len(features),"points":len(vertices),"roads":sum(f[2]==4 for f in features),"omitted_optional_features":dropped["other"],"osm_way_ids":selected_ids,"source":"OpenStreetMap via Overpass API","attribution":"© OpenStreetMap contributors","license":"ODbL 1.0","license_url":"https://www.openstreetmap.org/copyright","payload_crc":f"{zlib.crc32(payload):08x}"}
    return header+payload,meta

def fetch(lat, lon, radius, endpoint):
    dlat=radius/111319.490793;dlon=dlat/math.cos(math.radians(lat))
    bbox=f"{lat-dlat:.7f},{lon-dlon:.7f},{lat+dlat:.7f},{lon+dlon:.7f}"
    query=f'[out:json][timeout:25];(way["highway"]({bbox});way["building"]({bbox});way["waterway"]({bbox});way["natural"="water"]({bbox});way["leisure"~"^(park|garden|pitch|golf_course)$"]({bbox});way["landuse"~"^(grass|forest|meadow|farmland|orchard|basin)$"]({bbox}););out tags geom;'
    request=urllib.request.Request(endpoint,data=urllib.parse.urlencode({"data":query}).encode(),headers={"User-Agent":USER_AGENT})
    with urllib.request.urlopen(request,timeout=45) as response:
        result=json.load(response)
    if result.get("remark"): raise RuntimeError(result["remark"])
    return result

def upload_pack(path, port, slot, log_path=None):
    import serial
    data=Path(path).read_bytes()
    logs=[]
    connection=serial.Serial(port=None,baudrate=115200,timeout=.1)
    connection.dtr=False;connection.rts=False;connection.port=port
    def command(text, prefix, timeout=12):
        connection.write((text+"\n").encode())
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            reply=connection.readline().decode("ascii",errors="replace").strip()
            if reply.startswith("MAP "):
                logs.append(reply)
                if reply.startswith("MAP ERROR"): raise RuntimeError(reply)
                if reply.startswith(prefix): return reply
        raise TimeoutError(f"No {prefix} response to {text[:35]}")
    try:
        with connection:
            connection.reset_input_buffer()
            command("MAPABORT","MAP ABORTED")
            command(f"MAPBEGIN {slot} {len(data)} {zlib.crc32(data):08x}","MAP READY 0")
            for offset in range(0,len(data),96):
                chunk=data[offset:offset+96]
                reply=command(f"MAPDATA {offset} {chunk.hex()}","MAP ACK ")
                if reply!=f"MAP ACK {offset+len(chunk)}": raise RuntimeError("Incorrect upload offset")
                if offset//96%100==0: print(f"Upload {offset+len(chunk)}/{len(data)}",flush=True)
            expected=f"MAP SAVED {slot} {len(data)} {zlib.crc32(data):08x}"
            if command("MAPEND","MAP SAVED ",20)!=expected: raise RuntimeError("Commit CRC mismatch")
            connection.write(b"MAPINFO\nMAPSHOW\n")
            until=time.monotonic()+3
            while time.monotonic()<until:
                reply=connection.readline().decode("ascii",errors="replace").strip()
                if reply.startswith("MAP "): logs.append(reply);print(reply,flush=True)
    finally:
        if log_path: Path(log_path).write_text("\n".join(logs)+"\n",encoding="utf-8")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lat",type=float);parser.add_argument("--lon",type=float)
    parser.add_argument("--radius",type=int,default=1200);parser.add_argument("--name",default="KU BANGKHEN")
    parser.add_argument("--source-json",type=Path);parser.add_argument("--output",type=Path,default=ROOT/"output"/"maps"/"ku_bangkhen.kum")
    parser.add_argument("--endpoint",default="https://overpass-api.de/api/interpreter")
    parser.add_argument("--port");parser.add_argument("--slot",type=int,choices=[0,1],default=0)
    parser.add_argument("--upload-only",type=Path)
    args=parser.parse_args()
    if args.upload_only:
        if not args.port: parser.error("--port required for upload")
        upload_pack(args.upload_only,args.port,args.slot,args.upload_only.with_suffix(".upload.log"));return
    if args.lat is None or args.lon is None: parser.error("--lat and --lon required; use a verified location")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    source=json.loads(args.source_json.read_text(encoding="utf-8")) if args.source_json else fetch(args.lat,args.lon,args.radius,args.endpoint)
    source_path=args.output.with_suffix(".osm.json")
    source_path.write_text(json.dumps(source,ensure_ascii=False),encoding="utf-8")
    pack,metadata=prepare(source,args.lat,args.lon,args.radius,args.name)
    metadata.update(prepared_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),osm_timestamp=source.get("osm3s",{}).get("timestamp_osm_base"),bytes=len(pack),full_crc=f"{zlib.crc32(pack):08x}")
    args.output.write_bytes(pack)
    args.output.with_suffix(".metadata.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in metadata.items() if k!="osm_way_ids"},ensure_ascii=False,indent=2),flush=True)
    if args.port: upload_pack(args.output,args.port,args.slot,args.output.with_suffix(".upload.log"))

if __name__=="__main__": main()
