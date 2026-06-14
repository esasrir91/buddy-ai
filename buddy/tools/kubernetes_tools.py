import json
from os import getenv
from typing import Any, Dict, List, Optional

import yaml

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger


class KubernetesTools(Toolkit):
    def __init__(
        self,
        config_file: Optional[str] = None,
        namespace: str = "default",
        **kwargs,
    ):
        """Initialize Kubernetes Tools.

        Args:
            config_file (Optional[str]): Path to kubeconfig file
            namespace (str): Default namespace
        """
        self.config_file = config_file
        self.namespace = namespace

        tools: List[Any] = [
            self.get_pods,
            self.create_pod,
            self.delete_pod,
            self.get_services,
            self.get_deployments,
            self.scale_deployment,
            self.apply_yaml,
            self.get_logs,
        ]

        super().__init__(name="kubernetes", tools=tools, **kwargs)

    def _get_k8s_client(self):
        """Get Kubernetes client."""
        try:
            from kubernetes import client, config
        except ImportError:
            raise ImportError("kubernetes client not installed. Please install using `pip install kubernetes`")

        try:
            if self.config_file:
                config.load_kube_config(config_file=self.config_file)
            else:
                config.load_incluster_config()
        except Exception:
            try:
                config.load_kube_config()
            except Exception as e:
                raise Exception(f"Failed to load kubeconfig: {e}")

        return client

    def get_pods(self, namespace: Optional[str] = None) -> str:
        """Get list of pods.

        Args:
            namespace (Optional[str]): Kubernetes namespace

        Returns:
            str: List of pods or error message
        """
        try:
            k8s_client = self._get_k8s_client()
            v1 = k8s_client.CoreV1Api()

            ns = namespace or self.namespace
            pods = v1.list_namespaced_pod(namespace=ns)

            pod_list = []
            for pod in pods.items:
                pod_list.append(
                    {
                        "name": pod.metadata.name,
                        "namespace": pod.metadata.namespace,
                        "status": pod.status.phase,
                        "node": pod.spec.node_name,
                        "created": (
                            pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
                        ),
                    }
                )

            return json.dumps({"pods": pod_list})
        except Exception as e:
            return json.dumps({"error": f"Failed to get pods: {str(e)}"})

    def create_pod(self, name: str, image: str, namespace: Optional[str] = None) -> str:
        """Create a pod.

        Args:
            name (str): Pod name
            image (str): Container image
            namespace (Optional[str]): Kubernetes namespace

        Returns:
            str: Creation result or error message
        """
        try:
            k8s_client = self._get_k8s_client()
            v1 = k8s_client.CoreV1Api()

            ns = namespace or self.namespace

            pod_manifest = {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {"name": name},
                "spec": {"containers": [{"name": name, "image": image}]},
            }

            pod = v1.create_namespaced_pod(namespace=ns, body=pod_manifest)

            return json.dumps(
                {
                    "success": f"Pod {name} created successfully",
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                }
            )
        except Exception as e:
            return json.dumps({"error": f"Failed to create pod: {str(e)}"})

    def delete_pod(self, name: str, namespace: Optional[str] = None) -> str:
        """Delete a pod.

        Args:
            name (str): Pod name
            namespace (Optional[str]): Kubernetes namespace

        Returns:
            str: Deletion result or error message
        """
        try:
            k8s_client = self._get_k8s_client()
            v1 = k8s_client.CoreV1Api()

            ns = namespace or self.namespace
            v1.delete_namespaced_pod(name=name, namespace=ns)

            return json.dumps({"success": f"Pod {name} deleted successfully"})
        except Exception as e:
            return json.dumps({"error": f"Failed to delete pod: {str(e)}"})

    def get_services(self, namespace: Optional[str] = None) -> str:
        """Get list of services.

        Args:
            namespace (Optional[str]): Kubernetes namespace

        Returns:
            str: List of services or error message
        """
        try:
            k8s_client = self._get_k8s_client()
            v1 = k8s_client.CoreV1Api()

            ns = namespace or self.namespace
            services = v1.list_namespaced_service(namespace=ns)

            service_list = []
            for svc in services.items:
                service_list.append(
                    {
                        "name": svc.metadata.name,
                        "namespace": svc.metadata.namespace,
                        "type": svc.spec.type,
                        "cluster_ip": svc.spec.cluster_ip,
                        "ports": [
                            {"port": port.port, "target_port": port.target_port} for port in svc.spec.ports or []
                        ],
                    }
                )

            return json.dumps({"services": service_list})
        except Exception as e:
            return json.dumps({"error": f"Failed to get services: {str(e)}"})

    def get_deployments(self, namespace: Optional[str] = None) -> str:
        """Get list of deployments.

        Args:
            namespace (Optional[str]): Kubernetes namespace

        Returns:
            str: List of deployments or error message
        """
        try:
            k8s_client = self._get_k8s_client()
            apps_v1 = k8s_client.AppsV1Api()

            ns = namespace or self.namespace
            deployments = apps_v1.list_namespaced_deployment(namespace=ns)

            deployment_list = []
            for dep in deployments.items:
                deployment_list.append(
                    {
                        "name": dep.metadata.name,
                        "namespace": dep.metadata.namespace,
                        "replicas": dep.spec.replicas,
                        "ready_replicas": dep.status.ready_replicas or 0,
                        "available_replicas": dep.status.available_replicas or 0,
                    }
                )

            return json.dumps({"deployments": deployment_list})
        except Exception as e:
            return json.dumps({"error": f"Failed to get deployments: {str(e)}"})

    def scale_deployment(self, name: str, replicas: int, namespace: Optional[str] = None) -> str:
        """Scale a deployment.

        Args:
            name (str): Deployment name
            replicas (int): Number of replicas
            namespace (Optional[str]): Kubernetes namespace

        Returns:
            str: Scaling result or error message
        """
        try:
            k8s_client = self._get_k8s_client()
            apps_v1 = k8s_client.AppsV1Api()

            ns = namespace or self.namespace

            # Update deployment replicas
            body = {"spec": {"replicas": replicas}}
            apps_v1.patch_namespaced_deployment(name=name, namespace=ns, body=body)

            return json.dumps({"success": f"Deployment {name} scaled to {replicas} replicas"})
        except Exception as e:
            return json.dumps({"error": f"Failed to scale deployment: {str(e)}"})

    def apply_yaml(self, yaml_content: str, namespace: Optional[str] = None) -> str:
        """Apply YAML configuration.

        Args:
            yaml_content (str): YAML content
            namespace (Optional[str]): Kubernetes namespace

        Returns:
            str: Apply result or error message
        """
        try:
            k8s_client = self._get_k8s_client()
            from kubernetes import utils

            # Parse YAML content
            yaml_objects = list(yaml.safe_load_all(yaml_content))

            results = []
            for obj in yaml_objects:
                if obj is None:
                    continue

                # Set namespace if not specified and needed
                if namespace and obj.get("kind") in ["Pod", "Service", "Deployment"]:
                    if "metadata" not in obj:
                        obj["metadata"] = {}
                    if "namespace" not in obj["metadata"]:
                        obj["metadata"]["namespace"] = namespace

                # Apply the object
                try:
                    utils.create_from_dict(k8s_client.ApiClient(), obj)
                    results.append(f"Applied {obj['kind']}: {obj['metadata']['name']}")
                except Exception as e:
                    results.append(f"Failed to apply {obj['kind']}: {str(e)}")

            return json.dumps({"results": results})
        except Exception as e:
            return json.dumps({"error": f"Failed to apply YAML: {str(e)}"})

    def get_logs(
        self, pod_name: str, container: Optional[str] = None, namespace: Optional[str] = None, tail_lines: int = 100
    ) -> str:
        """Get pod logs.

        Args:
            pod_name (str): Pod name
            container (Optional[str]): Container name
            namespace (Optional[str]): Kubernetes namespace
            tail_lines (int): Number of lines to tail

        Returns:
            str: Pod logs or error message
        """
        try:
            k8s_client = self._get_k8s_client()
            v1 = k8s_client.CoreV1Api()

            ns = namespace or self.namespace

            kwargs = {"name": pod_name, "namespace": ns, "tail_lines": tail_lines}

            if container:
                kwargs["container"] = container

            logs = v1.read_namespaced_pod_log(**kwargs)

            return json.dumps({"logs": logs})
        except Exception as e:
            return json.dumps({"error": f"Failed to get logs: {str(e)}"})
