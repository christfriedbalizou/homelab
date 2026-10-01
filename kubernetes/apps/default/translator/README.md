# Translator

The API and worker share one pinned image and environment in
[the HelmRelease](app/helmrelease.yaml). Flux deploys this configuration;
application releases are verified in Forgejo and the containers repository
builds the image from the exact release tag.

## Glossary capacity

| Setting | Deployment value | Scope |
| --- | --- | --- |
| `GLOSSARY__MAX_ENTRIES` | `2000` | Entries per created/edited glossary |
| `GLOSSARY__MAX_CONTENT_BYTES` | `1048576` | Serialized UTF-8 content per created/edited glossary |
| `INGESTION__MAX_GLOSSARY_SNAPSHOT_BYTES` | `1048576` | Combined terminology admitted for a new job |

These are independent positive limits. The application supplies authoring
limits to its editor; editing and viewing show 25 terms per page. Full glossaries
stay local; only matched terms may appear in bounded model context. Increasing
the limits can increase API, storage and matching costs. Lowering them does not
invalidate saved glossaries or accepted jobs, but oversized records cannot be
saved again without reducing their size or raising the authoring limits.

No credentials or secret templates are changed by these settings. The existing
local/remote provider configuration and automatic currency-rate setting remain
in the shared environment and existing Secrets.

## Release and rollback

Deploy the API/worker image together with its matching source revision, archive
checksum and immutable NFS release directory. Keep source archives outside the
frontend assets and readable only through the application's authenticated source
route. Model/font/OCR assets can be reused unchanged between releases; never
modify an archive already mounted by a running release.

v0.5.0 adds configurable glossary limits and fixes pypdf security advisories.
There is no database migration. Earlier application versions cannot decode
records above their old 200-entry/64-KiB limits. Review and reduce those records
before rolling back to older code; changing the environment limits alone does
not shrink stored records. Preserve existing data, keys and prior release files.

Application decisions and qualification evidence are maintained in the private
[Translator repository](https://git.christfriedbalizou.app/christfried.balizou/translator/src/tag/v0.5.0/docs/evidence/configurable-glossaries.md).
France/UK family law, personal taxes and household terminology content is a
separate follow-up: each topic needs explicit English-to-French and
French-to-English glossaries.

## v0.5.0 release receipt

- Application: `d7f4b8d49909e598d5f985ad0163c4e32b121724`, verified by
  [Forgejo CI run 169](https://git.christfriedbalizou.app/christfried.balizou/translator/actions/runs/169).
- Packaging: `c68d62bf6ecb29b0f30b25ed6300259dc8d093e0`;
  [container release run](https://github.com/christfriedbalizou/containers/actions/runs/36938827571)
  passed, including image attestation.
- Source archive: `/volume1/apps/default/translator/releases/0.5.0/source.tar.gz`.
- Archive SHA-256: `981a91b0d52020b479d8cba0f316a5c1121088cddde7dba25cdf292050e9efe8`.
- Source review: 555 dependency archives checksum-verified; expanded application
  source and staged-bundle secret scans passed. pypdf license inventory updated.
- Local qualification: 569 backend, 28 PostgreSQL, 24 frontend unit and five
  browser cases passed. Kustomize, repository kubeconform and the chart render
  passed. The generated API and operator documentation were updated together.

The deployed image digest and source settings are recorded in the HelmRelease.

## Rollout verification — 2026-10-02

Flux applied deployment commit `398aa696cd025d567e105ac8d77eb73e57a78ee8`;
the Kustomization and HelmRelease were Ready, with release `translator.v11`.
Both API and worker ran v0.5.0 / pypdf 6.19.0 at the pinned digest, with zero
restarts. Runtime settings confirmed 2000 entries, 1048576 content bytes,
1048576 snapshot bytes and automatic FX enabled. The API verified the mounted
source archive against the recorded SHA-256 and application revision.

A public Chromium smoke check loaded the sign-in page and received HTTP 200
from `/health` and `/ready`; unauthenticated glossary and source requests
returned 401. Service-level checks gave the same expected results. Non-browser
command-line requests received 403 from the public endpoint, so they were not
used as the browser-access acceptance check. The HTTPRoute was Accepted with
ResolvedRefs. The initial Flux dependency readiness transition cleared during
normal reconciliation without changing dependency configuration.
