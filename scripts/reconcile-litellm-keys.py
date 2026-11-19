#!/usr/bin/env python3
"""Preview, or apply, LiteLLM model grants for keys the operator does not manage.

Keys created by bootstrap or by hand live only in the LiteLLM database, so their
model lists are reconciled here. Keys owned by a LiteLLMVirtualKey resource are
left to the operator. Credentials stay in memory; only aliases and model names
are written to stdout.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import (
    HTTPRedirectHandler,
    OpenerDirector,
    ProxyHandler,
    Request,
    build_opener,
)

NAMESPACE = "ai"
LOCAL_PORT = 15441
AGENT_ACCESS_GROUP = "agents"
ALL_MODELS: tuple[str, ...] = ()
DESIRED_GRANTS: dict[str, tuple[str, ...]] = {
    "translator-local-20261009": ALL_MODELS,
    "n8n": ("qwen3-local-fast",),
    "opencode-admin": (AGENT_ACCESS_GROUP,),
}
RETIRED_KEYS: tuple[str, ...] = ("open-webui",)
OPERATOR_MANAGED_KEYS = ("hermes",)


class ReconcileError(RuntimeError):
    pass


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        raise ReconcileError("unexpected redirect; refusing to forward credentials")


@dataclass(frozen=True)
class VirtualKey:
    alias: str
    token: str
    models: tuple[str, ...]


@dataclass(frozen=True)
class Change:
    alias: str
    action: str
    current: tuple[str, ...]
    desired: tuple[str, ...]

    def describe(self) -> str:
        if self.action == "delete":
            return f"{self.alias}: delete (grants {list(self.current)})"
        return f"{self.alias}: {list(self.current)} -> {list(self.desired)}"


class LiteLLMAdmin:
    def __init__(self, master_key: str) -> None:
        self._master_key = master_key
        self._opener: OpenerDirector = build_opener(ProxyHandler({}), NoRedirects())

    def call(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        request = Request(
            f"http://127.0.0.1:{LOCAL_PORT}{path}",
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={
                "Authorization": f"Bearer {self._master_key}",
                "Content-Type": "application/json",
            },
        )
        with self._opener.open(request, timeout=20) as response:
            return json.load(response)

    def list_keys(self) -> list[VirtualKey]:
        listing = self.call(
            "/key/list?" + urlencode({"return_full_object": "true", "size": 100})
        )
        keys = []
        for entry in listing["keys"]:
            models = entry.get("models") or []
            if not all(isinstance(model, str) for model in models):
                raise ReconcileError("unexpected key model list")
            keys.append(
                VirtualKey(
                    alias=entry.get("key_alias") or "",
                    token=entry["token"],
                    models=tuple(sorted(models)),
                )
            )
        return keys

    def served_models(self) -> set[str]:
        return {model["id"] for model in self.call("/v1/models")["data"]}


def read_master_key() -> str:
    secret = subprocess.run(
        [
            "kubectl",
            "get",
            "secret",
            "cluster-litellm-secrets",
            "-o",
            "json",
            "--request-timeout=10s",
            "-n",
            NAMESPACE,
        ],
        capture_output=True,
        check=True,
        timeout=15,
    )
    encoded = json.loads(secret.stdout)["data"]["LITELLM_MASTER_KEY"]
    return base64.b64decode(encoded).decode()


def start_port_forward() -> subprocess.Popen[bytes]:
    forward = subprocess.Popen(
        [
            "kubectl",
            "port-forward",
            "svc/litellm",
            f"{LOCAL_PORT}:4000",
            "-n",
            NAMESPACE,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)
    if forward.poll() is not None:
        raise ReconcileError("kubectl port-forward exited")
    return forward


def plan_changes(
    keys: list[VirtualKey], served: set[str]
) -> list[tuple[Change, VirtualKey]]:
    unknown = {
        model
        for models in DESIRED_GRANTS.values()
        for model in models
        if model not in served and model != AGENT_ACCESS_GROUP
    }
    if unknown:
        raise ReconcileError(f"models not served by LiteLLM: {sorted(unknown)}")
    by_alias: dict[str, list[VirtualKey]] = {}
    for key in keys:
        by_alias.setdefault(key.alias, []).append(key)
    unmanaged = sorted(
        set(by_alias)
        - set(DESIRED_GRANTS)
        - set(RETIRED_KEYS)
        - set(OPERATOR_MANAGED_KEYS)
    )
    if unmanaged:
        raise ReconcileError(f"keys without a declared grant: {unmanaged}")
    plan = []
    for alias, desired in DESIRED_GRANTS.items():
        for key in by_alias.get(alias, []):
            wanted = tuple(sorted(desired))
            if key.models != wanted:
                plan.append((Change(alias, "update", key.models, wanted), key))
    for alias in RETIRED_KEYS:
        for key in by_alias.get(alias, []):
            plan.append((Change(alias, "delete", key.models, ()), key))
    return plan


def apply_change(admin: LiteLLMAdmin, change: Change, key: VirtualKey) -> None:
    if change.action == "delete":
        admin.call("/key/delete", {"keys": [key.token]})
        return
    admin.call("/key/update", {"key": key.token, "models": list(change.desired)})


def verify(admin: LiteLLMAdmin) -> None:
    remaining = plan_changes(admin.list_keys(), admin.served_models())
    if remaining:
        raise ReconcileError(
            "grants still differ: "
            + "; ".join(change.describe() for change, _ in remaining)
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="update and delete keys")
    arguments = parser.parse_args()
    forward = start_port_forward()
    try:
        admin = LiteLLMAdmin(read_master_key())
        plan = plan_changes(admin.list_keys(), admin.served_models())
        for change, _ in plan:
            sys.stdout.write(change.describe() + "\n")
        if not plan:
            sys.stdout.write("Grants already match.\n")
            return 0
        if not arguments.apply:
            sys.stdout.write("Preview only; nothing changed.\n")
            return 0
        for change, key in plan:
            apply_change(admin, change, key)
        verify(admin)
        sys.stdout.write("Applied and verified.\n")
        return 0
    finally:
        forward.terminate()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except HTTPError as error:
        sys.exit(f"LiteLLM returned HTTP {error.code}; response suppressed.")
    except (ReconcileError, URLError, subprocess.SubprocessError) as error:
        sys.exit(f"Key reconciliation stopped: {error}")
