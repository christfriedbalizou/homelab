# Memini memory filter

`memini_memory.py` is the unmodified Open WebUI filter from Memini v0.7.32:
https://github.com/eleboucher/memini/blob/v0.7.32/integrations/openwebui/filter/memini_memory.py

SHA-256: `139b255f8d06c107e9395384ff8aea3f813c633e02eb07519e28ba2a661e1f9e`.

Installed in Open WebUI as `memini_memory`, active and global. Function code
and valves are persisted in Open WebUI's database; this directory preserves
the installation source and is not automatically imported by Helm.

For recovery, import this file through Admin Panel → Functions, then set:

- `base_url`: `http://memini.ai.svc.cluster.local:8080`
- `namespace`: `openwebui`
- `scope_by_user`: `true`
- `recall`: `true`
- `capture`: `true`
- `fallback_on_error`: `true`

Enable the function and its global toggle. The API key comes from the pod's
`MEMINI_API_KEY` Secret reference, never from function code or valves.
Only new completed conversations are captured; existing chats are not imported.
Each user's namespace is `openwebui-<user-id>`.

Chat requests use LiteLLM. Memini independently uses LiteLLM for consolidation;
LiteLLM does not send its other clients' conversations to Memini.
