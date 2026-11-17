"""CI-only draft-first publishing. Credentials are provided by GitHub, never printed."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

NAMES = ('GreenTokens-Provider-Setup.exe', 'GreenTokens-Provider-macOS.dmg')
UNSIGNED_PREVIEW_TAG = 'provider-v0.3.1'


def gh(*args, capture=False):
    return subprocess.run(['gh', *args], check=True, text=True, capture_output=capture).stdout


def digest(name):
    data = (Path('out') / name).read_bytes()
    if not data:
        raise RuntimeError('Empty release asset')
    return hashlib.sha256(data).hexdigest(), len(data)


def main():
    tag = os.environ['GITHUB_REF_NAME']
    version = json.loads(Path('apps/provider_app/package.json').read_text())['version']
    if tag != 'provider-v' + version:
        raise RuntimeError('Release tag/version mismatch')
    unsigned_preview = tag == UNSIGNED_PREVIEW_TAG
    if sys.argv[1] == 'prepare':
        publisher = os.environ.get('WINDOWS_PUBLISHER', '').strip()
        if not unsigned_preview and not publisher:
            raise RuntimeError('Verified publisher must be configured')
        hashes = {name: digest(name)[0] for name in NAMES}
        windows_expected = Path('out/Windows-SHA256SUMS.txt').read_text().strip()
        if windows_expected != hashes[NAMES[0]] + '  ' + NAMES[0]:
            raise RuntimeError('Signed installer checksum mismatch')
        Path('out/SHA256SUMS.txt').write_text(''.join(f'{value}  {name}\n' for name, value in hashes.items()))
        notes_file = '.github/provider-preview-release-notes.md' if unsigned_preview else '.github/provider-release-notes.md'
        notes = Path(notes_file).read_text(encoding='utf-8')
        for key, value in {'VERSION': version, 'TAG': tag, 'REPO': os.environ['GITHUB_REPOSITORY'],
                           'SHA': os.environ['GITHUB_SHA'], 'PUBLISHER': publisher}.items():
            notes = notes.replace('@' + key + '@', value)
        Path('notes.md').write_text(notes, encoding='utf-8')
        return
    if sys.argv[1] != 'publish':
        raise RuntimeError('Unknown action')
    # No delete, --clobber, tag rewrite, or replacement of published assets.
    # An existing draft after a failure is preserved for operator review.
    gh('release', 'create', tag, '--verify-tag', '--draft', '--prerelease',
       '--title', f'GreenTokens Provider {version} ({"unsigned preview" if unsigned_preview else "signed"})',
       '--notes-file', 'notes.md')
    names = (*NAMES, 'SHA256SUMS.txt')
    gh('release', 'upload', tag, *(str(Path('out') / name) for name in names))
    release = json.loads(gh('api', f'repos/{os.environ["GITHUB_REPOSITORY"]}/releases/tags/{tag}', capture=True))
    assets = {a['name']: a for a in release['assets']}
    if not release['draft'] or set(assets) != set(names):
        raise RuntimeError('Incomplete draft release')
    for name in names:
        expected, size = digest(name)
        if assets[name]['size'] != size or assets[name].get('digest') != 'sha256:' + expected:
            raise RuntimeError('Uploaded release checksum mismatch; draft remains unpublished')
    gh('release', 'edit', tag, '--draft=false', '--prerelease')


if __name__ == '__main__':
    main()
