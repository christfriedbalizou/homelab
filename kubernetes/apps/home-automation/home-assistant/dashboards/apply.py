#!/usr/bin/env python3
"""Back up and apply these storage dashboards through Home Assistant's API."""

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import urllib.parse

import requests
import websocket


SOURCE = Path(__file__).resolve().parent
ASSET_URL = 'https://raw.githubusercontent.com/Clooos/Bubble-Card/v3.4.1/dist/bubble-card.js'
ASSET_SHA256 = 'b96ef3c279a574c1cbd66b23c7efd6bfb0c4817bf094c1c37f4426e403080cfb'
RESOURCE_URL = '/local/bubble-card/bubble-card-3.4.1.js'


def entity_ids(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ('entity', 'camera_image') and isinstance(item, str):
                yield item
            else:
                yield from entity_ids(item)
    elif isinstance(value, list):
        for item in value:
            yield from entity_ids(item)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True, help='Home Assistant base URL')
    parser.add_argument('--token-file', type=Path, required=True)
    parser.add_argument('--config-dir', type=Path, required=True,
                        help='Mounted Home Assistant configuration directory')
    args = parser.parse_args()
    token = args.token_file.read_text().strip()
    if not token:
        raise SystemExit('Token file is empty.')
    base = args.url.rstrip('/')
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme not in ('http', 'https'):
        raise SystemExit('Expected an http or https URL.')
    ws_url = urllib.parse.urlunsplit((
        'wss' if parsed.scheme == 'https' else 'ws', parsed.netloc,
        parsed.path + '/api/websocket', '', ''))
    ws = websocket.create_connection(ws_url, timeout=30, suppress_origin=True)
    assert json.loads(ws.recv())['type'] == 'auth_required'
    ws.send(json.dumps({'type': 'auth', 'access_token': token}))
    if json.loads(ws.recv())['type'] != 'auth_ok':
        raise SystemExit('Home Assistant authentication failed.')
    sequence = 0

    def call(kind, **kwargs):
        nonlocal sequence
        sequence += 1
        ws.send(json.dumps({'id': sequence, 'type': kind, **kwargs}))
        while True:
            response = json.loads(ws.recv())
            if response.get('id') == sequence:
                if not response.get('success'):
                    raise RuntimeError(f'{kind}: {response.get("error", {}).get("code", "failed")}')
                return response.get('result')

    assert call('auth/current_user')['is_admin'], 'Administrator token required.'
    dashboards = {'dashboard-overview': json.loads((SOURCE / 'overview.json').read_text()),
                  'dashboard-home': json.loads((SOURCE / 'home.json').read_text())}
    states = {item['entity_id']: item for item in call('get_states')}
    missing = set(entity_ids(list(dashboards.values()))) - states.keys()
    if missing:
        raise SystemExit('Missing entities: ' + ', '.join(sorted(missing)))
    listed = call('lovelace/dashboards/list')
    home = next((d for d in listed if d['url_path'] == 'dashboard-home'), None)
    assert home and home['mode'] == 'storage', 'Expected existing Home storage dashboard.'
    assert call('lovelace/info')['resource_mode'] == 'storage', 'Expected storage resources.'
    overview = next((d for d in listed if d['url_path'] == 'dashboard-overview'), None)
    if overview:
        assert overview['mode'] == 'storage', 'Expected Overview storage dashboard.'
    else:
        call('lovelace/dashboards/create', url_path='dashboard-overview',
             title='Overview', icon='mdi:view-dashboard-outline',
             require_admin=False, show_in_sidebar=True)
    before = {}
    for path in dashboards:
        try:
            before[path] = call('lovelace/config', url_path=path)
        except RuntimeError as exc:
            if path == 'dashboard-overview' and str(exc).endswith('config_not_found'):
                before[path] = None
            else:
                raise
    resources = call('lovelace/resources')
    backup = args.config_dir / '.configuration-backups' / (
        'bubble-api-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    backup.mkdir(parents=True, mode=0o700)
    for path, data in before.items():
        (backup / f'{path or "overview"}.json').write_text(json.dumps(data, indent=2) + '\n')
    (backup / 'resources.json').write_text(json.dumps(resources, indent=2) + '\n')
    previous_default = call('frontend/get_system_data', key='core')
    (backup / 'default-panel.json').write_text(json.dumps(previous_default, indent=2) + '\n')
    asset = requests.get(ASSET_URL, timeout=30)
    asset.raise_for_status()
    assert hashlib.sha256(asset.content).hexdigest() == ASSET_SHA256, 'Asset checksum mismatch.'
    asset_path = args.config_dir / 'www' / 'bubble-card' / 'bubble-card-3.4.1.js'
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    if asset_path.exists():
        assert asset_path.read_bytes() == asset.content, 'Existing asset differs.'
    else:
        asset_path.write_bytes(asset.content)
    theme = args.config_dir / 'themes' / 'bubble-home.yaml'
    theme.parent.mkdir(exist_ok=True)
    if theme.exists():
        (backup / 'bubble-home.yaml').write_bytes(theme.read_bytes())
    theme.write_text('---\n' + (SOURCE / 'bubble-home-theme.json').read_text())
    response = requests.post(base + '/api/services/frontend/reload_themes',
                             headers={'Authorization': 'Bearer ' + token}, json={}, timeout=30)
    response.raise_for_status()
    assert 'Bubble Home' in call('frontend/get_themes')['themes'], 'Theme was not loaded.'
    bubble = [r for r in resources if 'bubble-card' in r['url']]
    if bubble:
        assert len(bubble) == 1 and bubble[0]['url'] == RESOURCE_URL, (
            'Another Bubble Card resource exists; review before adding a duplicate.')
    else:
        call('lovelace/resources/create', res_type='module', url=RESOURCE_URL)
    saved = []
    try:
        for path, config in dashboards.items():
            call('lovelace/config/save', url_path=path, config=config)
            saved.append(path)
            assert call('lovelace/config', url_path=path) == config, 'Saved config differs.'
        call('frontend/set_system_data', key='core',
             value={**(previous_default.get('value') or {}), 'default_panel': 'dashboard-overview'})
    except Exception:
        for path in reversed(saved):
            if before[path] is None:
                call('lovelace/config/delete', url_path=path)
            else:
                call('lovelace/config/save', url_path=path, config=before[path])
        raise
    ws.close()
    print(f'Applied and verified Overview and Home. Backup: {backup}')


if __name__ == '__main__':
    main()
