# Collabora for Nextcloud

Collabora CODE provides the free, self-hosted editing server for Nextcloud Office.
It uses the shared app-template chart in `default`. Documents remain in
Nextcloud's existing storage; Collabora's local cache and worker jails are
ephemeral. The admin console is disabled and no additional credentials are needed.

Connections:

- Browser → `https://collabora.${SECRET_DOMAIN}` through Envoy and Authelia.
- Nextcloud → `http://collabora.default.svc.cluster.local:9980` for discovery and
  server-side requests, without an interactive authentication redirect.
- Collabora → `http://nextcloud.default.svc.cluster.local:8080` for WOPI document
  access. This is the only allowed WOPI host. Nextcloud validates document access
  tokens and restricts WOPI requests to `${K8S_CLUSTER_CIDR}`.

The browser frame policy explicitly permits `https://nextcloud.${SECRET_DOMAIN}`.
The `admin` and `family` groups can access the editor using their Authelia session.
An expired Authelia session may require opening the Collabora URL in a separate
tab to sign in again, then reopening the document. Anonymous public-share editing
is intentionally unavailable with this authentication policy.

Nextcloud's `before-starting` hook installs `richdocuments` if absent, enables it,
disables either built-in CODE app if present, and sets the three connection URLs
and WOPI allowlist. It runs as Nextcloud's configured non-root user. Initial
installation requires access to the Nextcloud app store; subsequent starts reuse
the installed app. The hook does not upgrade an already installed Office app.

The image runs as UID/GID 1001. Its document worker isolation requires CHOWN,
FOWNER and SYS_CHROOT file capabilities, privilege escalation, and a writable
container filesystem. Other capabilities are dropped and the pod uses the
RuntimeDefault seccomp profile. One replica avoids routing editing sessions
between independent workers.

After committing and pushing these manifests, reconcile the `home-kubernetes`
GitRepository in `flux-system` (or trigger its webhook). The Nextcloud Flux and
Helm dependencies ensure Collabora is ready before the Nextcloud rollout.
Check the `collabora` and `nextcloud` HelmReleases in `default`, then sign into
Nextcloud and open a DOCX, XLSX, or PPTX file. Edit, save, close and reopen the file
to verify persistence. Check Administration settings → Office if discovery or
the connection fails; its server URL should remain the internal Service URL.

References:

- [Nextcloud Office integration settings](https://github.com/nextcloud/richdocuments/blob/main/docs/app_settings.md)
- [Collabora CODE](https://www.collaboraonline.com/code/)
