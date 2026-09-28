"""Explicit checks and artifact binding, independent of the CAD writer."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
import json
import re

from .guard import GuardError, inside, sha256


REQUIRED = {"solid_body_count", "volume", "extents", "feature_errors", "native_units", "driving_dimensions", "fully_constrained_sketches", "cylindrical_geometry", "reopened_native", "step_roundtrip"}


def verdict(checks: dict[str, dict], required: set[str] | None = None) -> dict:
    required = REQUIRED if required is None else required
    missing = sorted(required - set(checks))
    failed = sorted(k for k in required & set(checks) if checks[k].get("status") != "pass")
    return {"automated_validation": "passed" if not missing and not failed else "failed",
            "missing_checks": missing, "failed_checks": failed,
            "engineering_release": "human_review_required"}


def check(passed: bool, **evidence) -> dict:
    return {"status": "pass" if passed else "fail", **evidence}


def unique_cylinders(faces: list[dict]) -> list[dict]:
    """STEP can split a cylindrical face at its seam; compare geometry, not face IDs."""
    result = []
    for face in faces:
        def equivalent(other):
            return (abs(face['diameter_mm']-other['diameter_mm']) < 1e-6
                    and all(abs(a-b)<1e-6 for a,b in zip(face['center_xy_mm'],other['center_xy_mm']))
                    and abs(abs(sum(a*b for a,b in zip(face['axis'],other['axis'])))-1.) < 1e-8)
        if not any(equivalent(other) for other in result):
            result.append(face)
    return result


def file_records(folder: Path, names: list[str]) -> list[dict]:
    result = []
    for name in names:
        path = inside(folder, folder / name)
        if not path.is_file() or path.stat().st_size == 0:
            raise GuardError(f"Missing or empty artifact: {name}")
        result.append({"path": name, "sha256": sha256(path), "bytes": path.stat().st_size})
    return result


def verify_manifest(folder: Path) -> dict:
    folder = folder.resolve()
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("artifacts"), list):
        raise GuardError("Unsupported manifest")
    records = manifest["artifacts"]
    if not records:
        raise GuardError("Manifest has no artifacts")
    checked = []
    seen = set()
    for item in records:
        name = item["path"]
        if not isinstance(name, str) or "\\" in name or ':' in name or '..' in PurePosixPath(name).parts or Path(name).is_absolute() or name.casefold() in seen:
            raise GuardError("Invalid artifact path")
        seen.add(name.casefold())
        path = inside(folder, folder / name)
        digest = item.get("sha256", "")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise GuardError("Invalid artifact digest")
        ok = path.is_file() and path.stat().st_size == item["bytes"] and sha256(path) == digest
        checked.append({"path": name, "matches": ok})
    return {"status": "pass" if all(x["matches"] for x in checked) else "fail",
            "scope": "artifact integrity only; no fresh CAD or engineering validation",
            "artifacts": checked, "recorded_validation": manifest.get("validation")}
