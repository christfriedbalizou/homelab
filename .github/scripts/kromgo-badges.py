import os
import sys
import requests

secret_domain = os.environ.get("SECRET_DOMAIN")

# All my external domain are protected with authelia
# this should be enough for authelia to authenticate
# this job.
apikey = os.environ.get("KROMGO_AUTHELIA_APIKEY")


def build_kromgo_url(tag: str, base_url: str = secret_domain):
    print(f"Building kromgo {tag} url", file=sys.stdout)
    return f"https://kromgo.{secret_domain}/{tag}?format=badge&apikey={apikey}"


def download_svg(tag: str):
    response = requests.get(build_kromgo_url(tag))
    print(f"Downloaded badge {tag} with status: {response.status_code}", file=sys.stdout)

    response.raise_for_status()

    with open(f"./kromgo/{tag}.svg", "wb") as file_descriptor:
        print(f"Saving badge {tag}", file=sys.stdout)

        for chunk in response:
            file_descriptor.write(chunk)


if __name__ == "__main__":

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
            download_svg(tag)
        except:
            print(f"Downloading badge {tag} failed.", file=sys.stderr)
