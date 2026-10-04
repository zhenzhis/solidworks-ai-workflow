"""Real stdio installation probe; live CAD is an explicit opt-in."""
from __future__ import annotations

from pathlib import Path
import os
import sys

from jsonschema import Draft202012Validator
from mcp import Client, StdioServerParameters

from . import __version__

TOOLS = {'workflow_doctor', 'workflow_plan', 'workflow_build', 'workflow_edit', 'workflow_verify'}


async def probe(root: Path, *, live=False, mode='auto', python=None) -> dict:
    env = {'SW_WORKFLOW_OUTPUT': str(root.resolve()), 'PYTHONUTF8': '1'}
    for key in ('SW_WORKFLOW_PART_TEMPLATE', 'SW_WORKFLOW_DRAWING_TEMPLATE'):
        if key in os.environ:
            env[key] = os.environ[key]
    params = StdioServerParameters(command=str(python or sys.executable),
        args=['-X', 'utf8', '-B', '-m', 'sw_workflow.mcp_server'], env=env)
    async with Client(params, mode=mode, read_timeout_seconds=300 if live else 30) as client:
        listing = await client.list_tools()
        tools = {t.name: t for t in listing.tools}
        if set(tools) != TOOLS:
            raise RuntimeError('Unexpected MCP tool surface')
        if client.server_info is None or client.server_info.version != __version__:
            raise RuntimeError('MCP server version does not match installer')
        for name, tool in tools.items():
            Draft202012Validator.check_schema(tool.input_schema)
            if tool.output_schema is None:
                raise RuntimeError('Missing MCP output schema: ' + name)
            Draft202012Validator.check_schema(tool.output_schema)
            expected_read = name not in {'workflow_build', 'workflow_edit'}
            if tool.annotations is None or tool.annotations.read_only_hint != expected_read:
                raise RuntimeError('Incorrect tool annotation: ' + name)

        async def checked(name, args):
            Draft202012Validator(tools[name].input_schema).validate(args)
            result = await client.call_tool(name, args)
            if result.is_error or result.structured_content is None:
                raise RuntimeError(f'{name} failed: {result.content}')
            Draft202012Validator(tools[name].output_schema).validate(result.structured_content)
            return result.structured_content

        planned = await checked('workflow_plan', {'spec': {'template': 'bushing'}})
        if planned.get('spec', {}).get('template') != 'bushing':
            raise RuntimeError('MCP plan content is incorrect')
        for name, args in (
            ('workflow_plan', {'spec': {'template': 'plate', 'parameters': {'thickness': -1}}}),
            ('workflow_verify', {'job': '../private'}),
        ):
            bad = await client.call_tool(name, args)
            if not bad.is_error:
                raise RuntimeError('MCP failure did not set isError: ' + name)
        report = {'status': 'passed', 'protocol': client.protocol_version, 'server_version': __version__,
                  'tools': sorted(tools), 'schemas': 'passed', 'error_flags': 'passed', 'cad': 'not_run'}
        if live:
            built = await checked('workflow_build', {'job': 'install-smoke', 'spec': {'template': 'bushing'}})
            verified = await checked('workflow_verify', {'job': 'install-smoke'})
            if verified.get('status') != 'pass' or built.get('validation', {}).get('automated_validation') != 'passed':
                raise RuntimeError('Native smoke acceptance or artifact integrity failed')
            report.update(cad='passed', manifest_sha256=verified['manifest_sha256'],
                          job_directory=str(root.resolve() / 'install-smoke'))
        return report
