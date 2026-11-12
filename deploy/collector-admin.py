"""Run inside the backend container; never expose the admin API publicly."""
import argparse
import json
import sys
import httpx


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['status','login','finish','cancel'])
    parser.add_argument('network',nargs='?',choices=['instagram','facebook'])
    args=parser.parse_args()
    if args.action=='login' and not args.network: parser.error('login needs instagram or facebook')
    paths={'status':'/api/collector/status','login':'/api/collector/login','finish':'/api/collector/login/finish','cancel':'/api/collector/cancel'}
    try:
        with httpx.Client(base_url='http://127.0.0.1:8000',timeout=40) as client:
            response=client.get(paths[args.action]) if args.action=='status' else client.post(paths[args.action],json={'network':args.network} if args.action=='login' else {})
            response.raise_for_status()
            print(json.dumps(response.json(),indent=2))
    except httpx.HTTPError:
        print('The local collector control did not complete. Check docker compose logs backend.',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__': raise SystemExit(main())
