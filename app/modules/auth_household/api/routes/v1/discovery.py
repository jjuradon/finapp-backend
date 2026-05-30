# app/modules/auth_household/api/routes/v1/discovery.py
import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.modules.auth_household.services.auth_query_service import AuthQueryService

router = APIRouter()


@router.get("/.well-known/openid-configuration", response_class=JSONResponse)
async def discovery():
    discovery_data = AuthQueryService.get_discovery()
    return JSONResponse(content=json.loads(discovery_data.json()))


@router.get("/v1/auth/.well-known/jwks.json", response_class=JSONResponse)
async def jwks():
    jwks_data = AuthQueryService.get_jwks()
    return JSONResponse(content=json.loads(jwks_data.json()))
