#!/usr/bin/env python3
"""Build a deterministic archive of the fixed Perspective code snapshot."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parent
NAME = 'CF_LIBS_Perspective_CodeS1_v1.0.0'
EXCLUDE = {'.git', '__pycache__', '.pytest_cache', 'dist', 'diagnostic_figures'}

def release_paths():
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and
                  not EXCLUDE.intersection(p.relative_to(ROOT).parts) and
                  p.suffix != '.pyc')

def main():
    manifest = json.loads((ROOT / 'verification/release_manifest.json').read_text())
    files = release_paths()
    actual = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in files if p.name != 'release_manifest.json'}
    if actual != manifest['files']:
        raise SystemExit('The release files do not match the fixed archive manifest.')
    dest = ROOT / 'dist'
    dest.mkdir(exist_ok=True)
    path = dest / (NAME + '.zip')
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in files:
            info = zipfile.ZipInfo(NAME + '/' + str(source.relative_to(ROOT)), (2026, 10, 6, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    (dest / (NAME + '.zip.sha256')).write_text(checksum + '  ' + path.name + '\n')
    print(path.name, checksum)

if __name__ == '__main__':
    main()
