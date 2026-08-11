#!/usr/bin/env python3
"""Stage and verify the PromptBoard v1.1.1 release set.

The release directory is deliberately treated as a generated, local-only
surface.  The source archive is assembled from tracked files so runtime data,
build caches, Store staging and previous release outputs cannot silently enter
the certification set.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath


APP_VERSION = "1.1.1"
APP_NAME = "PromptBoard"
EXE_NAME = f"{APP_NAME}-{APP_VERSION}-win64.exe"
SOURCE_NAME = f"{APP_NAME}-{APP_VERSION}-source.zip"
CHANGELOG_NAME = "CHANGELOG.txt"
MSIX_NAME = f"{APP_NAME}.msix"
HASH_NAME = "SHA256SUMS.txt"
ARCHIVE_ROOT = f"{APP_NAME}-{APP_VERSION}-source"

RELEASE_FILES = (EXE_NAME, SOURCE_NAME, CHANGELOG_NAME, MSIX_NAME)
EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    "build",
    "dist",
    "releases",
    "store_package",
    "__pycache__",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".db", ".db-shm", ".db-wal"}


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def release_dir(root: Path) -> Path:
    return root / "releases" / f"v{APP_VERSION}"


def _tracked_paths(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    paths = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        paths.append(Path(raw.decode("utf-8")))
    return paths


def _archive_allowed(path: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return True


def _archive_members(root: Path) -> list[Path]:
    members = [path for path in _tracked_paths(root) if _archive_allowed(path)]
    if Path("THIRD_PARTY_LICENSES.txt") not in members:
        raise RuntimeError("THIRD_PARTY_LICENSES.txt fehlt im Source-Archiv")
    return sorted(members, key=lambda path: path.as_posix().lower())


def _write_source_archive(root: Path, target: Path) -> int:
    members = _archive_members(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        target,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for relative in members:
            source = root / relative
            if not source.is_file():
                raise RuntimeError(f"Getrackte Datei fehlt: {relative}")
            info = zipfile.ZipInfo(
                f"{ARCHIVE_ROOT}/{PurePosixPath(relative.as_posix())}",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())
    return len(members)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_lines(directory: Path, names: list[str]) -> str:
    return "".join(f"{_sha256(directory / name)}  {name}\n" for name in sorted(names))


def _hash_names(directory: Path) -> list[str]:
    return sorted(
        path.name
        for path in directory.iterdir()
        if path.is_file() and path.name != HASH_NAME and path.name in RELEASE_FILES
    )


def stage(root: Path, *, explicit_exe: Path | None, explicit_msix: Path | None) -> int:
    target = release_dir(root)
    target.mkdir(parents=True, exist_ok=True)

    executable = explicit_exe or (root / "dist" / EXE_NAME)
    executable = executable if executable.is_absolute() else root / executable
    if not executable.is_file():
        raise RuntimeError(f"EXE fehlt: {executable}")
    shutil.copy2(executable, target / EXE_NAME)

    member_count = _write_source_archive(root, target / SOURCE_NAME)
    changelog = root / "CHANGELOG.md"
    if not changelog.is_file():
        raise RuntimeError(f"CHANGELOG fehlt: {changelog}")
    shutil.copy2(changelog, target / CHANGELOG_NAME)

    msix = explicit_msix or (root / "releases" / MSIX_NAME)
    msix = msix if msix.is_absolute() else root / msix
    if msix.is_file() and msix.resolve() != (target / MSIX_NAME).resolve():
        shutil.copy2(msix, target / MSIX_NAME)
    elif not (target / MSIX_NAME).is_file():
        print(f"[!] MSIX fehlt (Store-P1 offen): {msix}")

    duplicate_hashes = sorted(
        path.name
        for path in target.glob("SHA256SUMS*")
        if path.name != HASH_NAME
    )
    if duplicate_hashes:
        raise RuntimeError(
            "Doppelte SHA-Dateien im Release-Verzeichnis; nicht automatisch gelöscht: "
            + ", ".join(duplicate_hashes)
        )

    names = _hash_names(target)
    (target / HASH_NAME).write_text(_hash_lines(target, names), encoding="utf-8")
    print(f"[+] {len(names)} Artefakte gehasht; Source-Archiv enthält {member_count} getrackte Dateien")
    print(f"[+] Release-Verzeichnis: {target}")
    return 0


def _read_hash_file(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise RuntimeError(f"Ungültige SHA-Zeile {path}:{line_number}")
        digest, name = parts
        name = name.strip()
        if name.startswith("*"):
            name = name[1:]
        if name in entries:
            raise RuntimeError(f"Doppelter SHA-Eintrag: {name}")
        entries[name] = digest.lower()
    return entries


def verify(root: Path, *, require_msix: bool) -> int:
    target = release_dir(root)
    sums = target / HASH_NAME
    if not sums.is_file():
        raise RuntimeError(f"SHA-Datei fehlt: {sums}")
    entries = _read_hash_file(sums)
    required = {EXE_NAME, SOURCE_NAME, CHANGELOG_NAME}
    if require_msix:
        required.add(MSIX_NAME)
    missing = sorted(name for name in required if name not in entries or not (target / name).is_file())
    if missing:
        raise RuntimeError("Nicht zertifizierbare Artefakte: " + ", ".join(missing))

    for name, expected in entries.items():
        file_path = target / name
        if not file_path.is_file():
            raise RuntimeError(f"SHA verweist auf fehlende Datei: {name}")
        actual = _sha256(file_path)
        if actual != expected:
            raise RuntimeError(f"SHA mismatch für {name}: {actual} != {expected}")

    archive_path = target / SOURCE_NAME
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if not names or any(
            any(part in EXCLUDED_DIRS for part in PurePosixPath(name).parts)
            or PurePosixPath(name).suffix.lower() in EXCLUDED_SUFFIXES
            for name in names
        ):
            raise RuntimeError("Source-Archiv enthält ausgeschlossene Laufzeit-/Build-Dateien")
        license_name = f"{ARCHIVE_ROOT}/THIRD_PARTY_LICENSES.txt"
        if license_name not in names:
            raise RuntimeError("Source-Archiv enthält kein THIRD_PARTY_LICENSES.txt")

    if MSIX_NAME not in entries:
        print("[!] MSIX nicht in SHA256SUMS.txt; Store-P1/WACK bleibt offen")
    print(f"[+] SHA256 und Source-Archiv geprüft: {len(entries)} Einträge")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    stage_parser = subparsers.add_parser("stage", help="EXE, Source-Archiv, Changelog und SHA256SUMS erzeugen")
    stage_parser.add_argument("--exe", type=Path, help="Pfad zur PyInstaller-EXE")
    stage_parser.add_argument("--msix", type=Path, help="Optionaler Pfad zur MSIX")

    verify_parser = subparsers.add_parser("verify", help="Release-Dateien und Prüfsummen prüfen")
    verify_parser.add_argument("--require-msix", action="store_true", help="MSIX als zwingendes Artefakt verlangen")

    args = parser.parse_args(argv)
    root = project_root()
    try:
        if args.command == "stage":
            return stage(root, explicit_exe=args.exe, explicit_msix=args.msix)
        return verify(root, require_msix=args.require_msix)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
