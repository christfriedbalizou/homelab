# Staged local AI stack

Prepared from [Diaoul/home-ops at 5e337d3](https://github.com/Diaoul/home-ops/tree/5e337d342fd403850146a0817ddffec228ec855e/kubernetes/apps/ai).
The [onedr0p Home Assistant MCP deployment](https://github.com/onedr0p/home-ops/blob/main/kubernetes/apps/default/home-assistant/mcp/helmrelease.yaml)
was also checked for its internal Home Assistant endpoint and container settings.

**First activation stage is registered in Git.** The AI namespace now includes
LLMKube, LiteLLM and its operator, Home Assistant MCP, Context7, and the Ollama
local-model overlay. NVIDIA scheduling is configured for four shared allocations.
Their required Secrets are SOPS-encrypted. LiteLLM SSO is restricted to the
configured administrator with two-factor authentication; its dashboard is admin-only.
These changes have not been pushed or applied to the live cluster.

Memini and the Open WebUI LiteLLM overlay remain unregistered until separate
scoped LiteLLM client keys have been issued. Existing Open WebUI stays on its
current configuration during this first stage.

Storage placement: Lordcommander holds replaceable Ollama model downloads.
Ollama configuration and Open WebUI data stay on Jericho. The embedding cache
is disposable OpenEBS storage. Memini's SQLite database uses OpenEBS with hourly
snapshots on Jericho/APPS; never put memories or backups on Lordcommander.
Before enabling Memini, create `/volume1/apps/ai/memini-backups` on the APPS
NFS server, owned by UID/GID 1000, and include it in APPS backups. A direct NFS
mount does not create this server directory. The OpenEBS PVC is provisioned
automatically. Local memory writes since the last successful snapshot can be
lost if the OpenEBS node is lost.

The remaining sections describe the full setup and activation sequence; the
first-stage registrations, SSO client, and provider credentials are now prepared.

## Layout and connections

| Path | Purpose |
| --- | --- |
| `llmkube/` | Operator and Qwen3-Embedding-0.6B served by CUDA llama.cpp on the shared NVIDIA GPU. Downloaded model cache uses OpenEBS hostpath. |
| `litellm-operator/` | Manages proxy, model and MCP resources; auto-registers ready LLMKube models. |
| `../storage/cloudnative-pg/databases/` | Declares a retained CloudNativePG DatabaseRole and Database in storage, with an encrypted role password Secret. |
| `litellm/app/` | Internal gateway to local Ollama models, OpenAI models and embeddings; uses shared Dragonfly. |
| `litellm/app/models/` | One model catalog containing all local and OpenAI model declarations, following the upstream layout. |
| `ollama/local/`, `ollama/models/` | Optional NVIDIA memory settings and a one-time Job that downloads the selected chat models through the existing Ollama server. |
| `ha-mcp/` | Runs Home Assistant MCP inside the cluster and registers it with LiteLLM. |
| `context7-mcp/` | Optional hosted documentation lookup through LiteLLM; separate from model inference and disabled until registered. |
| `memini/` | Persistent memory, using local Qwen embeddings directly and local Qwen3 4B through LiteLLM. |
| `open-webui/litellm/` | Optional overlay switching existing Open WebUI to LiteLLM for chat and embeddings. |
| `../../components/ai-nvidia-sharing/` | Optional NVIDIA ConfigMap patch allowing four shared GPU scheduling allocations. |

```text
Open WebUI -> LiteLLM -> Ollama (one local chat model loaded at a time)
                     -> OpenAI API (explicitly selected cloud aliases)
                     -> LLMKube embedding service
MCP clients -> LiteLLM -> ha-mcp -> Home Assistant
                     -> Context7 documentation API (optional tool)
Memory clients -> Memini -> embedding service
                        -> LiteLLM -> local Qwen3 4B
```

All local chat aliases point to `ollama.ai.svc.cluster.local:11434`. Open WebUI
defaults to `qwen3-local`, and Memini's processing model is also `qwen3-local`.
There are no automatic fallbacks. Anthropic and OpenCode Go have been removed.
OpenAI is the only configured external inference provider. Local and OpenAI
models are registered together through LiteLLM's model catalog, and OpenAI
requests require explicit model selection. Context7 is an optional external documentation
tool, with its own registration and credential.

Selecting an enabled `openai-...-cloud` alias sends that conversation and any
attached context/tool results to OpenAI. Local aliases keep inference in the
cluster. Image/model downloads still use external registries; this is a routing
configuration, not a cluster-wide egress firewall. No Intel GPU is used.

LLMKube owns the generated embedding Service `qwen3-embedding-0-6b`. Its direct
model alias is `qwen3-embedding`; LiteLLM auto-registers it as
`qwen3-embedding-0.6b`. These different names are intentional.

## Models selected for the RTX 3050 6 GB

The repository documents a 6 GB NVIDIA GPU on `k8s-3` with 16 GB system RAM.
Selection assumes the full 6 GB is available for AI, as confirmed by the owner;
Frigate and Jellyfin retain their existing scheduling reservations.

| LiteLLM alias | Ollama model | Approximate model download | Use |
| --- | --- | --- | --- |
| `qwen3-local` | `qwen3:4b-q4_K_M` | 2.6 GB | Default chat, tool use and Memini processing; thinking disabled. |
| `qwen3-local-think` | Same 4B model | Same stored weights | Optional reasoning mode; slower and shares the same context budget. |
| `qwen3-local-fast` | `qwen3:1.7b-q4_K_M` | 1.4 GB | Faster, simpler chat when lower answer quality is acceptable. |
| `qwen2.5-coder-local` | `qwen2.5-coder:3b-instruct-q4_K_M` | 1.9 GB | Code explanation and small edits; agent tool support is not advertised. |
| `qwen3-embedding-0.6b` | Separate CUDA llama.cpp service | Q8_0 weights, about 0.7 GB | Document and memory embeddings, 1024 dimensions. |

The explicit quantization tags avoid accidentally selecting larger weights.
Sizes come from the [4B](https://ollama.com/library/qwen3:4b-q4_K_M),
[1.7B](https://ollama.com/library/qwen3:1.7b-q4_K_M), and
[coder](https://ollama.com/library/qwen2.5-coder:3b-instruct-q4_K_M) model pages.
Download sizes are not total VRAM consumption: context caches and runtime
buffers also need memory. The 4B model plus embeddings is the intended fit,
subject to an actual GPU test. Larger 7-8B models leave insufficient headroom
for this simultaneous embedding workload; CPU offload is not the baseline.

The registered Ollama overlay uses an 8192-token context, Flash Attention, a
`q8_0` KV cache, one loaded chat model and one parallel request. Unused chat
weights unload after 60 seconds. These settings follow the
[Ollama memory guidance](https://docs.ollama.com/faq). Selecting another chat
model swaps weights; it does not reserve another GPU share. The embedding
service stays separate. Start with short prompts and confirm model loading,
latency and memory use before increasing context or concurrency. Memini's
JSON extraction/consolidation quality must be tested with representative
memories; a 4B model is not equivalent to a large hosted model.

## OpenAI models

The GPT-6 and local model manifests all live in
[`litellm/app/models/`](litellm/app/models/) and are included by its
`kustomization.yaml`, following the upstream structure. The normal
[`litellm/ks.yaml`](litellm/ks.yaml) registers the entire catalog. OpenAI's API
key is stored in the shared `cluster-litellm-secrets` Secret, alongside the
other LiteLLM credentials. There is no provider-specific folder or Flux
registration. Models will appear after LiteLLM activation and client-key grants.

| Alias | API model | Use |
| --- | --- | --- |
| `openai-gpt-6-luna-cloud` | `gpt-6-luna` | Lower-cost everyday external requests. |
| `openai-gpt-6-sol-cloud` | `gpt-6-sol` | More demanding coding and general tasks. |
| `openai-gpt-6-astra-cloud` | `gpt-6-astra` | Complex reasoning/chat; tool calling requires the Responses API. |

The [OpenAI model catalog](https://developers.openai.com/api/docs/models)
documents these choices. All three declarations use `https://api.openai.com/v1`,
disable background health probes and request `store: false`. Sol/Luna default
to at most 4096 output tokens. Astra defaults to low reasoning and an 8192-token
completion budget including reasoning and visible output. `store: false` does
not mean no provider retention;
OpenAI's [data controls](https://developers.openai.com/api/docs/guides/your-data)
still apply. Sol/Luna's Chat Completions interface uses `reasoning_effort: none` to
retain tool calling, as required by the
[Sol](https://developers.openai.com/api/docs/models/gpt-6-sol) and
[Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) documentation.
Confirm model access with your API project when activating.

[Astra](https://developers.openai.com/api/docs/guides/reasoning) does not accept
`reasoning_effort: none`, and its Chat Completions endpoint cannot call tools.
Its current declaration therefore advertises reasoning and vision, but not
function calling. Use Sol/Luna for tool use through the current Chat Completions
integration; Astra tool use needs a client/integration using Responses.

Use your OpenAI Platform API key, not a ChatGPT browser session or password.
API requests use separate API billing. Add the key only to the ignored local
bootstrap configuration, then render/encrypt it using the template below.
Memini's key must remain restricted to `qwen3-local`; grant the OpenAI aliases
only to clients/users that should be able to select them. There is no automatic
local-to-OpenAI fallback, including on context overflow or local failures.

## Optional Context7 documentation tool

[Context7](https://github.com/upstash/context7) retrieves current library
documentation and code examples for an assistant. It is not a replacement
chat model and does not require a local GPU. A local model can use the returned
documentation while doing its own inference in the cluster.

The staged integration calls the hosted `https://mcp.context7.com/mcp` endpoint.
When a client invokes it, library names and search queries supplied as tool
arguments leave the cluster; sensitive text included in a query leaves too.
Restoring these manifests makes the tool available for later activation, not
enabled now. To avoid all external tool lookups, leave it unregistered.

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

   This component is now registered for the first activation stage. Idle video workloads can still reserve
   scheduling shares. Four shares still share the same 6 GB
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
5. Prepare the OpenAI API key, the Home Assistant token, LiteLLM
   database/master/OIDC credentials and Memini API key as described below.
6. The LiteLLM Authelia client is now registered under
   `identity_providers.oidc.clients`. Its `litellm_admin` authorization policy
   denies everyone except `user:${LITELLM_ADMIN_ID}`, who must use two-factor
   authentication. The client configuration is:

   ```yaml
   - client_id: litellm
     client_name: LiteLLM
     client_secret: "${LITELLM_OAUTH_CLIENT_SECRET_PBKDF2}"
     public: false
     authorization_policy: litellm_admin
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

   The **cluster-secrets bootstrap template** now includes
   `LITELLM_OAUTH_CLIENT_SECRET_PBKDF2` when `ai_litellm_secrets_enabled` is true,
   using `{{ pbkdf2(litellm_oauth_client_secret) }}` like the other OIDC clients.
   The clear client secret is only in the encrypted
   LiteLLM app Secret. `litellm_admin_id` must match the intended Authelia user
   identity returned to LiteLLM. Keep API access token-based: do not attach
   an interactive ext-auth redirect to LiteLLM's API/MCP endpoints.

Internal hostnames are `litellm.${SECRET_DOMAIN}`, `memini.${SECRET_DOMAIN}`
(admin UI) and `memini-api.${SECRET_DOMAIN}` (authenticated API/MCP). Ensure
LAN/VPN DNS resolves them to the internal Envoy Gateway. Open WebUI retains
`ai.${SECRET_DOMAIN}` and its current Authelia family/admin role mapping.

## Secrets: templates only until credentials are available

### Collect the remaining credentials

Keep all inputs in the ignored `bootstrap/vars/config.yaml`; do not paste
credentials into chat or commit that file. Locally generated inputs are
`litellm_postgres_password`, `litellm_master_key`,
`litellm_oauth_client_secret`, and `memini_api_key`. Preserve existing values
on subsequent runs rather than rotating them during setup.

1. **OpenAI:** sign in to the [API platform](https://platform.openai.com/api-keys),
   select the intended project, and create a secret API key named
   `homelab-litellm`. Save it as `litellm_openai_api_key`. See the
   [official quickstart](https://developers.openai.com/api/docs/quickstart).
2. **Home Assistant:** open your profile, select **Security**, and create a
   **Long-lived access token** named `homelab-ha-mcp`. Save it as
   `ha_mcp_homeassistant_token`. See
   [Home Assistant authentication](https://www.home-assistant.io/docs/authentication/).
3. **LiteLLM administrator:** supply `litellm_admin_id` matching the identity
   returned by Authelia to LiteLLM. This is an account identifier, not a newly
   generated password; verify the SSO identity when activating.
4. **Context7 (optional):** sign in at [Context7](https://context7.com/dashboard),
   create an API key, and save it as `context7_api_key`. Leave its secret flag
   disabled if this integration is not wanted.
5. After LiteLLM is running, issue separate virtual keys for Open WebUI and
   Memini and save them as `open_webui_litellm_api_key` and
   `memini_litellm_api_key`. These must be registered with LiteLLM, not merely
   generated as random strings. Use the model grants described below.

Only enable each template flag after all its inputs are present. Complete
the GPU, NFS backup directory and SSO prerequisites before activation;
credential generation alone does not make the stack ready to deploy.

App credential templates live in `bootstrap/templates/kubernetes/apps/ai/`.
The LiteLLM database password template lives at
`bootstrap/templates/kubernetes/apps/storage/cloudnative-pg/databases/litellm.sops.yaml.j2`.
Both LiteLLM templates share `ai_litellm_secrets_enabled`; each other integration
has its own opt-in flag. Flags default to false, so normal `just configure` does not
require new credentials. Disabled templates render no Secret documents.
These flags render secrets; they do **not** deploy apps.

Set the relevant flag and inputs in the ignored `bootstrap/vars/config.yaml`:

| Flag | Inputs | Destination Secret |
| --- | --- | --- |
| `ai_litellm_secrets_enabled` | `litellm_postgres_password`, `litellm_master_key`, `litellm_oauth_client_secret`, `litellm_admin_id`, `litellm_openai_api_key` | `cluster-litellm-secrets` in `litellm/app/secret.sops.yaml` (ai) and `litellm-db` in `../storage/cloudnative-pg/databases/litellm.sops.yaml` (storage) |
| `ai_context7_secrets_enabled` | `context7_api_key` | `cluster-context7-mcp-secrets` |
| `ai_ha_mcp_secrets_enabled` | `ha_mcp_homeassistant_token` | `cluster-ha-mcp-secrets` |
| `ai_memini_secrets_enabled` | `memini_api_key`, `memini_litellm_api_key` | `cluster-memini-secrets` |
| `ai_open_webui_litellm_secrets_enabled` | `open_webui_litellm_api_key` | `cluster-open-webui-litellm-secrets` in `open-webui/litellm/secret.sops.yaml` |

Use fresh random credentials on the personal laptop. LiteLLM master/virtual
keys use the `sk-` prefix. Use a URL-safe database password. Supply the OpenAI
API key with the other LiteLLM inputs before activating the staged catalog.
The role password Secret is deployed to `storage` alongside `postgres18`.
The connection/API/OIDC Secret stays in `ai`; both templates use the same
`litellm_postgres_password` input. LiteLLM waits for the database phase, which
checks both resources for `status.applied: true` at their current generation.
The `cloudnative-pg-databases` Flux Kustomization and its resources live in
`storage`; LiteLLM in `ai` depends on it.
No superuser credential is passed to an AI bootstrap Job.

Run `mise exec -- just configure` using the existing Age key, review the diff,
and verify every new rendered Secret is SOPS-encrypted. Then uncomment
`- ./secret.sops.yaml` in that app's `kustomization.yaml`. No missing Secret
files are referenced in the builds.

Activate LiteLLM first to issue **separate scoped virtual keys** for Open WebUI
and Memini. Open WebUI needs its chosen chat models and
`qwen3-embedding-0.6b`; Memini's LLM key only needs `qwen3-local`.
Then enable the corresponding client secret flags and run `just configure`
again. Do not distribute the LiteLLM master key to clients.

CloudNativePG manages LiteLLM's role and database; there is no initialization
Job. Both resources use explicit `retain` reclaim policies. The role password
Secret carries `cnpg.io/reload: "true"` so password updates are observed.
For rotation, regenerate both Secrets from the same password input, apply the
storage Secret first, confirm the role has applied its new Secret resource
version, then update the app Secret and roll the proxy. A rotation is not atomic
across namespaces; generation checks alone cannot prove a password-only change
has been applied. Application schema migrations remain LiteLLM's responsibility.
This feature adopts the new approach only for LiteLLM. Existing Open WebUI
postgres-init and database provisioning in other namespaces are unchanged.

## Activation order

Register the new entries in `kubernetes/apps/ai/kustomization.yaml` only after
the relevant prerequisites and encrypted secrets are ready:

1. **Replace** `./ollama/ks.yaml` with `./ollama/ks-local.yaml`; never include
   both. This applies the memory settings and registers `ollama-models`, which
   waits for Ollama and downloads the three explicit model tags. Allow at least
   10 GB free in its existing model store (MEDIA NFS); existing weights are not
   deleted. Pulls do not load all three models into GPU memory. The completed
   Job is retained for Flux health; rerun it after model-store loss, or change
   its versioned name when intentionally refreshing tags. Model tags can change
   upstream; record the returned model IDs when activating.
2. `./llmkube/ks.yaml` and `./litellm-operator/ks.yaml`. The first file contains
   both the operator and the separate `llmkube-models` Flux Kustomization.
3. `./litellm/ks.yaml`. The central `cloudnative-pg-databases` Kustomization
   waits for `cloudnative-pg-cluster` in `storage`; the proxy waits for the
   applied role/database through that dependency, its operator,
   `ollama-models` and shared
   `dragonfly-cluster`. This also registers the local and OpenAI model catalog.
   Prepare the shared LiteLLM Secret, including `OPENAI_API_KEY`, first. Grant
   cloud aliases explicitly to the desired client keys; Memini remains local-only.
4. `./ha-mcp/ks.yaml` when its Home Assistant token is ready.
5. `./memini/ks.yaml` after its local-only client key, storage and embeddings
   are ready.
6. **Replace** `./open-webui/ks.yaml` with `./open-webui/ks-litellm.yaml`.
   Never include both: they name the same Flux Kustomization.
7. Optionally register `./context7-mcp/ks.yaml` after rendering/encrypting its
   separate key and uncommenting its Secret resource. Grant Context7 tool
   access only to the chosen MCP clients. This permits hosted documentation
   queries independently of whether a local or OpenAI model is selected.

After the activation commit is merged, use the repository webhook or explicit
Flux reconciliation. Check operator/HelmRelease readiness, embedding output
(1024 dimensions), all local aliases, and the Home Assistant MCP tools.
Confirm Ollama reports GPU inference and healthy memory use with chat plus
embeddings running; test OpenAI separately only after granting its client key.
Use LiteLLM request/provider records to verify Memini stays on local inference.
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

First-stage activation checks passed on 2026-09-29: all namespace and
first-stage app Kustomize builds, the repository kubeconform sweep, SOPS
decryption/integrity checks, matching LiteLLM/Authelia client credentials, and
the administrator-only authorization policy structure. No live checks were run.


Preparation checks passed on 2026-09-28: unchanged active AI build and Flux
entrypoint, all namespace Kustomize builds, the pinned Helm charts and both overlays,
custom resources against the installed chart CRDs, and core/Flux schemas.
All five disabled templates were checked with makejinja 2.9.1 and produce no
output files. Synthetic SQLite tests verified WAL recovery, repeated snapshots,
retention, and preserving previous backups when the source is unavailable.

No live Kubernetes credentials are needed:

```sh
mise exec -- just --list
mise exec -- bash template/resources/kubeconform.sh kubernetes
for app in litellm-operator llmkube litellm ha-mcp context7-mcp memini; do
  mise exec -- kustomize build "kubernetes/apps/ai/$app/app" --load-restrictor LoadRestrictionsNone >/dev/null
done
mise exec -- kustomize build kubernetes/apps/ai/llmkube/models >/dev/null
mise exec -- kustomize build kubernetes/apps/storage/cloudnative-pg/databases >/dev/null
mise exec -- kustomize build kubernetes/apps/ai/litellm/app/models >/dev/null
mise exec -- kustomize build kubernetes/apps/ai/ollama/local --load-restrictor LoadRestrictionsNone >/dev/null
mise exec -- kustomize build kubernetes/apps/ai/ollama/models >/dev/null
mise exec -- kustomize build kubernetes/apps/ai/open-webui/litellm --load-restrictor LoadRestrictionsNone >/dev/null
```

Also render the pinned Helm charts and validate custom resources against those
charts' CRDs. The broad kubeconform script skips missing CRD schemas, so it
alone cannot confirm LLMKube or LiteLLM fields. Flux-local's normal entrypoint
does not exercise the new apps until registered. NVIDIA memory capacity,
provider credentials, SSO, MCP clients and a real Memini restore still require
the activation checks above.
