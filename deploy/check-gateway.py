"""Verify Caddy auth/proxy/control-route behavior on loopback with dummy data."""
import argparse,json,os,socket,subprocess,threading,time
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import httpx
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--caddy',required=True,help='Path to an official Caddy executable')
args=parser.parse_args()
root=Path(__file__).resolve().parents[1];caddy=Path(args.caddy)
scratch=root/'.tmp-gateway-check';scratch.mkdir(exist_ok=True)
def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body=json.dumps({'path':self.path,'authorization_forwarded':bool(self.headers.get('Authorization'))}).encode()
        self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
    do_POST=do_GET
    def log_message(self,*args):pass
upstream=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=upstream.serve_forever,daemon=True).start()
webroot=scratch/'web';webroot.mkdir(exist_ok=True);(webroot/'index.html').write_text('Speculara gateway fixture')
listen=port();pwd='local-test-only';env={**os.environ,'DOMAIN':f'http://127.0.0.1:{listen}','SITE_USER':'tester'}
env['SITE_PASSWORD_HASH']=subprocess.check_output([str(caddy),'hash-password','--algorithm','bcrypt','--bcrypt-cost','4','--plaintext',pwd],text=True).strip()
source=(root/'deploy/Caddyfile').read_text().replace('backend:8000',f'127.0.0.1:{upstream.server_port}').replace('/srv/www',json.dumps(webroot.as_posix()))
fixture=scratch/'fixture.Caddyfile';fixture.write_text('{\n admin off\n}\n'+source)
adapted=subprocess.run([str(caddy),'adapt','--config',str(fixture),'--adapter','caddyfile','--validate'],env=env,capture_output=True,text=True)
assert adapted.returncode==0,adapted.stderr
proc=subprocess.Popen([str(caddy),'run','--config',str(fixture),'--adapter','caddyfile'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    with httpx.Client(base_url=f'http://127.0.0.1:{listen}',timeout=3) as client:
        for _ in range(40):
            try:client.get('/');break
            except httpx.ConnectError:time.sleep(.1)
        assert client.get('/').status_code==401
        assert client.get('/api/health').status_code==401
        auth=('tester',pwd)
        assert client.get('/',auth=auth).text=='Speculara gateway fixture'
        assert client.get('/deep/spa/route',auth=auth).text=='Speculara gateway fixture'
        result=client.get('/api/health',auth=auth).json()
        assert result['path']=='/api/health' and result['authorization_forwarded'] is False
        for path in ('/api/collector/login','/api/collector/login/finish','/api/collector/cancel'):
            assert client.post(path,auth=auth,headers={'X-Forwarded-For':'127.0.0.1'}).status_code==403
    print('Caddy validation and 8 loopback gateway checks passed: authentication, SPA fallback, API proxy, credential stripping, operator routes.')
finally:
    proc.terminate();proc.wait(timeout=10);upstream.shutdown();upstream.server_close()
