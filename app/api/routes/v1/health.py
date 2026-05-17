import time
import asyncio
from typing import Dict, Any
from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import aio_pika
from app.core.config import settings

router = APIRouter()

async def check_postgres() -> Dict[str, Any]:
    if not settings.db_url_auth:
        return {"status": "unreachable", "latency_ms": 0}
    
    start_time = time.time()
    try:
        engine = create_async_engine(settings.db_url_auth)
        async with engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), timeout=2.0)
        await engine.dispose()
        latency = int((time.time() - start_time) * 1000)
        return {"status": "ok", "latency_ms": latency}
    except Exception:
        return {"status": "unreachable", "latency_ms": 0}

async def check_rabbitmq() -> Dict[str, Any]:
    if not settings.rabbitmq_url:
        return {"status": "unreachable", "latency_ms": 0}
        
    start_time = time.time()
    try:
        connection = await asyncio.wait_for(aio_pika.connect_robust(settings.rabbitmq_url), timeout=2.0)
        await connection.close()
        latency = int((time.time() - start_time) * 1000)
        return {"status": "ok", "latency_ms": latency}
    except Exception:
        return {"status": "unreachable", "latency_ms": 0}

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    pg_res, rm_res = await asyncio.gather(check_postgres(), check_rabbitmq())
    
    status = "ok"
    if pg_res["status"] == "unreachable" or rm_res["status"] == "unreachable":
        status = "degraded"
        
    return {
        "data": {
            "status": status,
            "service": "finapp-backend",
            "version": settings.app_version,
            "dependencies": {
                "postgres": pg_res,
                "rabbitmq": rm_res
            }
        },
        "meta": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        },
        "error": None
    }
