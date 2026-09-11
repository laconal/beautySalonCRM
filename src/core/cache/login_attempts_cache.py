import logging
from datetime import datetime, timedelta, timezone
from typing import Literal
from redis.exceptions import RedisError
from src.core.cache.permission_cache import get_redis_client
from src.core.config import settings

logger = logging.getLogger(__name__)

def _ip_attempts_key(ip: str) -> str:
    return f"login_ip:{ip}:attempts"

def _ip_blocked_key(ip: str) -> str:
    return f"login_ip:{ip}:blocked"

def _account_attempts_key(login: str) -> str:
    return f"login_account:{login}:attempts"

def _account_blocked_key(login: str) -> str:
    return f"login_account:{login}:blocked"

async def _is_blocked(blocked_key: str) -> bool:
    try:
        return await get_redis_client().exists(blocked_key) == 1
    except RedisError:
        logger.warning("Redis unavailable, could not check login block for key %s", blocked_key)
        return False

async def _blocked_until(blocked_key: str) -> datetime | None:
    try:
        ttl = await get_redis_client().ttl(blocked_key)
        if ttl is None or ttl < 0:
            return None
        return datetime.now(timezone.utc) + timedelta(seconds = ttl)
    except RedisError:
        logger.warning("Redis unavailable, could not read block expiration for key %s", blocked_key)
        return None

async def _get_ttl(label: Literal["ip", "login"]) -> int:
    return settings.LOGIN_BLOCK_TTL if label == "login" else settings.IP_BLOCK_TTL

async def _register_failure(attempts_key: str, 
        blocked_key: str,
        label: Literal["ip", "login"], 
        identifier: str) -> int:
    try:
        client = get_redis_client()
        attempts = await client.incr(attempts_key)
        if attempts == 1:
            await client.expire(attempts_key, settings.ATTEMPTS_WINDOW_TTL)

        logger.warning("Failed login attempt (%s): %s attempt #%d", label, identifier, attempts)

        if attempts >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
            await client.set(blocked_key, 1, ex = _get_ttl(label))
            await client.delete(attempts_key)
            logger.warning("Blocked login (%s): %s for %d seconds after %d failed attempts", label, identifier, _get_ttl(label), attempts)

        return attempts
    except RedisError:
        logger.warning("Redis unavailable, could not track failed login attempts for (%s) %s", label, identifier)
        return 0

async def _reset(attempts_key: str, blocked_key: str) -> None:
    try:
        client = get_redis_client()
        await client.delete(attempts_key)
        await client.delete(blocked_key)
    except RedisError:
        logger.warning("Redis unavailable, could not reset login attempts for key %s", attempts_key)

async def is_ip_blocked(ip: str) -> bool:
    return await _is_blocked(_ip_blocked_key(ip))

async def ip_blocked_until(ip: str) -> datetime | None:
    return await _blocked_until(_ip_blocked_key(ip))

async def register_failed_ip_login(ip: str) -> int:
    return await _register_failure(_ip_attempts_key(ip), _ip_blocked_key(ip), "ip", ip)

async def reset_failed_ip_login(ip: str) -> None:
    await _reset(_ip_attempts_key(ip), _ip_blocked_key(ip))

async def is_account_blocked(login: str) -> bool:
    return await _is_blocked(_account_blocked_key(login))

async def account_blocked_until(login: str) -> datetime | None:
    return await _blocked_until(_account_blocked_key(login))

async def register_failed_account_login(login: str) -> int:
    return await _register_failure(_account_attempts_key(login), _account_blocked_key(login), "login", login)

async def reset_failed_account_login(login: str) -> None:
    await _reset(_account_attempts_key(login), _account_blocked_key(login))
