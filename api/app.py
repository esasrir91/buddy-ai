from buddy.api.api import api
from buddy.api.routes import ApiRoutes
from buddy.api.schemas.app import AppCreate
from buddy.cli.settings import BUDDY_cli_settings
from buddy.utils.log import log_debug


def create_app(app: AppCreate) -> None:
    if not BUDDY_cli_settings.api_enabled:
        return

    with api.AuthenticatedClient() as api_client:
        try:
            api_client.post(
                ApiRoutes.APP_CREATE,
                json=app.model_dump(exclude_none=True),
            )

        except Exception as e:
            log_debug(f"Could not create App: {e}")


async def acreate_app(app: AppCreate) -> None:
    if not BUDDY_cli_settings.api_enabled:
        return

    async with api.AuthenticatedAsyncClient() as api_client:
        try:
            await api_client.post(
                ApiRoutes.APP_CREATE,
                json=app.model_dump(exclude_none=True),
            )

        except Exception as e:
            log_debug(f"Could not create App: {e}")
