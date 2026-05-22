set quiet
set script-interpreter := ['bash', '-euo', 'pipefail']
set shell := ['bash', '-euo', 'pipefail', '-c']

clusterconfig_dir := justfile_dir() + '/talos/clusterconfig'
talconfig_file := justfile_dir() + '/talos/talconfig.yaml'

[private]
default:
    just -l talos

[confirm('Apply Talos config to ' + node + ' [y|N] ?')]
[doc('Apply Talos config to a node')]
apply-node node *args:
    just talos render-config "{{ node }}" | talosctl -n "{{ node }}" apply-config -f /dev/stdin {{ args }}

[doc('Download Talos machine image')]
[script]
download-image version:
    export SCHEMATIC="$(just talos schematic-id)"
    curl -fL --remove-on-error --retry 5 --retry-delay 5 --retry-all-errors --progress-bar \
        -o "{{ justfile_dir() }}/talos-{{ version }}-${SCHEMATIC:0:8}.iso" \
        "https://factory.talos.dev/image/${SCHEMATIC}/{{ version }}/metal-amd64.iso"
    just log info "Downloaded Talos" version "{{ version }}" schematic "${SCHEMATIC}"

[confirm('Reboot node ' + node + ' [y|N] ?')]
[doc('Reboot a node')]
reboot-node node:
    talosctl -n {{ node }} reboot -m powercycle

[doc('Render Talos config for a node')]
[script]
render-config node:
    if [ -f "{{ clusterconfig_dir }}/kubernetes-{{ node }}.yaml" ]; then
        cat "{{ clusterconfig_dir }}/kubernetes-{{ node }}.yaml"
        exit 0
    fi
    hostname="$(yq -er '.nodes[] | select(.ipAddress == "{{ node }}") | .hostname' "{{ talconfig_file }}")"
    cat "{{ clusterconfig_dir }}/kubernetes-${hostname}.yaml"

[confirm('Reset node ' + node + ' [y|N] ?')]
[doc('Reset a node')]
reset-node node *args:
    talosctl -n "{{ node }}" reset --system-labels-to-wipe STATE --system-labels-to-wipe EPHEMERAL --graceful=false {{ args }}

[confirm('Gracefully retire node ' + node + ' from Kubernetes and etcd [y|N] ?')]
[doc('Gracefully reset a node before replacing hardware')]
retire-node node *args:
    talosctl -n "{{ node }}" reset --system-labels-to-wipe STATE --system-labels-to-wipe EPHEMERAL --graceful=true --reboot=false {{ args }}

[confirm('Shutdown node ' + node + ' [y|N] ?')]
[doc('Shutdown a node')]
shutdown-node node *args:
    talosctl -n "{{ node }}" shutdown --force {{ args }}

[confirm('Upgrade Kubernetes to ' + version + ' [y|N] ?')]
[doc('Upgrade Kubernetes version on the cluster')]
upgrade-k8s version:
    talosctl -n "$(talosctl config info -o yaml | yq -e '.endpoints[0]')" upgrade-k8s --to {{ version }}

[confirm('Upgrade node ' + node + ' [y|N] ?')]
[doc('Upgrade Talos version on a node')]
upgrade-node node *args:
    talosctl -n "{{ node }}" upgrade -i "$(just talos machine-image "{{ node }}")" -m powercycle --timeout=10m {{ args }}

[private]
schematic-id:
    yq -er '.nodes[] | select(.talosImageURL) | .talosImageURL' "{{ talconfig_file }}" | head -1 | sed -E 's#.*installer/([^:/]+).*#\1#'

[private]
machine-image node:
    just talos render-config "{{ node }}" | yq -e 'select(.machine) | .machine.install.image'
