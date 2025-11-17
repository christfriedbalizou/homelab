<div align="center">
  <img src="https://raspbernetes.github.io/img/logo.svg">
  <br /> <br />

  ### My Home Operations Repository
  _... managed by Flux, Renovate, and GitHub Actions_ 🤖

</div>

<br />

<div align="center">

[![Talos](https://img.shields.io/badge/dynamic/yaml?label=Talos&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.talos_version.message&queryColor=%24.metrics.talos_version.color&style=for-the-badge&logo=talos&logoColor=white&color=blue)](https://talos.dev/)&nbsp;
[![Flux](https://img.shields.io/badge/dynamic/yaml?label=Flux&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.flux_version.message&queryColor=%24.metrics.flux_version.color&style=for-the-badge&logo=flux&logoColor=white&color=1aaaed)](https://fluxcd.io/)&nbsp;
[![kubernetes](https://img.shields.io/badge/dynamic/yaml?label=Kubernetes&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.kubernetes_version.message&queryColor=%24.metrics.kubernetes_version.color&style=for-the-badge&logo=kubernetes&logoColor=white&color=326ce5)](https://k3s.io/)&nbsp;


[![Age-Days](https://img.shields.io/badge/dynamic/yaml?label=Age-Days&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.cluster_age_days.message&queryColor=%24.metrics.cluster_age_days.color&style=for-the-badge&logo=clock&logoColor=white&color=orange)](https://github.com/kashalls/kromgo/)&nbsp;
[![Node-Count](https://img.shields.io/badge/dynamic/yaml?label=Node-Count&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.cluster_node_count.message&queryColor=%24.metrics.cluster_node_count.color&style=for-the-badge&logo=server&logoColor=white&color=purple)](https://github.com/kashalls/kromgo/)&nbsp;
[![Pod-Count](https://img.shields.io/badge/dynamic/yaml?label=Pod-Count&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.cluster_pod_count.message&queryColor=%24.metrics.cluster_pod_count.color&style=for-the-badge&logo=podcast&logoColor=white&color=informational)](https://github.com/kashalls/kromgo/)&nbsp;
[![CPU-Usage](https://img.shields.io/badge/dynamic/yaml?label=CPU-Usage&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.cluster_cpu_usage.message&queryColor=%24.metrics.cluster_cpu_usage.color&style=for-the-badge&logo=cpu&logoColor=white&color=yellow)](https://github.com/kashalls/kromgo/)&nbsp;
[![Memory-Usage](https://img.shields.io/badge/dynamic/yaml?label=Memory-Usage&url=https://raw.githubusercontent.com/ChristfriedBalizou/homelab/main/kromgo/metrics.yaml&query=%24.metrics.cluster_memory_usage.message&queryColor=%24.metrics.cluster_memory_usage.color&style=for-the-badge&logo=memory&logoColor=white&color=yellowgreen)](https://github.com/kashalls/kromgo/)&nbsp;

</div>

## :telescope:&nbsp; Overview

This repo is my home Kubernetes cluster declared using yaml files and contains everything I use to setup my cluster. The Kubernetes flavor I use is [k3s](https://k3s.io) to keep the size to a minimum. I use [Flux](https://fluxcd.io) to watch this repo and deploy any changes I push here. Each folder represents a different namespace. Visit my [ansible](ansible/) to see how I setup my cluster.

## :computer:&nbsp; Hardware

| Device              | Count | Memory    | Role               | Storage                               |
|:-------------------:|:-----:|:---------:|:------------------:|:-------------------------------------:|
| Ιntel NUC7i7BNH     |   2   | 32GB DDR4 |   K3s controller   |    256GB M.2 SSD                      |
| Ιntel Xeon          |   1   | 64GB DDR4 |   K3s controller   |    256GB M.2 SSD                      |
| Intel NUC7i5BNH     |   1   | 16GB DDR4 |   K3s controller   |    256GB M.2 SSG                      |
| Intel NUC7i5BNH     |   1   |  8GB DDR4 |   K3s worker       |    256GB M.2 SSG                      |
| Ιntel Celeron J4125 |   1   |  8GB DDR4 |   K3s worker       |    128GB M.2 SSD                      |
| Synology NAS DS423+ |   1   |  2GB DDR4 |   Main storage     | 56TB(2x12TB + 2x16TB) SHR + 4TB cache |

And some standby Rasbpberry Pi's 4B awaiting resurection when needed!

## :handshake:&nbsp; Thanks

I learned a lot from the people that have shared their clusters over from
[template-cluster-k3s](https://github.com/k8s-at-home/template-cluster-k3s/) and [Diaoul home-ops](https://github.com/Diaoul/home-ops) mainly [onedr0p](https://github.com/onedr0p/k3s-gitops)
and from the [k8s@home discord channel](https://discord.gg/DNCynrJ).
