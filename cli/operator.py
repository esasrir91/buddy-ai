from pathlib import Path
from typing import List, Optional

from typer import launch as typer_launch

from buddy.cli.config import BuddyCliConfig
from buddy.cli.console import print_heading, print_info
from buddy.cli.settings import BUDDY_CLI_CONFIG_DIR, BUDDY_cli_settings
from buddy.infra.resources import InfraResources
from buddy.utils.log import logger


def delete_buddy_config() -> None:
    from buddy.utils.filesystem import delete_from_fs

    logger.debug("Removing existing Buddy configuration")
    delete_from_fs(BUDDY_CLI_CONFIG_DIR)


def authenticate_user() -> None:
    """Authenticate the user using credentials from buddy.com
    Steps:
    1. Authenticate the user by opening the buddy sign-in url.
        Once authenticated, buddy.com will post an auth token to a
        mini http server running on the auth_server_port.
    2. Using the auth_token, authenticate the user with the api.
    3. After the user is authenticated update the BuddyCliConfig.
    4. Save the auth_token locally for future use.
    """
    from buddy.api.schemas.user import UserSchema
    from buddy.api.user import authenticate_and_get_user
    from buddy.cli.auth_server import (
        get_auth_token_from_web_flow,
        get_port_for_auth_server,
    )
    from buddy.cli.credentials import save_auth_token

    print_heading("Authenticating with buddy.com")

    auth_server_port = get_port_for_auth_server()
    redirect_uri = "http%3A%2F%2Flocalhost%3A{}%2Fauth".format(auth_server_port)
    auth_url = "{}?source=cli&action=signin&redirection_supported=true&redirecturi={}".format(
        BUDDY_cli_settings.cli_auth_url, redirect_uri
    )
    print_info("\nYour browser will be opened to visit:\n{}".format(auth_url))
    typer_launch(auth_url)
    print_info("\nWaiting for a response from the browser...\n")

    auth_token = get_auth_token_from_web_flow(auth_server_port)
    if auth_token is None:
        logger.error("Could not authenticate, please set BUDDY_API_KEY or try again")
        return

    BUDDY_config: Optional[BuddyCliConfig] = BuddyCliConfig.from_saved_config()
    existing_user: Optional[UserSchema] = BUDDY_config.user if BUDDY_config is not None else None
    # Authenticate the user and claim any workspaces from anon user
    try:
        user: Optional[UserSchema] = authenticate_and_get_user(auth_token=auth_token, existing_user=existing_user)
    except Exception as e:
        logger.exception(e)
        logger.error("Could not authenticate, please set BUDDY_API_KEY or try again")
        return

    # Save the auth token if user is authenticated
    if user is not None:
        save_auth_token(auth_token)
    else:
        logger.error("Could not authenticate, please set BUDDY_API_KEY or try again")
        return

    if BUDDY_config is None:
        BUDDY_config = BuddyCliConfig(user)
        BUDDY_config.save_config()
    else:
        BUDDY_config.user = user

    print_info("Welcome {}".format(user.email))


def initialize_buddy(reset: bool = False, login: bool = False) -> Optional[BuddyCliConfig]:
    """Initialize Buddy on the users machine.

    1. If reset is True, a new BuddyCliConfig is created.
    2. If BuddyCliConfig does not exist, a new BuddyCliConfig is created.
    3. If BuddyCliConfig exists and auth is valid, returns BuddyCliConfig.
    """
    from buddy.api.user import create_anon_user
    from buddy.utils.filesystem import delete_from_fs

    print_heading("Welcome to Buddy!")
    if reset:
        delete_buddy_config()

    logger.debug("Initializing Buddy")

    # Check if ~/.config/ag exists, if it is not a dir - delete it and create the directory
    if BUDDY_CLI_CONFIG_DIR.exists():
        logger.debug(f"{BUDDY_CLI_CONFIG_DIR} exists")
        if not BUDDY_CLI_CONFIG_DIR.is_dir():
            try:
                delete_from_fs(BUDDY_CLI_CONFIG_DIR)
            except Exception as e:
                logger.exception(e)
                raise Exception(f"Something went wrong, please delete {BUDDY_CLI_CONFIG_DIR} and run again")
            BUDDY_CLI_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    else:
        BUDDY_CLI_CONFIG_DIR.mkdir(parents=True)
        logger.debug(f"Created {BUDDY_CLI_CONFIG_DIR}")

    # Confirm BUDDY_CLI_CONFIG_DIR exists otherwise we should return
    if BUDDY_CLI_CONFIG_DIR.exists():
        logger.debug(f"Buddy config location: {BUDDY_CLI_CONFIG_DIR}")
    else:
        raise Exception("Something went wrong, please try again")

    BUDDY_config: Optional[BuddyCliConfig] = BuddyCliConfig.from_saved_config()
    if BUDDY_config is None:
        logger.debug("Creating new BuddyCliConfig")
        BUDDY_config = BuddyCliConfig()
        BUDDY_config.save_config()

    # Authenticate user
    if login:
        print_info("")
        authenticate_user()
    else:
        anon_user = create_anon_user()
        if anon_user is not None and BUDDY_config is not None:
            BUDDY_config.user = anon_user

    logger.debug("Buddy initialized")
    return BUDDY_config


def start_resources(
    BUDDY_config: BuddyCliConfig,
    resources_file_path: Path,
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
    print_heading(f"Starting resources in: {resources_file_path}")
    logger.debug(f"\ttarget_env   : {target_env}")
    logger.debug(f"\ttarget_infra : {target_infra}")
    logger.debug(f"\ttarget_name  : {target_name}")
    logger.debug(f"\ttarget_type  : {target_type}")
    logger.debug(f"\ttarget_group : {target_group}")
    logger.debug(f"\tdry_run      : {dry_run}")
    logger.debug(f"\tauto_confirm : {auto_confirm}")
    logger.debug(f"\tforce        : {force}")
    logger.debug(f"\tpull         : {pull}")

    from buddy.workspace.config import WorkspaceConfig

    if not resources_file_path.exists():
        logger.error(f"File does not exist: {resources_file_path}")
        return

    # Get resources to deploy
    resource_groups_to_create: List[InfraResources] = WorkspaceConfig.get_resources_from_file(
        resource_file=resources_file_path,
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
    if num_resources_created != num_resources_to_create:
        logger.error("Some resources failed to create, please check logs")


def stop_resources(
    BUDDY_config: BuddyCliConfig,
    resources_file_path: Path,
    target_env: Optional[str] = None,
    target_infra: Optional[str] = None,
    target_group: Optional[str] = None,
    target_name: Optional[str] = None,
    target_type: Optional[str] = None,
    dry_run: Optional[bool] = False,
    auto_confirm: Optional[bool] = False,
    force: Optional[bool] = None,
) -> None:
    print_heading(f"Stopping resources in: {resources_file_path}")
    logger.debug(f"\ttarget_env   : {target_env}")
    logger.debug(f"\ttarget_infra : {target_infra}")
    logger.debug(f"\ttarget_name  : {target_name}")
    logger.debug(f"\ttarget_type  : {target_type}")
    logger.debug(f"\ttarget_group : {target_group}")
    logger.debug(f"\tdry_run      : {dry_run}")
    logger.debug(f"\tauto_confirm : {auto_confirm}")
    logger.debug(f"\tforce        : {force}")

    from buddy.workspace.config import WorkspaceConfig

    if not resources_file_path.exists():
        logger.error(f"File does not exist: {resources_file_path}")
        return

    # Get resource groups to shutdown
    resource_groups_to_shutdown: List[InfraResources] = WorkspaceConfig.get_resources_from_file(
        resource_file=resources_file_path,
        env=target_env,
        infra=target_infra,
        order="create",
    )

    # Track number of resource groups deleted
    num_rgs_shutdown = 0
    num_rgs_to_shutdown = len(resource_groups_to_shutdown)
    # Track number of resources created
    num_resources_shutdown = 0
    num_resources_to_shutdown = 0

    if num_rgs_to_shutdown == 0:
        print_info("No resources to delete")
        return

    logger.debug(f"Deleting {num_rgs_to_shutdown} resource groups")
    for rg in resource_groups_to_shutdown:
        _num_resources_shutdown, _num_resources_to_shutdown = rg.delete_resources(
            group_filter=target_group,
            name_filter=target_name,
            type_filter=target_type,
            dry_run=dry_run,
            auto_confirm=auto_confirm,
            force=force,
        )
        if _num_resources_shutdown > 0:
            num_rgs_shutdown += 1
        num_resources_shutdown += _num_resources_shutdown
        num_resources_to_shutdown += _num_resources_to_shutdown
        logger.debug(f"Deleted {num_resources_shutdown} resources in {num_rgs_shutdown} resource groups")

    if dry_run:
        return

    if num_resources_shutdown == 0:
        return

    print_heading(f"\n--**-- ResourceGroups deleted: {num_rgs_shutdown}/{num_rgs_to_shutdown}\n")
    if num_resources_shutdown != num_resources_to_shutdown:
        logger.error("Some resources failed to delete, please check logs")


def patch_resources(
    BUDDY_config: BuddyCliConfig,
    resources_file_path: Path,
    target_env: Optional[str] = None,
    target_infra: Optional[str] = None,
    target_group: Optional[str] = None,
    target_name: Optional[str] = None,
    target_type: Optional[str] = None,
    dry_run: Optional[bool] = False,
    auto_confirm: Optional[bool] = False,
    force: Optional[bool] = None,
) -> None:
    print_heading(f"Updating resources in: {resources_file_path}")
    logger.debug(f"\ttarget_env   : {target_env}")
    logger.debug(f"\ttarget_infra : {target_infra}")
    logger.debug(f"\ttarget_name  : {target_name}")
    logger.debug(f"\ttarget_type  : {target_type}")
    logger.debug(f"\ttarget_group : {target_group}")
    logger.debug(f"\tdry_run      : {dry_run}")
    logger.debug(f"\tauto_confirm : {auto_confirm}")
    logger.debug(f"\tforce        : {force}")

    from buddy.workspace.config import WorkspaceConfig

    if not resources_file_path.exists():
        logger.error(f"File does not exist: {resources_file_path}")
        return

    # Get resource groups to update
    resource_groups_to_patch: List[InfraResources] = WorkspaceConfig.get_resources_from_file(
        resource_file=resources_file_path,
        env=target_env,
        infra=target_infra,
        order="create",
    )

    num_rgs_patched = 0
    num_rgs_to_patch = len(resource_groups_to_patch)
    # Track number of resources updated
    num_resources_patched = 0
    num_resources_to_patch = 0

    if num_rgs_to_patch == 0:
        print_info("No resources to patch")
        return

    logger.debug(f"Patching {num_rgs_to_patch} resource groups")
    for rg in resource_groups_to_patch:
        _num_resources_patched, _num_resources_to_patch = rg.update_resources(
            group_filter=target_group,
            name_filter=target_name,
            type_filter=target_type,
            dry_run=dry_run,
            auto_confirm=auto_confirm,
            force=force,
        )
        if _num_resources_patched > 0:
            num_rgs_patched += 1
        num_resources_patched += _num_resources_patched
        num_resources_to_patch += _num_resources_to_patch
        logger.debug(f"Patched {num_resources_patched} resources in {num_rgs_patched} resource groups")

    if dry_run:
        return

    if num_resources_patched == 0:
        return

    print_heading(f"\n--**-- ResourceGroups patched: {num_rgs_patched}/{num_rgs_to_patch}\n")
    if num_resources_patched != num_resources_to_patch:
        logger.error("Some resources failed to patch, please check logs")
