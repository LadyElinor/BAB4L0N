#!/usr/bin/env python3
"""Verify and build a source-only ZIP, excluding databases and local metadata."""
from pathlib import Path
import hashlib
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ("README.md", "NOTICE.md", "pyproject.toml", ".gitignore")
DIRECTORIES = ("babalon", "docs", "examples", "scripts", "tests", ".github", "reports")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/package.py OUTPUT.zip")
    output = Path(sys.argv[1]).resolve()
    if output.exists():
        raise SystemExit("refusing to overwrite existing archive")
    subprocess.run([sys.executable, "scripts/verify.py"], cwd=ROOT, check=True)
    files = [ROOT / name for name in FILES]
    for directory in DIRECTORIES:
        files.extend(path for path in (ROOT / directory).rglob("*")
                     if path.is_file() and "__pycache__" not in path.parts
                     and path.suffix not in (".pyc", ".pyo", ".sqlite"))
    files = sorted(files)
    prefix = "babalon-0.1.0/"
    manifest = "".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT).as_posix()}\n"
                       for path in files)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, prefix + path.relative_to(ROOT).as_posix())
        archive.writestr(prefix + "SHA256SUMS", manifest)
    print(output)
    print("SHA256", hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
