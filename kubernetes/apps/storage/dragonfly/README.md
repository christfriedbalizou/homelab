# Dragonfly CRD

`app/crd.yaml` contains the upstream Dragonfly operator v1.6.1 CRD, matching
the operator image. Keeping it in Git avoids GitHub/network failures during
Flux builds. Its source URL and original SHA256 are recorded in the header.

When upgrading the operator, refresh the CRD from the same upstream release,
update the source/hash header and this version note, and validate the rendered
CRD and existing Dragonfly resource. Renovate updates the operator image but
does not refresh this vendored file automatically.
