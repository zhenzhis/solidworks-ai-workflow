"""Filesystem and cross-process job boundaries; no CAD imports."""
from __future__ import annotations

from contextlib import AbstractContextManager
from pathlib import Path
import hashlib
import json
import os
import re
import tempfile
import time
import uuid


class GuardError(RuntimeError):
    pass


def job_name(value: str) -> str:
    reserved = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,47}", value) or value in reserved:
        raise GuardError("Use a short lowercase ASCII job name, not a path or device name")
    return value


def inside(root: Path, path: Path) -> Path:
    root = root.resolve()
    path = path.resolve()
    if not path.is_relative_to(root) or path == root:
        raise GuardError("Path escapes the job output directory")
    return path


def sha256(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


class CadLock(AbstractContextManager):
    """One writer across this user's workflow processes, with bounded waiting."""
    def __init__(self, timeout: float = 5, path: Path | None = None):
        self.path = path or Path(tempfile.gettempdir()) / "solidworks-ai-workflow.lock"
        self.timeout = timeout
        self.file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open("a+b")
        if self.path.stat().st_size == 0:
            self.file.write(b"0")
            self.file.flush()
        start = time.monotonic()
        while True:
            try:
                self.file.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.monotonic() - start >= self.timeout:
                    self.file.close()
                    self.file = None
                    raise GuardError("Another CAD job holds the writer lock") from None
                time.sleep(0.05)

    def __exit__(self, *exc):
        if self.file:
            try:
                self.file.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.file, fcntl.LOCK_UN)
            finally:
                self.file.close()
                self.file = None


def stage_job(root: Path, name: str) -> tuple[Path, Path]:
    name = job_name(name)
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    final = inside(root, root / name)
    if final.exists():
        raise GuardError("Job already exists; verify it or choose a new job name")
    staging = inside(root, root / ("." + name + "-" + uuid.uuid4().hex + ".partial"))
    staging.mkdir()
    return staging, final


def publish_job(root: Path, staging: Path, final: Path) -> None:
    staging, final = inside(root, staging), inside(root, final)
    if final.exists() or staging.parent != root.resolve() or final.parent != root.resolve():
        raise GuardError("Unsafe job activation")
    staging.rename(final)
