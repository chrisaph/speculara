"""Protected laptop backend for the existing Netlify frontend. No cloud login needed."""
import argparse
import asyncio
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time

import httpx

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'.tmp-laptop-demo'
CREDS=PRIVATE/'access.json'
STATE=PRIVATE/'status.json'
STOP=PRIVATE/'stop.request'
LOCAL='http://127.0.0.1:8010'
FRONTEND='https://speculara.netlify.app'


def credentials():
    PRIVATE.mkdir(mode=0o700,exist_ok=True)
    if os.name=='nt':
        principal=subprocess.check_output(['whoami'],text=True).strip()
        subprocess.run(['icacls',str(PRIVATE),'/inheritance:r','/grant:r',f'{principal}:(OI)(CI)F'],check=True,stdout=subprocess.DEVNULL)
    else: PRIVATE.chmod(0o700)
    if not CREDS.exists():
        with CREDS.open('x',encoding='utf-8') as file:
            json.dump({'demo':secrets.token_urlsafe(32),'operator':secrets.token_urlsafe(32)},file)
        if os.name!='nt': CREDS.chmod(0o600)
    return json.loads(CREDS.read_text(encoding='utf-8'))


def backend_environment(keys):
    return {**os.environ,'SPECULARA_REQUIRE_AUTH':'1','DEMO_ACCESS_TOKEN':keys['demo'],
            'OPERATOR_ACCESS_TOKEN':keys['operator'],'FRONTEND_URL':FRONTEND,
            'CORS_ORIGINS':FRONTEND+',http://localhost:8443,http://127.0.0.1:8443',
            'CORS_ORIGIN_REGEX':'','SPECULARA_COLLECTOR_DATA_DIR':str(ROOT/'backend/.socialmonitor'),
            'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}


def verify_protection(client,keys):
    assert client.get('/api/access').status_code==401,'Backend is not protected; tunnel refused.'
    response=client.get('/api/access',headers={'Authorization':'Bearer '+keys['demo']})
    assert response.status_code==200 and response.json().get('ok') is True,'Demo key check failed.'
    for action in ('login','login/finish','cancel'):
        response=client.post('/api/collector/'+action,headers={'Authorization':'Bearer '+keys['demo']},json={'network':'instagram'})
        assert response.status_code==403,'Visitor control is not blocked; tunnel refused.'
    response=client.options('/api/access',headers={'Origin':FRONTEND,'Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'authorization'})
    assert response.status_code==200 and response.headers.get('access-control-allow-origin')==FRONTEND,'Netlify CORS check failed.'


def save_state(**values):
    PRIVATE.mkdir(exist_ok=True)
    temp=PRIVATE/'status.new'
    temp.write_text(json.dumps(values,indent=2),encoding='utf-8')
    temp.replace(STATE)


def child_options():
    return {'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}


async def host_ngrok(keys,api):
    import ngrok
    listener=await asyncio.wait_for(ngrok.forward(LOCAL,authtoken=keys['ngrok']),timeout=60)
    try:
        url=listener.url()
        if not url.startswith('https://'):raise RuntimeError('ngrok did not provide an HTTPS endpoint.')
        save_state(status='ready',provider='ngrok',url=url,backend=LOCAL,frontend=FRONTEND,owner=getpass.getuser())
        print('Netlify VITE_API_URL: '+url,flush=True)
        print('Demo code: run laptop-demo.py code to copy it privately. Leave this process running.',flush=True)
        while not STOP.exists():
            if api.poll() is not None:raise RuntimeError('Backend exited; ngrok is being stopped.')
            await asyncio.sleep(1)
    finally:await listener.close()


def start(provider='cloudflare'):
    keys=credentials()
    cloudflared=shutil.which('cloudflared') or str(PRIVATE/'bin/cloudflared.exe')
    if provider=='ngrok':
        if not keys.get('ngrok'):raise RuntimeError('Create a free ngrok account, copy its authtoken, then run laptop-demo.py ngrok-auth. Do not paste the token into chat.')
        try:import ngrok
        except ImportError:raise RuntimeError('Install the optional tunnel SDK: python -m pip install -r deploy/requirements-laptop.txt')
    elif not Path(cloudflared).is_file():
        raise RuntimeError('Install cloudflared first, or put its official Windows executable at .tmp-laptop-demo/bin/cloudflared.exe.')
    # Never attach a public tunnel to an unrelated/pre-existing local server.
    with httpx.Client(base_url=LOCAL,timeout=2,trust_env=False) as client:
        try: client.get('/api/health')
        except httpx.TransportError: pass
        else: raise RuntimeError('Port 8010 is already in use. Stop the previous laptop demo first.')
    STOP.unlink(missing_ok=True)
    save_state(status='starting',backend=LOCAL,frontend=FRONTEND,owner=getpass.getuser())
    api=None;tunnel=None
    with (PRIVATE/'backend.log').open('a',encoding='utf-8') as api_log:
        try:
            api=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8010','--workers','1','--no-proxy-headers','--timeout-graceful-shutdown','15'],
                                 cwd=ROOT/'backend',env=backend_environment(keys),stdin=subprocess.DEVNULL,stdout=api_log,stderr=subprocess.STDOUT,**child_options())
            with httpx.Client(base_url=LOCAL,timeout=10,trust_env=False) as client:
                for _ in range(90):
                    if api.poll() is not None: raise RuntimeError('Backend exited. Inspect .tmp-laptop-demo/backend.log.')
                    try:
                        if client.get('/api/health').json().get('ok'): break
                    except (httpx.TransportError,ValueError): pass
                    time.sleep(1)
                else: raise RuntimeError('Backend did not become ready within 90 seconds.')
                verify_protection(client,keys)
            if provider=='ngrok':
                try:asyncio.run(host_ngrok(keys,api))
                except TimeoutError:raise RuntimeError('ngrok did not connect within 60 seconds. Check this network permits ngrok HTTPS access.')
                return
            # Empty explicit config avoids accidentally selecting an unrelated named tunnel.
            config=PRIVATE/'cloudflared.yml';config.write_text('{}\n',encoding='utf-8')
            tunnel_env={k:v for k,v in os.environ.items() if not any(word in k.upper() for word in ('TOKEN','SECRET','API_KEY','SUPABASE'))}
            tunnel=subprocess.Popen([cloudflared,'--config',str(config),'tunnel','--url',LOCAL,'--protocol','http2','--no-autoupdate'],
                                    cwd=ROOT,env=tunnel_env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',**child_options())
            found=threading.Event()
            def output():
                url=None
                with (PRIVATE/'cloudflared.log').open('a',encoding='utf-8') as log:
                    for line in tunnel.stdout:
                        log.write(line);log.flush()
                        match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',line)
                        if match: url=match.group()
                        # Allocation of a URL does not mean the edge connected.
                        if url and 'Registered tunnel connection' in line and not found.is_set():
                            save_state(status='ready',url=url,backend=LOCAL,frontend=FRONTEND,owner=getpass.getuser())
                            print('Netlify VITE_API_URL: '+url,flush=True)
                            print('Demo code: run laptop-demo.py code to copy it privately. Leave this process running.',flush=True)
                            found.set()
            thread=threading.Thread(target=output,daemon=True);thread.start()
            started=time.monotonic()
            while not STOP.exists():
                if api.poll() is not None: raise RuntimeError('Backend exited; tunnel is being stopped.')
                if tunnel.poll() is not None: raise RuntimeError('Tunnel exited. Inspect .tmp-laptop-demo/cloudflared.log.')
                if not found.is_set() and time.monotonic()-started>90: raise RuntimeError('Tunnel did not connect within 90 seconds. Check DNS/network access and inspect cloudflared.log. Do not point Netlify at an unconnected URL.')
                time.sleep(1)
        finally:
            # Remove public access first; then close only this backend's owned browser.
            if tunnel and tunnel.poll() is None:
                tunnel.terminate()
                try:tunnel.wait(timeout=10)
                except subprocess.TimeoutExpired:tunnel.kill();tunnel.wait()
            if api and api.poll() is None:
                with httpx.Client(base_url=LOCAL,timeout=20,trust_env=False,headers={'X-Speculara-Operator-Key':keys['operator']}) as client:
                    for action in ('cancel','login/finish'):
                        try:client.post('/api/collector/'+action,json={})
                        except httpx.HTTPError:pass
                api.terminate()
                try:api.wait(timeout=20)
                except subprocess.TimeoutExpired:api.kill();api.wait()
            save_state(status='stopped',backend=LOCAL,frontend=FRONTEND)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['start','status','login','finish','cancel','code','stop','ngrok-auth'])
    parser.add_argument('network',nargs='?',default='instagram',choices=['instagram','facebook'])
    parser.add_argument('--provider',choices=['cloudflare','ngrok'],default='cloudflare')
    args=parser.parse_args()
    if args.action=='start':start(args.provider);return
    if args.action=='ngrok-auth':
        if os.name!='nt':raise RuntimeError('Clipboard import is available on Windows only.')
        keys=credentials()
        token=subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command','Get-Clipboard -Raw'],text=True,creationflags=subprocess.CREATE_NO_WINDOW).strip()
        if not 20<=len(token)<=300 or re.search(r'\s|[\x00-\x1f\x7f]',token):
            raise RuntimeError('Clipboard does not look like a single ngrok authtoken. Copy only its value from the ngrok dashboard.')
        keys['ngrok']=token
        CREDS.write_text(json.dumps(keys),encoding='utf-8')
        print('ngrok authtoken saved privately on this laptop. No token was printed.');return
    if args.action=='status':
        print(STATE.read_text(encoding='utf-8') if STATE.exists() else 'Laptop demo has not been started.');return
    if args.action=='stop':
        PRIVATE.mkdir(exist_ok=True);STOP.touch();print('Stop requested.');return
    if not CREDS.exists():raise RuntimeError('Run laptop-demo.py start first.')
    keys=json.loads(CREDS.read_text(encoding='utf-8'))
    if args.action=='code':
        if os.name!='nt':raise RuntimeError('Clipboard copy is available on Windows only.')
        subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command','$input | Set-Clipboard'],input=keys['demo'],text=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        print('Laptop demo code copied to clipboard. Paste it into the Netlify access screen, not into chat.');return
    path={'login':'login','finish':'login/finish','cancel':'cancel'}[args.action]
    with httpx.Client(base_url=LOCAL,timeout=120,trust_env=False,headers={'X-Speculara-Operator-Key':keys['operator']}) as client:
        response=client.post('/api/collector/'+path,json={'network':args.network} if args.action=='login' else {})
        response.raise_for_status();print(json.dumps(response.json(),indent=2))


if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:pass
    except (RuntimeError,AssertionError,httpx.HTTPError,OSError) as error:
        message=str(error)
        if CREDS.exists():
            for value in json.loads(CREDS.read_text(encoding='utf-8')).values():
                if isinstance(value,str) and value:message=message.replace(value,'[redacted]')
        print(message[:2000],file=sys.stderr);sys.exit(1)
