"""Aggregates resource routers into one top-level router."""

from fastapi import APIRouter

from app.api.tokens import router as tokens_router
from app.api.users import router as users_router
from app.api.checkin import router as checkin_router
from app.api.teams import router as teams_router
from app.api.contests import router as contests_router
from app.api.extended_auth import router as extended_auth_router
from app.api.user_profile import router as user_profile_router
from app.api.benben import router as benben_router
from app.api.admin import router as admin_router
from app.api.admin_users import router as admin_users_router
from app.api.judgement import router as judgement_router
from app.api.tickets import router as tickets_router
from app.api.forum import router as forum_router
from app.api.notifications import router as notifications_router
from app.api.admin_upload import router as admin_upload_router
from app.api.problems import router as problems_router
from app.api.submissions import router as submissions_router
from app.api.images import router as images_router

api_router = APIRouter()
api_router.include_router(users_router)
api_router.include_router(checkin_router)
api_router.include_router(teams_router)
api_router.include_router(contests_router)
api_router.include_router(tokens_router)
api_router.include_router(extended_auth_router)
api_router.include_router(user_profile_router)
api_router.include_router(benben_router)
api_router.include_router(admin_router)
api_router.include_router(admin_users_router)
api_router.include_router(judgement_router)
api_router.include_router(tickets_router)
api_router.include_router(forum_router)
api_router.include_router(notifications_router)
api_router.include_router(admin_upload_router)
api_router.include_router(problems_router)
api_router.include_router(submissions_router)
api_router.include_router(images_router)
