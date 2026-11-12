"""Run inside the backend container; never expose the admin API publicly."""
import argparse
import json
import sys
import os
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
    if target.username or target.password or target.query or target.fragment or target.path not in ('','/') or (target.scheme!='https' and not (target.scheme=='http' and target.hostname in ('localhost','127.0.0.1','::1'))):
        parser.error('Use an HTTPS backend origin, or a local HTTP loopback address.')
    paths={'status':'/api/collector/status','login':'/api/collector/login','finish':'/api/collector/login/finish','cancel':'/api/collector/cancel'}
    try:
        token=os.getenv('OPERATOR_ACCESS_TOKEN','')
        with httpx.Client(base_url=args.url,timeout=40,headers={'X-Speculara-Operator-Key':token} if token else {}) as client:
            response=client.get(paths[args.action]) if args.action=='status' else client.post(paths[args.action],json={'network':args.network} if args.action=='login' else {})
            response.raise_for_status()
            print(json.dumps(response.json(),indent=2))
    except httpx.HTTPError:
        print('The collector control did not complete. Check the operator key and backend logs.',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__': raise SystemExit(main())
