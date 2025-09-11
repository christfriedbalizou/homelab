<div align="center">
  <img src="https://raspbernetes.github.io/img/logo.svg">
  <br /> <br />
  
  ### My Home Operations Repository
  _... managed by Flux, Renovate, and GitHub Actions_ 🤖
 
</div> 
<br />
<div align="center">
  
[![kubernetes](https://img.shields.io/badge/dynamic/yaml?url=https://raw.githubusercontent.com/christfriedbalizou/homelab/main/talos/talenv.yaml&query=$.kubernetesVersion&style=for-the-badge&logo=kubernetes&logoColor=white&label=Kubernetes)](https://k3s.io/) &nbsp;
[![GitHub last commit](https://img.shields.io/github/last-commit/christfriedbalizou/homelab?color=purple&style=for-the-badge)](https://github.com/christfriedbalizou/homelab/commits/main) &nbsp;
![GitHub Release](https://img.shields.io/github/release/christfriedbalizou/homelab?style=for-the-badge&logo=dependabot)


[![Age-Days](https://raw.githubusercontent.com/ChristfriedBalizou/homelab/refs/heads/main/kromgo/cluster_age_days.svg)](https://github.com/kashalls/kromgo/)&nbsp;
[![Node-Count](https://raw.githubusercontent.com/ChristfriedBalizou/homelab/refs/heads/main/kromgo/cluster_node_count.svg)](https://github.com/kashalls/kromgo/)&nbsp;
[![Pod-Count](https://raw.githubusercontent.com/ChristfriedBalizou/homelab/refs/heads/main/kromgo/cluster_pod_count.svg)](https://github.com/kashalls/kromgo/)&nbsp;
[![CPU-Usage](https://raw.githubusercontent.com/ChristfriedBalizou/homelab/refs/heads/main/kromgo/cluster_cpu_usage.svg)](https://github.com/kashalls/kromgo/)&nbsp;
[![Memory-Usage](https://raw.githubusercontent.com/ChristfriedBalizou/homelab/refs/heads/main/kromgo/cluster_memory_usage.svg)](https://github.com/kashalls/kromgo/)&nbsp;

</div>

---

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
