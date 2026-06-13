"""Main class for the Buddy-UI app, used to expose a Buddy Agent or Team in a Buddy-UI compatible format."""

from fastapi.routing import APIRouter

from buddy.app.agui.async_router import get_async_agui_router
from buddy.app.agui.sync_router import get_sync_agui_router
from buddy.app.base import BaseAPIApp


class AGUIApp(BaseAPIApp):
    type = "agui"

    def get_router(self) -> APIRouter:
        return get_sync_agui_router(agent=self.agent, team=self.team)

    def get_async_router(self) -> APIRouter:
        return get_async_agui_router(agent=self.agent, team=self.team)

