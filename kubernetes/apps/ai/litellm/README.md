# Model catalogue and CPU rollout

Ollama runs one CPU-only instance on either `k8s-6` or `k8s-7`, with a
32 GiB memory limit, one loaded model, one parallel request, and an 8192-token
context. Node RAM is not pooled. The memory request remains 2 GiB; the scheduler
does not reserve the full limit. Measure available memory and CPU inference
latency before increasing concurrency or context.

| Client model ID | Backend |
| --- | --- |
| `translategemma-4b-q4-local` | `translategemma:4b-it-q4_K_M` |
| `qwen3-1.7b-q4-local` | `qwen3:1.7b-q4_K_M`, thinking enabled |
| `qwen3-4b-q4-local` | `qwen3:4b-q4_K_M`, thinking enabled |
| `qwen3-8b-q4-local` | `qwen3:8b-q4_K_M`, thinking enabled |
| `qwen3-14b-q4-local` | `qwen3:14b-q4_K_M`, thinking enabled |
| `qwen3-32b-q4-local` | `qwen3:32b-q4_K_M`, thinking enabled |
| `gpt-6-astra-openai-cloud` | `openai/gpt-6-astra` |
| `gpt-6-sol-openai-cloud` | `openai/gpt-6-sol` |
| `gpt-6-luna-openai-cloud` | `openai/gpt-6-luna` |

The separately auto-registered `qwen3-embedding-0.6b` already identifies its
family, task, and size. Its llmkube deployment is separate from Ollama.
The router retains old chat model IDs as aliases for saved clients. Keep these
until saved settings and restricted key permissions have migrated. There are
no cross-provider fallbacks.

All Qwen3 routes enable thinking through `reasoning_effort: medium` (Ollama
uses an on/off switch for these models). Cloud routes use `low` reasoning;
Luna and Sol no longer advertise Chat Completions tool calling with this setting.
Use the Responses API for cloud tool calls. TranslateGemma remains the default
translation model and has no supported thinking mode. Reasoning is returned
separately from final content so it cannot be inserted into translated documents.
Reasoning also consumes output tokens; clients with small completion budgets
may truncate before producing a final answer and need qualification.

The separate 4B thinking model and Qwen2.5-Coder route are removed. The legacy
`qwen3-local-think` alias resolves to the regular 4B route, which now thinks.
The permission helper maps the retired descriptive thinking ID to that route.
Saved clients using the retired descriptive ID must switch to `qwen3-4b-q4-local`;
Qwen2.5-Coder clients must explicitly select another model. Cached model files
are not deleted by this catalogue change.

## Deployment order

1. Preview and apply the existing virtual keys' model permissions **before**
   deploying the renamed models. The helper keeps old permissions, adds their
   renamed equivalents, and grants the three new Qwen choices to Translator's
   local key and Open WebUI. Memini retains access only to its existing model;
   Translator's cloud key retains access only to Luna. Keys are not rotated,
   and credentials are never printed. The helper's default is read-only.

   In one terminal:

   ```sh
   kubectl port-forward service/litellm 15441:4000 -n ai
   ```

   From the repository root in another terminal:

   ```sh
   python3 scripts/update-litellm-model-access.py
   python3 scripts/update-litellm-model-access.py --apply
   ```

   Stop the port-forward after the helper completes. Independently managed
   clients/keys outside these four known credentials need the same alias-to-name
   permission migration if they have restricted model lists.

2. Commit and push the reviewed manifests, then explicitly reconcile Flux.
   The `ollama-pull-local-models-v5` Job pulls and verifies all six local
   models. Its name changes because Kubernetes Job pod templates are immutable.
   Verify the Job completes before testing new provider choices.
3. Verify LiteLLM lists the new names with each application's own key and run
   small synthetic inference checks. Cloud billing remains an independent
   requirement; this change does not restore upstream credits.
4. Verify Translator has TranslateGemma as the default and selectable Qwen3
   8B, 14B, and 32B providers. Its existing cloud provider remains available for
   explicit selection. Existing provider IDs are preserved; new Qwen IDs are
   stable. Renaming an existing configured provider increments its revision,
   so jobs pinned to its old revision may need an explicit retry with updated
   settings. Do not delete documents or reset the database.

Translator's model list is rendered from
`bootstrap/templates/kubernetes/apps/default/translator/app/secret.sops.yaml.j2`.
The new Qwen providers use the existing local key file, 600-second read and
900-second overall timeouts, and concurrency one. These are deployment settings,
not a claim that larger-model latency or translation quality is qualified.
