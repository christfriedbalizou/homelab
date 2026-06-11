set quiet
set shell := ['bash', '-euo', 'pipefail', '-c']
set script-interpreter := ['bash', '-euo', 'pipefail']
set working-directory := '..'

ansible_dir := justfile_dir() + '/ansible'
bootstrap_dir := justfile_dir() + '/bootstrap'
kubernetes_dir := justfile_dir() + '/kubernetes'
talos_dir := justfile_dir() + '/talos'
private_dir := justfile_dir() + '/.private'

template_dir := bootstrap_dir + '/templates'
template_resources := justfile_dir() + '/template/resources'
makejinja_config := justfile_dir() + '/makejinja.toml'

config_file := bootstrap_dir + '/vars/config.yaml'
deploy_key := justfile_dir() + '/github-deploy.key'
push_token_file := justfile_dir() + '/github-push-token.txt'

[private]
default:
    just -l template

[confirm("Any conflicting files in the kubernetes directory will be overwritten - continue? [y/N]")]
[doc('Render and validate configuration files')]
[group('template')]
configure: configure-preconditions render validate-rendered-sops-secrets encrypt-secrets validate-kubernetes validate-talos

[doc('Gather common resources in your cluster')]
[group('template')]
debug:
    for resource in certificates certificaterequests gitrepositories helmrepositories helmreleases httproutes kustomizations nodes pods; do kubectl get --all-namespaces "$resource"; done

[doc('Initialize configuration files (age key, deploy key, push token)')]
[group('template')]
init:
    [ -f "$SOPS_AGE_KEY_FILE" ]    || age-keygen --output "$SOPS_AGE_KEY_FILE"
    [ -f "{{ deploy_key }}" ]      || ssh-keygen -t ecdsa -b 521 -C "deploy-key" -f "{{ deploy_key }}" -q -P ""
    [ -f "{{ push_token_file }}" ] || python -c "import secrets; print(secrets.token_hex(16))" > "{{ push_token_file }}"

[confirm("Remove all templated files and directories - continue? [y/N]")]
[doc('Remove rendered files (bootstrap/, kubernetes/, talos/, .sops.yaml)')]
[group('template')]
reset:
    rm -rf "{{ bootstrap_dir }}" "{{ kubernetes_dir }}" "{{ talos_dir }}" "{{ justfile_dir() }}/.sops.yaml"

[confirm("All template related config will be archived - continue? [y/N]")]
[doc('Archive template related files under .private/<ts>/')]
[group('template')]
tidy: tidy-preconditions tidy-strip tidy-archive

[private]
configure-preconditions:
    ! test -f ~/.config/sops/age/keys.txt || { just log error "An existing Age key interferes with this repository; rename or delete ~/.config/sops/age/keys.txt"; exit 1; }

[private]
[script]
encrypt-secrets:
    find "{{ ansible_dir }}" "{{ bootstrap_dir }}" "{{ kubernetes_dir }}" "{{ talos_dir }}" \
        -path "{{ template_dir }}" -prune -o \
        -type f -name '*.sops.*' ! -name '*.j2' ! -name 'talsecret.sops.yaml' -print0 \
        | while IFS= read -r -d '' f; do
            if [ "$(sops filestatus "$f" | jq '.encrypted')" = "false" ]; then
                sops --encrypt --in-place "$f"
            fi
        done

[private]
render:
    test -f "{{ justfile_dir() }}/scripts/plugin.py"
    test -f "{{ makejinja_config }}"
    PYTHONDONTWRITEBYTECODE=1 makejinja

[private]
validate-rendered-sops-secrets:
    PYTHONDONTWRITEBYTECODE=1 python "{{ justfile_dir() }}/scripts/validate-sops-secrets.py" "{{ ansible_dir }}" "{{ bootstrap_dir }}" "{{ kubernetes_dir }}" "{{ talos_dir }}" --exclude "{{ template_dir }}"

[private]
[script]
tidy-archive:
    TIDY_FOLDER="{{ private_dir }}/$(date +%s)"
    mkdir -p "$TIDY_FOLDER"
    rm -rf "{{ justfile_dir() }}/.github/tests" "{{ justfile_dir() }}/.github/workflows/e2e.yaml" "{{ justfile_dir() }}/.github/workflows/mise.yaml" "{{ justfile_dir() }}/.github/workflows/release.yaml"
    [ ! -d "{{ template_dir }}" ]     || mv "{{ template_dir }}" "$TIDY_FOLDER/templates"
    [ ! -f "{{ makejinja_config }}" ] || mv "{{ makejinja_config }}" "$TIDY_FOLDER/makejinja.toml"
    [ ! -f "{{ config_file }}" ]      || mv "{{ config_file }}" "$TIDY_FOLDER/config.yaml"

[private]
tidy-preconditions:
    test -d "{{ template_dir }}"
    test -f "{{ makejinja_config }}"
    test -f "{{ justfile_dir() }}/.renovaterc.json5"

[private]
tidy-strip:
    sed -i 's/(..\.j2)\?//g' "{{ justfile_dir() }}/.renovaterc.json5"
    sed -i '/# === template ===/,$d' "{{ justfile_dir() }}/justfile"
    sed -i '/required:template/d' "{{ justfile_dir() }}/.mise.toml"

[private]
validate-kubernetes:
    test -f "{{ template_resources }}/kubeconform.sh"
    bash "{{ template_resources }}/kubeconform.sh" "{{ kubernetes_dir }}"

[private]
[working-directory('talos')]
validate-talos:
    test -d clusterconfig
    for config in clusterconfig/kubernetes-*.yaml; do talosctl validate --config "$config" --mode metal; done
