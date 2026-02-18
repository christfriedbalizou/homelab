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
| [Purelymail](https://purelymail.com/)     | Email hosting                                                  | ~$10/yr        |
|                                           |                                                                | Total: ~$1/mo  |

## <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/2699_fe0f/512.gif" alt="⚙" width="20" height="20"> Hardware

| Device              | Count | Memory    | Role               | Storage                               |
|---------------------|-------|-----------|--------------------|---------------------------------------|
| Ιntel NUC7i7BNH     |   2   | 32GB DDR4 |   K3s controller   |    256GB M.2 SSD                      |
| Ιntel Xeon          |   1   | 64GB DDR4 |   K3s controller   |    256GB M.2 SSD                      |
| Intel NUC7i5BNH     |   1   | 16GB DDR4 |   K3s controller   |    256GB M.2 SSG                      |
| Intel NUC7i5BNH     |   1   |  8GB DDR4 |   K3s worker       |    256GB M.2 SSG                      |
| Ιntel Celeron J4125 |   1   |  8GB DDR4 |   K3s worker       |    128GB M.2 SSD                      |
| Synology NAS DS423+ |   1   |  2GB DDR4 |   Main storage     | 56TB(2x12TB + 2x16TB) SHR + 4TB cache |

Raspberry Pi 4B units remain on the shelf, ready to join the self-hosted fabric if more capacity or ARM testing is needed.

## <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f64f/512.gif" alt="🙏" width="20" height="20"> Gratitude and Thanks

I learned a lot from the people who have shared their clusters over from
[template-cluster-k3s](https://github.com/k8s-at-home/template-cluster-k3s/) and [Diaoul home-ops](https://github.com/Diaoul/home-ops) mainly [onedr0p](https://github.com/onedr0p/k3s-gitops)
and from the [k8s@home discord channel](https://discord.gg/DNCynrJ).
