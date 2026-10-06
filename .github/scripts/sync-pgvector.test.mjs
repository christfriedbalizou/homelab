import assert from 'node:assert/strict';
import test from 'node:test';
import { controlVersion, imageReference, supported, vectorPin } from './sync-pgvector.mjs';

test('requires an immutable PostgreSQL image and derives its major version', () => {
  const image = `ghcr.io/cloudnative-pg/postgresql:18.6@sha256:${'a'.repeat(64)}`;
  assert.equal(imageReference(`  imageName: ${image}\n`).image, image);
  assert.throws(() => imageReference('  imageName: ghcr.io/cloudnative-pg/postgresql:18.6\n'));
  for (const major of ['18', '19', '20']) {
    const reference = image.replace(':18.', `:${major}.`);
    assert.deepEqual(imageReference(`  imageName: ${reference}\n`), { image: reference, major });
  }
});

test('reads the control file, rejecting missing or ambiguous defaults', () => {
  assert.equal(controlVersion("# vector\ndefault_version = '0.8.6'\n"), '0.8.6');
  assert.throws(() => controlVersion("default_version = 'unknown'\n"));
  assert.throws(() => controlVersion("default_version = '0.8.6'\ndefault_version = '0.8.7'\n"));
});

test('changes only the vector version and preserves line endings', () => {
  for (const newline of ['\n', '\r\n']) {
    const original = ['  - name: cube', '    version: 1.0.0', '  - name: vector',
      '    ensure: present', '    # generated', '    version: 0.8.6',
      '  - name: other', '    version: 2.0.0', ''].join(newline);
    const result = vectorPin(original, '0.8.7');
    assert.equal(result.current, '0.8.6');
    assert.equal(result.updated, original.replace('version: 0.8.6', 'version: 0.8.7'));
  }
  assert.throws(() => vectorPin('  - name: vector\n    ensure: present\n  - name: other\n    version: 1.0.0\n', '0.8.7'));
});

test('checks all range bounds and rejects unsupported range syntax', () => {
  assert.equal(supported('0.8.7', '>=0.5 <1'), true);
  assert.equal(supported('0.4.9', '>=0.5 <1'), false);
  assert.equal(supported('1.0.0', '>=0.5 <1'), false);
  assert.equal(supported('0.5.0', '>=0.5 <1'), true);
  assert.throws(() => supported('0.8.7', '^0.8'));
  assert.throws(() => supported('0.1.0', '>=0.5 || <1'));
});
