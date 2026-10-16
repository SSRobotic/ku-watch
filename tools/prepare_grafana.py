"""Repair only KU Watch provisioning paths and prepare 1s live refresh.

Back up installed configuration and verify that provisioned JSON preserves the
stored dashboards. Never write Grafana's database or change authentication.
"""
from pathlib import Path
import argparse,configparser,datetime,json,re,sqlite3

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--home',type=Path,default=Path('D:/iot2026/Grafana/grafana'))
    a=p.parse_args(); home=a.home
    provider=home/'conf/provisioning/dashboards/ku-watch.yaml'
    custom=home/'conf/custom.ini'
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup=ROOT/'output/grafana_config_backup'/stamp
    backup.mkdir(parents=True,exist_ok=True)
    sources={}
    con=sqlite3.connect((home/'data/grafana.db').as_uri()+'?mode=ro',uri=True)
    try:
        for uid in ['ku-watch-live','ku-watch-friends']:
            row=con.execute('SELECT data FROM dashboard WHERE uid=?',(uid,)).fetchone()
            stored=json.loads(row[0]) if row else None
            if stored is None:
                row=con.execute("SELECT value FROM resource WHERE resource='dashboards' AND name=?",(uid,)).fetchone()
                if row: stored=json.loads(row[0])['spec']
            if stored is None: raise RuntimeError('Stored KU dashboard missing: '+uid)
            source=ROOT/'integration/grafana'/(uid+'.json')
            data=json.loads(source.read_text(encoding='utf8'))
            differences=[k for k in set(stored)|set(data)
                         if k not in {'id','uid','version','refresh','timepicker'} and stored.get(k)!=data.get(k)]
            if differences: raise RuntimeError('Preserve UI edits before provisioning: '+uid+' '+str(differences))
            (backup/(uid+'.local.json')).write_text(json.dumps(stored,ensure_ascii=False,indent=2),encoding='utf8')
            sources[source]=data
    finally: con.close()
    old=provider.read_text(encoding='utf8')
    if old.count('      path:')!=1 or 'name: KU Watch' not in old:
        raise RuntimeError('Unexpected KU provider; no changes made')
    new=re.sub(r'(?m)^      path:.*$', '      path: '+(ROOT/'integration/grafana').as_posix(),old)
    configuration=configparser.ConfigParser(interpolation=None)
    if custom.exists(): configuration.read(custom,encoding='utf-8-sig')
    if not configuration.has_section('dashboards'): configuration.add_section('dashboards')
    configuration.set('dashboards','min_refresh_interval','1s')
    changed=[]
    for file,content in [(provider,new),(ROOT/'integration/grafana/ku-watch.yaml',new)]:
        previous=file.read_text(encoding='utf8') if file.exists() else ''
        if previous!=content:
            (backup/('installed-provider.yaml' if file==provider else 'source-provider.yaml')).write_text(previous,encoding='utf8')
            file.write_text(content,encoding='utf8');changed.append(str(file))
    live=ROOT/'integration/grafana/ku-watch-live.json'
    data=sources[live]
    if data.get('refresh')!='1s' or '1s' not in data.get('timepicker',{}).get('refresh_intervals',[]):
        (backup/'live-source.json').write_bytes(live.read_bytes())
        data['refresh']='1s'; data.setdefault('timepicker',{})['refresh_intervals']=['1s','5s','10s','30s','1m']
        live.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8');changed.append(str(live))
    # Write only when this setting differs, preserving all existing settings.
    original=configparser.ConfigParser(interpolation=None)
    if custom.exists(): original.read(custom,encoding='utf-8-sig')
    if original.get('dashboards','min_refresh_interval',fallback=None)!='1s':
        if custom.exists(): (backup/'custom.before.local.ini').write_bytes(custom.read_bytes())
        with custom.open('w',encoding='utf8') as f: configuration.write(f)
        changed.append(str(custom))
    report={'boundary':'Configuration prepared on disk; service restart and runtime verification required',
            'changed':changed,'backup':str(backup),'database_modified':False,
            'live_refresh':'1s','friends_refresh':sources[ROOT/'integration/grafana/ku-watch-friends.json']['refresh']}
    target=ROOT/'output/requirements_audit_20261009/grafana_config_20261010.json'
    target.write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))

if __name__=='__main__': main()
