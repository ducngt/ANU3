from __future__ import annotations

import shutil
import sqlite3
import subprocess
from pathlib import Path

from sqlalchemy.engine import make_url


class BackupError(RuntimeError):
    pass


def _sqlite_path(database_url: str) -> Path:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        raise BackupError("not a SQLite URL")
    if not url.database or url.database == ":memory:":
        raise BackupError("SQLite backup requires a file-backed database")
    return Path(url.database).resolve()


def _libpq_url(database_url: str) -> str:
    rendered = make_url(database_url).render_as_string(hide_password=False)
    return rendered.replace("postgresql+psycopg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")


def backup_database(database_url: str, destination: str | Path) -> dict:
    destination = Path(destination).resolve()
    backend = make_url(database_url).get_backend_name()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if backend == "sqlite":
        source = _sqlite_path(database_url)
        with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
            src.backup(dst)
        return {"backend": "sqlite", "backup_path": str(destination), "status": "PASS"}
    if backend == "postgresql":
        if shutil.which("pg_dump") is None:
            raise BackupError("pg_dump is required for PostgreSQL backup")
        subprocess.run(
            ["pg_dump", "--format=custom", "--no-owner", "--file", str(destination), _libpq_url(database_url)],
            check=True,
            capture_output=True,
            text=True,
        )
        return {"backend": "postgresql", "backup_path": str(destination), "status": "PASS"}
    raise BackupError(f"unsupported backend: {backend}")


def restore_database(backup_path: str | Path, database_url: str) -> dict:
    backup_path = Path(backup_path).resolve()
    backend = make_url(database_url).get_backend_name()
    if backend == "sqlite":
        target = _sqlite_path(database_url)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.unlink()
        with sqlite3.connect(backup_path) as src, sqlite3.connect(target) as dst:
            src.backup(dst)
        return {"backend": "sqlite", "restored_database": str(target), "status": "PASS"}
    if backend == "postgresql":
        if shutil.which("pg_restore") is None:
            raise BackupError("pg_restore is required for PostgreSQL restore")
        subprocess.run(
            ["pg_restore", "--clean", "--if-exists", "--no-owner", "--dbname", _libpq_url(database_url), str(backup_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return {"backend": "postgresql", "restored_database": database_url, "status": "PASS"}
    raise BackupError(f"unsupported backend: {backend}")
