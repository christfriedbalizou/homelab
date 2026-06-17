# Persistence components

These Kustomize components create reusable persistence resources for charts that
support mounting existing PVCs.

## Tiers

- `jericho-nfs`: static NFS PV/PVC on `${NFS_SERVER_APPS}`.
- `lordcommander-nfs`: static NFS PV/PVC on `${NFS_SERVER_MEDIA}`.
- `openebs-pvc`: dynamic OpenEBS hostpath PVC using `openebs-hostpath`.

## Usage

Add the component to an app `ks.yaml` and provide the component-specific
substitutions under `spec.postBuild.substitute`.

```yaml
spec:
  components:
    - ../../../../components/persistence/jericho-nfs
  postBuild:
    substitute:
      APP: paperless
      JERICHO_PATH: /volume1/apps/default
```

The component creates a PVC named `<app>-jericho`, `<app>-lordcommander`, or
`<app>-openebs`. Reference that PVC from the chart values.

For app-template:

```yaml
values:
  persistence:
    jericho:
      existingClaim: paperless-jericho
      globalMounts:
        - subPath: paperless
          path: /data/local
```

For charts with a single existing-claim setting, use the chart's native value:

```yaml
values:
  persistence:
    enabled: true
    existingClaim: paperless-jericho
```

Apps that need multiple storage tiers can include multiple components and mount
each PVC wherever the chart supports it.

Defaults:

- `JERICHO_ACCESS_MODE`: `ReadWriteMany`
- `JERICHO_CAPACITY`: `1Mi`
- `LORDCOMMANDER_ACCESS_MODE`: `ReadWriteMany`
- `LORDCOMMANDER_CAPACITY`: `1Mi`
- `OPENEBS_ACCESS_MODE`: `ReadWriteOnce`
- `OPENEBS_CAPACITY`: `5Gi`
