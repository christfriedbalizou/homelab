# Staged AI stack

Prepared from [Diaoul/home-ops at 5e337d3](https://github.com/Diaoul/home-ops/tree/5e337d342fd403850146a0817ddffec228ec855e/kubernetes/apps/ai).
The [onedr0p Home Assistant MCP deployment](https://github.com/onedr0p/home-ops/blob/main/kubernetes/apps/default/home-assistant/mcp/helmrelease.yaml)
was also checked for its internal Home Assistant endpoint and container settings.

**Nothing new is registered in `ai/kustomization.yaml`.** Existing Ollama and
Open WebUI manifests remain unchanged. New apps, the NVIDIA component and the
Open WebUI overlay are dormant. This branch is preparation, not an activation.
No credentials were generated and no cluster commands were run.

## Layout and connections

| Path | Purpose |
| --- | --- |
| `llmkube/` | Operator and Qwen3-Embedding-0.6B served by CUDA llama.cpp on the shared NVIDIA GPU. Downloaded model cache uses OpenEBS hostpath. |
| `litellm-operator/` | Manages proxy, model and MCP resources; auto-registers ready LLMKube models. |
| `litellm/database/` | Provisions a role/database on shared CloudNativePG using a postgres-init init container. |
| `litellm/app/` | Internal gateway to existing Ollama, Anthropic and OpenCode Go models; uses shared Dragonfly. |
| `context7-mcp/` | Registers the hosted Context7 documentation endpoint with LiteLLM. |
| `ha-mcp/` | Runs Home Assistant MCP inside the cluster and registers it with LiteLLM. |
| `memini/` | Persistent memory, using Qwen embeddings directly and Claude Haiku through LiteLLM. |
| `open-webui/litellm/` | Optional overlay switching existing Open WebUI to LiteLLM for chat and embeddings. |
| `../../components/ai-nvidia-sharing/` | Optional NVIDIA ConfigMap patch allowing four shared GPU scheduling allocations. |

```text
Open WebUI -> LiteLLM -> Ollama (existing qwen3:4b)
                     -> Anthropic / OpenCode Go
                     -> LLMKube embedding service
MCP clients -> LiteLLM -> Context7 / ha-mcp -> Home Assistant
Memory clients -> Memini -> embedding service
                        -> LiteLLM -> Claude Haiku
```

Local aliases are `qwen3-local` and `qwen3-local-think`, both pointing to
`ollama.ai.svc.cluster.local:11434`. There is no Jupiter hostname or Intel
resource claim. Local requests have no automatic cloud fallback. The provider
model declarations follow the referenced upstream commit; verify account/model
availability before enabling providers.

LLMKube owns the generated embedding Service `qwen3-embedding-0-6b`. Its direct
model alias is `qwen3-embedding`; LiteLLM auto-registers it as
`qwen3-embedding-0.6b`. These different names are intentional.

## Before activation on the personal laptop

1. Check out this branch and review/rebase against current `main` before merging.
2. Confirm GPU scheduling capacity. The existing NVIDIA ConfigMap exposes three
   shares, and Ollama, Frigate and Jellyfin each request one. The embedding
   service needs a fourth. Add the following component to
   `kubernetes/apps/kube-system/device-plugin/nvidia/app/kustomization.yaml`
   when ready, or free a share by moving another consumer:

   ```yaml
   components:
     - ../../../../../components/ai-nvidia-sharing
   ```

   This component is not registered now. Four shares still share the same 6 GB
   of VRAM; they provide neither memory isolation nor additional capacity.
   Validate concurrent inference, video workloads and rollouts before enabling
   all consumers. Embeddings use one replica, one shared GPU resource, a 2048
   context and 512-token micro-batches. Longer individual embedding inputs need
   chunking or a reviewed micro-batch increase. Memini initially embeds only the
   first 1200 characters per memory; tune this with measured memory use later.
3. Confirm OpenEBS can provision a 5 GiB model cache on the GPU node and a 5 GiB
   Memini PVC. The model cache is disposable; the Memini PVC contains user data.
4. Create `/volume1/apps/ai/memini-backups` on the APPS NFS server, writable by
   UID/GID 1000. Confirm the export permits this path and includes it in the
   existing APPS backup policy.
5. Prepare provider credentials, the Home Assistant token, Context7 key, LiteLLM
   database/master/OIDC credentials and Memini API key as described below.
6. Configure the LiteLLM Authelia client before using its admin UI. Add the
   snippet below under `identity_providers.oidc.clients` in the existing
   Authelia configuration:

   ```yaml
   - client_id: litellm
     client_name: LiteLLM
     client_secret: "${LITELLM_OAUTH_CLIENT_SECRET_PBKDF2}"
     public: false
     authorization_policy: two_factor
     require_pkce: false
     pkce_challenge_method: ""
     redirect_uris:
       - https://litellm.${SECRET_DOMAIN}/sso/callback
     scopes: [openid, profile, email]
     response_types: [code]
     grant_types: [authorization_code]
     userinfo_signed_response_alg: none
     token_endpoint_auth_method: client_secret_basic
   ```

   Add `LITELLM_OAUTH_CLIENT_SECRET_PBKDF2` to the existing **cluster-secrets
   bootstrap template**, using `{{ pbkdf2(litellm_oauth_client_secret) }}` like
   the other OIDC clients. The clear client secret is only in the encrypted
   LiteLLM app Secret. `litellm_admin_id` must match the intended Authelia user
   identity returned to LiteLLM. Keep API access token-based: do not attach
   an interactive ext-auth redirect to LiteLLM's API/MCP endpoints.

Internal hostnames are `litellm.${SECRET_DOMAIN}`, `memini.${SECRET_DOMAIN}`
(admin UI) and `memini-api.${SECRET_DOMAIN}` (authenticated API/MCP). Ensure
LAN/VPN DNS resolves them to the internal Envoy Gateway. Open WebUI retains
`ai.${SECRET_DOMAIN}` and its current Authelia family/admin role mapping.

## Secrets: templates only until credentials are available

New templates live in `bootstrap/templates/kubernetes/apps/ai/`. Each has a
separate opt-in flag, defaulting to false, so normal `just configure` does not
require new credentials. Disabled templates render no Secret documents.
These flags render secrets; they do **not** deploy apps.

Set the relevant flag and inputs in the ignored `bootstrap/vars/config.yaml`:

| Flag | Inputs | Destination Secret |
| --- | --- | --- |
| `ai_litellm_secrets_enabled` | `litellm_postgres_password`, `litellm_master_key`, `litellm_oauth_client_secret`, `litellm_admin_id`, `litellm_anthropic_api_key`, `litellm_opencode_go_api_key` | `cluster-litellm-secrets` in `litellm/database/secret.sops.yaml` |
| `ai_context7_secrets_enabled` | `context7_api_key` | `cluster-context7-mcp-secrets` |
| `ai_ha_mcp_secrets_enabled` | `ha_mcp_homeassistant_token` | `cluster-ha-mcp-secrets` |
| `ai_memini_secrets_enabled` | `memini_api_key`, `memini_litellm_api_key` | `cluster-memini-secrets` |
| `ai_open_webui_litellm_secrets_enabled` | `open_webui_litellm_api_key` | `cluster-open-webui-litellm-secrets` in `open-webui/litellm/secret.sops.yaml` |

Use fresh random credentials on the personal laptop. LiteLLM master/virtual
keys use the `sk-` prefix. Use a URL-safe database password. If a provider is
unwanted, remove its model resource entries and matching secret-template key
before enabling LiteLLM; do not insert a fake credential.

Run `mise exec -- just configure` using the existing Age key, review the diff,
and verify every new rendered Secret is SOPS-encrypted. Then uncomment
`- ./secret.sops.yaml` in that app's `kustomization.yaml`. No missing Secret
files are referenced in the staged builds.

Activate LiteLLM first to issue **separate scoped virtual keys** for Open WebUI
and Memini. Open WebUI needs its chosen chat models and
`qwen3-embedding-0.6b`; Memini's initial LLM key only needs `claude-haiku-4-5`.
Then enable the corresponding client secret flags and run `just configure`
again. Do not distribute the LiteLLM master key to clients.

The database Job deliberately remains after completion for Flux dependency
health. If the PostgreSQL password is rotated later, rerun this idempotent Job
as part of the rotation before rolling the proxy; changing only a Secret does
not rerun an already completed Job.

## Activation order

Register the new entries in `kubernetes/apps/ai/kustomization.yaml` only after
the relevant prerequisites and encrypted secrets are ready:

1. `./llmkube/ks.yaml` and `./litellm-operator/ks.yaml`. The first file contains
   both the operator and the separate `llmkube-models` Flux Kustomization.
2. `./litellm/ks.yaml`. Its database Job waits for `cloudnative-pg-cluster`;
   the proxy waits for that Job, its operator and shared `dragonfly-cluster`.
3. `./context7-mcp/ks.yaml` and `./ha-mcp/ks.yaml` when their tokens are ready.
4. `./memini/ks.yaml` after its client key, storage and embeddings are ready.
5. **Replace** `./open-webui/ks.yaml` with `./open-webui/ks-litellm.yaml`.
   Never include both: they name the same Flux Kustomization. Keep
   `./ollama/ks.yaml`, since local chat still uses your existing Ollama.

After the activation commit is merged, use the repository webhook or explicit
Flux reconciliation. Check operator/HelmRelease readiness, embedding output
(1024 dimensions), each provider, the local-only alias, and both MCP tools.
Check that Memini writes a usable NFS snapshot and can recover from it.

Open WebUI can retain connection settings in its database. Inspect its admin
connections and document settings after switching: saved values may override
environment defaults. Back up the existing PostgreSQL database and APPS data
before migrating document embeddings; reindex existing knowledge from
`nomic-embed-text` to Qwen. Verify chats and existing Authelia access still work.

Configure MCP client connections and tool permissions explicitly. Add the
Memini integration to chosen clients (Open WebUI's filter/tools or an MCP client
at `https://memini-api.<domain>/mcp`); deploying the server alone does not attach
memory to chats. Separate family/user memory namespaces and client keys before
using private memories. The upstream SearXNG web-search setting is deliberately
deferred: this repo has no SearXNG deployment yet.

## Memini storage and recovery

Memini's SQLite WAL store is on OpenEBS, not NFS. A backup sidecar in the same
pod uses SQLite's online backup API, including committed WAL transactions,
and atomically publishes an hourly snapshot on protected APPS NFS. It retains
the latest snapshot for each of seven UTC days. No database contents or API
credentials are logged. The daily fsck job performs maintenance, not backups.

The local PVC can be lost with its node. Recovery therefore depends on a
successful NFS snapshot; the intended recovery point is at most one hour old
while backups are healthy. Check sidecar logs and NFS file timestamps before
trusting the service. No VectorChord changes, dedicated PostgreSQL deployment,
Ceph, Miroir or VolSync are required.

For recovery, stop Memini and suspend its fsck job, restore the chosen snapshot
as `/data/memini.db` on a replacement PVC, remove stale WAL/SHM files belonging
to the old store, and ensure UID/GID 1000 ownership. Keep the same embedding
model alias and 1024 dimensions, then restart and test recall. Memini's
[backup guide](https://github.com/eleboucher/memini/blob/v0.7.32/docs/operations/backup-restore.md)
also describes logical export/import for changing embedding dimensions.

## Offline validation

Preparation checks passed on 2026-09-28: unchanged active AI build and Flux
entrypoint, all namespace Kustomize builds, the four pinned Helm charts,
20 custom resources against the installed chart CRDs, and core/Flux schemas.
All five disabled templates were checked with makejinja 2.9.1 and produce no
output files. Synthetic SQLite tests verified WAL recovery, repeated snapshots,
retention, and preserving previous backups when the source is unavailable.

No live Kubernetes credentials are needed:

```sh
mise exec -- just --list
mise exec -- bash template/resources/kubeconform.sh kubernetes
for app in litellm-operator llmkube litellm context7-mcp ha-mcp memini; do
  mise exec -- kustomize build "kubernetes/apps/ai/$app/app" --load-restrictor LoadRestrictionsNone >/dev/null
done
mise exec -- kustomize build kubernetes/apps/ai/llmkube/models >/dev/null
mise exec -- kustomize build kubernetes/apps/ai/litellm/database >/dev/null
mise exec -- kustomize build kubernetes/apps/ai/open-webui/litellm --load-restrictor LoadRestrictionsNone >/dev/null
```

Also render the pinned Helm charts and validate custom resources against those
charts' CRDs. The broad kubeconform script skips missing CRD schemas, so it
alone cannot confirm LLMKube or LiteLLM fields. Flux-local's normal entrypoint
does not exercise the new apps until registered. NVIDIA memory capacity,
provider credentials, SSO, MCP clients and a real Memini restore still require
the activation checks above.
