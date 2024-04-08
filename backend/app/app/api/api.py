from fastapi import APIRouter
from .endpoints import address

api_router = APIRouter()

api_router.include_router(address.router, tags=["Address"])