from buddy.api.api import api
from buddy.api.routes import ApiRoutes
from buddy.api.schemas.app import AppCreate
from buddy.cli.settings import BUDDY_cli_settings
from buddy.utils.log import log_debug


def create_app(app: AppCreate) -> None:
    if not BUDDY_cli_settings.api_enabled:
        return

    try:
        with api.AuthenticatedClient() as api_client:
            api_client.post(
                ApiRoutes.APP_CREATE,
                json=app.model_dump(exclude_none=True),
            ).raise_for_status()

    except Exception as e:
        log_debug(f"Could not create App: {e}")


async def acreate_app(app: AppCreate) -> None:
    if not BUDDY_cli_settings.api_enabled:
        return

    try:
        async with api.AuthenticatedAsyncClient() as api_client:
            response = await api_client.post(
                ApiRoutes.APP_CREATE,
                json=app.model_dump(exclude_none=True),
            )
            response.raise_for_status()

    except Exception as e:
        log_debug(f"Could not create App: {e}")
