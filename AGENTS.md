# AGENTS.md - Codex Guide for this Homelab

This is a Kubernetes homelab GitOps monorepo managed with Flux on Talos Linux.
Read this file before changing manifests, scripts, or bootstrap configuration.

## Project Overview

| Layer | Technology |
| --- | --- |
| OS | Talos Linux |
| Kubernetes | Kubernetes |
| GitOps | Flux v2 with flux-operator and flux-instance |
| CNI | Cilium, native routing, BGP/L2 announcements, kube-proxy replacement |
| Ingress | Envoy Gateway (Kubernetes Gateway API) |
| Storage | OpenEBS hostpath for local PVCs, NFS mounts for app data/media |
| Database | CloudNativePG in the `storage` namespace |
| Object storage | MinIO in the `storage` namespace |
| Secrets | SOPS + Age |
| Helm charts | Mostly bjw-s app-template via shared OCIRepository |
| Updates | Renovate via GitHub Actions |
| Auth | Authelia + LLDAP |

## Repository Layout

```text
kubernetes/
├── flux/cluster/ks.yaml        # Flux entrypoint → kubernetes/apps/
├── components/                 # Reusable Kustomize components
│   ├── common/                 # Namespace, OCI repos, SOPS secret, Flux alerts
│   ├── ext-auth/               # Authelia external auth (Envoy SecurityPolicy)
│   └──  nfs-scaler/             # KEDA autoscaler for NFS-dependent pods
└── apps/<namespace>/<app>/
    ├── ks.yaml                 # Flux Kustomization
    └── app/
        ├── kustomization.yaml
        ├── helmrelease.yaml
        └── secret.sops.yaml    # (optional) SOPS-encrypted secret
```

Current app namespaces include `cert-manager`, `default`, `flux-system`,
`home-automation`, `identity`, `kube-system`, `media`, `monitoring`,
`networking`, `openebs-system`, `storage`, and `system-upgrade`.

## Universal App Pattern

Most apps use a namespace-level `kustomization.yaml`, a Flux `ks.yaml`, and an
app-template `HelmRelease`. Before adding a new app, inspect a similar existing
app in the same namespace and follow its shape.

Use these defaults unless the surrounding app already does something different:

- `ks.yaml` lives at `kubernetes/apps/<namespace>/<app>/ks.yaml`.
- `spec.path` points to `./kubernetes/apps/<namespace>/<app>/app`.
- `sourceRef.name` is `home-kubernetes` in namespace `flux-system`.
- `targetNamespace` should match the namespace folder unless the app already has
  a good reason to differ.
- Add `commonMetadata.labels.app.kubernetes.io/name` for the app.
- Set `prune: true`; use `wait: true` where nearby apps do.
- Enable SOPS decryption with `secretRef.name: sops-age` when secrets are used.
- Add `postBuild.substituteFrom` with `cluster-secrets` when using `${...}`
  substitutions such as `${SECRET_DOMAIN}`, `${TIMEZONE}`, `${NFS_SERVER_APPS}`,
  or `${NFS_SERVER_MEDIA}`.
- Add `postBuild.substitute.APP` when a shared component such as `ext-auth` or
  `zeroscaler` needs the app or route name.
- Add a HelmRelease health check when the app is Helm-managed.
- Prefer `chartRef` to shared `OCIRepository` resources, especially
  `app-template` from `kubernetes/components/common/repos`.
- For app-template apps with tightly coupled helper processes, prefer one
  controller with multiple containers over separate controllers. Keep sidecars
  such as app-local caches, workers, or machine-learning helpers in the main
  controller when they share lifecycle, storage, and scheduling needs. Use
  separate controllers only when the component needs independent scaling,
  scheduling, rollout, persistence semantics, or fault isolation.

`ks.yaml` convention:

```yaml
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: &app <app>
  namespace: flux-system
spec:
  commonMetadata:
    labels:
      app.kubernetes.io/name: *app
  path: ./kubernetes/apps/<namespace>/<app>/app
  targetNamespace: <namespace>
  prune: true
  sourceRef:
    kind: GitRepository
    name: home-kubernetes
    namespace: flux-system
  postBuild:
    substituteFrom:
      - name: cluster-secrets
        kind: Secret
    substitute:
      APP: <app>
```

`app/kustomization.yaml` convention:

```yaml
---
# yaml-language-server: $schema=https://json.schemastore.org/kustomization
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: <namespace>
resources:
  - ./helmrelease.yaml
  - ./secret.sops.yaml
```

Only include `secret.sops.yaml` when the app has a secret.

For app-template HelmReleases:

- Use `controllers.<app>.containers.app` for the main container unless the
  surrounding app uses another established name.
- Use `service.app` for the primary HTTP service when the app has one public
  web surface.
- Use `values.route` for Gateway API exposure; do not leave old
  `values.ingress` stanzas behind.
- Put secrets in `secret.sops.yaml` and reference them with `envFrom` or
  `valueFrom.secretKeyRef`.
- Add `reloader.stakater.com/auto: "true"` where ConfigMaps or Secrets should
  trigger rollouts.

`app/helmrelease.yaml` convention for app-template:

```yaml
---
# yaml-language-server: $schema=https://raw.githubusercontent.com/bjw-s/helm-charts/main/charts/other/app-template/schemas/helmrelease-helm-v2.schema.json
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: &app <app>
spec:
  interval: 30m
  chartRef:
    kind: OCIRepository
    name: app-template
  values:
    controllers:
      <app>:
        containers:
          app:
            image:
              repository: <image>
              tag: <version>@sha256:<digest>
            env:
              TZ: ${TIMEZONE}
    service:
      app:
        controller: *app
        ports:
          http:
            port: <port>
    route:
      app:
        hostnames:
          - "<app>.${SECRET_DOMAIN}"
        parentRefs:
          - name: envoy-external
            namespace: networking
```

`app/secret.sops.yaml` convention:

```yaml
---
apiVersion: v1
kind: Secret
metadata:
  name: cluster-<app>-secrets
  namespace: <namespace>
stringData:
  SECRET_KEY: <encrypted-value>
```

If the secret is generated by the bootstrap template pipeline, update the
matching `bootstrap/templates/**/secret.sops.yaml.j2` file as well.

## Networking Rules

This cluster uses Envoy Gateway and Gateway API for HTTP exposure.

- Use `values.route` in app-template HelmReleases for normal web apps.
- Use a separate `app/httproute.yaml` only when the chart/app-template path is
  not enough or the app is not managed by app-template.
- Use `parentRefs` with `name: envoy-external` and `namespace: networking` for
  public routes through Cloudflare/cloudflare-dns.
- Use `parentRefs` with `name: envoy-internal` and `namespace: networking` for
  LAN-only routes.
- Do not add Kubernetes `Ingress`, ingress-nginx, Traefik, or nginx auth
  annotations for app exposure.
- The `cloudflare-dns` app uses the external-dns chart and watches
  `gateway-httproute` plus `DNSEndpoint` sources. Do not add the old
  `external-dns.home.arpa/*` Kyverno annotations.
- Cloudflare Tunnel should point at the Envoy Gateway service, not individual
  app services.

Authelia is wired through Envoy `SecurityPolicy` resources:

- For normal protected apps, add the `../../../../components/ext-auth` component
  to the app `ks.yaml` and set `postBuild.substitute.APP` to the HTTPRoute name.
- The ext-auth component defaults to `${APP}` and can target a different
  HTTPRoute with `postBuild.substitute.ROUTE`.
- For app-template generated routes, remember that `HTTPRoute.metadata.name`
  may differ from the hostname. For example, the Home Assistant route key
  `code-server` renders to `home-assistant-code-server`, while the hostname is
  `hass-code.${SECRET_DOMAIN}`.
- For apps with multiple protected routes, prefer local explicit
  `SecurityPolicy` resources in the app directory.
- Cross-namespace access to the Authelia service is allowed by the
  `ReferenceGrant` in `kubernetes/apps/identity/authelia/app/referencegrant.yaml`.

Raw `HTTPRoute` example:

```yaml
---
# yaml-language-server: $schema=https://k8s-schemas.home-operations.com/gateway.networking.k8s.io/httproute_v1.json
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app
spec:
  parentRefs:
    - name: envoy-external
      namespace: networking
      sectionName: https
  hostnames:
    # yaml-language-server-disable
    - app.${SECRET_DOMAIN}
  rules:
    - backendRefs:
        - name: app
          port: 8080
```

Hajimari does not discover `HTTPRoute` resources. Keep dashboard entries in
`kubernetes/apps/default/hajimari/app/helmrelease.yaml` under `customApps`;
do not add `hajimari.io/*` annotations to routes.

## Database Rules

PostgreSQL is centralized on CloudNativePG in the `storage` namespace.

- Do not add app-local PostgreSQL containers, statefulsets, subcharts, or PVCs for
  normal applications.
- For apps that need PostgreSQL, add an init container using
  `repository: ghcr.io/home-operations/postgres-init` and `tag: 18` to
  create/update the database and role.
- Point application database clients and `INIT_POSTGRES_HOST` at
  `postgres-lb.storage.svc.cluster.local`; include `:5432` only when the app
  expects host-and-port in one value.
- Add `spec.dependsOn` for `cloudnative-pg` in namespace `storage` when the app
  has a HelmRelease and needs the shared database.
- Reuse each app's existing secret keys for `INIT_POSTGRES_USER` and
  `INIT_POSTGRES_PASS` whenever they already exist; otherwise use
  `valueFrom.secretKeyRef` and keep generated secrets in the bootstrap template
  pipeline.
- Use `${POSTGRES_SUPER_PASS}` for `INIT_POSTGRES_SUPER_PASS` unless the app
  already sources that value from an encrypted app secret.
- Only make an exception for a dedicated PostgreSQL deployment when the user
  explicitly asks for isolation or the app requires extensions/features not
  available in the shared cluster; document the reason in the manifest.

## Storage Rules

- Use NFS mounts in app-template persistence for most app data and media.
  App/config paths under `/volume1/apps/...` use `server: ${NFS_SERVER_APPS}`;
  media paths under `/volume1/media...` use `server: ${NFS_SERVER_MEDIA}`.
- Treat NFS APPS as the protected, critical data tier. It is the only NFS
  storage currently backed up, so irreplaceable application state, databases,
  user uploads, generated app libraries, and configuration belong there.
- Treat NFS MEDIA as bulk/recreatable storage. It can hold large media caches or
  data that can be reconstructed from APPS, but it must not be the only copy of
  user-critical state.
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
- Keep app-template controller, service, route, and persistence naming aligned
  with the existing app style.
- For raw `HTTPRoute` manifests with Flux-substituted hostnames such as
  `${SECRET_DOMAIN}`, put `# yaml-language-server-disable` immediately before
  the hostname line if the YAML language server reports a schema warning.
- Avoid unnecessary quotes around ordinary strings. Keep quotes for values that
  YAML could misparse, such as boolean-like strings, number-like strings, empty
  strings, `@daily`, wildcard hostnames like `"*.${SECRET_DOMAIN}"`, and strings
  containing template syntax that benefits from quoting.

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

- Prefer pinned image tags with digests when the existing app pattern supports it
  (`tag: 1.2.3@sha256:<digest>`).
- Do not use `latest`.
- Use shared OCIRepository definitions from `kubernetes/components/common/repos`
  where available.
- Only add a new OCIRepository when the chart is genuinely new to the repo.
- Use `chartRef` in HelmReleases; avoid inline `chart:` source definitions unless
  a nearby chart already requires that pattern.
- Keep Flux remediation settings consistent with nearby HelmReleases.

## Validation

Useful local checks:

```sh
mise exec -- just --list
mise exec -- bash template/resources/kubeconform.sh kubernetes
for k in kubernetes/apps/*/kustomization.yaml; do
  d=$(dirname "$k")
  mise exec -- kustomize build "$d" --load-restrictor LoadRestrictionsNone >/dev/null
done
```

The repo kubeconform script intentionally skips some CRDs such as `HTTPRoute`,
`Gateway`, and `Secret`; use it with the Kustomize sweep for broad coverage.
CI also runs `flux-local` checks for Flux render/test coverage.
Use the repo's `just` modules for Talos, bootstrap, Kubernetes, and template
workflows when possible. Do not run destructive Talos, kubectl, or git commands
without a clear user request.

## kubectl Conventions

- Prefer read-only `kubectl get`, `kubectl describe`, and `kubectl logs` when
  inspecting the live cluster.
- Put `-n <namespace>` at the end of kubectl commands, for example
  `kubectl logs -l app=foo -n media`.
- Do not exec into pods to retrieve cluster information when Kubernetes objects,
  logs, or Prometheus data can answer the question.

## Working Rules for Codex

- Inspect existing manifests before proposing new patterns.
- Keep changes scoped to the user's request.
- Preserve user edits and do not revert unrelated dirty files.
- If a task touches live cluster access, explain the command before running it.
- Before implementing a new app or configuration pattern, check the
  [onedr0p/home-ops](https://github.com/onedr0p/home-ops) repo as a reference.
- Never suggest waiting for Flux reconciliation when a webhook or manual reconcile
  is more appropriate.

## Flux Reconciliation

This repository is GitOps-driven. Do not touch the live cluster for changes that
belong in manifests unless the user explicitly asks for live inspection or a
manual reconcile. If a pushed commit should be applied immediately, prefer a
webhook or explicit Flux reconcile over telling the user to wait.

## Git Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` for adding or removing apps/features
- `fix:` for bug fixes
- `chore:` for maintenance (dependency bumps, formatting) — **not** for adding/removing apps


## What Not To Do

- Do not add Rook-Ceph resources or dependencies.
- Do not add VolSync backup components unless explicitly requested.
- Do not add Kubernetes `Ingress`, ingress-nginx, Traefik, or nginx auth
  annotations for app exposure.
- Do not reintroduce Kyverno ingress annotation mutation policies.
- Do not use inline Helm chart sources when a shared `OCIRepository` exists.
- Do not pin container images by tag only when the surrounding app pattern uses
  tag-and-digest pinning.
- Do not skip schema headers on new YAML manifests.
- Do not commit plaintext secrets or expose existing secret values.
- Do not create broad refactors while making a narrow app change.
- Do not add new namespaces, controllers, or storage systems unless the user asks.
