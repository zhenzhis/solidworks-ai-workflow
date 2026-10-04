"""Small JSON CLI with meaningful failure exit codes."""
import argparse
import json
from pathlib import Path
import sys

from . import service


def main(argv=None):
    parser = argparse.ArgumentParser(prog='sw-workflow')
    parser.add_argument('--root', type=Path, default=Path('artifacts'), help='Owned output directory')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('doctor')
    for name in ('plan', 'build'):
        sub = commands.add_parser(name)
        sub.add_argument('spec', type=Path)
        if name == 'build':
            sub.add_argument('--job', required=True)
    sub = commands.add_parser('verify')
    sub.add_argument('job')
    sub = commands.add_parser('edit')
    sub.add_argument('source_job')
    sub.add_argument('--job', required=True)
    sub.add_argument('--parameters', type=Path, required=True, help='JSON object of changed millimetre parameters')
    sub.add_argument('--expected-state', required=True, help='Source manifest SHA-256 from verify')
    args = parser.parse_args(argv)
    try:
        if args.command == 'doctor':
            result = service.doctor()
        elif args.command in ('plan', 'build'):
            data = json.loads(args.spec.read_text(encoding='utf-8-sig'))
            result = service.plan(data) if args.command=='plan' else service.build(args.root, args.job, data)
        elif args.command == 'verify':
            result = service.verify(args.root, args.job)
        else:
            parameters = json.loads(args.parameters.read_text(encoding='utf-8-sig'))
            result = service.edit(args.root, args.source_job, args.job, parameters, args.expected_state)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 2 if result.get('status') == 'fail' or (args.command == 'doctor' and not result['cad_ready']) else 0
    except Exception as exc:
        print(json.dumps({'status':'error','type':type(exc).__name__,'message':str(exc)},ensure_ascii=False),file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
