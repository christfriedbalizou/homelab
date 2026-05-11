set quiet
set shell := ['bash', '-euo', 'pipefail', '-c']
set script-interpreter := ['bash', '-euo', 'pipefail']

[private]
default:
    just -l kube

[doc('Verify Flux meets the prerequisites')]
[group('kube')]
verify:
    flux check --pre

[doc('Force Flux to pull in changes from your Git repository')]
[group('kube')]
reconcile:
    flux --namespace flux-system reconcile kustomization flux-system --with-source

[doc('Force update Flux to pull in cluster app changes')]
[group('kube')]
reconcile-apps:
    flux reconcile -n flux-system kustomization cluster-apps --with-source

[doc('Restart all failed HelmReleases')]
[group('kube')]
hr-restart:
    kubectl get hr --all-namespaces | grep False | awk '{print $2, $1}' | xargs -L1 bash -c 'flux suspend hr $0 -n $1'
    kubectl get hr --all-namespaces | grep False | awk '{print $2, $1}' | xargs -L1 bash -c 'flux resume hr $0 -n $1'

[doc('Reload a HelmRelease')]
[group('kube')]
hr-reload *args:
    flux suspend hr {{ args }}
    flux resume hr {{ args }}

[doc('List all nodes in your cluster')]
[group('kube')]
nodes *args='-o wide':
    kubectl get nodes {{ args }}

[doc('List all pods in your cluster')]
[group('kube')]
pods *args='-A':
    kubectl get pods {{ args }}

[doc('List all Kustomizations in your cluster')]
[group('kube')]
kustomizations *args='-A':
    kubectl get kustomizations {{ args }}

[doc('List all HelmReleases in your cluster')]
[group('kube')]
helmreleases *args='-A':
    kubectl get helmreleases {{ args }}

[doc('List all HelmRepositories in your cluster')]
[group('kube')]
helmrepositories *args='-A':
    kubectl get helmrepositories {{ args }}

[doc('List all GitRepositories in your cluster')]
[group('kube')]
gitrepositories *args='-A':
    kubectl get gitrepositories {{ args }}

[doc('List all Certificates and CertificateRequests in your cluster')]
[group('kube')]
certificates *args='-A':
    kubectl get certificates {{ args }}
    kubectl get certificaterequests {{ args }}

[doc('List all ingresses in your cluster')]
[group('kube')]
ingresses *args='-A':
    kubectl get ingress {{ args }}

[doc('Gather common resources in your cluster, useful when asking for support')]
[group('kube')]
resources: nodes kustomizations helmreleases helmrepositories gitrepositories certificates ingresses pods
