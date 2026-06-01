# AGENTS.md - Codex Guide for this Homelab

This is a Kubernetes homelab GitOps monorepo managed with Flux on Talos Linux.
Read this file before changing manifests, scripts, or bootstrap configuration.

This file is the Codex equivalent of the upstream `CLAUDE.md` style guide. Keep
it tracked at the repo root so Codex loads the same project context whenever the
repository is opened from VS Code or the CLI.

## Project Overview

| Layer | Technology |
| --- | --- |
| OS | Talos Linux |
| Kubernetes | Kubernetes |
| GitOps | Flux v2 with flux-operator and flux-instance |
| CNI | Cilium, native routing, BGP/L2 announcements, kube-proxy replacement |
| Ingress | ingress-nginx only, with `internal` and `external` classes |
| Storage | OpenEBS hostpath for local PVCs, NFS mounts for app data/media |
| Database | CloudNativePG in the `storage` namespace |
| Object storage | MinIO in the `storage` namespace |
| Secrets | SOPS + Age |
| Helm charts | Mostly bjw-s app-template via shared OCIRepository |
| Auth | Authelia + LLDAP, wired through Ingress annotations |
| DNS/Tunnel | external-dns, k8s-gateway, Cloudflare Tunnel |

## Repository Layout

```text
kubernetes/
|-- flux/cluster/ks.yaml        # Flux entrypoint into kubernetes/apps
|-- components/common/          # Namespace, SOPS, shared OCI repositories
`-- apps/<namespace>/<app>/
    |-- ks.yaml                 # Flux Kustomization
    `-- app/
        |-- kustomization.yaml
        |-- helmrelease.yaml
        |-- secret.sops.yaml    # optional encrypted secret
        `-- ingress.yaml        # optional hand-written Ingress
```

Current app namespaces include `cert-manager`, `default`, `flux-system`,
`home-automation`, `identity`, `kube-system`, `kyverno`, `media`, `monitoring`,
`networking`, `openebs-system`, `storage`, and `system-upgrade`.

## App Pattern

Most apps use a namespace-level `kustomization.yaml`, a Flux `ks.yaml`, and an
app-template `HelmRelease`. Before adding a new app, inspect a similar existing
app in the same namespace.

Use these defaults unless the surrounding app already does something different:

- `ks.yaml` lives at `kubernetes/apps/<namespace>/<app>/ks.yaml`.
- `spec.path` points to `./kubernetes/apps/<namespace>/<app>/app`.
- `sourceRef.name` is `home-kubernetes` in namespace `flux-system`.
- Enable SOPS decryption with `secretRef.name: sops-age` when secrets are used.
- Add `postBuild.substituteFrom` with `cluster-secrets` when using `${...}`
  substitutions such as `${SECRET_DOMAIN}`, `${TIMEZONE}`, `${NFS_SERVER_APPS}`,
  or `${NFS_SERVER_MEDIA}`.
- Add a HelmRelease health check when the app is Helm-managed.
- Prefer `chartRef` to shared `OCIRepository` resources, especially
  `app-template` from `kubernetes/components/common/repos`.

## Networking Rules

This cluster is Ingress-first.

- Use `values.ingress` in app-template HelmReleases for normal web apps.
- Use a separate `app/ingress.yaml` only when the chart/app-template path is not
  enough or the app is not managed by app-template.
- Use `className: external` for public routes through Cloudflare/external DNS.
- Use `className: internal` for LAN-only routes.
- Do not add `HTTPRoute`, `Gateway`, `GatewayClass`, Envoy Gateway, Traefik, or
  Gateway API resources for app exposure.

Common annotations:

```yaml
external-dns.home.arpa/enabled: "true"   # Kyverno targets ipv4.${SECRET_DOMAIN}
external-dns.home.arpa/enabled: "false"  # Kyverno targets internal.${SECRET_DOMAIN}
auth.home.arpa/enabled: "true"           # Kyverno adds Authelia nginx auth
hajimari.io/enable: "true"               # Adds app to Hajimari
```

Kyverno policy `kubernetes/apps/kyverno/kyverno/policies/ingress-annotations.yaml`
mutates Ingress annotations for DNS and Authelia. Prefer those short home.arpa
annotations over repeating long nginx auth annotations in each app.

## Storage Rules

- Use NFS mounts in app-template persistence for most app data and media.
  App/config paths under `/volume1/apps/...` use `server: ${NFS_SERVER_APPS}`;
  media paths under `/volume1/media...` use `server: ${NFS_SERVER_MEDIA}`.
- Use OpenEBS hostpath (`openebs-hostpath`) for local PVC-backed services that
  need it, such as CloudNativePG or monitoring storage.
- Do not introduce Rook-Ceph, `ceph-block`, `ceph-filesystem`, or RBD settings.
- MinIO is available in `storage` and CloudNativePG uses Barman object-store
  backups there.

## Secrets

Never commit new plaintext secrets.

- This repo uses the bootstrap template pipeline for generated secrets. Templates
  live under `bootstrap/templates/**` and are rendered by `just configure`
  through `makejinja.toml` into their final repo locations.
- If a new secret file is part of the templated configuration, create or update
  the `*.sops.yaml.j2` template under `bootstrap/templates/**`, not the
  rendered `*.sops.yaml` file.
- Do not print, summarize, or expose secret values from existing files.
- Prefer `valueFrom.secretKeyRef` for sensitive environment variables.

## YAML and Manifest Conventions

- Start YAML manifests with `---`.
- Add `# yaml-language-server: $schema=...` headers where existing files in the
  same area use them.
- Keep formatting consistent with nearby files. Do not perform broad whitespace
  or quote-only rewrites.
- Quote boolean-like and number-like strings when Kubernetes or Helm expects a
  string, for example `"true"`, `"false"`, `"1000"`, or `"1"`.
- Use `${TIMEZONE}` instead of hardcoding a timezone in app manifests.
- Keep app-template controller, service, ingress, and persistence naming aligned
  with the existing app style.

## Security Defaults

Use the hardened defaults already present in nearby apps when the image supports
them:

- `allowPrivilegeEscalation: false`
- `capabilities: { drop: ["ALL"] }`
- `readOnlyRootFilesystem: true` when compatible
- `runAsNonRoot: true` and non-root UID/GID when compatible
- `seccompProfile: { type: RuntimeDefault }` at pod level when compatible
- `automountServiceAccountToken: false` unless the app needs Kubernetes API access

Do not force these settings onto images that are known to break without checking
the chart/app behavior first.

## Images and Helm

- Prefer pinned image tags with digests when the existing app pattern supports it.
- Do not use `latest`.
- Use shared OCIRepository definitions from `kubernetes/components/common/repos`
  where available.
- Only add a new OCIRepository when the chart is genuinely new to the repo.
- Keep Flux remediation settings consistent with nearby HelmReleases.

## Validation

Useful local checks:

```sh
mise exec -- just --list
for k in kubernetes/apps/*/kustomization.yaml; do
  d=$(dirname "$k")
  mise exec -- kustomize build "$d" --load-restrictor LoadRestrictionsNone >/dev/null
done
```

Use the repo's `just` modules for Talos, bootstrap, Kubernetes, and template
workflows when possible. Do not run destructive Talos, kubectl, or git commands
without a clear user request.

## Working Rules for Codex

- Inspect existing manifests before proposing new patterns.
- Keep changes scoped to the user's request.
- Preserve user edits and do not revert unrelated dirty files.
- If a task touches live cluster access, explain the command before running it.
- Before implementing a new app or configuration pattern, check the
  [onedr0p/home-ops](https://github.com/onedr0p/home-ops) repo as a reference.
- Never suggest waiting for Flux reconciliation when a webhook or manual reconcile
  is more appropriate.

## Git Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` for adding or removing apps/features
- `fix:` for bug fixes
- `chore:` for maintenance (dependency bumps, formatting) — **not** for adding/removing apps


## What Not To Do

- Do not add Rook-Ceph resources or dependencies.
- Do not add VolSync backup components unless explicitly requested.
- Do not use Gateway API, Envoy Gateway, or HTTPRoute for app exposure.
- Do not replace ingress-nginx annotations with Gateway policies.
- Do not commit plaintext secrets or expose existing secret values.
- Do not create broad refactors while making a narrow app change.
- Do not add new namespaces, controllers, or storage systems unless the user asks.
