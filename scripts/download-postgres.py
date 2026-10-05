"""Fetch official portable PostgreSQL into ignored local runtime storage."""
from pathlib import Path
import hashlib
import zipfile
import httpx

root = Path(__file__).resolve().parent.parent / '.local'
archive_path = root / 'postgresql-17.11-3-windows-x64-binaries.zip'
target = root / 'postgres-runtime'
root.mkdir(exist_ok=True)
url = 'https://get.enterprisedb.com/postgresql/postgresql-17.11-3-windows-x64-binaries.zip'
if not archive_path.exists():
    with httpx.stream('GET', url, follow_redirects=True, timeout=60) as response:
        response.raise_for_status()
        if response.url.host != 'get.enterprisedb.com': raise RuntimeError('Unexpected download host')
        with archive_path.with_suffix('.part').open('wb') as output:
            for chunk in response.iter_bytes(): output.write(chunk)
    archive_path.with_suffix('.part').replace(archive_path)
with zipfile.ZipFile(archive_path) as archive:
    if archive.testzip(): raise RuntimeError('Archive integrity check failed')
    for entry in archive.infolist():
        if not entry.filename.startswith(('pgsql/bin/', 'pgsql/lib/', 'pgsql/share/')): continue
        destination = (target / entry.filename).resolve()
        if not destination.is_relative_to(target.resolve()): raise RuntimeError('Unsafe archive path')
        if entry.is_dir(): destination.mkdir(parents=True, exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, destination.open('wb') as output: output.write(source.read())
digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
(root / 'postgres-download.txt').write_text(f'{url}\nSHA256 downloaded archive: {digest}\n')
print('Official PostgreSQL archive extracted to project-local runtime. No system install.')
