"""Loopback-only checks of the Render gateway with dummy upstreams and keys."""
import argparse, json, os, socket, subprocess, threading, time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import httpx

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--caddy', required=True)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
caddy=str(Path(args.caddy).resolve())
scratch=root/'.tmp-gateway-check';scratch.mkdir(exist_ok=True)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
        self.wfile.write(json.dumps({'path':self.path,'authorization':self.headers.get('Authorization')}).encode())
    def log_message(self,*args):pass

upstream=ThreadingHTTPServer(('127.0.0.1',0), Handler)
threading.Thread(target=upstream.serve_forever,daemon=True).start()
password='dummy-operator-only'
hashed=subprocess.run([caddy,'hash-password','--algorithm','bcrypt','--bcrypt-cost','4'],input=password,text=True,capture_output=True,check=True).stdout.strip()
checks=0
try:
    for enabled in ('0','1'):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
        env={**os.environ,'PORT':str(port),'SPECULARA_INTERNAL_API_PORT':str(upstream.server_port),'ENABLE_REMOTE_DESKTOP':enabled,'OPERATOR_PASSWORD_HASH':hashed}
        source=(root/'deploy/RenderCaddyfile').read_text().replace(':{$PORT:10000} {','http://127.0.0.1:{$PORT:10000} {').replace('127.0.0.1:6080',f'127.0.0.1:{upstream.server_port}')
        fixture=scratch/'render.Caddyfile';fixture.write_text(source)
        validation=subprocess.run([caddy,'adapt','--config',str(fixture),'--adapter','caddyfile','--validate'],env=env,capture_output=True,text=True)
        assert validation.returncode==0,validation.stderr
        proc=subprocess.Popen([caddy,'run','--config',str(fixture),'--adapter','caddyfile'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=3,trust_env=False) as client:
                for _ in range(40):
                    try:client.get('/');break
                    except httpx.ConnectError:time.sleep(.1)
                result=client.get('/api/access',headers={'Authorization':'Bearer dummy-demo'})
                assert result.status_code==200,(result.status_code,result.text)
                assert result.json()['authorization']=='Bearer dummy-demo';checks+=1
                path='/operator/desktop/vnc.html'
                assert client.get(path).status_code==(401 if enabled=='1' else 404);checks+=1
                auth=('operator',password)
                if enabled=='1':
                    assert client.get(path,auth=auth).json()['path']=='/vnc.html';checks+=1
                    assert client.get(path,auth=auth,headers={'Origin':'https://evil.example'}).status_code==403;checks+=1
                    assert client.get(path,auth=auth,headers={'Origin':f'https://127.0.0.1:{port}'}).status_code==200;checks+=1
                else:
                    assert client.get(path,auth=auth).status_code==404;checks+=1
        finally:
            proc.terminate();proc.wait(timeout=10)
finally:upstream.shutdown()
print(f'{checks} Render gateway checks passed; real hosted WebSocket/browser smoke remains required.')
