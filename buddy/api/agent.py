from buddy.api.api import api
from buddy.api.routes import ApiRoutes
from buddy.api.schemas.agent import AgentCreate, AgentRunCreate, AgentSessionCreate
from buddy.cli.settings import BUDDY_cli_settings
from buddy.utils.log import log_debug


def create_agent_session(session: AgentSessionCreate, monitor: bool = False) -> None:
    if not BUDDY_cli_settings.api_enabled:
        return

    log_debug("Logging Agent Session")
    try:
        with api.AuthenticatedClient() as api_client:
            api_client.post(
                ApiRoutes.AGENT_SESSION_CREATE if monitor else ApiRoutes.AGENT_TELEMETRY_SESSION_CREATE,
                json={"session": session.model_dump(exclude_none=True)},
            ).raise_for_status()
    except Exception as e:
        log_debug(f"Could not create Agent session: {e}")


def create_agent_run(run: AgentRunCreate, monitor: bool = False) -> None:
    if not BUDDY_cli_settings.api_enabled:
        return

    try:
        with api.AuthenticatedClient() as api_client:
            api_client.post(
                ApiRoutes.AGENT_RUN_CREATE if monitor else ApiRoutes.AGENT_TELEMETRY_RUN_CREATE,
                json={"run": run.model_dump(exclude_none=True)},
            ).raise_for_status()
    except Exception as e:
        log_debug(f"Could not create Agent run: {e}")


async def acreate_agent_run(run: AgentRunCreate, monitor: bool = False) -> None:
    if not BUDDY_cli_settings.api_enabled:
        return

    try:
        async with api.AuthenticatedAsyncClient() as api_client:
            response = await api_client.post(
                ApiRoutes.AGENT_RUN_CREATE if monitor else ApiRoutes.AGENT_TELEMETRY_RUN_CREATE,
                json={"run": run.model_dump(exclude_none=True)},
            )
            response.raise_for_status()
    except Exception as e:
        log_debug(f"Could not create Agent run: {e}")


def create_agent(agent: AgentCreate) -> None:
    if not BUDDY_cli_settings.api_enabled:
        return

    try:
        with api.AuthenticatedClient() as api_client:
            api_client.post(
                ApiRoutes.AGENT_CREATE,
                json=agent.model_dump(exclude_none=True),
            ).raise_for_status()

            log_debug(f"Created Agent on Platform. ID: {agent.agent_id}")
    except Exception as e:
        log_debug(f"Could not create Agent: {e}")


async def acreate_agent(agent: AgentCreate) -> None:
    if not BUDDY_cli_settings.api_enabled:
        return

    try:
        async with api.AuthenticatedAsyncClient() as api_client:
            await api_client.post(
                ApiRoutes.AGENT_CREATE,
                json=agent.model_dump(exclude_none=True),
            ).raise_for_status()
            log_debug(f"Created Agent on Platform. ID: {agent.agent_id}")
    except Exception as e:
        log_debug(f"Could not create Agent: {e}")
