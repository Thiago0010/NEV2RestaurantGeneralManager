import redis
from app.core.config import settings

# Initialize Redis client
# In a production environment, we would use a connection pool.
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def block_token(token: str, expires_in: int):
    """Blocks a JWT token until it naturally expires."""
    # We store the token as a key and use the original expiry as TTL
    redis_client.setex(f"blocked_token:{token}", expires_in, "1")

async def is_token_blocked(token: str) -> bool:
    """Checks if a token is in the blocklist."""
    return redis_client.exists(f"blocked_token:{token}") > 0
