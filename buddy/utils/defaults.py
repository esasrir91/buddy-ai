# Don't import anything which may lead to circular imports


def get_default_ns_name(app_name: str) -> str:
    return f"{app_name}-ns"


def get_default_ctx_name(app_name: str) -> str:
    return f"{app_name}-ctx"


def get_default_sa_name(app_name: str) -> str:
    return f"{app_name}-sa"


def get_default_cr_name(app_name: str) -> str:
    return f"{app_name}-cr"


def get_default_crb_name(app_name: str) -> str:
    return f"{app_name}-crb"


def get_default_pod_name(app_name: str) -> str:
    return f"{app_name}-pod"


def get_default_container_name(app_name: str) -> str:
    return f"{app_name}-container"


def get_default_service_name(app_name: str) -> str:
    return f"{app_name}-svc"


def get_default_ingress_name(app_name: str) -> str:
    return f"{app_name}-ingress"


def get_default_deploy_name(app_name: str) -> str:
    return f"{app_name}-deploy"


def get_default_configmap_name(app_name: str) -> str:
    return f"{app_name}-cm"


def get_default_secret_name(app_name: str) -> str:
    return f"{app_name}-secret"


def get_default_volume_name(app_name: str) -> str:
    return f"{app_name}-volume"


def get_default_pvc_name(app_name: str) -> str:
    return f"{app_name}-pvc"
