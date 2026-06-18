# Homelab

<div align=center>

![Homelab logo](https://raspbernetes.github.io/img/logo.svg)

[![Talos](https://img.shields.io/badge/dynamic/yaml?label=Talos&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.talos_version.message&style=for-the-badge&logo=talos&logoColor=white&color=blue)](https://talos.dev/)
[![Flux](https://img.shields.io/badge/dynamic/yaml?label=Flux&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.flux_version.message&color=blue&style=for-the-badge&logo=flux&logoColor=white)](https://fluxcd.io/)
[![Kubernetes](https://img.shields.io/badge/dynamic/yaml?label=Kubernetes&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.kubernetes_version.message&color=blue&style=for-the-badge&logo=kubernetes&logoColor=white)](https://k3s.io/)

[![Age](https://img.shields.io/badge/dynamic/yaml?label=Age&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.cluster_age_days.message&color=%24.metrics.cluster_age_days.color&style=for-the-badge&logo=clock&logoColor=white)](https://github.com/kashalls/kromgo/)
[![Uptime](https://img.shields.io/badge/dynamic/yaml?label=Uptime&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.cluster_uptime_days.message&color=%24.metrics.cluster_uptime_days.color&style=for-the-badge&logo=clock&logoColor=white)](https://github.com/kashalls/kromgo/)
[![Nodes](https://img.shields.io/badge/dynamic/yaml?label=Nodes&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.cluster_node_count.message&color=%24.metrics.cluster_node_count.color&style=for-the-badge&logo=node&logoColor=white)](https://github.com/kashalls/kromgo/)
[![Pods](https://img.shields.io/badge/dynamic/yaml?label=Pods&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.cluster_pod_count.message&color=%24.metrics.cluster_pod_count.color&style=for-the-badge&logo=podcast&logoColor=white)](https://github.com/kashalls/kromgo/)
[![CPU](https://img.shields.io/badge/dynamic/yaml?label=CPU&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.cluster_cpu_usage.message&color=%24.metrics.cluster_cpu_usage.color&style=for-the-badge&logo=cpu&logoColor=white)](https://github.com/kashalls/kromgo/)
[![Memory](https://img.shields.io/badge/dynamic/yaml?label=Memory&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.cluster_memory_usage.message&color=%24.metrics.cluster_memory_usage.color&style=for-the-badge&logo=memory&logoColor=white)](https://github.com/kashalls/kromgo/)

</div>

> Homelab is my fully self-hosted control plane, storage, and automation repository. Every manifest and script in this collection is designed to run on hardware I own, with minimal reliance on public cloud services and maximal control over the entire stack.

## <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f636_200d_1f32b_fe0f/512.gif" alt="😶" width="20" height="20"> Cloud Dependencies

Most of my infrastructure and workloads are self-hosted, but I rely on the cloud for certain key parts of my setup.

| Service                                   | Use                                                            | Cost           |
|-------------------------------------------|----------------------------------------------------------------|----------------|
| [Cloudflare](https://www.cloudflare.com/) | Domain and security                                            | Free           |
| [GitHub](https://github.com/)             | Hosting this repository and continuous integration/deployments | Free           |
| [GCP](https://cloud.google.com/)          | Voice interactions with Home Assistant over Google Assistant   | Free           |
| [Purelymail](https://purelymail.com/)     | Email hosting                                                  | ~$10/yr        |
|                                           |                                                                | Total: ~$1/mo  |

## <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/2699_fe0f/512.gif" alt="⚙" width="20" height="20"> Hardware

| Device                  | Count | Memory    | Role                                                                            | Storage                               |
|-------------------------|-------|-----------|---------------------------------------------------------------------------------|---------------------------------------|
| PowerEdge R630          |   2   | 64GB DDR4 |   Talos/Kubernetes control-plane nodes (`k8s-6`, `k8s-7`)                       | ~1.1TiB ephemeral each (`/dev/sdb`)   |
| OptiPlex 7050           |   1   | 16GB DDR4 |   Talos/Kubernetes control-plane and accelerator node (`k8s-3`)                 | ~236GiB ephemeral (`/dev/sda`)        |
| NVIDIA GeForce RTX 3050 |   1   | 6GB GDDR6 |   GPU acceleration via Talos NVIDIA extensions and `nvidia.com/gpu.shared`      | N/A                                   |
| Google Coral TPU        |   1   | N/A       |   Edge TPU acceleration via Talos gasket/apex and `squat.ai/coral`              | N/A                                   |
| Synology DS423+         |   1   |  2GB DDR4 |   Apps NFS storage (`NFS_SERVER_APPS`)                                          | 36.6T usable   |
| Synology RS2416RP+      |   1   |  2GB DDR4 |   Media NFS storage and backup (`NFS_SERVER_MEDIA`)                             | 69.8T usable  |

## <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f64f/512.gif" alt="🙏" width="20" height="20"> Gratitude and Thanks

I learned a lot from the people who have shared their clusters over from
[template-cluster-k3s](https://github.com/k8s-at-home/template-cluster-k3s/) and [Diaoul home-ops](https://github.com/Diaoul/home-ops) mainly [onedr0p](https://github.com/onedr0p/k3s-gitops)
and from the [k8s@home discord channel](https://discord.gg/DNCynrJ).
