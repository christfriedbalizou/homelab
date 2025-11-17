import os
import sys

import requests
import yaml

secret_domain = os.environ.get("SECRET_DOMAIN")

# All my external domain are protected with authelia
# this should be enough for authelia to authenticate
# this job.
apikey = os.environ.get("KROMGO_AUTHELIA_APIKEY")


def build_kromgo_url(tag: str, base_url: str = secret_domain):
    print(f"Building kromgo {tag} url", file=sys.stdout)
    return f"https://kromgo.{secret_domain}/{tag}?apikey={apikey}"


def fetch_metric(tag: str):
    response = requests.get(build_kromgo_url(tag))
    print(f"Downloaded metric {tag} with status: {response.status_code}", file=sys.stdout)
    response.raise_for_status()

    metric_data = response.json()
    print(f"Metric {tag} payload: {metric_data}", file=sys.stdout)
    return metric_data


if __name__ == "__main__":

    metrics_output = {}
    for tag in [
        "cluster_age_days",
        "cluster_node_count",
        "cluster_pod_count",
        "cluster_cpu_usage",
        "cluster_memory_usage",
        "cluster_uptime_days",
        "talos_version",
        "kubernetes_version",
        "flux_version",
    ]:
        try:
            metrics_output[tag] = fetch_metric(tag)
        except:
            print(f"Downloading badge {tag} failed.", file=sys.stderr)

    if metrics_output:
        export_path = "./kromgo/metrics.yaml"
        payload = { "metrics": metrics_output }
        with open(export_path, "w", encoding="utf-8") as yaml_file:
            yaml.safe_dump(payload, yaml_file, sort_keys=False)
        print(f"Metrics saved to {export_path}", file=sys.stdout)
