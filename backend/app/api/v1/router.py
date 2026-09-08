"""Aggregates the version 1 routers under a single prefix."""

from fastapi import APIRouter

from app.api.v1 import auth

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)