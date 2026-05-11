set quiet
set shell := ['bash', '-euo', 'pipefail', '-c']
set script-interpreter := ['bash', '-euo', 'pipefail']

export KUBECONFIG := justfile_dir() + '/kubeconfig'
export SOPS_AGE_KEY_FILE := justfile_dir() + '/age.key'
export TALOSCONFIG := justfile_dir() + '/talos/clusterconfig/talosconfig'
export PATH := justfile_dir() + '/.venv/bin:' + env_var('PATH')
export VIRTUAL_ENV := justfile_dir() + '/.venv'
export ANSIBLE_COLLECTIONS_PATH := justfile_dir() + '/.venv/galaxy'
export ANSIBLE_ROLES_PATH := justfile_dir() + '/.venv/galaxy/ansible_roles:' + justfile_dir() + '/ansible/roles'
export ANSIBLE_VARS_ENABLED := 'host_group_vars,community.sops.sops'
export K8S_AUTH_KUBECONFIG := justfile_dir() + '/kubeconfig'

[group: 'bootstrap']
mod? bootstrap 'bootstrap'

[group: 'kubernetes']
mod? kube 'kubernetes'

[group: 'talos']
mod? talos 'talos'

[group: 'pihole']
mod? pihole 'ansible'

[private]
default:
    just -l

[private]
log lvl msg *args:
    @if command -v gum >/dev/null 2>&1; then \
        gum log -t rfc3339 -s -l "{{ lvl }}" "{{ msg }}" {{ args }}; \
    else \
        printf '[%s] %s' "{{ lvl }}" "{{ msg }}"; \
        if [ -n "{{ args }}" ]; then printf ' %s' {{ args }}; fi; \
        printf '\n'; \
    fi

[doc('Create a Python virtual env and install required packages')]
[group('deps')]
deps:
    python3 -m venv "{{ justfile_dir() }}/.venv"
    "{{ justfile_dir() }}/.venv/bin/python3" -m pip install --upgrade pip setuptools wheel
    "{{ justfile_dir() }}/.venv/bin/python3" -m pip install --upgrade --requirement "{{ justfile_dir() }}/requirements.txt"
    "{{ justfile_dir() }}/.venv/bin/ansible-galaxy" install --role-file "{{ justfile_dir() }}/requirements.yaml" --force

# === template ===

[group: 'template']
mod template 'template'

[doc('Render and validate configuration files')]
[group('template')]
configure:
    just template configure

[doc('Initialize configuration files (age key, deploy key, push token)')]
[group('template')]
init:
    just template init

[doc('Force Flux to pull in changes from your Git repository')]
[group('kubernetes')]
reconcile:
    just kube reconcile
