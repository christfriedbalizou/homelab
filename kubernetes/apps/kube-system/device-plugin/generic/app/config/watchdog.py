#!/usr/bin/env python3
"""Recover generic-device-plugin registration and stale device allocations.

A kubelet restart recreates kubelet.sock as root-only, so the non-root plugin
cannot register again until its pod restarts and the init container re-owns
the socket directory. Every node exposes 1000 "tun" devices, so zero or
missing allocatable tun on a Ready node means its plugin is unregistered.

A USB device such as the Coral re-enumerates with a new /dev/bus/usb path
after a reset. Kubelet keeps a pod's original allocation across container
restarts, so the consumer stays in CreateContainerError until the pod is
recreated and receives a fresh allocation.

Set WATCHDOG_API_URL (for example a `kubectl proxy` address) to run outside
the cluster, and WATCHDOG_DRY_RUN=1 to request server-side dry-run deletes.
"""

import json
import logging
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

NAMESPACE = "kube-system"
PLUGIN_SELECTOR = "app.kubernetes.io/name=generic-device-plugin"
SENTINEL_RESOURCE = "squat.ai/tun"
PLUGIN_RESOURCE_PREFIX = "squat.ai/"
STALE_DEVICE_REASON = "CreateContainerError"
STALE_DEVICE_MARKERS = ("lstat /dev/", "no such file or directory")
SERVICE_ACCOUNT_DIR = "/var/run/secrets/kubernetes.io/serviceaccount"
REQUEST_TIMEOUT_SECONDS = 30

logger = logging.getLogger(__name__)


class KubernetesApiError(Exception):
    pass


@dataclass(frozen=True)
class NodeStatus:
    name: str
    ready: bool
    plugin_registered: bool


@dataclass(frozen=True)
class PluginPod:
    name: str
    node_name: str


@dataclass(frozen=True)
class DeviceConsumerPod:
    namespace: str
    name: str
    controlled: bool
    stale_device_error: str | None


@dataclass(frozen=True)
class ApiClient:
    base_url: str
    headers: dict[str, str]
    tls_context: ssl.SSLContext | None
    dry_run: bool

    def request(
        self,
        method: str,
        path: str,
        query: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        api_request = urllib.request.Request(
            url, method=method, headers=self.headers
        )
        try:
            with urllib.request.urlopen(
                api_request,
                context=self.tls_context,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                payload: dict[str, Any] = json.load(response)
        except (urllib.error.URLError, TimeoutError) as error:
            raise KubernetesApiError(
                f"{method} {path} failed: {error}"
            ) from error
        return payload


def build_api_client() -> ApiClient:
    dry_run = os.environ.get("WATCHDOG_DRY_RUN") == "1"
    override_url = os.environ.get("WATCHDOG_API_URL")
    if override_url:
        return ApiClient(override_url.rstrip("/"), {}, None, dry_run)
    host = os.environ["KUBERNETES_SERVICE_HOST"]
    port = os.environ["KUBERNETES_SERVICE_PORT"]
    with open(f"{SERVICE_ACCOUNT_DIR}/token", encoding="utf-8") as token_file:
        token = token_file.read().strip()
    tls_context = ssl.create_default_context(
        cafile=f"{SERVICE_ACCOUNT_DIR}/ca.crt"
    )
    return ApiClient(
        f"https://{host}:{port}",
        {"Authorization": f"Bearer {token}"},
        tls_context,
        dry_run,
    )


def parse_node_status(node: dict[str, Any]) -> NodeStatus:
    status = node.get("status", {})
    ready = any(
        condition.get("type") == "Ready" and condition.get("status") == "True"
        for condition in status.get("conditions", [])
    )
    allocatable_tun = status.get("allocatable", {}).get(SENTINEL_RESOURCE, "0")
    return NodeStatus(
        name=node["metadata"]["name"],
        ready=ready,
        plugin_registered=allocatable_tun not in ("", "0"),
    )


def select_unregistered_nodes(nodes: list[NodeStatus]) -> list[str]:
    selected = []
    for node in nodes:
        if not node.ready:
            logger.info("%s: not Ready, skipping", node.name)
        elif node.plugin_registered:
            logger.info("%s: plugin registered", node.name)
        else:
            selected.append(node.name)
    return selected


def list_node_statuses(api: ApiClient) -> list[NodeStatus]:
    response = api.request("GET", "/api/v1/nodes")
    return [parse_node_status(node) for node in response["items"]]


def list_plugin_pods(api: ApiClient) -> list[PluginPod]:
    response = api.request(
        "GET",
        f"/api/v1/namespaces/{NAMESPACE}/pods",
        {"labelSelector": PLUGIN_SELECTOR},
    )
    return [
        PluginPod(pod["metadata"]["name"], pod["spec"].get("nodeName", ""))
        for pod in response["items"]
    ]


def delete_pod(api: ApiClient, namespace: str, name: str) -> None:
    query = {"dryRun": "All"} if api.dry_run else None
    api.request("DELETE", f"/api/v1/namespaces/{namespace}/pods/{name}", query)


def requests_plugin_resource(pod: dict[str, Any]) -> bool:
    for container in pod["spec"].get("containers", []):
        resources = container.get("resources", {})
        for section in ("limits", "requests"):
            if any(
                resource.startswith(PLUGIN_RESOURCE_PREFIX)
                for resource in resources.get(section, {})
            ):
                return True
    return False


def find_stale_device_error(pod: dict[str, Any]) -> str | None:
    for status in pod.get("status", {}).get("containerStatuses", []):
        waiting = status.get("state", {}).get("waiting", {})
        message = str(waiting.get("message", ""))
        if waiting.get("reason") == STALE_DEVICE_REASON and all(
            marker in message for marker in STALE_DEVICE_MARKERS
        ):
            return message
    return None


def parse_device_consumer(pod: dict[str, Any]) -> DeviceConsumerPod:
    metadata = pod["metadata"]
    return DeviceConsumerPod(
        namespace=metadata["namespace"],
        name=metadata["name"],
        controlled=any(
            owner.get("controller")
            for owner in metadata.get("ownerReferences", [])
        ),
        stale_device_error=find_stale_device_error(pod),
    )


def list_device_consumers(api: ApiClient) -> list[DeviceConsumerPod]:
    response = api.request("GET", "/api/v1/pods")
    return [
        parse_device_consumer(pod)
        for pod in response["items"]
        if requests_plugin_resource(pod)
    ]


def recycle_stale_device_consumers(api: ApiClient) -> None:
    for pod in list_device_consumers(api):
        if pod.stale_device_error is None:
            continue
        if not pod.controlled:
            logger.warning(
                "%s/%s: stale device allocation but no controller, skipping",
                pod.namespace,
                pod.name,
            )
            continue
        logger.info(
            "%s/%s: stale device allocation (%s), deleting",
            pod.namespace,
            pod.name,
            pod.stale_device_error,
        )
        delete_pod(api, pod.namespace, pod.name)


def recycle_unregistered_plugins(api: ApiClient) -> None:
    unregistered_nodes = select_unregistered_nodes(list_node_statuses(api))
    if not unregistered_nodes:
        return
    plugin_pods = list_plugin_pods(api)
    for node_name in unregistered_nodes:
        node_pods = [pod for pod in plugin_pods if pod.node_name == node_name]
        if not node_pods:
            logger.warning("%s: plugin unregistered, no pod found", node_name)
        for pod in node_pods:
            logger.info(
                "%s: plugin unregistered, deleting %s", node_name, pod.name
            )
            delete_pod(api, NAMESPACE, pod.name)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )
    try:
        api = build_api_client()
        recycle_unregistered_plugins(api)
        recycle_stale_device_consumers(api)
    except (KubernetesApiError, KeyError, OSError) as error:
        logger.error("watchdog failed: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
