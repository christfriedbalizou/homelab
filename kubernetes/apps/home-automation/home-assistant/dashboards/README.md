# Home Assistant dashboards

Editable source for the **Overview** and **Home** storage dashboards. These are
Home Assistant configuration files, not Kubernetes resources; do not add them to
the app Kustomization.

- `overview.json`: clock, daily forecast, live entrance camera, activity, and home shortcuts.
- `home.json`: bedroom heating, entrance activity, household status, detail pop-ups,
  and a Cameras view. Unavailable heating controls and empty temperature graphs
  are replaced with an offline message until the thermostat reconnects.
- `bubble-home-theme.json`: Bubble Home theme with light and dark palettes.
- `apply.py`: backs up existing configurations and saves changes through the API.

Overview lives at `/dashboard-overview/overview` and is the system default dashboard.
Home keeps its existing `/dashboard-home/default_view` and `/dashboard-home/cameras`
URLs. This Home Assistant version's built-in Overview cannot display arbitrary
Lovelace cards, so the custom Overview replaces it as the default sidebar entry.
Individual users' explicit default-dashboard preferences are preserved.

The design uses native Sections, Clock, Weather, History, and Picture Entity cards,
plus [Bubble Card 3.4.1](https://github.com/Clooos/Bubble-Card/releases/tag/v3.4.1).
Bubble is installed manually as a versioned static resource with a SHA-256 check;
it is not managed by HACS. Its resource URL is
`/local/bubble-card/bubble-card-3.4.1.js`. Existing resources, including Advanced
Camera Card, are retained. No automation or device setting changes are needed.

## Apply

Requires Python packages `requests` and `websocket-client`, a Home Assistant admin
token in a local file, and access to the mounted Home Assistant configuration
directory. The existing configuration must include
`frontend.themes: !include_dir_merge_named themes`.

```sh
python3 kubernetes/apps/home-automation/home-assistant/dashboards/apply.py \
  --url https://YOUR-HOME-ASSISTANT-HOST \
  --token-file /path/to/local-token \
  --config-dir /path/to/home-assistant-config
```

The script checks entity IDs, backs up dashboards and resource registration,
installs the pinned asset, reloads themes, saves the two dashboards, and reads them
back for verification. It does not restart Home Assistant or operate devices.
Dashboards remain editable through Home Assistant; export later UI changes into
these source files before reapplying them.

Backups are under `<config>/.configuration-backups/bubble-api-<timestamp>/`.
Restore dashboard JSON through the dashboard raw configuration editor or the
`lovelace/config/save` WebSocket API. The original installation also has a
`bubble-redesign-<timestamp>` backup of the storage files. Do not overwrite live
`.storage` files while Home Assistant is running. To return to the original
built-in Overview, select it as the default dashboard in Home Assistant's dashboard
settings; preserve other frontend settings when restoring `default-panel.json`.

## Verification

Validate JSON and entity references, then inspect desktop and phone layouts in
Home Assistant. Confirm live video is playing, navigation opens the right views,
Heating details and Home system open without migration prompts, and no card errors
appear. Verify both theme modes. Do not change the thermostat setpoint merely to
test dashboard rendering.
