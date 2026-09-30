# Translator release and recovery

Translator runs in `default` at `https://translator.${SECRET_DOMAIN}`. The
app-template release contains one API, one durable worker and one retention
process in a single Recreate deployment. A bounded init container verifies the
release, migrates the application schema and performs idempotent initial setup.
It does not create PostgreSQL roles or databases.

## Release configuration

- Image: `ghcr.io/christfriedbalizou/translator:0.3.0`, pinned by digest.
- Application revision: `a060883c6055465018e4aafe4d42eeed286cb5aa`.
- PostgreSQL: `translator`, owned by the non-superuser `translator` role on
  `postgres18`. Both CloudNativePG resources use `retain`.
- Ciphertext: Jericho `/volume1/apps/default/translator/documents`, on backed-up
  NFS APPS. PostgreSQL stores metadata and wrapped keys, not PDF files.
- Read-only release assets and corresponding source:
  `/volume1/apps/default/translator/releases/0.3.0`.
  Init copies the reproducible source archive to a 2 GiB ephemeral local cache
  and verifies its checksum before startup. Application containers mount the
  cache read-only, avoiding slow NFS reads for authenticated source downloads.
  Documents, keys and database state are not stored in this cache.
- Separate random 32-byte document and provider encryption keys are mounted from
  SOPS Secrets. Keep their bootstrap inputs and Age key in your existing secure
  backup; database/filesystem backups alone cannot recover encrypted content.
- LiteLLM: Local / Private uses `qwen3-local` through the internal Service.
  Public / Cloud uses `openai-gpt-6-luna-cloud` through LiteLLM's HTTPS API.
  Each provider has an independent encrypted key scoped to its one model and
  concurrency one. The local key cannot call the cloud model; no cloud fallback
  is configured. Both keys have metadata `cache: {no-cache: true, no-store: true}`
  to bypass shared response-cache reads/writes, using LiteLLM's
  [per-key cache controls](https://docs.litellm.ai/docs/proxy/caching_controls).
  Preserve these controls and model scopes when rotating/recreating keys.
  Only synthetic test text was sent during qualification.
  OpenAI currently returns HTTP 429 for exhausted credits; add billing credits
  and repeat the provider test before expecting cloud translations to work.
- The new Translator frontend places LLM selection before Glossaries. Local is
  selected by default; cloud requires explicit confirmation covering documents
  and glossary terms. The published 0.3.0 image includes this selector.
- CPU OCR is enabled with six pinned, verified model files. No NVIDIA allocation
  is needed. API and worker plaintext workspaces are separate memory-backed
  volumes; the worker has a 6 GiB workspace, an 8 GiB engine address-space
  limit and a 10 GiB container memory limit. The upstream 4 GiB engine default
  failed a synthetic translation with a MuPDF allocation error.
- Upload limit: 50 MiB, 200 pages, ten files/active jobs per user. Retention is
  90 days, with a daily sweep. Backup retention is independent.

## Authentication and initial administrator

The existing confidential Authelia `translator` client uses an exact HTTPS
callback, Authorization Code flow and PKCE S256. The `translator_family` policy
allows `family` OR `admin` with two-factor authentication and denies everyone
else. The development localhost callback is removed from this production client.

The initial owner is reserved using the existing public OIDC subject read from
Authelia for `christfried.balizou`. The subject is encrypted in the app Secret.
Bootstrap claims the application's initial-administrator marker before accepting
logins, preventing a family member from winning the first-login race. It fails
rather than adopting an unrelated populated database. Subsequent bootstraps do
not reset account roles or overwrite provider settings edited in the application.
Authelia groups grant login access; additional application administrators are
managed in Translator after the owner signs in.

Provider seeding is create-only. Later credential rotations must update both
LiteLLM and the encrypted provider credential through Translator's admin API/UI,
then update the bootstrap input/SOPS seed for recovery. Changing the mounted
seed alone does not overwrite an existing provider record. LiteLLM's virtual-key
records (model scopes and cache controls) live in its own PostgreSQL database;
restore that database too. A token in the Translator Secret alone does not
recreate its authorization record.

## GitOps rollout

Translator 0.3.0 is published from the verified source release. The matching
container passed build, smoke tests and provenance verification. The HelmRelease
pins the image digest, application revision, source archive checksum and release
directory together. The Translator Kustomization is enabled for reconciliation.

The database/role, storage password Secret, two scoped LiteLLM keys and Jericho
directories were provisioned before rollout. A matched snapshot of the initial
database was restored and verified in isolated PostgreSQL 18 before deployment.
The application schema is unchanged from the qualified 0.2.1 baseline.

`bootstrap/vars/config.yaml` and `.private/` are ignored and must never be added
to Git. After merging reviewed deployment changes, explicitly reconcile:

```sh
mise exec -- flux reconcile source git home-kubernetes -n flux-system
mise exec -- flux reconcile kustomization cloudnative-pg-databases -n storage
mise exec -- flux reconcile kustomization authelia -n identity
mise exec -- flux reconcile kustomization translator -n default
mise exec -- flux reconcile kustomization hajimari -n default
```

Verify the actual Kustomization namespaces with `kubectl get kustomizations -A`
if the surrounding Flux layout changes. Translator's dependencies enforce the
role/database, Authelia and LiteLLM ordering. Check all three running containers,
`/ready`, a real owner OIDC login, a real family login and denial for an account
outside both groups. Upload a synthetic PDF, download both output variants and
the corresponding-source archive, and verify the source checksum against the
HelmRelease. A browser login with real two-factor authentication and the deployed
Envoy/Cilium route still requires this post-push acceptance check.

## Updates

The containers repository already tracks Translator's private Forgejo tags and
publishes the image. Its packaging and shared Renovate runner have the required
Forgejo secrets configured. Homelab Renovate tracks the published Docker tags
and digest. Translator updates are manual: an image-only automatic rollout could
migrate the database without a corresponding source bundle or recovery set.

For each proposed image:

1. Verify `/usr/share/translator/source-revision` against the exact clean tag.
2. Prepare a NEW versioned release directory. Export committed source with
   `git archive`, never the working directory. Include the matching Python/npm
   dependency sources, notices, packaging build instructions and checksum
   manifest, following Translator's `docs/source-distribution.md`.
3. Provision BabelDOC and OCR assets from that release's locked dependencies.
   Check all hashes; do not download assets during translation. Mount the assets
   read-only. Keep old release directories for rollback.
4. Update image tag/digest, release path, source revision and source SHA-256
   together. The init verifier rejects mismatches before running migrations.
5. Run the new image against a disposable restored database and encrypted files.
   Verify migrations, bootstrap idempotency, health, user isolation, a real-engine
   synthetic translation, source downloads and cleanup.
6. Stop all writers and take a matched database/ciphertext backup before allowing
   the reviewed update to reconcile. Recreate prevents old/new API and worker
   versions overlapping; Helm automatic rollback is deliberately disabled because
   an old application may be incompatible with a migrated schema.

## Matched backups and recovery

Jericho APPS backup and CloudNativePG/Barman protect the storage tiers, but their
independent schedules do not establish a matched application snapshot. Before a
migration, suspend the Translator Kustomization and HelmRelease, scale its one
Deployment to zero, and confirm every Translator pod has terminated. This stops
API, worker and retention together. Keep PostgreSQL available.

Use the application's `python -m translator.operations backup --writers-stopped`
with the same image, keys, settings and files, plus PostgreSQL 18 `pg_dump` tools
in the maintenance environment. The published image does not bundle PostgreSQL
client utilities. Keep the completed manifest and ciphertext/database snapshot
together on protected storage, with keys escrowed separately. Never claim a
matched backup while any writer or retention process is running.

Restore a verified matched snapshot into isolated empty database and blob targets
using the matching application and keys. Run `translator.operations verify
--writers-stopped`, migrations and the synthetic acceptance checks before
reopening traffic. Do not restore over active production data or regenerate
keys during recovery. Resume the HelmRelease and Kustomization only after the
manifest, image, schema, source and data agree.

## Verification boundaries

The full `mise exec -- just configure` pipeline passed on the final manifests,
including rendered-secret, Kubernetes and Talos validation. All 55 re-rendered
SOPS files were semantically identical; unrelated ciphertext churn was removed.
Source and packaging were checked for deployment secret values. The archive
contains 551 verified dependency-source records, and the release has 182 verified
BabelDOC assets and six OCR models matching the published image.

The source release passed hosted application and security checks. Its frontend
passed 24 unit tests, typecheck, lint, formatting, build and accessibility checks.
A complete browser run passed 53 cases and identified five stale-fixture failures;
after correcting those fixtures, all 33 affected cases passed, including the
four responsive widths. The production image passed container smoke tests and
provenance verification. See `release-verification.json` for runtime qualification
and explicit remaining verification limits.

Real-user MFA callbacks through production Envoy/Cilium/DNS require an owner and
family login after rollout. Synthetic authenticated application tests do not
prove that interactive identity flow. Public cloud completion remains blocked
by exhausted OpenAI credits. Temporary test credentials and detailed verification
logs remain in ignored `.private/translator-release` with restricted permissions;
they are not release artifacts.
