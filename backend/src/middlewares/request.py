import uuid
from starlette.middleware.base import BaseHTTPMiddleware
class RequestId(BaseHTTPMiddleware):
 async def dispatch(self,request,call_next):
  response=await call_next(request);response.headers['X-Request-ID']=str(uuid.uuid4());return response
class SecurityHeaders(BaseHTTPMiddleware):
 async def dispatch(self,request,call_next):
  response=await call_next(request);response.headers['X-Content-Type-Options']='nosniff';return response
