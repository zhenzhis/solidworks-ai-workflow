"""Shared CLI/MCP job API. Pure plan/verify never start SolidWorks."""
from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime, timezone
from importlib import metadata, util
from pathlib import Path
import json
import os
import platform
import re
import shutil
import sys
import time

from . import __version__
from .evidence import REQUIRED, file_records, verdict, verify_manifest
from .guard import CadLock, GuardError, inside, job_name, publish_job, sha256, stage_job, write_json
from .spec import PartSpec


def doctor() -> dict:
    missing = [name for name in ('pythoncom', 'win32com', 'comtypes') if util.find_spec(name) is None]
    installation = {"installed": False, "registered": False}
    if os.name == 'nt':
        from ._vendor.cad_installation import discover_installation
        installation = discover_installation('solidworks')
    return {"workflow_version": __version__, "python": platform.python_version(), "platform": platform.system(),
            "missing_cad_modules": missing, "solidworks": installation,
            "cad_ready": os.name == 'nt' and not missing and installation['installed'] and installation['registered'],
            "scope": "installation discovery only; CAD was not connected or modified"}


def plan(data: dict) -> dict:
    spec = PartSpec.parse(data)
    return {"spec": spec.to_dict(), "spec_sha256": spec.fingerprint,
            "expected": {"solid_bodies": 1, "volume_mm3": spec.volume_mm3, "extents_mm": spec.extents_mm},
            "engineering_release": "human_review_required"}


def _preflight():
    result = doctor()
    if not result['cad_ready']:
        raise GuardError("CAD is unavailable; run sw-workflow doctor and install the cad extra in this environment")
    return result


def _runtime():
    packages = {}
    for name in ('pywin32', 'comtypes', 'mcp'):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            pass
    return {"workflow": __version__, "python": platform.python_version(), "dependencies": packages}


def _load_source(source, expected_state, spec=None):
    manifest_path=source/'manifest.json'
    if sha256(manifest_path)!=expected_state:
        raise GuardError('Source state changed; inspect and supply the current manifest SHA-256')
    if verify_manifest(source)['status']!='pass':
        raise GuardError('Source artifact integrity failed')
    old=json.loads(manifest_path.read_text(encoding='utf-8'))
    original=PartSpec.parse(old['spec'])
    if original.fingerprint!=old['spec_sha256'] or (spec is not None and spec.template!=original.template):
        raise GuardError('Source specification binding failed')
    if old.get('validation',{}).get('automated_validation')!='passed':
        raise GuardError('Source job was not accepted')
    native=inside(source,source/old['native_file'])
    if native.suffix.lower()!='.sldprt' or native.name not in {r['path'] for r in old['artifacts']}:
        raise GuardError('Source native file is not bound to the manifest')
    return old,original,native


def _execute(root: Path, name: str, spec: PartSpec, source: Path | None = None, expected_state: str | None = None) -> dict:
    name = job_name(name)
    _preflight()
    with CadLock(), redirect_stdout(sys.stderr):
        # Imports may log discovery; stdout must remain clean for MCP framing.
        from .cad import Session, TemplateBuilder, finish_part, update_globals
        staging, final = stage_job(root, name)
        started = time.monotonic()
        created = datetime.now(timezone.utc).isoformat()
        parent = None
        try:
            if source is not None:
                old,_,native=_load_source(source,expected_state,spec)
            with Session() as session:
                if source is None:
                    model = session.new()
                    session.expect(model)
                    contract = TemplateBuilder(model, spec, staging/(name+'.SLDPRT')).build()
                else:
                    contract = old['native_contract']
                    # Copy-on-write: never edit the prior accepted artifact.
                    target = staging/(name+'.SLDPRT')
                    shutil.copyfile(native, target)
                    model = session.open(target)
                    session.expect(model, target)
                    config = str(model.ConfigurationManager.ActiveConfiguration.Name)
                    if config != old['configuration']:
                        raise GuardError("Source active configuration changed")
                    update_globals(model, spec)
                    parent = {"job": old['job'], "manifest_sha256": expected_state}
                configuration = str(model.ConfigurationManager.ActiveConfiguration.Name)
                checks, files = finish_part(session, model, staging, name, spec, contract)
                sw_version = session.version
            validation = verdict(checks)
            if validation['automated_validation'] != 'passed':
                write_json(staging/'failed-checks.json',checks)
                raise GuardError("Native acceptance failed: " + ', '.join(validation['failed_checks'] + validation['missing_checks']))
            # Model/drawing references are created at their final location. The
            # acceptance manifest is the commit marker, written only at the end.
            publish_job(root, staging, final)
            if spec.drawing:
                from .drawing import create_review_drawing
                drawing_check,drawing_files=create_review_drawing(final,name,spec)
                checks['review_drawing']=drawing_check
                files.extend(drawing_files)
                validation=verdict(checks,REQUIRED|{'review_drawing'})
                if validation['automated_validation']!='passed':
                    write_json(final/'failed-checks.json',checks)
                    raise GuardError('Review drawing acceptance failed')
            report = {"schema_version": 1, "job": name, "created_utc": created,
                      "runtime": _runtime(), "solidworks": sw_version,
                      "elapsed_seconds": round(time.monotonic()-started, 3),
                      "spec": spec.to_dict(), "spec_sha256": spec.fingerprint,
                      "parent": parent, "native_file": name+'.SLDPRT', "configuration": configuration,
                      "native_contract": contract, "checks": checks, "validation": validation,
                      "artifacts": file_records(final, files)}
            write_json(final/'manifest.json', report)
            return {"job": name, "folder": str(final), "manifest_sha256": sha256(final/'manifest.json'),
                    "validation": validation, "elapsed_seconds": report['elapsed_seconds']}
        except BaseException as exc:
            # Checkpoints stay recoverable, but a failed job is never presented as accepted.
            recovery = staging if staging.exists() else final
            if recovery.exists():
                write_json(recovery/'failure.json', {"status": "failed", "error_type": type(exc).__name__,
                                                  "message": str(exc), "job": name})
            raise


def build(root: Path, name: str, data: dict) -> dict:
    return _execute(root.resolve(), name, PartSpec.parse(data))


def edit(root: Path, source_job: str, name: str, parameters: dict, expected_state: str) -> dict:
    root = root.resolve()
    source = inside(root, root/job_name(source_job))
    if not isinstance(expected_state, str) or not re.fullmatch(r'[0-9a-f]{64}',expected_state):
        raise GuardError("An expected manifest SHA-256 is required")
    _,original,_=_load_source(source,expected_state)
    spec = original.changed(parameters)
    return _execute(root, name, spec, source, expected_state)


def verify(root: Path, name: str) -> dict:
    folder = inside(root.resolve(), root.resolve()/job_name(name))
    result = verify_manifest(folder)
    result['manifest_sha256'] = sha256(folder/'manifest.json')
    return result
