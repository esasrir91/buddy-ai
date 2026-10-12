from buddy.api.api import api
from buddy.api.routes import ApiRoutes
from buddy.api.schemas.workflows import WorkflowCreate
from buddy.cli.settings import BUDDY_cli_settings
from buddy.utils.log import log_debug


def create_workflow(workflow: WorkflowCreate) -> None:
    if not BUDDY_cli_settings.api_enabled:
        return

    with api.AuthenticatedClient() as api_client:
        try:
            response = api_client.post(
                ApiRoutes.WORKFLOW_CREATE,
                json=workflow.model_dump(exclude_none=True),
            )
            response.raise_for_status()
        except Exception as e:
            log_debug(f"Could not create Workflow: {e}")


async def acreate_workflow(workflow: WorkflowCreate) -> None:
    if not BUDDY_cli_settings.api_enabled:
        return

    async with api.AuthenticatedAsyncClient() as api_client:
        try:
            response = await api_client.post(
                ApiRoutes.WORKFLOW_CREATE,
                json=workflow.model_dump(exclude_none=True),
            )
            response.raise_for_status()
        except Exception as e:
            log_debug(f"Could not create Workflow: {e}")
