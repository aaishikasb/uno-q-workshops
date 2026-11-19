"""Build the App Lab ZIP and verify every member against its source."""

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def main():
    root = Path(__file__).resolve().parent
    source = root / "workshop-app"
    files = sorted(p for p in source.rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts
                   and p.suffix != ".pyc" and not p.name.startswith("."))
    names = [p.relative_to(source).as_posix() for p in files]
    required = {"app.yaml", "python/main.py", "python/requirements.txt",
                "sketch/sketch.ino", "sketch/sketch.yaml", "python/models/opponent.pte"}
    assert required.issubset(names), "Incomplete App Lab source"
    metadata = json.loads((source / "python/models/metadata.json").read_text())
    assert hashlib.sha256((source / "python/models/opponent.pte").read_bytes()).hexdigest() == metadata["sha256"]
    archive = root / "workshop-app.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as output:
        for path, name in zip(files, names):
            output.write(path, name)
    with ZipFile(archive) as check:
        assert check.namelist() == names
        assert check.testzip() is None
        assert all(check.read(name) == path.read_bytes() for path, name in zip(files, names))
    print(f"Packaged and verified {len(files)} files: {archive.name}")


if __name__ == "__main__":
    main()
