def parse_resource_filter(
    resource_filter: str,
) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    target_env: str | None = None
    target_infra: str | None = None
    target_group: str | None = None
    target_name: str | None = None
    target_type: str | None = None

    filters = resource_filter.split(":")
    num_filters = len(filters)
    if num_filters >= 1 and filters[0] != "":
        target_env = filters[0]
    if num_filters >= 2 and filters[1] != "":
        target_infra = filters[1]
    if num_filters >= 3 and filters[2] != "":
        target_group = filters[2]
    if num_filters >= 4 and filters[3] != "":
        target_name = filters[3]
    if num_filters >= 5 and filters[4] != "":
        target_type = filters[4]

    return target_env, target_infra, target_group, target_name, target_type
