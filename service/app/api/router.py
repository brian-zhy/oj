"""Aggregates resource routers into one top-level router."""

from fastapi import APIRouter

from app.api.tokens import router as tokens_router
from app.api.users import router as users_router
from app.api.extended_auth import router as extended_auth_router
from app.api.user_profile import router as user_profile_router

api_router = APIRouter()
api_router.include_router(users_router)
api_router.include_router(tokens_router)
api_router.include_router(extended_auth_router)
api_router.include_router(user_profile_router)
