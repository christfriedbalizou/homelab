# PostgreSQL and Immich pgvector updates

Renovate tracks the digest-pinned PostgreSQL 18 image. Its post-upgrade task runs
`node .github/scripts/sync-pgvector.mjs --write` and includes the resulting
Immich Database extension version in the same commit. The task reads
`vector.control` from both Linux image architectures using stopped temporary
containers, without starting PostgreSQL or accessing the cluster.

The script checks the pgvector range declared by the pinned Immich release.
Missing files, unsupported range syntax, unavailable images, and different
versions across architectures fail the check. It never falls back to an
upstream pgvector release number. PostgreSQL major upgrades require a separate
migration and are excluded from automatic proposals.

Run from the repository root with Node >=22 and Docker available:

```sh
node --test .github/scripts/sync-pgvector.test.mjs
node .github/scripts/sync-pgvector.mjs --check
```

For a manual image change, pin its multi-platform digest first, then run the
script with `--write`. Commit the image and database changes together. The CI
job `Pgvector compatibility` checks the same relationship on every PR,
including Immich upgrades. Configure that job as a required branch check in
GitHub if it is not already enforced by repository rules.

The Renovate runner mounts the Docker socket and permits only the exact sync
command as a post-upgrade task. It runs on the existing trusted main-branch
workflow. The PR check has read-only repository permissions and no secrets.

After deployment, check the Database resource's applied status/current
generation and Immich startup logs. CI validates image metadata and the
declared Immich version range; it does not test an upgrade of production data.
The existing Flux database dependency on the PostgreSQL cluster remains in
place. Do not merge the obsolete standalone pgvector release PR (#3267).
