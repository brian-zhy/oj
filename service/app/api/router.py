"""Aggregates resource routers into one top-level router."""

from fastapi import APIRouter

from app.api.tokens import router as tokens_router
from app.api.users import router as users_router
from app.api.extended_auth import router as extended_auth_router
from app.api.user_profile import router as user_profile_router
from app.api.benben import router as benben_router
from app.api.admin import router as admin_router
from app.api.admin_users import router as admin_users_router
from app.api.judgement import router as judgement_router
from app.api.admin_upload import router as admin_upload_router

api_router = APIRouter()
api_router.include_router(users_router)
api_router.include_router(tokens_router)
api_router.include_router(extended_auth_router)
api_router.include_router(user_profile_router)
api_router.include_router(benben_router)
api_router.include_router(admin_router)
api_router.include_router(admin_users_router)
api_router.include_router(judgement_router)
api_router.include_router(admin_upload_router)
