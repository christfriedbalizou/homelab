#!/usr/bin/env python3

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
TALOS_DIR   = SCRIPTS_DIR.parent / "talos"


def talosctl(*args: str) -> None:
    subprocess.run(["talosctl", *args], check=True)


def sops_decrypt(path: Path) -> bytes:
    return subprocess.run(
        ["sops", "--decrypt", str(path)],
        check=True,
        capture_output=True,
    ).stdout


def tmp_yaml(data: Any) -> str:
    with tempfile.NamedTemporaryFile(
        suffix=".yaml", mode="w", delete=False
    ) as tmp_file:
        yaml.safe_dump(
            data,
            tmp_file,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        return tmp_file.name


def tmp_yaml_documents(documents: list[Any]) -> str:
    with tempfile.NamedTemporaryFile(
        suffix=".yaml", mode="w", delete=False
    ) as tmp_file:
        yaml.safe_dump_all(
            documents,
            tmp_file,
            default_flow_style=False,
            allow_unicode=True,
            explicit_start=True,
            sort_keys=False,
        )
        return tmp_file.name


def normalize_patch_keys(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            "$patch" if key == "$$patch" else key: normalize_patch_keys(value)
            for key, value in data.items()
        }

    if isinstance(data, list):
        return [normalize_patch_keys(value) for value in data]

    return data


def patch_arg(patch_file: Path, tmp_files: list[Path]) -> str:
    patch_text = patch_file.read_text()
    if "$$patch" not in patch_text:
        return f"@{patch_file}"

    docs = [
        normalize_patch_keys(document)
        for document in yaml.safe_load_all(patch_text)
    ]

    with tempfile.NamedTemporaryFile(
        suffix=".yaml", mode="w", delete=False
    ) as tmp_file:
        yaml.safe_dump_all(
            docs,
            tmp_file,
            default_flow_style=False,
            allow_unicode=True,
            explicit_start=len(docs) > 1,
            sort_keys=False,
        )
        tmp_files.append(Path(tmp_file.name))
        return f"@{tmp_file.name}"


def node_patch(node: dict, installer_image: str) -> list[dict]:
    install: dict[str, Any] = {"image": installer_image}
    if "installDiskSelector" in node:
        install["diskSelector"] = node["installDiskSelector"]
    else:
        install["disk"] = node["installDisk"]

    return [
        {
            "machine": {
                "network": {
                    "interfaces": node["networkInterfaces"],
                },
                "install": install,
            },
        },
        {
            "apiVersion": "v1alpha1",
            "kind": "HostnameConfig",
            "hostname": node["hostname"],
            "auto": {"$patch": "delete"},
        },
    ]


def main() -> None:
    os.chdir(TALOS_DIR)

    talenv    = yaml.safe_load(open("talenv.yaml"))
    talconfig = yaml.safe_load(open("talconfig.yaml"))

    talos_version      = talenv["talosVersion"]
    kubernetes_version = talenv["kubernetesVersion"]
    cluster_name       = talconfig["clusterName"]
    endpoint           = talconfig["endpoint"]
    sans               = talconfig.get("additionalApiServerCertSans", [])
    secrets_bytes = sops_decrypt(TALOS_DIR / "talsecret.sops.yaml")
    cni_patch     = {
        "cluster": {
            "network": {
                "cni":            {"name": "none"},
                "podSubnets":     talconfig.get("clusterPodNets", []),
                "serviceSubnets": talconfig.get("clusterSvcNets", []),
            }
        }
    }

    with tempfile.NamedTemporaryFile(
        suffix=".yaml", delete=False
    ) as secrets_file:
        secrets_file.write(secrets_bytes)
        tmp_secrets = secrets_file.name

    tmp_cni = tmp_yaml(cni_patch)

    Path("clusterconfig").mkdir(exist_ok=True)

    global_patches = sorted(Path("patches/global").glob("*.yaml"))
    cp_patches     = sorted(Path("patches/controller").glob("*.yaml"))
    tmp_patches: list[Path] = []

    try:
        sans_args = [
            flag for address in sans
            for flag in ("--additional-sans", address)
        ]
        global_args = [
            flag for patch_file in global_patches
            for flag in ("--config-patch", patch_arg(patch_file, tmp_patches))
        ]
        global_args += ["--config-patch", f"@{tmp_cni}"]

        cp_args = [
            flag for patch_file in cp_patches
            for flag in (
                "--config-patch-control-plane",
                patch_arg(patch_file, tmp_patches),
            )
        ]

        print(
            f"Generating base configs"
            f"  talosVersion={talos_version}"
            f"  kubernetesVersion={kubernetes_version}",
        )
        talosctl(
            "gen", "config",
            "--talos-version",      talos_version,
            "--kubernetes-version", kubernetes_version,
            "--with-secrets",       tmp_secrets,
            *sans_args,
            *global_args,
            *cp_args,
            "--force",
            cluster_name, endpoint,
        )
    finally:
        Path(tmp_secrets).unlink(missing_ok=True)
        Path(tmp_cni).unlink(missing_ok=True)
        for tmp_patch in tmp_patches:
            tmp_patch.unlink(missing_ok=True)

    Path("talosconfig").rename("clusterconfig/talosconfig")

    nodes = talconfig["nodes"]
    print(f"Generating per-node configs ({len(nodes)} nodes)...")

    for node in nodes:
        hostname  = node["hostname"]
        is_cp     = node.get("controlPlane", False)
        image_url = node["talosImageURL"]
        base      = "controlplane.yaml" if is_cp else "worker.yaml"
        output    = f"clusterconfig/kubernetes-{hostname}.yaml"

        patch_path = tmp_yaml_documents(
            node_patch(node, f"{image_url}:{talos_version}")
        )
        try:
            talosctl(
                "machineconfig", "patch", base,
                "--patch", f"@{patch_path}",
                "--output", output,
            )
        finally:
            Path(patch_path).unlink(missing_ok=True)

        for raw_patch in node.get("patches", []):
            # talconfig |- block scalars are parsed as strings by PyYAML
            patch_data = (
                yaml.safe_load(raw_patch) if isinstance(raw_patch, str)
                else raw_patch
            )
            inline_patch_path = tmp_yaml(normalize_patch_keys(patch_data))
            try:
                talosctl(
                    "machineconfig", "patch", output,
                    "--patch", f"@{inline_patch_path}",
                    "--output", output,
                )
            finally:
                Path(inline_patch_path).unlink(missing_ok=True)

        print(f"  ok  {output}")

    for base_config in ("controlplane.yaml", "worker.yaml"):
        Path(base_config).unlink(missing_ok=True)

    print("Done.")


if __name__ == "__main__":
    main()
