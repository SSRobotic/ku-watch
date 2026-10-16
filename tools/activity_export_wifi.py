"""Read stopped activities through the authenticated watch setup portal."""
from pathlib import Path
import argparse,getpass,json,time,urllib.request,urllib.parse
from activity_export import save_activity
class WifiWatch:
    def __init__(self,url,password):
        if not url.startswith('http://'):raise ValueError('Use the local watch http:// address')
        self.url=url.rstrip('/')+'/';self.password=password
        manager=urllib.request.HTTPPasswordMgrWithDefaultRealm();manager.add_password(None,self.url,'admin',password)
        self.opener=urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(manager))
    def get(self,path):
        with self.opener.open(self.url+path,timeout=30) as r:return r.read()
    def close(self):pass
    def list(self):
        result=json.loads(self.get('activities'))
        return sorted((r['id'],r['size']) for r in result['files'] if r['id']!=result['active'])
    def status(self):
        result=json.loads(self.get('activities'));return {'active':bool(result['active']),'ready':1,'id':result['active'],'count':len(result['files']),'message':'WIFI READY'}
    def set_time(self):
        data=urllib.parse.urlencode({'token':self.password,'utc':int(time.time())}).encode()
        with self.opener.open(urllib.request.Request(self.url+'clock',data=data),timeout=5) as r:r.read()
    def download(self,identity):return self.get('activity?id='+str(int(identity)))
    def remove(self,identity):
        data=urllib.parse.urlencode({'token':self.password,'id':int(identity)}).encode()
        with self.opener.open(urllib.request.Request(self.url+'delete',data=data),timeout=5) as r:r.read()
def main():
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--id',type=int);p.add_argument('--output',type=Path,default=Path('activities'));a=p.parse_args()
    watch=WifiWatch(a.url,getpass.getpass('Watch setup password: '))
    if a.id is None:print(watch.list())
    else:print(save_activity(watch.download(a.id),a.id,a.output)[0])
if __name__=='__main__':main()
