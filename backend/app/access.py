"""Shared private-demo access, separate from privileged collector controls."""
from hmac import compare_digest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from .config import get_settings

CONTROLS={'/api/collector/login','/api/collector/login/finish','/api/collector/cancel'}


def matches(value,expected):
    return bool(value and expected) and compare_digest(value.encode('utf-8'),expected.encode('utf-8'))


def operator_access(request):
    return matches(request.headers.get('x-speculara-operator-key',''),get_settings().operator_access_token)


class DemoAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self,request,call_next):
        settings=get_settings()
        enabled=settings.require_access_code or bool(settings.demo_access_token)
        if not enabled or request.method=='OPTIONS' or (request.method=='GET' and request.url.path=='/api/health'):
            return await call_next(request)
        if not settings.demo_access_token:
            return JSONResponse({'detail':'Hosted access is not configured.'},status_code=503)
        if request.url.path.rstrip('/') in CONTROLS:
            if not operator_access(request):
                return JSONResponse({'detail':'Only the demo operator can manage connected accounts.'},status_code=403)
        else:
            scheme,_,token=request.headers.get('authorization','').partition(' ')
            guest=scheme.lower()=='bearer' and matches(token,settings.demo_access_token)
            if not guest and not operator_access(request):
                return JSONResponse({'detail':'Enter the demo access code to continue.'},status_code=401)
        return await call_next(request)
