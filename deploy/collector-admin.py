"""Manage local sessions or use the private operator key over HTTPS."""
import argparse
import json
import sys
import os
import ssl
import re
from urllib.parse import urlparse
import httpx


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['status','login','finish','cancel'])
    parser.add_argument('network',nargs='?',choices=['instagram','facebook'])
    parser.add_argument('--url',default='http://127.0.0.1:'+os.getenv('SPECULARA_INTERNAL_API_PORT','8000'))
    args=parser.parse_args()
    if args.action=='login' and not args.network: parser.error('login needs instagram or facebook')
    target=urlparse(args.url)
    if not target.hostname or target.username or target.password or target.query or target.fragment or target.path not in ('','/') or (target.scheme!='https' and not (target.scheme=='http' and target.hostname in ('localhost','127.0.0.1','::1'))):
        parser.error('Use an HTTPS backend origin, or a local HTTP loopback address.')
    paths={'status':'/api/collector/status','login':'/api/collector/login','finish':'/api/collector/login/finish','cancel':'/api/collector/cancel'}
    try:
        token=os.getenv('OPERATOR_ACCESS_TOKEN','').strip()
        if target.hostname not in ('localhost','127.0.0.1','::1') and not token:
            print('OPERATOR_ACCESS_TOKEN is missing in this terminal. Load the Render operator key again; do not use the demo token.',file=sys.stderr)
            return 1
        # Trust the operating system's certificates, including managed Windows CAs.
        # Keep TLS verification enabled, as in the application's Google client.
        with httpx.Client(base_url=args.url,timeout=120,verify=ssl.create_default_context(),headers={'X-Speculara-Operator-Key':token} if token else {}) as client:
            response=client.get(paths[args.action]) if args.action=='status' else client.post(paths[args.action],json={'network':args.network} if args.action=='login' else {})
            response.raise_for_status()
            print(json.dumps(response.json(),indent=2))
    except httpx.HTTPStatusError as error:
        status=error.response.status_code
        try:
            detail=error.response.json().get('detail','')
        except (ValueError,AttributeError):
            detail=''
        detail=re.sub(r'[\x00-\x1f\x7f]+',' ',detail.replace(token,'[redacted]'))[:700] if isinstance(detail,str) and detail else ''
        message=('Operator key rejected. Reload OPERATOR_ACCESS_TOKEN from Render in this same terminal; the demo token will not work.' if status in (401,403)
                 else 'The collector is busy. Finish the existing sign-in or collection before starting another.' if status==409
                 else 'Backend could not complete this action.' if status in (502,503,504) and detail
                 else 'Render is starting or unavailable. Wait for the service to show Live and retry.' if status in (502,503,504)
                 else 'Check the backend deployment and collector logs.')
        print(f'HTTP {status}: {message}',file=sys.stderr)
        if detail: print(f'Server detail: {detail}',file=sys.stderr)
        return 1
    except httpx.TimeoutException:
        print('Render did not respond within 120 seconds. Check service status and memory/restart logs, then retry.',file=sys.stderr)
        return 1
    except httpx.ConnectError as error:
        message='TLS certificate verification failed. Check your Windows trusted certificates or corporate network certificate configuration.' if 'CERTIFICATE_VERIFY_FAILED' in str(error) else 'Cannot connect to Render. Check the HTTPS service URL, network connection and service status.'
        print(message,file=sys.stderr)
        return 1
    except (httpx.HTTPError,ValueError):
        print('Render did not return a valid API response. Check the service URL and backend deployment.',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__': raise SystemExit(main())
