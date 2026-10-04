"""Validate before activating project configuration. No global configuration writes."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import uuid

from configure import configure, prepare, safe_path
from sw_workflow import __version__, service
from sw_workflow.guard import write_json
from sw_workflow.probe import probe


def error_text(exc):
    if isinstance(exc, BaseExceptionGroup):
        return '; '.join(error_text(item) for item in exc.exceptions)
    return f'{type(exc).__name__}: {exc}'


def install(root, python, *, verify_cad=False, with_docs=False):
    root = Path(root).resolve()
    report_path = safe_path(root, '.local/install-report.json')
    report = {'schema_version': 1, 'workflow_version': __version__, 'status': 'failed',
              'tested_utc': datetime.now(timezone.utc).isoformat(), 'cad': 'not_run',
              'host_activation': 'open_and_trust_project_required'}
    try:
        prepare(root, python, with_docs)
        commit = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True)
        report['commit'] = commit.stdout.strip() if commit.returncode == 0 else None
        state = subprocess.run(['git', '-C', str(root), 'status', '--porcelain'], capture_output=True, text=True)
        report['checkout_dirty'] = bool(state.stdout.strip()) if state.returncode == 0 else None
        report['environment'] = service.doctor()
        if not report['environment']['cad_ready']:
            raise RuntimeError('CAD environment unavailable. Check Windows, licensed SolidWorks registration and the cad dependencies in this project environment.')
        output = safe_path(root, '.local/install-checks/' + uuid.uuid4().hex)
        report['mcp'] = asyncio.run(probe(output, live=verify_cad, python=python))
        report['configuration'] = str(configure(root, python, with_docs))
        report['cad'] = report['mcp']['cad']
        report['status'] = 'cad_smoke_passed' if verify_cad else 'configured'
    except Exception as exc:
        report['error'] = error_text(exc)
    write_json(report_path, report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-cad', action='store_true')
    parser.add_argument('--with-docs', action='store_true')
    args = parser.parse_args()
    report = install(Path(__file__).resolve().parents[1], sys.executable,
                     verify_cad=args.verify_cad, with_docs=args.with_docs)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report['status'] == 'failed' else 0


if __name__ == '__main__':
    sys.exit(main())
