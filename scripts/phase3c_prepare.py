"""Collect candidate wheels and a fixed HF model from official endpoints.

Run only from phase3c_prepare.ps1 in a normal Windows user session. This is
collection plus provenance checking, not installation or model validation.
The small greedy resolver deliberately fails on conflicts: it is not pip's
full dependency solver, so the generated lock requires independent review.
"""
import email.parser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import time
import urllib.parse
import urllib.request
import uuid
import zipfile

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.tags import sys_tags
from pip._vendor.packaging.utils import canonicalize_name, parse_wheel_filename
from pip._vendor.packaging.version import Version, InvalidVersion
from pip._vendor.packaging.specifiers import SpecifierSet

ROOT = Path(__file__).resolve().parent.parent
REVISION = 'a80717a3a48b1b28aa687bca146cb7301feae1b1'
REPO = 'Systran/faster-whisper-base'
MAX_FILE = 1024 * 1024 * 1024


class Blocked(Exception):
    pass


def approved(url):
    p = urllib.parse.urlsplit(url)
    host = (p.hostname or '').lower()
    return (p.scheme == 'https' and p.username is None and p.password is None
            and (host in {'pypi.org', 'files.pythonhosted.org', 'huggingface.co'}
                 or host.endswith('.huggingface.co') or host.endswith('.hf.co')))


class StrictRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not approved(newurl):
            raise Blocked('Redirect host is outside the official allowlist')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(StrictRedirect())


def fetch(url, limit=16 * 1024 * 1024):
    if not approved(url):
        raise Blocked('URL host is outside the official allowlist')
    request = urllib.request.Request(url, headers={'User-Agent': 'CODEX-clipping-phase3c/1'})
    with OPENER.open(request, timeout=25) as response:
        if not approved(response.geturl()):
            raise Blocked('Unexpected final download host')
        data = response.read(limit + 1)
    if len(data) > limit:
        raise Blocked('Metadata exceeds size limit')
    return data


def fetch_json(url):
    value = json.loads(fetch(url))
    if not isinstance(value, dict):
        raise Blocked('Invalid official metadata')
    return value


def download(url, dest):
    if not approved(url):
        raise Blocked('URL host is outside the official allowlist')
    request = urllib.request.Request(url, headers={'User-Agent': 'CODEX-clipping-phase3c/1'})
    h = hashlib.sha256()
    length = 0
    with OPENER.open(request, timeout=25) as response, dest.open('xb') as out:
        if not approved(response.geturl()):
            raise Blocked('Unexpected final download host')
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            length += len(chunk)
            if length > MAX_FILE:
                raise Blocked('File exceeds size limit')
            h.update(chunk)
            out.write(chunk)
    return h.hexdigest()


def safe_name(name):
    return (isinstance(name, str) and name not in ('', '.', '..')
            and PurePosixPath(name).name == name and '\\' not in name and ':' not in name)


def wheel_requirements(path, expected_name, expected_version):
    with zipfile.ZipFile(path) as archive:
        metas = [x for x in archive.infolist() if x.filename.endswith('.dist-info/METADATA')]
        if len(metas) != 1 or metas[0].file_size > 1024 * 1024:
            raise Blocked('Wheel metadata missing or ambiguous')
        info = email.parser.BytesParser().parsebytes(archive.read(metas[0]))
    if canonicalize_name(info.get('Name', '')) != expected_name or info.get('Version') != expected_version:
        raise Blocked('Wheel identity mismatch')
    return info.get_all('Requires-Dist', []), info.get('License-Expression') or info.get('License') or ''


def collect_wheels(directory):
    wheel_dir = directory / 'wheelhouse'
    wheel_dir.mkdir()
    tags = set(sys_tags())
    constraints = {}
    selected = {}
    pending = [Requirement('faster-whisper==1.2.1')]
    # This is intentionally not a backtracking resolver. Conflict => BLOCKED.
    while pending:
        req = pending.pop(0)
        if req.url:
            raise Blocked('Direct dependency URLs are not permitted')
        if req.marker and not req.marker.evaluate({'extra': ''}):
            continue
        name = canonicalize_name(req.name)
        constraints.setdefault(name, []).append(req.specifier)
        if req.extras:
            raise Blocked('Dependency extras require separate resolver review')
        if name in selected:
            if not all(Version(selected[name]['version']) in spec for spec in constraints[name]):
                raise Blocked('Dependency constraints conflict; manual resolution required')
            continue
        metadata = fetch_json('https://pypi.org/pypi/' + urllib.parse.quote(name) + '/json')
        choices = []
        for version, artifacts in metadata.get('releases', {}).items():
            try:
                parsed = Version(version)
            except InvalidVersion:
                continue
            if parsed.is_prerelease or not all(parsed in spec for spec in constraints[name]):
                continue
            for artifact in artifacts:
                filename = artifact.get('filename', '')
                if not safe_name(filename) or not filename.endswith('.whl') or artifact.get('yanked'):
                    continue
                try:
                    wheel_name, wheel_version, _, wheel_tags = parse_wheel_filename(filename)
                    py_req = SpecifierSet(artifact.get('requires_python') or '')
                except Exception:
                    continue
                if (canonicalize_name(wheel_name) == name and wheel_version == parsed
                    and tags.intersection(wheel_tags) and Version('3.12.4') in py_req):
                    choices.append((parsed, filename))
        if not choices:
            raise Blocked('No compatible official wheel for ' + name)
        version, filename = max(choices, key=lambda item: (item[0], item[1]))
        version = str(version)
        release = fetch_json('https://pypi.org/pypi/' + urllib.parse.quote(name) + '/' + urllib.parse.quote(version) + '/json')
        matches = [x for x in release.get('urls', []) if x.get('filename') == filename]
        if len(matches) != 1:
            raise Blocked('Official wheel release metadata ambiguous')
        item = matches[0]
        expected = item.get('digests', {}).get('sha256', '')
        url = item.get('url', '')
        if not re.fullmatch(r'[0-9a-f]{64}', expected) or urllib.parse.urlsplit(url).hostname != 'files.pythonhosted.org':
            raise Blocked('Official wheel URL or SHA-256 missing')
        actual = download(url, wheel_dir / filename)
        if actual != expected:
            raise Blocked('Official wheel hash mismatch for ' + name)
        dependencies, wheel_license = wheel_requirements(wheel_dir / filename, name, version)
        for raw in dependencies:
            pending.append(Requirement(raw))
        info = release.get('info', {})
        license_value = info.get('license_expression') or info.get('license') or wheel_license or 'UNKNOWN'
        selected[name] = {'version': version, 'filename': filename, 'sha256': expected,
                          'metadata_url': 'https://pypi.org/pypi/' + name + '/' + version + '/json',
                          'license': str(license_value)[:2000], 'requires_dist': dependencies}
        print('Verified official wheel:', name, version, flush=True)
    lock = ''.join(f'{name}=={item["version"]} --hash=sha256:{item["sha256"]}\n'
                   for name, item in sorted(selected.items()))
    (directory / 'candidate-requirements.txt').write_text(lock, encoding='utf-8')
    (directory / 'wheel-metadata.json').write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding='utf-8')
    return selected


def git_blob_sha1(path):
    h = hashlib.sha1()
    h.update(('blob ' + str(path.stat().st_size) + '\0').encode('ascii'))
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def collect_model(directory, packages):
    api = 'https://huggingface.co/api/models/' + REPO + '/revision/' + REVISION + '?blobs=true'
    meta = fetch_json(api)
    if meta.get('sha') != REVISION or str(meta.get('id', '')).lower() != REPO.lower():
        raise Blocked('Model repository or revision mismatch')
    siblings = meta.get('siblings')
    if not isinstance(siblings, list) or not siblings:
        raise Blocked('Model file list unavailable')
    model = directory / 'model'
    model.mkdir()
    hashes = {}
    identities = {}
    seen = set()
    for record in siblings:
        name = record.get('rfilename')
        if not safe_name(name) or name in seen or name == 'model-manifest.json':
            raise Blocked('Unexpected model file name')
        seen.add(name)
        url = ('https://huggingface.co/' + REPO + '/resolve/' + REVISION + '/'
               + urllib.parse.quote(name, safe=''))
        dest = model / name
        sha = download(url, dest)
        lfs = record.get('lfs')
        if lfs:
            official = lfs.get('sha256') if isinstance(lfs, dict) else None
            if not official or sha != official:
                raise Blocked('Official LFS model hash mismatch')
            identities[name] = {'type': 'lfs-sha256', 'official': official, 'computed': sha}
        else:
            blob = record.get('blobId')
            computed = git_blob_sha1(dest)
            if not blob or computed != blob:
                raise Blocked('Official Git blob ID mismatch')
            identities[name] = {'type': 'git-blob-sha1', 'official': blob, 'computed': computed}
        hashes[name] = sha
        print('Verified official model file:', name, flush=True)
    if not {'config.json', 'model.bin', 'tokenizer.json'} <= seen:
        raise Blocked('Critical model files absent from official list')
    manifest = {'schema_version': 1, 'repository': REPO, 'revision': REVISION, 'model': 'base',
                'files': hashes, 'packages': {name: value['version'] for name, value in packages.items()}}
    (model / 'model-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    license_value = (meta.get('cardData') or {}).get('license') or 'UNKNOWN'
    return {'revision': REVISION, 'files': hashes, 'official_file_identities': identities,
            'metadata_url': api, 'official_license_metadata': license_value}


def main():
    root = ROOT / 'AI-Video-Workspace' / 'phase3c-r1' / 'runs'
    for part in (root, *root.parents):
        if part.is_symlink() or part.is_junction():
            raise Blocked('Linked workspace paths are not permitted')
    if not root.resolve().is_relative_to(ROOT.resolve()):
        raise Blocked('Workspace path escapes the project')
    root.mkdir(parents=True, exist_ok=True)
    run = root / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    run.mkdir()
    result = {'status': 'BLOCKED', 'wheel_collection': 'NOT_RUN', 'model_collection': 'NOT_RUN',
              'dependency_lock': 'CANDIDATE_REQUIRES_REVIEW', 'installation': 'NOT_RUN',
              'license_review': 'NOT_RUN', 'model_loading': 'NOT_RUN',
              'offline_inference': 'NOT_RUN', 'chinese_asr': 'NOT_RUN'}
    try:
        result['wheel_collection'] = 'IN_PROGRESS'
        packages = collect_wheels(run)
        result['wheel_collection'] = 'PASS_OFFICIAL_FILE_HASHES'
        result['model_collection'] = 'IN_PROGRESS'
        result['model'] = collect_model(run, packages)
        result['model_collection'] = 'PASS_OFFICIAL_FILE_IDS'
        result['status'] = 'FILES_VERIFIED_REVIEW_REQUIRED'
        result['note'] = ('Greedy dependency collection is not a complete solver. Independently review '
                          'all licenses and dependencies; no package has been installed.')
    except Exception as error:
        for stage in ('wheel_collection', 'model_collection'):
            if result[stage] == 'IN_PROGRESS':
                result[stage] = 'BLOCKED'
        # Never log URLs, tokens, proxy details or private local paths.
        result['error_type'] = type(error).__name__
        result['error'] = str(error) if isinstance(error, Blocked) else 'Collection failed; check connection and official source.'
    (run / 'collection-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Run directory:', run, flush=True)
    print('Status:', result['status'], flush=True)
    if result['status'] != 'FILES_VERIFIED_REVIEW_REQUIRED':
        print('Failure:', result.get('error_type'), result.get('error'), flush=True)
        return 1
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print('Status: BLOCKED; initialization failed:', type(error).__name__)
        sys.exit(1)
