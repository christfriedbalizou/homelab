// No cluster access or npm dependencies. Requires Node >=22 and the Docker CLI/daemon.
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const clusterPath = 'kubernetes/apps/storage/cloudnative-pg/cluster/cluster18.yaml';
const databasePath = 'kubernetes/apps/storage/cloudnative-pg/databases/immich.yaml';
const immichPath = 'kubernetes/apps/default/immich/app/helmrelease.yaml';

function exactlyOne(text, pattern, label) {
  const matches = [...text.matchAll(pattern)];
  if (matches.length !== 1) throw new Error(`Expected exactly one ${label}; found ${matches.length}`);
  return matches[0];
}

export function imageReference(text) {
  const match = exactlyOne(text,
    /^  imageName: (ghcr\.io\/cloudnative-pg\/postgresql:(\d+)\.[\w.-]+@sha256:[a-f0-9]{64})\s*$/gm,
    'digest-pinned PostgreSQL image');
  return { image: match[1], major: match[2] };
}

export function controlVersion(text) {
  return exactlyOne(text, /^default_version\s*=\s*'(\d+\.\d+\.\d+)'\s*(?:#.*)?$/gm,
    'vector default_version')[1];
}

export function vectorPin(text, version) {
  // Stay within the vector list item; never match a sibling extension's version.
  const match = exactlyOne(text,
    /(^  - name: vector\r?\n(?:^    [^\r\n]*\r?\n)*?^    version: )(\d+\.\d+\.\d+)(?=\r?$)/gm,
    'vector version pin');
  return { current: match[2], updated: text.slice(0, match.index) + match[1] + version +
    text.slice(match.index + match[0].length) };
}

export function supported(version, range) {
  // Immich currently declares ">=0.5 <1". Fail closed if upstream changes syntax.
  const parts = range.trim().split(/\s+/);
  if (!parts.length) throw new Error('Empty Immich pgvector range');
  const compare = (a, b) => {
    const left = a.split('.').map(Number), right = b.split('.').map(Number);
    for (let i = 0; i < 3; i++) {
      if ((left[i] ?? 0) !== (right[i] ?? 0)) return (left[i] ?? 0) - (right[i] ?? 0);
    }
    return 0;
  };
  const checks = parts.map(part => {
    const match = /^(>=|>|<=|<|=)(\d+(?:\.\d+){0,2})$/.exec(part);
    if (!match) throw new Error(`Unsupported Immich range syntax: ${range}`);
    const comparison = compare(version, match[2]);
    return { '>=': comparison >= 0, '>': comparison > 0, '<=': comparison <= 0,
      '<': comparison < 0, '=': comparison === 0 }[match[1]];
  });
  return checks.every(Boolean);
}

function docker(...args) {
  return execFileSync('docker', args, { encoding: 'utf8', timeout: 600_000,
    stdio: ['ignore', 'pipe', 'inherit'] }).trim();
}

function imageVersion(image, major, platform) {
  const directory = mkdtempSync(join(tmpdir(), 'pgvector-'));
  let container;
  try {
    docker('pull', '--platform', platform, image);
    // The container is never started. No image code, database, or mounts are used.
    container = docker('create', '--platform', platform, '--network', 'none',
      '--entrypoint', '/bin/true', image);
    const destination = join(directory, 'vector.control');
    docker('cp', `${container}:/usr/share/postgresql/${major}/extension/vector.control`, destination);
    return controlVersion(readFileSync(destination, 'utf8'));
  } finally {
    try {
      if (container) docker('rm', '-v', container);
    } finally {
      rmSync(directory, { recursive: true, force: true });
    }
  }
}

async function main() {
  const mode = process.argv[2];
  if (!['--check', '--write'].includes(mode) || process.argv.length !== 3) {
    throw new Error('Usage: node .github/scripts/sync-pgvector.mjs --check|--write');
  }
  const { image, major } = imageReference(readFileSync(clusterPath, 'utf8'));
  const versions = ['linux/amd64', 'linux/arm64'].map(platform => {
    const version = imageVersion(image, major, platform);
    console.log(`${platform}: vector ${version}`);
    return version;
  });
  if (new Set(versions).size !== 1) throw new Error('PostgreSQL image architectures disagree on pgvector');
  const version = versions[0];
  const immich = exactlyOne(readFileSync(immichPath, 'utf8'),
    /repository: ghcr\.io\/immich-app\/immich-server\r?\n\s+tag: (v\d+\.\d+\.\d+)@sha256:[a-f0-9]{64}/g,
    'pinned Immich server release')[1];
  const url = `https://raw.githubusercontent.com/immich-app/immich/${immich}/server/src/constants.ts`;
  const response = await fetch(url, { signal: AbortSignal.timeout(30_000) });
  if (!response.ok) throw new Error(`Cannot check Immich compatibility: HTTP ${response.status}`);
  const range = exactlyOne(await response.text(),
    /^export const VECTOR_VERSION_RANGE = ['"]([^'"\r\n]+)['"];?\r?$/gm,
    'Immich VECTOR_VERSION_RANGE')[1];
  if (!supported(version, range)) throw new Error(`pgvector ${version} is outside Immich ${immich}'s range ${range}`);
  console.log(`Immich ${immich}: pgvector ${version} satisfies ${range}`);
  const original = readFileSync(databasePath, 'utf8');
  const { current, updated } = vectorPin(original, version);
  if (current === version) {
    console.log(`Database pin matches image: ${version}`);
  } else if (mode === '--check') {
    throw new Error(`Database pin ${current} differs from image ${version}; run this script with --write`);
  } else {
    writeFileSync(databasePath, updated);
    console.log(`Updated database pin: ${current} -> ${version}`);
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
