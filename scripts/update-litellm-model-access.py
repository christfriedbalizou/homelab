#!/usr/bin/env python3
"""Preview, or explicitly apply, model access for the renamed homelab models.

Run with a loopback port-forward to service/litellm on port 15441.
Credentials stay in memory; only model names are printed.
"""

import argparse
import base64
import json
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import (
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)

RENAMES = {
    "qwen3-local": "qwen3-4b-q4-local",
    "qwen3-local-think": "qwen3-4b-q4-local",
    "qwen3-4b-q4-thinking-local": "qwen3-4b-q4-local",
    "qwen3-local-fast": "qwen3-1.7b-q4-local",
    "translategemma-local": "translategemma-4b-q4-local",
    "openai-gpt-6-astra-cloud": "gpt-6-astra-openai-cloud",
    "openai-gpt-6-sol-cloud": "gpt-6-sol-openai-cloud",
    "openai-gpt-6-luna-cloud": "gpt-6-luna-openai-cloud",
}
QWEN_MODELS = [f"qwen3-{size}b-q4-local" for size in (8, 14, 32)]
KEYS = (
    ("default", "translator-keys", "litellm-api-key", True),
    ("default", "translator-keys", "public-litellm-api-key", False),
    ("ai", "cluster-open-webui-secrets", "OPENAI_API_KEY", True),
    ("ai", "cluster-memini-secrets", "LITELLM_API_KEY", False),
)


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError(
            "Unexpected LiteLLM redirect; refusing to forward credentials"
        )


def read_secret(namespace, name, field):
    result = subprocess.run(
        [
            "kubectl",
            "get",
            "secret",
            name,
            "-o",
            "json",
            "--request-timeout=10s",
            "-n",
            namespace,
        ],
        capture_output=True,
        check=True,
        timeout=15,
    )
    return base64.b64decode(json.loads(result.stdout)["data"][field]).decode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="Update key model permissions"
    )
    args = parser.parse_args()
    master = read_secret("ai", "cluster-litellm-secrets", "LITELLM_MASTER_KEY")
    client = build_opener(ProxyHandler({}), NoRedirects())

    def api(path, payload=None):
        request = Request(
            "http://127.0.0.1:15441" + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={
                "Authorization": "Bearer " + master,
                "Content-Type": "application/json",
            },
        )
        with client.open(request, timeout=20) as response:
            return json.load(response)

    plans = []
    for namespace, name, field, add_qwen in KEYS:
        key = read_secret(namespace, name, field)
        info = api("/key/info?" + urlencode({"key": key}))["info"]
        current = info["models"]
        if not isinstance(current, list) or not all(
            isinstance(m, str) for m in current
        ):
            raise RuntimeError("Unexpected key model permissions")
        desired = (
            sorted(
                set(
                    current
                    + [RENAMES[m] for m in current if m in RENAMES]
                    + (QWEN_MODELS if add_qwen else [])
                )
            )
            if current
            else []
        )
        plans.append((field, key, current, desired))
    if len({key for _, key, _, _ in plans}) != len(plans):
        raise RuntimeError(
            "Shared credentials require a separate permission review"
        )
    for field, key, current, desired in plans:
        print(
            f"{field}: {current or ['all models']} -> {desired or ['all models']}"
        )
        if args.apply and desired != sorted(current):
            api("/key/update", {"key": key, "models": desired})
            actual = api("/key/info?" + urlencode({"key": key}))["info"][
                "models"
            ]
            if sorted(actual) != desired:
                raise RuntimeError("Key permission verification failed")
    print(
        "Permissions applied and checked."
        if args.apply
        else "Preview only; no permissions changed."
    )


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        sys.exit(
            f"LiteLLM returned HTTP {error.code}; response suppressed to protect credentials."
        )
    except Exception as error:
        sys.exit(
            f"Model access update stopped ({type(error).__name__}); details suppressed to protect credentials."
        )
