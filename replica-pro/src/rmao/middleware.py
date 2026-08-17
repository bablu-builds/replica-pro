import time
import os
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", 10))
cache = {}

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_minute = int(time.time() // 60)
        key = f"{client_ip}:{current_minute}"

        # Check if IP exceeds limit
        count = cache.get(key, 0)
        if count >= RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Rate limit exceeded (max 10 req/min)")

        # Increment and store
        cache[key] = count + 1
        response = await call_next(request)

        # Clean up old cache entries (keep last 5 minutes)
        if len(cache) > 1000:
            for k in list(cache.keys()):
                if int(k.split(":")[1]) < (current_minute - 5):
                    del cache[k]

        return response
