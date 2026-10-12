from typing import ClassVar


class ApiRoutes:
    # User paths
    USER_HEALTH: ClassVar[str] = "/v1/user/health"
    USER_SIGN_IN: ClassVar[str] = "/v1/user/signin"
    USER_CLI_AUTH: ClassVar[str] = "/v1/user/cliauth"
    USER_AUTHENTICATE: ClassVar[str] = "/v1/user/authenticate"
    USER_CREATE_ANON: ClassVar[str] = "/v1/user/create/anon"

    # Workspace paths
    WORKSPACE_CREATE: ClassVar[str] = "/v1/workspace/create"
    WORKSPACE_UPDATE: ClassVar[str] = "/v1/workspace/update"
    WORKSPACE_DELETE: ClassVar[str] = "/v1/workspace/delete"
    WORKSPACE_EVENT_CREATE: ClassVar[str] = "/v1/workspace/event/create"

    # Team paths
    TEAM_READ_ALL: ClassVar[str] = "/v1/team/read/all"

    # Agent paths
    AGENT_SESSION_CREATE: ClassVar[str] = "/v1/agent-sessions"
    AGENT_RUN_CREATE: ClassVar[str] = "/v1/agent-runs"
    AGENT_CREATE: ClassVar[str] = "/v2/agents"

    # App paths
    APP_CREATE: ClassVar[str] = "/v2/apps"
    # Team paths
    TEAM_RUN_CREATE: ClassVar[str] = "/v1/team-runs"
    TEAM_SESSION_CREATE: ClassVar[str] = "/v1/team-sessions"
    TEAM_CREATE: ClassVar[str] = "/v2/teams"

    # Workflow paths
    WORKFLOW_CREATE: ClassVar[str] = "/v2/workflows"
    # Telemetry paths
    # TODO: Update to use the new telemetry paths
    AGENT_TELEMETRY_SESSION_CREATE: ClassVar[str] = "/v1/telemetry/agent/session/create"
    AGENT_TELEMETRY_RUN_CREATE: ClassVar[str] = "/v1/telemetry/agent/run/create"

    TEAM_TELEMETRY_RUN_CREATE: ClassVar[str] = "/v1/telemetry/team-runs"

    # Playground paths
    PLAYGROUND_ENDPOINT_CREATE: ClassVar[str] = "/v1/playground/endpoint/create"
    PLAYGROUND_APP_DEPLOY: ClassVar[str] = "/v1/playground/app/deploy"

    # Eval paths
    EVAL_RUN_CREATE: ClassVar[str] = "/v2/eval-runs"
