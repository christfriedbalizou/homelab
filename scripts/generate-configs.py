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
        yaml.dump(data, tmp_file, default_flow_style=False, allow_unicode=True)
        return tmp_file.name


def node_patch(node: dict, installer_image: str) -> dict:
    install: dict[str, Any] = {"image": installer_image}
    if "installDiskSelector" in node:
        install["diskSelector"] = node["installDiskSelector"]
    else:
        install["disk"] = node["installDisk"]

    return {
        "machine": {
            "network": {
                "hostname":   node["hostname"],
                "interfaces": node["networkInterfaces"],
            },
            "install": install,
        }
    }


def main() -> None:
    os.chdir(TALOS_DIR)

    talenv    = yaml.safe_load(open("talenv.yaml"))
    talconfig = yaml.safe_load(open("talconfig.yaml"))

    talos_version      = talenv["talosVersion"]
    kubernetes_version = talenv["kubernetesVersion"]
    cluster_name       = talconfig["clusterName"]
    endpoint           = talconfig["endpoint"]
    sans               = talconfig.get("additionalApiServerCertSans", [])
    pod_cidr           = ",".join(talconfig.get("clusterPodNets", []))
    svc_cidr           = ",".join(talconfig.get("clusterSvcNets", []))

    secrets_bytes = sops_decrypt(TALOS_DIR / "talsecret.sops.yaml")
    cni_patch     = {"cluster": {"network": {"cni": {"name": "none"}}}}

    with tempfile.NamedTemporaryFile(
        suffix=".yaml", delete=False
    ) as secrets_file:
        secrets_file.write(secrets_bytes)
        tmp_secrets = secrets_file.name

    tmp_cni = tmp_yaml(cni_patch)

    Path("clusterconfig").mkdir(exist_ok=True)

    global_patches = sorted(Path("patches/global").glob("*.yaml"))
    cp_patches     = sorted(Path("patches/controller").glob("*.yaml"))

    sans_args = [
        flag for address in sans
        for flag in ("--additional-sans", address)
    ]
    global_args = [
        flag for patch_file in global_patches
        for flag in ("--config-patch", f"@{patch_file}")
    ]
    global_args += ["--config-patch", f"@{tmp_cni}"]

    cp_args = [
        flag for patch_file in cp_patches
        for flag in ("--config-patch-control-plane", f"@{patch_file}")
    ]

    print(
        f"Generating base configs"
        f"  talosVersion={talos_version}"
        f"  kubernetesVersion={kubernetes_version}",
    )
    try:
        talosctl(
            "gen", "config",
            "--talos-version",      talos_version,
            "--kubernetes-version", kubernetes_version,
            "--with-secrets",       tmp_secrets,
            *sans_args,
            *global_args,
            *cp_args,
            "--cluster-pod-cidr",   pod_cidr,
            "--cluster-svc-cidr",   svc_cidr,
            "--force",
            cluster_name, endpoint,
        )
    finally:
        Path(tmp_secrets).unlink(missing_ok=True)
        Path(tmp_cni).unlink(missing_ok=True)

    Path("talosconfig").rename("clusterconfig/talosconfig")

    nodes = talconfig["nodes"]
    print(f"Generating per-node configs ({len(nodes)} nodes)...")

    for node in nodes:
        hostname  = node["hostname"]
        is_cp     = node.get("controlPlane", False)
        image_url = node["talosImageURL"]
        base      = "controlplane.yaml" if is_cp else "worker.yaml"
        output    = f"clusterconfig/kubernetes-{hostname}.yaml"

        patch_path = tmp_yaml(
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
            inline_patch_path = tmp_yaml(patch_data)
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
