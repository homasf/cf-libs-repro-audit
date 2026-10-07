#!/usr/bin/env python3
"""Create a deterministic Code S2/Data S2 archive of this package."""
from pathlib import Path
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parent


def main():
    version = (ROOT / 'VERSION').read_text().strip()
    name = 'CF_LIBS_Published_Records_CodeS2_DataS2_v' + version
    excluded = {'dist', '__pycache__', '.git', '.pytest_cache'}
    files = sorted(p for p in ROOT.rglob('*') if p.is_file()
                   and not excluded.intersection(p.relative_to(ROOT).parts)
                   and p.suffix != '.pyc')
    dest = ROOT / 'dist'
    dest.mkdir(exist_ok=True)
    path = dest / (name + '.zip')
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for source in files:
            info = zipfile.ZipInfo(name + '/' + source.relative_to(ROOT).as_posix(),
                                   (2026, 10, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes(),
                             compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_suffix('.zip.sha256').write_text(checksum + '  ' + path.name + '\n')
    print(path.name, checksum)


if __name__ == '__main__':
    main()
