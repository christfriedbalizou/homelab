#!/usr/bin/env python3
"""Recycle generic-device-plugin pods that lost kubelet registration.

A kubelet restart recreates kubelet.sock as root-only, so the non-root plugin
cannot register again until its pod restarts and the init container re-owns
the socket directory. Every node exposes 1000 "tun" devices, so zero or
missing allocatable tun on a Ready node means its plugin is unregistered.

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


def delete_pod(api: ApiClient, pod: PluginPod) -> None:
    query = {"dryRun": "All"} if api.dry_run else None
    api.request(
        "DELETE", f"/api/v1/namespaces/{NAMESPACE}/pods/{pod.name}", query
    )


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
            delete_pod(api, pod)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )
    try:
        recycle_unregistered_plugins(build_api_client())
    except (KubernetesApiError, KeyError, OSError) as error:
        logger.error("watchdog failed: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
