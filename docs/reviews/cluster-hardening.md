# Cluster security and performance review

This commit is for local review only. No cluster resources, GitHub rules, live
credentials, or Talos configuration were changed. The new MinIO root credentials
are encrypted in Git and staged for the next approved deployment.

## Changes and audit coverage

| Finding | Repository change | Deployment verification |
| --- | --- | --- |
| S1 Dashboard | Replace cluster-admin with view; remove permanent token Secret and insecure login arguments. | Obtain a short-lived token, verify viewing works and writes/secrets are denied. |
| S2 CI isolation | Move job RBAC and jobs into forgejo-ci, enforce baseline Pod Security, restrict network access and resource consumption. Remove privileged Docker/DinD label and template. Controller credentials remain in devtools. | Test a normal workflow. Workflows using runs-on: docker must migrate before deployment; the removed label will not schedule jobs. |
| S3 Network isolation | Restrict ingress in application namespaces; restrict storage service ports; restrict CI egress to public Git/package endpoints, DNS, Forgejo, and HTTPS ingress. | Exercise service integrations, OIDC, webhook callbacks, media clients, DB initialization, metrics, and backups. |
| S4 MinIO | Separate encrypted root credentials from Grafana, secretKeyRef injection, internal authenticated console, separate S3 route, realistic memory budget, remove scale-to-zero. | Rotate on deployment; check IAM users/service accounts and all storage clients. Image upgrade remains a separate publication prerequisite below. |
| S5 Pod security/audit | Restore metadata-only Kubernetes audit policy in both Talos template and patch. Enable restricted audit/warn defaults. CI enforces baseline. | Talos changes require an explicit rollout. Other namespaces deliberately start in audit/warn mode to inventory exceptions. |
| S6 Grafana | Disable insecure OAuth email lookup; correct group mapping location and Admin/Editor/Viewer roles. | Verify existing accounts still map correctly; use the existing admin recovery path if necessary. |
| S7 Hardware apps | Jellyfin RuntimeDefault seccomp. Frigate no longer privileged and no longer mounts the entire USB directory; Coral/NVIDIA access comes from existing device-plugin allocations. | Verify Coral detection, camera decode, recordings and GPU transcoding before accepting rollout. These checks cannot be proven by Helm rendering. |
| S8 Update controls | Pin the ten audited application images, plus BusyBox init; enable Renovate digest pinning. Add a main-branch ruleset and explicit apply helper. | Apply ruleset separately after review; no GitHub settings were changed. MinIO current image digest comes from the running pod because registry pulls were unavailable. |
| P1 Metrics | Remove load-balanced duplicate node-exporter scrape; retain per-node ServiceMonitor. | Verify one consistent identity per node and dashboard queries. |
| P2 Memory budgets | SABnzbd request 1Gi with existing 8Gi limit; Jellyfin request 4Gi/limit 8Gi; MinIO request 2Gi/limit 4Gi. | Starting budgets based on observed use, not a complete long-term capacity guarantee. Monitor extraction, scanning, upload and playback peaks. |
| P3 Frigate memory | Request 3Gi/limit 6Gi, cache tmpfs 1Gi, shm 512Mi. | Monitor camera processes and shared memory under full load. |
| P4 FlareSolverr | Request 512Mi/limit 1Gi. | Watch browser concurrency and OOM alerts; a larger limit does not cure a leak. |
| P5 Dragonfly | Set maxmemory 384Mi within a 512Mi container limit. | Verify peak replication/cache overhead fits; enlarge limit if measurements require. |
| P6 Envoy | Reduce connection buffer 64Mi to 1Mi; request body reception timeout 15 minutes; stop trusting arbitrary pod X-Forwarded-For headers. | Test long uploads and streams. Responses retain their existing unlimited duration. Behind Cloudflare Tunnel the client address may now be the proxy; do not rely on forwarded client IP for access rules until proxy identity is isolated. |
| P7 Prometheus | Retention 24GB on 30Gi storage; disable admin API; limit copied Kubernetes labels. | Check dashboards that depended on arbitrary copied labels and disk growth. |
| P8 Jellyfin | Enable startup/readiness/liveness probes. Init script preserves existing encoding options and a first-run backup, enables throttling and segment cleanup. | Inspect the live encoding settings and long playback sessions; the 2Gi RAM volume can still fill with multiple/high-bitrate sessions. |

## Network policy boundaries

These policies are intentionally staged: normal application egress remains open;
CI egress is restricted. Trusted LAN ingress (192.168.0.0/24) is retained for
existing local integrations. Same-namespace traffic remains allowed. Application
namespace allowlists preserve known integrations; this is not per-service
zero-trust isolation. Host-network traffic and privileged system components need
separate host policies. Do not claim these policies protect against a compromised
node. CI jobs must use the fully qualified Forgejo service name after migration.

## MinIO source-only upgrade prerequisite

Upstream RELEASE.2025-10-15T17-29-55Z fixes a security issue and instructs container
users to build from source:
https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z

`containers/minio/Dockerfile` pins upstream commit
9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a, its archive checksum, and both base images.
The initial Docker build exhausted local Docker storage. The pinned source was
then successfully compiled with the same Go image using a cache on the larger
home filesystem; version identification, startup health, and authenticated S3
create/list/write/read/delete passed against disposable local data. The complete
multistage container build and production-data migration remain unverified. The deployed
image reference intentionally remains unchanged in version until the new image
is built, tested, published to an approved registry, and its digest is known.
The 2024 image's age/security issue is **not resolved by digest pinning**.

Before upgrading, take a backup/snapshot of MinIO APPS data and IAM metadata,
verify a restore, then test S3 list/read/write and a PostgreSQL backup against the
new image. The build recipe keeps UID 0 for existing NFS ownership compatibility;
it does not migrate filesystem ownership. Do not change the image reference to
an unpublished local tag or blindly downgrade MinIO metadata after an upgrade.

## Secret handling

A dedicated MinIO root username/password was generated locally. The source is in
the ignored bootstrap/vars/config.yaml (mode 0600), the template is committed,
and the rendered Kubernetes Secret is SOPS-encrypted. No plaintext credentials
are committed. Existing Forgejo and PostgreSQL S3 credentials did not match the
old MinIO root values; they were preserved. This comparison is not a substitute
for checking server-side IAM policies/service-account parentage after rotation.
Any other external root-credential clients must be updated by the operator.

## Apply only after reviewing the commit

1. Review network allowlists, resource budgets and the removed Docker runner label.
2. Resolve the MinIO image upgrade prerequisite above. Verify S3 consumers before
   the root credential rotation and keep a recovery path to the previous secret.
3. Push only when approved. Reconcile the Flux source and affected Kustomizations
   explicitly; observe rollouts, events, endpoints, backups, GPU/Coral access and
   representative user workflows. No reconciliation is performed by this commit.
4. Apply the Talos patch through the existing template/Talos workflow separately;
   pushing Git does not apply machine configuration.
5. Review `.github/rulesets/main.json`; `python3 scripts/apply-repository-ruleset.py`
   prints it. Only `--apply` writes GitHub settings. It requires PRs and a passing
   Flux Local - Success check on an up-to-date branch, without requiring another
   human reviewer in this single-operator repository.
6. For Dashboard, request a short-lived token only when needed:
   `kubectl create token kubernetes-dashboard --duration=1h -n monitoring`.
   Treat the result as a credential. The legacy permanent token is pruned on deployment.

## Recovery verification still required

Daily PostgreSQL backups and WAL archiving were healthy during the audit. Perform
an isolated restore from MinIO to a new PostgreSQL cluster/PVC, with no production
service selectors or write access to the original archive. Verify roles, database
counts and representative application reads. Delete only the disposable restore
resources after recording the result. Verify that NAS APPS backups include MinIO
and that an independent/offsite copy survives loss of the cluster and NAS.
No restore or offsite-backup claim is made by this configuration change.

## Availability

Add minAvailable: 1 disruption budgets for the existing two-replica Authelia,
LLDAP, CoreDNS, Cloudflared and both Envoy gateway deployments. Spread CoreDNS
across nodes and prefer spreading Envoy proxies. These reduce voluntary-drain
outages; they do not make single-replica storage highly available. Existing
PostgreSQL and Dragonfly operator-managed budgets remain intact.

## Validation performed

- Full Flux/Helm render suite: 183 tests passed after the runner namespace changes.
- Repository kubeconform sweep passed (using its normal CRD/Secret skips).
- Final monitoring namespace build and policy schema validation passed.
- All modified YAML manifests parse; Helm rendering confirms the Jellyfin init
  container receives /config and /scripts, and MinIO routes select ports 9001
  and 9000 separately.
- Three encoding migration tests passed: preserves unrelated settings and the
  original backup on repeat, refuses malformed XML, and handles first startup.
- New Secret fields are SOPS-encrypted; plaintext bootstrap input remains ignored.
- MinIO pinned-source compilation and disposable local S3 smoke test passed as
  described above; no live storage or credentials were used in that test.

Schema/render checks do not prove network reachability, hardware permissions,
capacity under load, compatibility with existing IAM state, or recoverability.
