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


def draft_for_tag(repo, tag, title):
    # GitHub's /releases/tags/{tag} endpoint does not resolve unpublished drafts.
    # The authenticated releases list includes them, even when their URL is untagged-*.
    releases = json.loads(gh('api', f'repos/{repo}/releases?per_page=100', capture=True))
    matches = [release for release in releases
               if release.get('tag_name') == tag or
               (release.get('draft') and release.get('name') == title)]
    if len(matches) > 1:
        raise RuntimeError('Multiple releases match this tag; review them manually')
    if matches and not matches[0]['draft']:
        raise RuntimeError('Release is already published; refusing to replace assets')
    return matches[0] if matches else None


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
    # Retry safely after an interrupted upload. Never replace published assets.
    repo = os.environ['GITHUB_REPOSITORY']
    title = f'GreenTokens Provider {version} ({"unsigned preview" if unsigned_preview else "signed"})'
    release = draft_for_tag(repo, tag, title)
    if release is None:
        gh('release', 'create', tag, '--verify-tag', '--draft', '--prerelease',
           '--title', title, '--notes-file', 'notes.md')
        release = draft_for_tag(repo, tag, title)
        if release is None:
            raise RuntimeError('Created draft release was not found')
    names = (*NAMES, 'SHA256SUMS.txt')
    existing = {asset['name'] for asset in release['assets']}
    missing = [name for name in names if name not in existing]
    if missing:
        gh('release', 'upload', tag, *(str(Path('out') / name) for name in missing))
        release = draft_for_tag(repo, tag, title)
        if release is None:
            raise RuntimeError('Draft release disappeared after upload')
    assets = {a['name']: a for a in release['assets']}
    if not release['draft'] or set(assets) != set(names):
        raise RuntimeError('Incomplete draft release')
    for name in names:
        expected, size = digest(name)
        if assets[name]['size'] != size or assets[name].get('digest') != 'sha256:' + expected:
            raise RuntimeError('Uploaded release checksum mismatch; draft remains unpublished')
    published = json.loads(gh('api', '-X', 'PATCH', f'repos/{repo}/releases/{release["id"]}',
                              '-F', 'draft=false', '-F', 'prerelease=true', capture=True))
    if published.get('draft') or published.get('tag_name') != tag:
        raise RuntimeError('Release publication was not confirmed')


if __name__ == '__main__':
    main()
