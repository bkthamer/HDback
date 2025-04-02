from fastapi import Request
from monlogger import logme

async def log_requests(request: Request, call_next):
    logme.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    return response
