from pathlib import Path
from typing import Dict, List, Optional, cast

from rich.prompt import Prompt

from buddy.api.schemas.user import TeamIdentifier, TeamSchema
from buddy.api.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceEvent,
    WorkspaceSchema,
    WorkspaceUpdate,
)
from buddy.api.workspace import log_workspace_event
from buddy.cli.config import BuddyCliConfig
from buddy.cli.console import (
    console,
    log_config_not_available_msg,
    print_heading,
    print_info,
    print_subheading,
)
from buddy.infra.resources import InfraResources
from buddy.utils.common import str_to_int
from buddy.utils.log import logger
from buddy.workspace.config import WorkspaceConfig
from buddy.workspace.enums import WorkspaceStarterTemplate

TEMPLATE_TO_NAME_MAP: Dict[WorkspaceStarterTemplate, str] = {
    WorkspaceStarterTemplate.agent_app: "agent-app",
    WorkspaceStarterTemplate.agent_api: "agent-api",
}

# Local templates bundled with the package (no network required)
_TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATE_TO_LOCAL_PATH: Dict[WorkspaceStarterTemplate, Path] = {
    WorkspaceStarterTemplate.agent_app: _TEMPLATES_DIR / "agent-app",
    WorkspaceStarterTemplate.agent_api: _TEMPLATES_DIR / "agent-api",
}

# Legacy remote repo map — kept for -u/--url override support
TEMPLATE_TO_REPO_MAP: Dict[WorkspaceStarterTemplate, str] = {
    WorkspaceStarterTemplate.agent_app: "https://github.com/esasrir91/buddy-ai-agent-app",
    WorkspaceStarterTemplate.agent_api: "https://github.com/esasrir91/buddy-ai-agent-api",
}


def create_workspace(
    name: Optional[str] = None, template: Optional[str] = None, url: Optional[str] = None
) -> Optional[WorkspaceConfig]:
    """Creates a new workspace and returns the WorkspaceConfig.

    When no --url is given, the workspace is created from a local bundled template
    (no network required). When --url is given, the repo is cloned from that URL.
    """
    from shutil import copytree

    from buddy.cli.operator import initialize_buddy
    from buddy.workspace.helpers import get_workspace_dir_path

    current_dir: Path = Path(".").resolve()

    # Initialize Buddy before creating a workspace
    BUDDY_config: Optional[BuddyCliConfig] = BuddyCliConfig.from_saved_config()
    if not BUDDY_config:
        BUDDY_config = initialize_buddy()
        if not BUDDY_config:
            log_config_not_available_msg()
            return None
    BUDDY_config = cast(BuddyCliConfig, BUDDY_config)

    ws_dir_name: Optional[str] = name
    repo_to_clone: Optional[str] = url
    ws_template = WorkspaceStarterTemplate.agent_app
    templates = list(WorkspaceStarterTemplate.__members__.values())

    if repo_to_clone is None:
        # Get repo_to_clone from template
        if template is None:
            # Get starter template from the user if template is not provided
            # Display available starter templates and ask user to select one
            print_info("Select starter template or press Enter for default (agent-app)")
            for template_id, template_name in enumerate(templates, start=1):
                print_info("  [b][{}][/b] {}".format(template_id, WorkspaceStarterTemplate(template_name).value))

            # Get starter template from the user
            template_choices = [str(idx) for idx, _ in enumerate(templates, start=1)]
            template_inp_raw = Prompt.ask("Template Number", choices=template_choices, default="1", show_choices=False)
            # Convert input to int
            template_inp = str_to_int(template_inp_raw)

            if template_inp is not None:
                template_inp_idx = template_inp - 1
                ws_template = WorkspaceStarterTemplate(templates[template_inp_idx])
        elif template.lower() in WorkspaceStarterTemplate.__members__.values():
            ws_template = WorkspaceStarterTemplate(template)
        else:
            raise Exception(f"{template} is not a supported template, please choose from: {templates}")

        logger.debug(f"Selected Template: {ws_template.value}")
        repo_to_clone = TEMPLATE_TO_REPO_MAP.get(ws_template)

    if ws_dir_name is None:
        default_ws_name = "agent-app"
        if url is not None:
            # Get default_ws_name from url
            default_ws_name = url.split("/")[-1].split(".")[0]
        else:
            # Get default_ws_name from template
            default_ws_name = TEMPLATE_TO_NAME_MAP.get(ws_template, "agent-app")
        logger.debug(f"Asking for ws name with default: {default_ws_name}")
        # Ask user for workspace name if not provided
        ws_dir_name = Prompt.ask("Workspace Name", default=default_ws_name, console=console)

    if ws_dir_name is None:
        logger.error("Workspace name is required")
        return None

    # Check if we can create the workspace in the current dir
    ws_root_path: Path = current_dir.joinpath(ws_dir_name)
    if ws_root_path.exists():
        logger.error(f"Directory {ws_root_path} exists, please delete directory or choose another name for workspace")
        return None

    print_info(f"Creating {str(ws_root_path)}")

    if url is not None:
        # Clone from a user-provided URL
        try:
            import git
            from buddy.utils.git import GitCloneProgress
            from buddy.utils.filesystem import rmdir_recursive

            logger.debug("Cloning: {}".format(url))
            git.Repo.clone_from(url, str(ws_root_path), progress=GitCloneProgress())  # type: ignore
            _dot_git_folder = ws_root_path.joinpath(".git")
            if _dot_git_folder.exists():
                try:
                    rmdir_recursive(_dot_git_folder)
                except Exception as e:
                    logger.warning(f"Failed to delete .git folder: {e}")
        except Exception as e:
            logger.error(e)
            return None
    else:
        # Use local bundled template (no network required)
        local_template_path = TEMPLATE_TO_LOCAL_PATH.get(ws_template)
        if local_template_path is None or not local_template_path.exists():
            logger.error(f"Template directory not found: {local_template_path}")
            return None
        try:
            copytree(str(local_template_path), str(ws_root_path))
            logger.debug(f"Copied template from {local_template_path}")
        except Exception as e:
            logger.error(f"Failed to copy template: {e}")
            return None

    BUDDY_config.add_new_ws_to_config(ws_root_path=ws_root_path)

    try:
        # workspace_dir_path is the path to the ws_root/workspace dir
        workspace_dir_path: Path = get_workspace_dir_path(ws_root_path)
        workspace_secrets_dir = workspace_dir_path.joinpath("secrets").resolve()
        workspace_example_secrets_dir = workspace_dir_path.joinpath("example_secrets").resolve()

        print_info(f"Creating {str(workspace_secrets_dir)}")
        copytree(
            str(workspace_example_secrets_dir),
            str(workspace_secrets_dir),
        )
    except Exception as e:
        logger.warning(f"Could not create workspace/secrets: {e}")
        logger.warning("Please manually copy workspace/example_secrets to workspace/secrets")

    print_info(f"Your new workspace is available at {str(ws_root_path)}\n")
    return setup_workspace(ws_root_path=ws_root_path)


def setup_workspace(ws_root_path: Path) -> Optional[WorkspaceConfig]:
    """Setup a Buddy workspace at `ws_root_path` and return the WorkspaceConfig

    1. Pre-requisites
    1.1 Check ws_root_path exists and is a directory
    1.2 Create BuddyCliConfig if needed
    1.3 Create a WorkspaceConfig if needed
    1.4 Get the workspace name
    1.5 Get the git remote origin url
    1.6 Create anon user if needed

    2. Create or update WorkspaceSchema
    2.1 Check if a ws_schema exists for this workspace, meaning this workspace has a record in buddy-api
    2.2 Create WorkspaceSchema if it doesn't exist
    2.3 Update WorkspaceSchema if git_url is updated
    """
    from rich.live import Live
    from rich.status import Status

    from buddy.cli.operator import initialize_buddy
    from buddy.utils.git import get_remote_origin_for_dir
    from buddy.workspace.helpers import get_workspace_dir_path

    print_heading("Setting up workspace\n")

    ######################################################
    ## 1. Pre-requisites
    ######################################################
    # 1.1 Check ws_root_path exists and is a directory
    ws_is_valid: bool = ws_root_path is not None and ws_root_path.exists() and ws_root_path.is_dir()
    if not ws_is_valid:
        logger.error("Invalid directory: {}".format(ws_root_path))
        return None

    # 1.2 Create BuddyCliConfig if needed
    BUDDY_config: Optional[BuddyCliConfig] = BuddyCliConfig.from_saved_config()
    if not BUDDY_config:
        BUDDY_config = initialize_buddy()
        if not BUDDY_config:
            log_config_not_available_msg()
            return None

    # 1.3 Create a WorkspaceConfig if needed
    logger.debug(f"Checking for a workspace at {ws_root_path}")
    ws_config: Optional[WorkspaceConfig] = BUDDY_config.get_ws_config_by_path(ws_root_path)
    if ws_config is None:
        # There's no record of this workspace, reasons:
        # - The user is setting up a new workspace
        # - The user ran `buddy init -r` which erased existing workspaces
        logger.debug(f"Could not find a workspace at: {ws_root_path}")

        # Check if the workspace contains a `workspace` dir
        workspace_ws_dir_path = get_workspace_dir_path(ws_root_path)
        if workspace_ws_dir_path:
            logger.debug(f"Found the `workspace` configuration at: {workspace_ws_dir_path}")
        else:
            logger.debug(f"No `workspace` subdirectory found at: {ws_root_path}")
        ws_config = BUDDY_config.create_or_update_ws_config(ws_root_path=ws_root_path, set_as_active=True)
        if ws_config is None:
            logger.error(f"Failed to create WorkspaceConfig for {ws_root_path}")
            return None
    else:
        logger.debug(f"Found workspace at {ws_root_path}")
        # Always mark this workspace as active when setup_workspace is called explicitly
        BUDDY_config.set_active_ws_dir(ws_root_path)

    # 1.4 Get the workspace name
    workspace_name = ws_root_path.stem.replace(" ", "-").replace("_", "-").lower()
    logger.debug(f"Workspace name: {workspace_name}")

    # 1.5 Get the git remote origin url
    git_remote_origin_url: Optional[str] = get_remote_origin_for_dir(ws_root_path)
    logger.debug("Git origin: {}".format(git_remote_origin_url))

    # 1.6 Create anon user if the user is not logged in
    if BUDDY_config.user is None:
        from buddy.api.user import create_anon_user

        logger.debug("Creating anon user")
        with Live(transient=True) as live_log:
            status = Status("Creating user...", spinner="aesthetic", speed=2.0, refresh_per_second=10)
            live_log.update(status)
            anon_user = create_anon_user()
            status.stop()
        if anon_user is not None:
            BUDDY_config.user = anon_user

    ######################################################
    ## 2. Create or update WorkspaceSchema
    ######################################################
    # 2.1 Check if a ws_schema exists for this workspace, meaning this workspace has a record in buddy-api
    ws_schema: Optional[WorkspaceSchema] = ws_config.ws_schema if ws_config is not None else None
    if BUDDY_config.user is not None:
        # 2.2 Create WorkspaceSchema if it doesn't exist
        if ws_schema is None or ws_schema.id_workspace is None:
            from buddy.api.workspace import create_workspace_for_user, get_teams_for_user

            # If ws_schema is None, this is a NEW WORKSPACE.
            # We make a call to the api to create a new ws_schema
            logger.debug("Creating ws_schema")
            logger.debug(f"Getting teams for user: {BUDDY_config.user.email}")
            teams: Optional[List[TeamSchema]] = None
            selected_team: Optional[TeamSchema] = None
            team_identifier: Optional[TeamIdentifier] = None
            with Live(transient=True) as live_log:
                status = Status(
                    "Checking for available teams...", spinner="aesthetic", speed=2.0, refresh_per_second=10
                )
                live_log.update(status)
                teams = get_teams_for_user(BUDDY_config.user)
                status.stop()
            if teams is not None and len(teams) > 0:
                logger.debug(f"The user has {len(teams)} available teams. Checking if they want to use one of them")
                print_info("Which account would you like to create this workspace in?")
                print_info("  [b][1][/b] Personal (default)")
                for team_idx, team_schema in enumerate(teams, start=2):
                    print_info("  [b][{}][/b] {}".format(team_idx, team_schema.name))

                account_choices = ["1"] + [str(idx) for idx, _ in enumerate(teams, start=2)]
                account_inp_raw = Prompt.ask("Account Number", choices=account_choices, default="1", show_choices=False)
                account_inp = str_to_int(account_inp_raw)

                if account_inp is not None:
                    if account_inp == 1:
                        print_info("Creating workspace in your personal account")
                    else:
                        selected_team = teams[account_inp - 2]
                        print_info(f"Creating workspace in {selected_team.name}")
                        team_identifier = TeamIdentifier(id_team=selected_team.id_team, team_url=selected_team.url)

            with Live(transient=True) as live_log:
                status = Status("Creating workspace...", spinner="aesthetic", speed=2.0, refresh_per_second=10)
                live_log.update(status)
                ws_schema = create_workspace_for_user(
                    user=BUDDY_config.user,
                    workspace=WorkspaceCreate(
                        ws_name=workspace_name,
                        git_url=git_remote_origin_url,
                    ),
                    team=team_identifier,
                )
                status.stop()

            logger.debug(f"Workspace created: {workspace_name}")
            if selected_team is not None:
                logger.debug(f"Selected team: {selected_team.name}")
            ws_config = BUDDY_config.create_or_update_ws_config(
                ws_root_path=ws_root_path, ws_schema=ws_schema, ws_team=selected_team, set_as_active=True
            )

        # 2.3 Update WorkspaceSchema if git_url is updated
        if git_remote_origin_url is not None and ws_schema is not None and ws_schema.git_url != git_remote_origin_url:
            from buddy.api.workspace import update_workspace_for_team, update_workspace_for_user

            logger.debug("Updating workspace")
            logger.debug(f"Existing git_url: {ws_schema.git_url}")
            logger.debug(f"New git_url: {git_remote_origin_url}")

            if ws_config is not None and ws_config.ws_team is not None:
                updated_workspace_schema = update_workspace_for_team(
                    user=BUDDY_config.user,
                    workspace=WorkspaceUpdate(
                        id_workspace=ws_schema.id_workspace,
                        git_url=git_remote_origin_url,
                    ),
                    team=TeamIdentifier(id_team=ws_config.ws_team.id_team, team_url=ws_config.ws_team.url),
                )
            else:
                updated_workspace_schema = update_workspace_for_user(
                    user=BUDDY_config.user,
                    workspace=WorkspaceUpdate(
                        id_workspace=ws_schema.id_workspace,
                        git_url=git_remote_origin_url,
                    ),
                )
            if updated_workspace_schema is not None:
                # Update the ws_schema for this workspace.
                ws_config = BUDDY_config.create_or_update_ws_config(
                    ws_root_path=ws_root_path, ws_schema=updated_workspace_schema, set_as_active=True
                )
            else:
                logger.debug("Failed to update workspace. Please setup again")

    if ws_config is not None:
        # logger.debug("Workspace Config: {}".format(ws_config.model_dump_json(indent=2)))
        print_subheading("Setup complete! Next steps:")
        print_info("1. Start workspace:")
        print_info("\tbuddy ws up")
        print_info("2. Stop workspace:")
        print_info("\tbuddy ws down")

        if ws_config.ws_schema is not None and BUDDY_config.user is not None:
            log_workspace_event(
                user=BUDDY_config.user,
                workspace_event=WorkspaceEvent(
                    id_workspace=ws_config.ws_schema.id_workspace,
                    event_type="setup",
                    event_status="success",
                    event_data={"workspace_root_path": str(ws_root_path)},
                ),
            )
        return ws_config
    else:
        print_info("Workspace setup unsuccessful. Please try again.")
    return None
    ######################################################
    ## End Workspace setup
    ######################################################


def start_workspace(
    BUDDY_config: BuddyCliConfig,
    ws_config: WorkspaceConfig,
    target_env: Optional[str] = None,
    target_infra: Optional[str] = None,
    target_group: Optional[str] = None,
    target_name: Optional[str] = None,
    target_type: Optional[str] = None,
    dry_run: Optional[bool] = False,
    auto_confirm: Optional[bool] = False,
    force: Optional[bool] = None,
    pull: Optional[bool] = False,
) -> None:
    """Start an Buddy Workspace. This is called from `buddy ws up`"""
    if ws_config is None:
        logger.error("WorkspaceConfig invalid")
        return

    print_heading("Starting workspace: {}".format(str(ws_config.ws_root_path.stem)))
    logger.debug(f"\ttarget_env   : {target_env}")
    logger.debug(f"\ttarget_infra : {target_infra}")
    logger.debug(f"\ttarget_group : {target_group}")
    logger.debug(f"\ttarget_name  : {target_name}")
    logger.debug(f"\ttarget_type  : {target_type}")
    logger.debug(f"\tdry_run      : {dry_run}")
    logger.debug(f"\tauto_confirm : {auto_confirm}")
    logger.debug(f"\tforce        : {force}")
    logger.debug(f"\tpull         : {pull}")

    # Set the local environment variables before processing configs
    ws_config.set_local_env()

    # Get resource groups to deploy
    resource_groups_to_create: List[InfraResources] = ws_config.get_resources(
        env=target_env,
        infra=target_infra,
        order="create",
    )

    # Track number of resource groups created
    num_rgs_created = 0
    num_rgs_to_create = len(resource_groups_to_create)
    # Track number of resources created
    num_resources_created = 0
    num_resources_to_create = 0

    if num_rgs_to_create == 0:
        print_info("No resources to create")
        return

    logger.debug(f"Deploying {num_rgs_to_create} resource groups")
    for rg in resource_groups_to_create:
        _num_resources_created, _num_resources_to_create = rg.create_resources(
            group_filter=target_group,
            name_filter=target_name,
            type_filter=target_type,
            dry_run=dry_run,
            auto_confirm=auto_confirm,
            force=force,
            pull=pull,
        )
        if _num_resources_created > 0:
            num_rgs_created += 1
        num_resources_created += _num_resources_created
        num_resources_to_create += _num_resources_to_create
        logger.debug(f"Deployed {num_resources_created} resources in {num_rgs_created} resource groups")

    if dry_run:
        return

    if num_resources_created == 0:
        return

    print_heading(f"\n--**-- ResourceGroups deployed: {num_rgs_created}/{num_rgs_to_create}\n")

    workspace_event_status = "in_progress"
    if num_resources_created == num_resources_to_create:
        workspace_event_status = "success"
    else:
        logger.error("Some resources failed to create, please check logs")
        workspace_event_status = "failed"

    if (
        BUDDY_config.user is not None
        and ws_config.ws_schema is not None
        and ws_config.ws_schema.id_workspace is not None
    ):
        # Log workspace start event
        log_workspace_event(
            user=BUDDY_config.user,
            workspace_event=WorkspaceEvent(
                id_workspace=ws_config.ws_schema.id_workspace,
                event_type="start",
                event_status=workspace_event_status,
                event_data={
                    "target_env": target_env,
                    "target_infra": target_infra,
                    "target_group": target_group,
                    "target_name": target_name,
                    "target_type": target_type,
                    "dry_run": dry_run,
                    "auto_confirm": auto_confirm,
                    "force": force,
                },
            ),
        )


def stop_workspace(
    BUDDY_config: BuddyCliConfig,
    ws_config: WorkspaceConfig,
    target_env: Optional[str] = None,
    target_infra: Optional[str] = None,
    target_group: Optional[str] = None,
    target_name: Optional[str] = None,
    target_type: Optional[str] = None,
    dry_run: Optional[bool] = False,
    auto_confirm: Optional[bool] = False,
    force: Optional[bool] = None,
) -> None:
    """Stop an Buddy Workspace. This is called from `buddy ws down`"""
    if ws_config is None:
        logger.error("WorkspaceConfig invalid")
        return

    print_heading("Stopping workspace: {}".format(str(ws_config.ws_root_path.stem)))
    logger.debug(f"\ttarget_env   : {target_env}")
    logger.debug(f"\ttarget_infra : {target_infra}")
    logger.debug(f"\ttarget_group : {target_group}")
    logger.debug(f"\ttarget_name  : {target_name}")
    logger.debug(f"\ttarget_type  : {target_type}")
    logger.debug(f"\tdry_run      : {dry_run}")
    logger.debug(f"\tauto_confirm : {auto_confirm}")
    logger.debug(f"\tforce        : {force}")

    # Set the local environment variables before processing configs
    ws_config.set_local_env()

    # Get resource groups to delete
    resource_groups_to_delete: List[InfraResources] = ws_config.get_resources(
        env=target_env,
        infra=target_infra,
        order="delete",
    )

    # Track number of resource groups deleted
    num_rgs_deleted = 0
    num_rgs_to_delete = len(resource_groups_to_delete)
    # Track number of resources deleted
    num_resources_deleted = 0
    num_resources_to_delete = 0

    if num_rgs_to_delete == 0:
        print_info("No resources to delete")
        return

    logger.debug(f"Deleting {num_rgs_to_delete} resource groups")
    for rg in resource_groups_to_delete:
        _num_resources_deleted, _num_resources_to_delete = rg.delete_resources(
            group_filter=target_group,
            name_filter=target_name,
            type_filter=target_type,
            dry_run=dry_run,
            auto_confirm=auto_confirm,
            force=force,
        )
        if _num_resources_deleted > 0:
            num_rgs_deleted += 1
        num_resources_deleted += _num_resources_deleted
        num_resources_to_delete += _num_resources_to_delete
        logger.debug(f"Deleted {num_resources_deleted} resources in {num_rgs_deleted} resource groups")

    if dry_run:
        return

    if num_resources_deleted == 0:
        return

    print_heading(f"\n--**-- ResourceGroups deleted: {num_rgs_deleted}/{num_rgs_to_delete}\n")

    workspace_event_status = "in_progress"
    if num_resources_to_delete == num_resources_deleted:
        workspace_event_status = "success"
    else:
        logger.error("Some resources failed to delete, please check logs")
        workspace_event_status = "failed"

    if (
        BUDDY_config.user is not None
        and ws_config.ws_schema is not None
        and ws_config.ws_schema.id_workspace is not None
    ):
        # Log workspace stop event
        log_workspace_event(
            user=BUDDY_config.user,
            workspace_event=WorkspaceEvent(
                id_workspace=ws_config.ws_schema.id_workspace,
                event_type="stop",
                event_status=workspace_event_status,
                event_data={
                    "target_env": target_env,
                    "target_infra": target_infra,
                    "target_group": target_group,
                    "target_name": target_name,
                    "target_type": target_type,
                    "dry_run": dry_run,
                    "auto_confirm": auto_confirm,
                    "force": force,
                },
            ),
        )


def update_workspace(
    BUDDY_config: BuddyCliConfig,
    ws_config: WorkspaceConfig,
    target_env: Optional[str] = None,
    target_infra: Optional[str] = None,
    target_group: Optional[str] = None,
    target_name: Optional[str] = None,
    target_type: Optional[str] = None,
    dry_run: Optional[bool] = False,
    auto_confirm: Optional[bool] = False,
    force: Optional[bool] = None,
    pull: Optional[bool] = False,
) -> None:
    """Update an Buddy Workspace. This is called from `buddy ws patch`"""
    if ws_config is None:
        logger.error("WorkspaceConfig invalid")
        return

    print_heading("Updating workspace: {}".format(str(ws_config.ws_root_path.stem)))
    logger.debug(f"\ttarget_env   : {target_env}")
    logger.debug(f"\ttarget_infra : {target_infra}")
    logger.debug(f"\ttarget_group : {target_group}")
    logger.debug(f"\ttarget_name  : {target_name}")
    logger.debug(f"\ttarget_type  : {target_type}")
    logger.debug(f"\tdry_run      : {dry_run}")
    logger.debug(f"\tauto_confirm : {auto_confirm}")
    logger.debug(f"\tforce        : {force}")
    logger.debug(f"\tpull         : {pull}")

    # Set the local environment variables before processing configs
    ws_config.set_local_env()

    # Get resource groups to update
    resource_groups_to_update: List[InfraResources] = ws_config.get_resources(
        env=target_env,
        infra=target_infra,
        order="create",
    )
    # Track number of resource groups updated
    num_rgs_updated = 0
    num_rgs_to_update = len(resource_groups_to_update)
    # Track number of resources updated
    num_resources_updated = 0
    num_resources_to_update = 0

    if num_rgs_to_update == 0:
        print_info("No resources to update")
        return

    logger.debug(f"Updating {num_rgs_to_update} resource groups")
    for rg in resource_groups_to_update:
        _num_resources_updated, _num_resources_to_update = rg.update_resources(
            group_filter=target_group,
            name_filter=target_name,
            type_filter=target_type,
            dry_run=dry_run,
            auto_confirm=auto_confirm,
            force=force,
            pull=pull,
        )
        if _num_resources_updated > 0:
            num_rgs_updated += 1
        num_resources_updated += _num_resources_updated
        num_resources_to_update += _num_resources_to_update
        logger.debug(f"Updated {num_resources_updated} resources in {num_rgs_updated} resource groups")

    if dry_run:
        return

    if num_resources_updated == 0:
        return

    print_heading(f"\n--**-- ResourceGroups updated: {num_rgs_updated}/{num_rgs_to_update}\n")

    workspace_event_status = "in_progress"
    if num_resources_updated == num_resources_to_update:
        workspace_event_status = "success"
    else:
        logger.error("Some resources failed to update, please check logs")
        workspace_event_status = "failed"

    if (
        BUDDY_config.user is not None
        and ws_config.ws_schema is not None
        and ws_config.ws_schema.id_workspace is not None
    ):
        # Log workspace start event
        log_workspace_event(
            user=BUDDY_config.user,
            workspace_event=WorkspaceEvent(
                id_workspace=ws_config.ws_schema.id_workspace,
                event_type="update",
                event_status=workspace_event_status,
                event_data={
                    "target_env": target_env,
                    "target_infra": target_infra,
                    "target_group": target_group,
                    "target_name": target_name,
                    "target_type": target_type,
                    "dry_run": dry_run,
                    "auto_confirm": auto_confirm,
                    "force": force,
                },
            ),
        )


def delete_workspace(BUDDY_config: BuddyCliConfig, ws_to_delete: Optional[List[Path]]) -> None:
    if ws_to_delete is None or len(ws_to_delete) == 0:
        print_heading("No workspaces to delete")
        return

    for ws_root in ws_to_delete:
        BUDDY_config.delete_ws(ws_root_path=ws_root)


def set_workspace_as_active(ws_dir_name: Optional[str]) -> None:
    from buddy.cli.operator import initialize_buddy

    ######################################################
    ## 1. Validate Pre-requisites
    ######################################################
    ######################################################
    # 1.1 Check BuddyCliConfig is valid
    ######################################################
    BUDDY_config: Optional[BuddyCliConfig] = BuddyCliConfig.from_saved_config()
    if not BUDDY_config:
        BUDDY_config = initialize_buddy()
        if not BUDDY_config:
            log_config_not_available_msg()
            return

    ######################################################
    # 1.2 Check ws_root_path is valid
    ######################################################
    # By default, we assume this command is run from the workspace directory
    ws_root_path: Optional[Path] = None
    if ws_dir_name is None:
        # If the user does not provide a ws_name, that implies `ag set` is ran from
        # the workspace directory.
        ws_root_path = Path(".").resolve()
    else:
        # If the user provides a workspace name manually, we find the dir for that ws
        ws_config: Optional[WorkspaceConfig] = BUDDY_config.get_ws_config_by_dir_name(ws_dir_name)
        if ws_config is None:
            logger.error(f"Could not find workspace {ws_dir_name}")
            return
        ws_root_path = ws_config.ws_root_path

    ws_dir_is_valid: bool = ws_root_path is not None and ws_root_path.exists() and ws_root_path.is_dir()
    if not ws_dir_is_valid:
        logger.error("Invalid workspace directory: {}".format(ws_root_path))
        return

    ######################################################
    # 1.3 Validate WorkspaceConfig is available i.e. a workspace is available at this directory
    ######################################################
    logger.debug(f"Checking for a workspace at path: {ws_root_path}")
    active_ws_config: Optional[WorkspaceConfig] = BUDDY_config.get_ws_config_by_path(ws_root_path)
    if active_ws_config is None:
        # This happens when the workspace is not yet setup
        print_info(f"Could not find a workspace at path: {ws_root_path}")
        # TODO: setup automatically for the user
        print_info("If this workspace has not been setup, please run `buddy ws setup` from the workspace directory")
        return

    ######################################################
    ## 2. Set workspace as active
    ######################################################
    print_heading(f"Setting workspace {active_ws_config.ws_root_path.stem} as active")
    BUDDY_config.set_active_ws_dir(active_ws_config.ws_root_path)
    print_info("Active workspace updated")
    return
