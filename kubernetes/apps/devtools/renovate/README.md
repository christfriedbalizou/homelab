# Renovate and Forgejo

Renovate runs daily against the Forgejo API and discovers repositories the
configured account can access. Before enabling the Flux Kustomization, create a
dedicated `renovate` account in Forgejo, set its full name and email, and create
a personal access token with `repo` read/write, `user` read, `issue` read/write,
and `organization` read permissions.

Set that token as `renovate_forgejo_token` in the local
`bootstrap/vars/config.yaml`, then run `just configure` to render and encrypt
`app/secret.sops.yaml`. The checked-in encrypted secret currently contains an
empty token, so the bot cannot authenticate until this step is complete. Keep
the token out of Git and rotate it by updating the local variable and rerunning
`just configure`.
